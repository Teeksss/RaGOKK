# Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, select, update, insert, delete
import json
from datetime import datetime

from ..models.personalization import PersonalizationProfile, DocumentInteraction
from ..db.async_database import Base
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Veritabanı modeli
class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    user_id = Column(String, primary_key=True, index=True)
    profile_data = Column(Text, nullable=False)  # JSON olarak saklanan profil verileri
    last_updated = Column(String, nullable=False)  # ISO format tarih

class PersonalizationRepository:
    """Kişiselleştirme profillerini yönetmek için repository"""
    
    async def get_profile(self, db: AsyncSession, user_id: str) -> Optional[PersonalizationProfile]:
        """Kullanıcının kişiselleştirme profilini getirir"""
        try:
            # Profili veritabanından sorgula
            query = select(UserPreference).where(UserPreference.user_id == str(user_id))
            result = await db.execute(query)
            user_pref = result.scalars().first()
            
            if not user_pref:
                return None
            
            # JSON verilerini parse et ve PersonalizationProfile'a dönüştür
            profile_data = json.loads(user_pref.profile_data)
            return PersonalizationProfile.parse_obj(profile_data)
        except Exception as e:
            logger.error(f"Personalization profile retrieval error: {e}")
            return None
    
    async def save_profile(self, db: AsyncSession, profile: PersonalizationProfile) -> bool:
        """Kişiselleştirme profilini kaydeder"""
        try:
            # Profili JSON'a dönüştür
            profile_json = profile.json()
            
            # Güncellenme zamanını ayarla
            last_updated = datetime.utcnow().isoformat()
            
            # Önce profile'ın var olup olmadığını kontrol et
            query = select(UserPreference).where(UserPreference.user_id == str(profile.user_id))
            result = await db.execute(query)
            existing = result.scalars().first()
            
            if existing:
                # Güncelleme
                stmt = update(UserPreference).where(
                    UserPreference.user_id == str(profile.user_id)
                ).values(
                    profile_data=profile_json,
                    last_updated=last_updated
                )
            else:
                # Yeni kayıt
                stmt = insert(UserPreference).values(
                    user_id=str(profile.user_id),
                    profile_data=profile_json,
                    last_updated=last_updated
                )
            
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Personalization profile save error: {e}")
            await db.rollback()
            return False
    
    async def add_query(self, db: AsyncSession, user_id: str, query: str) -> bool:
        """Kullanıcı sorgu geçmişine yeni bir sorgu ekler"""
        try:
            profile = await self.get_profile(db, user_id)
            
            # Profil yoksa oluştur
            if not profile:
                profile = PersonalizationProfile(user_id=str(user_id))
            
            # Sorguyu ekle
            profile.add_query(query)
            
            # Profili kaydet
            return await self.save_profile(db, profile)
        except Exception as e:
            logger.error(f"Query history update error: {e}")
            return False
    
    async def add_document_interaction(
        self, 
        db: AsyncSession, 
        user_id: str, 
        doc_id: str, 
        interaction_type: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Belge etkileşimi ekler"""
        try:
            profile = await self.get_profile(db, user_id)
            
            # Profil yoksa oluştur
            if not profile:
                profile = PersonalizationProfile(user_id=str(user_id))
            
            # Etkileşim ekle
            profile.add_document_interaction(doc_id, interaction_type, metadata)
            
            # Profili kaydet
            return await self.save_profile(db, profile)
        except Exception as e:
            logger.error(f"Document interaction update error: {e}")
            return False
    
    async def delete_profile(self, db: AsyncSession, user_id: str) -> bool:
        """Kişiselleştirme profilini siler"""
        try:
            stmt = delete(UserPreference).where(UserPreference.user_id == str(user_id))
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Personalization profile delete error: {e}")
            await db.rollback()
            return False
    
    async def get_all_profiles(self, db: AsyncSession) -> List[PersonalizationProfile]:
        """Tüm kişiselleştirme profillerini getirir (admin için)"""
        try:
            query = select(UserPreference)
            result = await db.execute(query)
            user_prefs = result.scalars().all()
            
            profiles = []
            for user_pref in user_prefs:
                try:
                    profile_data = json.loads(user_pref.profile_data)
                    profiles.append(PersonalizationProfile.parse_obj(profile_data))
                except Exception as e:
                    logger.error(f"Profile parsing error: {e}")
                    
            return profiles
        except Exception as e:
            logger.error(f"Get all profiles error: {e}")
            return []