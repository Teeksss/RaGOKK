# Last reviewed: 2025-04-29 08:27:25 UTC (User: TeeksssTF-IDF)
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
import json
from datetime import datetime

class UserPreference(BaseModel):
    """Kullanıcı tercih modeli"""
    categories: Dict[str, float] = Field(default_factory=dict, description="Kategori tercihleri ve ağırlıkları")
    sources: Dict[str, float] = Field(default_factory=dict, description="Kaynak tercihleri ve ağırlıkları")
    authors: Dict[str, float] = Field(default_factory=dict, description="Yazar tercihleri ve ağırlıkları")
    topics: Dict[str, float] = Field(default_factory=dict, description="Konu tercihleri ve ağırlıkları")
    tags: Dict[str, float] = Field(default_factory=dict, description="Etiket tercihleri ve ağırlıkları")

class DocumentInteraction(BaseModel):
    """Belge etkileşim bilgisi"""
    viewed: int = 0
    clicked: int = 0 
    bookmarked: bool = False
    rating: Optional[float] = None
    view_duration_seconds: int = 0
    last_interaction: Optional[str] = None

class UserHistory(BaseModel):
    """Kullanıcı geçmişi modeli"""
    queries: List[Dict[str, Any]] = Field(default_factory=list, description="Geçmiş sorgular")
    document_interactions: Dict[str, DocumentInteraction] = Field(default_factory=dict, description="Belge etkileşimleri")
    categories_viewed: Dict[str, int] = Field(default_factory=dict, description="Görüntülenen kategoriler ve sayıları")
    sources_used: Dict[str, int] = Field(default_factory=dict, description="Kullanılan kaynaklar ve sayıları")
    tags_clicked: Dict[str, int] = Field(default_factory=dict, description="Tıklanan etiketler ve sayıları")

class PersonalizationProfile(BaseModel):
    """Kişiselleştirme profili"""
    user_id: str
    preferences: UserPreference = Field(default_factory=UserPreference)
    history: UserHistory = Field(default_factory=UserHistory)
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_query(self, query: str, timestamp: Optional[str] = None):
        """Kullanıcı sorgu geçmişine yeni bir sorgu ekler"""
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()
        
        self.history.queries.append({
            "query": query,
            "timestamp": timestamp
        })
        
        # Son 50 sorguyu sakla
        if len(self.history.queries) > 50:
            self.history.queries = self.history.queries[-50:]
        
        self.last_updated = timestamp
    
    def add_document_interaction(self, doc_id: str, interaction_type: str, metadata: Optional[Dict] = None):
        """Belge etkileşimi ekler"""
        timestamp = datetime.utcnow().isoformat()
        
        if doc_id not in self.history.document_interactions:
            self.history.document_interactions[doc_id] = DocumentInteraction()
        
        doc_interaction = self.history.document_interactions[doc_id]
        
        # Etkileşim tipine göre güncelle
        if interaction_type == "view":
            doc_interaction.viewed += 1
            if metadata and "duration_seconds" in metadata:
                doc_interaction.view_duration_seconds += metadata["duration_seconds"]
                
        elif interaction_type == "click":
            doc_interaction.clicked += 1
            
        elif interaction_type == "bookmark":
            doc_interaction.bookmarked = True
            
        elif interaction_type == "rate" and metadata and "rating" in metadata:
            doc_interaction.rating = float(metadata["rating"])
        
        doc_interaction.last_interaction = timestamp
        
        # Kategori ve kaynak bilgilerini güncelle
        if metadata:
            if "category" in metadata:
                category = metadata["category"]
                if category:
                    self.history.categories_viewed[category] = self.history.categories_viewed.get(category, 0) + 1
                    
            if "source" in metadata:
                source = metadata["source"]
                if source:
                    self.history.sources_used[source] = self.history.sources_used.get(source, 0) + 1
                    
            if "tags" in metadata and isinstance(metadata["tags"], list):
                for tag in metadata["tags"]:
                    self.history.tags_clicked[tag] = self.history.tags_clicked.get(tag, 0) + 1
        
        self.last_updated = timestamp
        
        # Tercihleri güncelle
        self._update_preferences_from_history()
    
    def _update_preferences_from_history(self):
        """Kullanıcı geçmişine dayanarak tercihleri otomatik günceller"""
        # Kategorileri güncelle
        for category, count in self.history.categories_viewed.items():
            normalized_weight = min(count / 10.0, 1.0)  # 10 ve üzeri görüntüleme maksimum ağırlığa ulaşır
            self.preferences.categories[category] = normalized_weight
            
        # Kaynakları güncelle
        for source, count in self.history.sources_used.items():
            normalized_weight = min(count / 5.0, 1.0)  # 5 ve üzeri kullanım maksimum ağırlığa ulaşır
            self.preferences.sources[source] = normalized_weight
            
        # Etiketleri güncelle
        for tag, count in self.history.tags_clicked.items():
            normalized_weight = min(count / 3.0, 1.0)  # 3 ve üzeri tıklama maksimum ağırlığa ulaşır
            self.preferences.tags[tag] = normalized_weight
    
    def to_dict(self) -> Dict:
        """Profili sözlük olarak döndürür"""
        return json.loads(self.json())
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Sözlükten profil oluşturur"""
        return cls.parse_obj(data)