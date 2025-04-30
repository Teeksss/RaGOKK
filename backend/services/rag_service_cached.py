# Last reviewed: 2025-04-29 14:43:27 UTC (User: Teeksss)
# RAG servisi için cache desteği ekleme

import logging
from typing import Dict, Any, List, Optional, Union, Set, Tuple
import uuid
from datetime import datetime
import json
import hashlib

from ..config import settings
from ..schemas.rag import RAGResponse, RAGSource, RAGQuery
from .cache_service import CacheService
from .rag_service import RAGService

logger = logging.getLogger(__name__)

class CachedRAGService(RAGService):
    """
    Önbellekli RAG (Retrieval Augmented Generation) servisi
    
    Temel RAGService'i genişleterek önbellek desteği ekler.
    Tekrarlanan sorguların hızlı yanıtlanmasını sağlar.
    """
    
    def __init__(self):
        """Önbellekli RAG servisi başlat"""
        super().__init__()
        
        # Cache servisi
        self.cache = CacheService[RAGResponse](
            prefix="rag", 
            default_ttl=settings.RAG_CACHE_TTL or 3600
        )
        
        # Önbellek stratejisi ayarları
        self.use_cache = settings.RAG_CACHE_ENABLED
        self.exact_match_ttl = settings.RAG_EXACT_CACHE_TTL or 7200  # 2 saat
        self.similar_match_ttl = settings.RAG_SIMILAR_CACHE_TTL or 3600  # 1 saat
        self.exact_match_threshold = 0.95  # Tam eşleşme eşiği
        self.similar_match_threshold = 0.80  # Benzer eşleşme eşiği
        
        # Sorgu kümeleme için vektör önbelleği
        self.query_vector_cache = {}
    
    def _get_cache_key(self, query: RAGQuery, user_id: str) -> str:
        """
        Önbellek anahtarı oluştur
        
        Args:
            query: Sorgu bilgileri
            user_id: Kullanıcı kimliği
            
        Returns:
            str: Önbellek anahtarı
        """
        # Sorgudaki hassas alanlar hariç parametreleri dahil et
        key_parts = {
            "question": query.question,
            "search_type": query.search_type,
            "prompt_template_id": query.prompt_template_id,
            "max_results": query.max_results,
            "user_id": user_id
        }
        
        # Anahtar oluştur (JSON serileştirme ve hash)
        key_str = json.dumps(key_parts, sort_keys=True)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _normalize_question(self, question: str) -> str:
        """
        Sorguyu normalize et
        
        Args:
            question: Orijinal soru
            
        Returns:
            str: Normalize edilmiş soru
        """
        # Küçük harf, boşluk normalizasyonu
        normalized = question.lower().strip()
        
        # Fazla boşlukları temizle
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _compute_query_similarity(self, query1: str, query2: str) -> float:
        """
        İki sorgu arasındaki benzerliği hesapla
        
        Args:
            query1: İlk sorgu
            query2: İkinci sorgu
            
        Returns:
            float: Benzerlik skoru (0-1 arası)
        """
        # Basit sözcük kesişim skoru (Jaccard benzerliği)
        q1_words = set(self._normalize_question(query1).split())
        q2_words = set(self._normalize_question(query2).split())
        
        if not q1_words or not q2_words:
            return 0.0
        
        intersection = len(q1_words.intersection(q2_words))
        union = len(q1_words.union(q2_words))
        
        return intersection / union if union > 0 else 0.0
    
    async def _find_similar_cached_query(
        self, 
        question: str, 
        user_id: str,
        search_type: str,
        prompt_template_id: Optional[str] = None
    ) -> Tuple[Optional[RAGResponse], float]:
        """
        Benzer sorgular için önbellekte arama yap
        
        Args:
            question: Sorgu metni
            user_id: Kullanıcı kimliği
            search_type: Arama tipi
            prompt_template_id: Prompt şablonu kimliği
            
        Returns:
            Tuple[Optional[RAGResponse], float]: Bulunan yanıt ve benzerlik skoru
        """
        # Önbellek hizmeti yoksa
        if not self.cache.redis_client:
            return None, 0.0
        
        try:
            # Sorgu önbellekte var mı?
            norm_question = self._normalize_question(question)
            
            # Tüm "rag:*" anahtarlarını tara
            cursor = 0
            while True:
                cursor, keys = await self.cache.redis_client.scan(cursor, "rag:*", 100)
                
                for key in keys:
                    # Anahtarı çözümle
                    cache_data = await self.cache.redis_client.get(key)
                    if not cache_data:
                        continue
                    
                    # Veriyi çözümle
                    cached_response = self.cache.deserialize_fn(cache_data)
                    if not cached_response or not isinstance(cached_response, RAGResponse):
                        continue
                    
                    # Benzerlik puanı hesapla
                    similarity = self._compute_query_similarity(norm_question, cached_response.question)
                    
                    # Benzerlik eşiğini geç
                    if similarity >= self.similar_match_threshold:
                        return cached_response, similarity
                
                # Tarama tamamlandı
                if cursor == 0:
                    break
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Error finding similar cached query: {str(e)}")
            return None, 0.0
    
    async def answer_query(
        self,
        query: RAGQuery,
        user_id: str,
        organization_id: Optional[str] = None,
        db = None
    ) -> RAGResponse:
        """
        Kullanıcı sorgusuna cevap oluştur (önbellekli)
        
        Args:
            query: Sorgu bilgileri
            user_id: Kullanıcı ID
            organization_id: Organizasyon ID (opsiyonel)
            db: Veritabanı bağlantısı (opsiyonel)
            
        Returns:
            RAGResponse: Oluşturulan cevap ve kaynaklar
        """
        # Önbellek devre dışı ise normal davran
        if not self.use_cache or not self.cache.redis_client:
            return await super().answer_query(query, user_id, organization_id, db)
        
        try:
            # Önbellek anahtarı oluştur
            cache_key = self._get_cache_key(query, user_id)
            
            # Tam eşleşen önbellek var mı?
            cached_response = await self.cache.get(cache_key)
            
            if cached_response:
                logger.info(f"Cache hit for query: {query.question}")
                return cached_response
            
            # Benzer bir sorgu için önbellek var mı?
            similar_response, similarity = await self._find_similar_cached_query(
                question=query.question,
                user_id=user_id,
                search_type=query.search_type,
                prompt_template_id=query.prompt_template_id
            )
            
            if similar_response and similarity >= self.exact_match_threshold:
                logger.info(f"Exact cache similarity match ({similarity:.2f}) for query: {query.question}")
                
                # Yeni bir kopya oluştur ve query_id'yi güncelle
                response_copy = RAGResponse(
                    query_id=str(uuid.uuid4()),
                    question=query.question,  # Orijinal soruyu koru
                    answer=similar_response.answer,
                    sources=similar_response.sources,
                    created_at=datetime.utcnow().isoformat()
                )
                
                # Önbelleğe kaydet (daha uzun TTL ile)
                await self.cache.set(cache_key, response_copy, self.exact_match_ttl)
                
                return response_copy
                
            elif similar_response and similarity >= self.similar_match_threshold:
                logger.info(f"Similar cache match ({similarity:.2f}) for query: {query.question}")
                
                # Benzer yanıtı döndür, kaynaklara aynı belgelerden geldiği bilgisini ekle
                response_copy = RAGResponse(
                    query_id=str(uuid.uuid4()),
                    question=query.question,  # Orijinal soruyu koru
                    answer=similar_response.answer,
                    sources=similar_response.sources,
                    created_at=datetime.utcnow().isoformat(),
                    metadata={
                        "similar_query": similar_response.question,
                        "similarity_score": similarity
                    }
                )
                
                # Önbelleğe kaydet (daha kısa TTL ile)
                await self.cache.set(cache_key, response_copy, self.similar_match_ttl)
                
                return response_copy
            
            # Önbellekte yoksa yeni yanıt oluştur
            response = await super().answer_query(query, user_id, organization_id, db)
            
            # Yanıtı önbelleğe kaydet
            await self.cache.set(cache_key, response, self.exact_match_ttl)
            
            return response
            
        except Exception as e:
            logger.error(f"Error using cached RAG answer: {str(e)}")
            # Hata durumunda normal RAG servisini kullan
            return await super().answer_query(query, user_id, organization_id, db)