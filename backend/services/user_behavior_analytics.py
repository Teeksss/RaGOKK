# Last reviewed: 2025-04-29 12:43:06 UTC (User: TeeksssKullanıcı Davranışları İzleme)
import asyncio
import time
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from collections import Counter, defaultdict

from ..db.session import SessionLocal
from ..repositories.document_repository import DocumentRepository
from ..repositories.user_repository import UserRepository
from ..repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)

class UserEvent:
    """Kullanıcı olay türleri"""
    VIEW_DOCUMENT = "view_document"
    EDIT_DOCUMENT = "edit_document"
    SHARE_DOCUMENT = "share_document"
    SEARCH = "search"
    CREATE_DOCUMENT = "create_document"
    DELETE_DOCUMENT = "delete_document"
    TAG_DOCUMENT = "tag_document"
    DOWNLOAD_DOCUMENT = "download_document"
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"


class UserBehaviorAnalytics:
    """
    Kullanıcı davranışlarını analiz eden servis.
    
    Özellikler:
    - Kullanıcı eylemlerini takip eder
    - Kullanıcı ilgi alanları ve tercihlerini çıkarır
    - Etiket bazlı ve içerik bazlı öneri sistemini destekler
    - Zaman içinde kullanıcı davranışlarındaki değişimleri tespit eder
    - İlgililik skorları ile dokümanları kişiselleştirebilir
    - Ortak çalışma örüntülerini belirler
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Args:
            db: Veritabanı oturumu (opsiyonel)
        """
        self.db = db
        self.document_repo = DocumentRepository()
        self.user_repo = UserRepository()
        self.analytics_repo = AnalyticsRepository()
        
        # İlgi alanları önbelleği
        self._user_interests_cache = {}
        self._user_interests_timestamp = {}
        self._cache_ttl = 300  # 5 dakika
        
        # Aktif kullanıcılar ve güncel oturumlar
        self._active_users = set()
        
        # Önbelleğe alınmış doküman vektörleri
        self._document_embedding_cache = {}
        
        # Kullanıcı davranışları için toplu işleme kuyruğu
        self._event_queue = []
        self._queue_lock = asyncio.Lock()
        self._processing_task = None
    
    async def start(self):
        """Analitik servisini başlatır"""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_events_periodically())
            logger.info("User behavior analytics service started")
    
    async def stop(self):
        """Analitik servisini durdurur"""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            
            # Kuyruktaki olayları işle
            await self._process_event_queue()
            
            logger.info("User behavior analytics service stopped")
    
    async def track_event(self, user_id: str, event_type: str, properties: Dict[str, Any] = None):
        """
        Kullanıcı olayını kaydeder
        
        Args:
            user_id: Kullanıcı ID'si
            event_type: Olay türü
            properties: Olay özellikleri
        """
        if user_id == "anonymous":
            return
        
        event = {
            "user_id": user_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "properties": properties or {}
        }
        
        # Kuyruk için mutex kilidi al
        async with self._queue_lock:
            self._event_queue.append(event)
        
        # Aktif kullanıcı olarak işaretle
        if event_type != UserEvent.LOGOUT:
            self._active_users.add(user_id)
        else:
            self._active_users.discard(user_id)
    
    async def _process_events_periodically(self):
        """Olayları periyodik olarak işler (arka plan görevi)"""
        try:
            while True:
                # Her 30 saniyede bir işle
                await asyncio.sleep(30)
                await self._process_event_queue()
                
        except asyncio.CancelledError:
            logger.info("Event processing task cancelled")
            raise
    
    async def _process_event_queue(self):
        """Kuyruktaki olayları toplu olarak işler"""
        async with self._queue_lock:
            events = self._event_queue.copy()
            self._event_queue.clear()
        
        if not events:
            return
        
        # Veritabanı bağlantısı
        async with SessionLocal() as db:
            try:
                # Olayları toplu olarak kaydet
                await self.analytics_repo.bulk_insert_events(db, events)
                await db.commit()
                
                # Etkilenen kullanıcıların önbelleklerini temizle
                affected_users = {event["user_id"] for event in events}
                for user_id in affected_users:
                    self._clear_user_cache(user_id)
                
                logger.info(f"Processed {len(events)} user events")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error processing events: {e}")
                
                # Olayları tekrar kuyruğa ekle
                async with self._queue_lock:
                    self._event_queue.extend(events)
    
    def _clear_user_cache(self, user_id: str):
        """
        Kullanıcının önbelleklenmiş bilgilerini temizler
        
        Args:
            user_id: Kullanıcı ID'si
        """
        if user_id in self._user_interests_cache:
            del self._user_interests_cache[user_id]
        
        if user_id in self._user_interests_timestamp:
            del self._user_interests_timestamp[user_id]
    
    async def get_user_interests(self, user_id: str, max_age: int = 30) -> Dict[str, float]:
        """
        Kullanıcının ilgi alanlarını getirir
        
        Args:
            user_id: Kullanıcı ID'si
            max_age: İlgi alanları için maksimum geçerlilik (gün)
            
        Returns:
            Dict[str, float]: İlgi alanları ve puanları
        """
        # Önbellekten getir
        if user_id in self._user_interests_cache:
            cache_time = self._user_interests_timestamp.get(user_id, 0)
            if time.time() - cache_time < self._cache_ttl:
                return self._user_interests_cache[user_id]
        
        # Veritabanından getir
        async with SessionLocal() as db:
            try:
                # Son 30 günde görüntülenen dokümanların etiketlerini analiz et
                since_date = datetime.utcnow() - timedelta(days=max_age)
                
                # Görüntüleme olaylarını getir
                view_events = await self.analytics_repo.get_user_events(
                    db,
                    user_id=user_id,
                    event_type=UserEvent.VIEW_DOCUMENT,
                    since=since_date
                )
                
                # Görüntülenen dokümanların ID'lerini topla
                document_ids = [
                    event["properties"].get("document_id") 
                    for event in view_events 
                    if "document_id" in event["properties"]
                ]
                
                if not document_ids:
                    return {}
                
                # Doküman etiketlerini getir
                tags_by_document = await self.document_repo.get_tags_for_documents(
                    db,
                    document_ids=document_ids
                )
                
                # Etiket sayımları
                tag_counts = Counter()
                document_counts = {}
                
                # Her doküman için
                for doc_id, tags in tags_by_document.items():
                    # Kaç kez görüntülenmiş?
                    doc_count = sum(1 for event in view_events 
                                   if event["properties"].get("document_id") == doc_id)
                    document_counts[doc_id] = doc_count
                    
                    # Her etiket için puan ekle
                    for tag in tags:
                        tag_counts[tag] += doc_count
                
                # Toplam görüntüleme
                total_views = sum(document_counts.values())
                
                # İlgi skoru hesapla (görüntülemeye göre normalize)
                interests = {}
                if total_views > 0:
                    for tag, count in tag_counts.items():
                        interests[tag] = count / total_views
                
                # Önbelleğe al
                self._user_interests_cache[user_id] = interests
                self._user_interests_timestamp[user_id] = time.time()
                
                return interests
                
            except Exception as e:
                logger.error(f"Error getting user interests: {e}")
                return {}
    
    async def get_trending_topics(self, days: int = 7, min_count: int = 2) -> List[Dict[str, Any]]:
        """
        Son günlerdeki popüler konuları getirir
        
        Args:
            days: Kaç gün geriye gidileceği
            min_count: Minimum görüntüleme sayısı
            
        Returns:
            List[Dict[str, Any]]: Popüler konular ve etiketler
        """
        async with SessionLocal() as db:
            try:
                # Son günlerdeki görüntüleme olaylarını getir
                since_date = datetime.utcnow() - timedelta(days=days)
                
                # Görüntüleme olaylarını getir
                view_events = await self.analytics_repo.get_events_by_type(
                    db,
                    event_type=UserEvent.VIEW_DOCUMENT,
                    since=since_date
                )
                
                # Görüntülenen dokümanların ID'lerini topla
                document_counts = Counter()
                for event in view_events:
                    doc_id = event["properties"].get("document_id")
                    if doc_id:
                        document_counts[doc_id] += 1
                
                # En çok görüntülenen dokümanları filtrele
                popular_docs = [doc_id for doc_id, count in document_counts.items() if count >= min_count]
                
                if not popular_docs:
                    return []
                
                # Doküman etiketlerini getir
                tags_by_document = await self.document_repo.get_tags_for_documents(
                    db,
                    document_ids=popular_docs
                )
                
                # Etiketleri görüntüleme sayılarına göre ağırlıklandır
                tag_scores = defaultdict(float)
                
                for doc_id, tags in tags_by_document.items():
                    doc_count = document_counts[doc_id]
                    for tag in tags:
                        tag_scores[tag] += doc_count
                
                # Puanlara göre sırala
                trending_tags = [
                    {"tag": tag, "score": score, "count": int(score)}
                    for tag, score in tag_scores.items()
                ]
                
                trending_tags.sort(key=lambda x: x["score"], reverse=True)
                
                return trending_tags[:20]  # En popüler 20 etiket
                
            except Exception as e:
                logger.error(f"Error getting trending topics: {e}")
                return []
    
    async def get_document_recommendations(
        self, 
        user_id: str, 
        count: int = 10,
        include_collaborative: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcı için doküman önerileri getirir
        
        Args:
            user_id: Kullanıcı ID'si
            count: Önerilecek doküman sayısı
            include_collaborative: İşbirlikçi filtreleme kullan
            
        Returns:
            List[Dict[str, Any]]: Önerilen dokümanlar ve skorları
        """
        # Kullanıcı ilgi alanlarını al
        user_interests = await self.get_user_interests(user_id)
        
        if not user_interests:
            # İlgi alanı yoksa, popüler dokümanları öner
            return await self._get_popular_documents(count)
        
        async with SessionLocal() as db:
            try:
                # Kullanıcının görüntülediği dokümanları al
                viewed_documents = await self._get_user_viewed_documents(db, user_id)
                
                # İçerik temelli öneriler
                content_based_docs = await self._get_content_based_recommendations(
                    db,
                    user_interests,
                    viewed_documents,
                    count=int(count * 0.7)  # %70 içerik temelli
                )
                
                # İşbirlikçi filtreleme bazlı öneriler
                collaborative_docs = []
                if include_collaborative:
                    collaborative_docs = await self._get_collaborative_recommendations(
                        db,
                        user_id,
                        viewed_documents,
                        count=int(count * 0.3)  # %30 işbirlikçi
                    )
                
                # Sonuçları birleştir
                all_recommendations = content_based_docs + collaborative_docs
                
                # Doküman ID'lerine göre benzersizleştir
                seen_ids = set()
                unique_recommendations = []
                
                for rec in all_recommendations:
                    doc_id = rec["document_id"]
                    if doc_id not in seen_ids and doc_id not in viewed_documents:
                        seen_ids.add(doc_id)
                        unique_recommendations.append(rec)
                
                # Skora göre sırala
                unique_recommendations.sort(key=lambda x: x["score"], reverse=True)
                
                # Doküman detayları
                result = await self._enrich_document_recommendations(db, unique_recommendations[:count])
                
                return result
                
            except Exception as e:
                logger.error(f"Error getting document recommendations: {e}")
                return []
    
    async def _get_popular_documents(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Popüler dokümanları getirir
        
        Args:
            count: Doküman sayısı
            
        Returns:
            List[Dict[str, Any]]: Popüler dokümanlar
        """
        async with SessionLocal() as db:
            try:
                # Son 30 günde en çok görüntülenen dokümanlar
                popular_docs = await self.document_repo.get_popular_documents(db, limit=count)
                
                result = []
                for doc in popular_docs:
                    result.append({
                        "document_id": doc["id"],
                        "title": doc["title"],
                        "source_type": doc["source_type"],
                        "view_count": doc["view_count"],
                        "score": doc["view_count"] / 100,  # Normalize edilmiş skor
                        "recommendation_type": "trending"
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Error getting popular documents: {e}")
                return []
    
    async def _get_user_viewed_documents(self, db: AsyncSession, user_id: str) -> Set[int]:
        """
        Kullanıcının görüntülediği dokümanları getirir
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID'si
            
        Returns:
            Set[int]: Görüntülenen doküman ID'leri
        """
        # Son 90 günde görüntülenen dokümanlar
        since_date = datetime.utcnow() - timedelta(days=90)
        
        # Görüntüleme olaylarını getir
        view_events = await self.analytics_repo.get_user_events(
            db,
            user_id=user_id,
            event_type=UserEvent.VIEW_DOCUMENT,
            since=since_date
        )
        
        # Doküman ID'lerini çıkar
        document_ids = set()
        for event in view_events:
            doc_id = event["properties"].get("document_id")
            if doc_id:
                document_ids.add(int(doc_id))
        
        return document_ids
    
    async def _get_content_based_recommendations(
        self, 
        db: AsyncSession,
        user_interests: Dict[str, float],
        viewed_documents: Set[int],
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        İçerik temelli doküman önerileri
        
        Args:
            db: Veritabanı oturumu
            user_interests: Kullanıcı ilgi alanları
            viewed_documents: Görüntülenen doküman ID'leri
            count: Önerilecek doküman sayısı
            
        Returns:
            List[Dict[str, Any]]: Önerilen dokümanlar
        """
        if not user_interests:
            return []
        
        try:
            # En önemli 5 etiketi al
            top_tags = sorted(user_interests.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Etiketlere sahip dokümanları getir
            tag_names = [tag for tag, _ in top_tags]
            tag_weights = {tag: weight for tag, weight in top_tags}
            
            # Etiketlerle doküman ara
            matching_docs = await self.document_repo.find_documents_by_tags(db, tag_names, limit=50)
            
            # Doküman skorlarını hesapla
            scored_docs = []
            for doc in matching_docs:
                if doc["id"] in viewed_documents:
                    continue  # Zaten görüntülenmiş, atla
                
                # Doküman etiketleri
                doc_tags = doc.get("tags", [])
                
                # Etiketlere dayalı ilgililik skoru
                score = 0.0
                for tag in doc_tags:
                    if tag in tag_weights:
                        score += tag_weights[tag]
                
                # Skoru normalize et
                if doc_tags:
                    score /= len(doc_tags)
                
                # Öneriye ekle
                scored_docs.append({
                    "document_id": doc["id"],
                    "score": float(score),
                    "recommendation_type": "content_based"
                })
            
            # Skora göre sırala
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            
            return scored_docs[:count]
            
        except Exception as e:
            logger.error(f"Error getting content-based recommendations: {e}")
            return []
    
    async def _get_collaborative_recommendations(
        self, 
        db: AsyncSession,
        user_id: str,
        viewed_documents: Set[int],
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        İşbirlikçi filtreleme bazlı doküman önerileri
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID'si
            viewed_documents: Görüntülenen doküman ID'leri
            count: Önerilecek doküman sayısı
            
        Returns:
            List[Dict[str, Any]]: Önerilen dokümanlar
        """
        try:
            # Benzer kullanıcıları bul
            similar_users = await self._find_similar_users(db, user_id)
            
            if not similar_users:
                return []
            
            # Benzer kullanıcıların görüntülediği dokümanları getir
            similar_user_ids = [user["user_id"] for user in similar_users]
            
            # Olay sorgusunu oluştur
            query = """
            SELECT properties->>'document_id' as document_id, COUNT(*) as view_count
            FROM user_events
            WHERE event_type = 'view_document'
                AND user_id = ANY(:user_ids)
                AND properties->>'document_id' IS NOT NULL
                AND created_at > NOW() - INTERVAL '90 days'
            GROUP BY document_id
            ORDER BY view_count DESC
            LIMIT 50
            """
            
            result = await db.execute(text(query), {"user_ids": similar_user_ids})
            rows = result.fetchall()
            
            # Doküman skorlarını hesapla
            scored_docs = []
            for row in rows:
                doc_id = int(row.document_id)
                
                if doc_id in viewed_documents:
                    continue  # Zaten görüntülenmiş, atla
                
                # Görüntüleme sayısına göre skor
                score = 0.5 + min(row.view_count / 10, 0.5)  # 0.5 - 1.0 arası skor
                
                # Öneriye ekle
                scored_docs.append({
                    "document_id": doc_id,
                    "score": float(score),
                    "recommendation_type": "collaborative"
                })
            
            # Skora göre sırala
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            
            return scored_docs[:count]
            
        except Exception as e:
            logger.error(f"Error getting collaborative recommendations: {e}")
            return []
    
    async def _find_similar_users(
        self, 
        db: AsyncSession,
        user_id: str,
        min_similarity: float = 0.2,
        max_users: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Benzer kullanıcıları bulur
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID'si
            min_similarity: Minimum benzerlik skoru
            max_users: Maksimum kullanıcı sayısı
            
        Returns:
            List[Dict[str, Any]]: Benzer kullanıcılar
        """
        try:
            # Kullanıcının görüntülediği dokümanları getir
            user_docs = await self._get_user_viewed_documents(db, user_id)
            
            if not user_docs:
                return []
            
            # Son 30 günde doküman görüntüleyen diğer kullanıcıları bul
            query = """
            SELECT DISTINCT user_id
            FROM user_events
            WHERE event_type = 'view_document'
                AND user_id != :user_id
                AND created_at > NOW() - INTERVAL '30 days'
            """
            
            result = await db.execute(text(query), {"user_id": user_id})
            other_users = [row.user_id for row in result.fetchall()]
            
            # Her kullanıcı için benzerlik skoru hesapla
            similar_users = []
            
            for other_id in other_users:
                # Diğer kullanıcının dokümanları
                other_docs = await self._get_user_viewed_documents(db, other_id)
                
                if not other_docs:
                    continue
                
                # Jaccard benzerliği: kesişim / birleşim
                intersection = len(user_docs.intersection(other_docs))
                union = len(user_docs.union(other_docs))
                
                if union > 0:
                    similarity = intersection / union
                    
                    if similarity >= min_similarity:
                        similar_users.append({
                            "user_id": other_id,
                            "similarity": similarity
                        })
            
            # Benzerliğe göre sırala
            similar_users.sort(key=lambda x: x["similarity"], reverse=True)
            
            return similar_users[:max_users]
            
        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []
    
    async def _enrich_document_recommendations(
        self, 
        db: AsyncSession,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Doküman önerilerine detay ekler
        
        Args:
            db: Veritabanı oturumu
            recommendations: Doküman önerileri
            
        Returns:
            List[Dict[str, Any]]: Detaylı öneriler
        """
        if not recommendations:
            return []
        
        try:
            # Doküman ID'lerini al
            doc_ids = [rec["document_id"] for rec in recommendations]
            
            # Dokümanları getir
            docs = await self.document_repo.get_documents_by_ids(db, doc_ids)
            
            # Doküman detaylarını ekle
            result = []
            docs_dict = {doc["id"]: doc for doc in docs}
            
            for rec in recommendations:
                doc_id = rec["document_id"]
                if doc_id in docs_dict:
                    doc = docs_dict[doc_id]
                    
                    result.append({
                        "document_id": doc_id,
                        "title": doc["title"],
                        "source_type": doc["source_type"],
                        "is_public": doc["is_public"],
                        "created_at": doc["created_at"],
                        "updated_at": doc["updated_at"],
                        "owner_id": doc["owner_id"],
                        "score": rec["score"],
                        "recommendation_type": rec["recommendation_type"],
                        "tags": doc.get("tags", [])
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching document recommendations: {e}")
            return recommendations  # Detaylar eklenemezse orijinali döndür