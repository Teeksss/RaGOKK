# Last reviewed: 2025-04-30 06:57:19 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Union
import logging
import json
import re
from enum import Enum
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.prompt_repository import PromptRepository
from ..models.prompt import PromptTemplate

logger = logging.getLogger(__name__)

class QueryType(str, Enum):
    """Sorgu türleri"""
    DEFINITION = "definition"  # Tanım soruları (Nedir?)
    PROCEDURAL = "procedural"  # Prosedürel sorular (Nasıl?)
    ANALYTICAL = "analytical"  # Analitik sorular (Karşılaştır, analiz et)
    FACTUAL = "factual"        # Olgusal sorular (Ne zaman?)
    LIST = "list"              # Liste soruları (Listele, sırala)
    CALCULATION = "calculation" # Hesaplama soruları (Hesapla, bul)
    OPINION = "opinion"        # Görüş soruları (Sen ne düşünüyorsun?)
    OTHER = "other"            # Diğer sorular

class PromptEngine:
    """
    Dinamik prompt yönetimi servisi.
    
    Sorgunun türüne göre en uygun prompt şablonunu seçer.
    """
    
    def __init__(self, use_openai: bool = True):
        """
        Args:
            use_openai: OpenAI modelini kullanmak için
        """
        self.use_openai = use_openai
        self.prompt_repository = PromptRepository()
        
        # OpenAI API
        if use_openai:
            self.client = AsyncOpenAI()
    
    async def get_optimal_prompt(
        self, 
        db: AsyncSession, 
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sorgu türüne göre en uygun promptu getirir
        
        Args:
            db: Veritabanı oturumu
            query: Kullanıcı sorgusu
            metadata: Ek metadata
            
        Returns:
            Dict[str, Any]: Optimal prompt şablonu ve tür bilgisi
        """
        try:
            # Sorgu türünü belirle
            query_type = await self.classify_query(query)
            
            # Türe göre şablonu getir
            prompt_template = await self._get_prompt_template_for_type(db, query_type)
            
            # Sonuçları döndür
            return {
                "prompt_template": prompt_template,
                "query_type": query_type,
                "original_query": query,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting optimal prompt: {str(e)}")
            # Hata durumunda genel bir şablon döndür
            default_template = await self._get_default_prompt_template(db)
            
            return {
                "prompt_template": default_template,
                "query_type": QueryType.OTHER,
                "original_query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def classify_query(self, query: str) -> str:
        """
        Sorgunun türünü belirler (rule-based veya ML-based)
        
        Args:
            query: Kullanıcı sorgusu
            
        Returns:
            str: Sorgu türü
        """
        # Basit ve hızlı rule-based sınıflandırma deneyelim önce
        query_lower = query.lower().strip()
        
        # Tanım soruları
        definition_patterns = [
            r"(nedir|ne demek|anlamı|tanımı|açıkla|açıklayabilir|açıklama)",
            r"(what is|what are|define|definition of|explain what|meaning of|tell me about)"
        ]
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                return QueryType.DEFINITION
        
        # Prosedürel sorular
        procedural_patterns = [
            r"(nasıl|adımları|yapılır|yap|yapmak|gerçekleştir|uygula|işlem|süreç)",
            r"(how to|how do i|steps to|how can|procedure|instructions|guide|method|approach)"
        ]
        for pattern in procedural_patterns:
            if re.search(pattern, query_lower):
                return QueryType.PROCEDURAL
        
        # Analitik sorular
        analytical_patterns = [
            r"(karşılaştır|analiz et|değerlendir|neden|sebep|ilişki|fark|benzerlik)",
            r"(compare|analyze|analyse|evaluate|why|reason|relationship|difference|similarity|versus|vs)"
        ]
        for pattern in analytical_patterns:
            if re.search(pattern, query_lower):
                return QueryType.ANALYTICAL
        
        # Olgusal sorular
        factual_patterns = [
            r"(ne zaman|nerede|kim|hangi tarihte|kaç yıl|tarihinde|tarihi|kaç|sayı)",
            r"(when|where|who|which date|how many|how much|date of|in what year)"
        ]
        for pattern in factual_patterns:
            if re.search(pattern, query_lower):
                return QueryType.FACTUAL
        
        # Liste soruları
        list_patterns = [
            r"(listele|sırala|tüm|hepsi|bütün|kaç tane|hangileri)",
            r"(list|enumerate|all of|what are all|how many different)"
        ]
        for pattern in list_patterns:
            if re.search(pattern, query_lower):
                return QueryType.LIST
        
        # Hesaplama soruları
        calculation_patterns = [
            r"(hesapla|bul|topla|çıkar|çarp|böl|oran|yüzde|miktar)",
            r"(calculate|compute|find the|sum|add|subtract|multiply|divide|percentage|amount)"
        ]
        for pattern in calculation_patterns:
            if re.search(pattern, query_lower):
                return QueryType.CALCULATION
        
        # Görüş soruları
        opinion_patterns = [
            r"(düşünce|fikir|görüş|öneri|tavsiye|değerlendirme|sen ne düşünüyorsun)",
            r"(opinion|idea|thought|suggestion|advice|recommendation|what do you think)"
        ]
        for pattern in opinion_patterns:
            if re.search(pattern, query_lower):
                return QueryType.OPINION
        
        # OpenAI ile daha karmaşık sınıflandırma
        if self.use_openai and not any(re.search(pattern, query_lower) for patterns_list in 
                                      [definition_patterns, procedural_patterns, analytical_patterns,
                                       factual_patterns, list_patterns, calculation_patterns, opinion_patterns] 
                                      for pattern in patterns_list):
            try:
                classification = await self._classify_with_openai(query)
                return classification
            except Exception as e:
                logger.warning(f"Error classifying with OpenAI: {str(e)}")
        
        # Varsayılan durum
        return QueryType.OTHER
    
    async def _classify_with_openai(self, query: str) -> str:
        """
        OpenAI kullanarak sorguyu sınıflandırır
        
        Args:
            query: Kullanıcı sorgusu
            
        Returns:
            str: Sorgu türü
        """
        try:
            system_prompt = """
            Bir sorgu sınıflandırıcı olarak görev alıyorsun. Verilen sorguyu aşağıdaki kategorilerden en uygun olana sınıflandır:
            
            1. DEFINITION: Tanım soruları (ör. "Nedir?", "Ne demek?", "Açıkla")
            2. PROCEDURAL: Prosedürel sorular (ör. "Nasıl yapılır?", "Adımları neler?")
            3. ANALYTICAL: Analitik sorular (ör. "Karşılaştır", "Analiz et", "Neden?")
            4. FACTUAL: Olgusal sorular (ör. "Ne zaman?", "Kim?", "Nerede?")
            5. LIST: Liste soruları (ör. "Listele", "Sırala", "Hangileri?")
            6. CALCULATION: Hesaplama soruları (ör. "Hesapla", "Topla", "Oranı nedir?")
            7. OPINION: Görüş soruları (ör. "Düşüncen nedir?", "Tavsiye")
            8. OTHER: Diğer sorular
            
            Sadece kategori adını büyük harflerle döndür. Başka hiçbir açıklama ekleme.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Sorgu: {query}"}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            if response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content.strip().upper()
                
                # QueryType enum'a çevir
                for query_type in QueryType:
                    if query_type.name == result:
                        return query_type
                
                # Bulunamadıysa OTHER
                return QueryType.OTHER
            else:
                return QueryType.OTHER
                
        except Exception as e:
            logger.error(f"Error with OpenAI query classification: {str(e)}")
            return QueryType.OTHER
    
    async def _get_prompt_template_for_type(self, db: AsyncSession, query_type: str) -> Optional[PromptTemplate]:
        """
        Belirli bir türe uygun prompt şablonunu getirir
        
        Args:
            db: Veritabanı oturumu
            query_type: Sorgu türü
            
        Returns:
            Optional[PromptTemplate]: Prompt şablonu veya None
        """
        try:
            # İlgili türe sahip aktif şablonu bul
            templates = await self.prompt_repository.get_prompt_templates_by_type(db, query_type)
            
            if templates and len(templates) > 0:
                # Aktif olanı seç
                active_templates = [t for t in templates if t.is_active]
                
                if active_templates:
                    # En son güncellenen şablonu kullan
                    return sorted(active_templates, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]
                else:
                    # Aktif yoksa listedeki ilk şablonu kullan
                    return templates[0]
            
            # İlgili türde şablon yoksa varsayılan şablonu kullan
            return await self._get_default_prompt_template(db)
            
        except Exception as e:
            logger.error(f"Error getting prompt template for type {query_type}: {str(e)}")
            return await self._get_default_prompt_template(db)
    
    async def _get_default_prompt_template(self, db: AsyncSession) -> PromptTemplate:
        """
        Varsayılan prompt şablonunu getirir
        
        Args:
            db: Veritabanı oturumu
            
        Returns:
            PromptTemplate: Varsayılan prompt şablonu
        """
        try:
            # Varsayılan şablonu bul
            default_templates = await self.prompt_repository.get_prompt_templates_by_type(db, "default")
            
            if default_templates and len(default_templates) > 0:
                # Aktif olanı seç
                active_templates = [t for t in default_templates if t.is_active]
                
                if active_templates:
                    return sorted(active_templates, key=lambda x: x.updated_at or x.created_at, reverse=True)[0]
                else:
                    return default_templates[0]
            
            # Varsayılan şablon yoksa yeni bir tane oluştur
            default_template = PromptTemplate(
                id=None,  # ID veritabanında oluşturulacak
                name="Default Prompt Template",
                description="Sistem tarafından oluşturulan varsayılan şablon",
                template="""Aşağıdaki soruya, verilen bağlam bilgilerine dayanarak yanıt verin.
Bağlam bilgilerinde bulamazsan "Bu soruya yanıt vermek için yeterli bilgi bulunamadı" diyebilirsin.

Bağlam:
{{context}}

Soru: {{query}}

Kaynaklara referans vererek yanıtlayın. Örneğin: "... [1]" veya "... [2]". Yanıtınız Markdown formatında olmalıdır.""",
                template_type="default",
                is_active=True,
                created_by="system",
                created_at=datetime.now(timezone.utc)
            )
            
            # Veritabanına kaydet
            await self.prompt_repository.create_prompt_template(db, default_template)
            
            return default_template
            
        except Exception as e:
            logger.error(f"Error getting default prompt template: {str(e)}")
            
            # Son çare: hardcoded şablon
            return PromptTemplate(
                name="Fallback Template",
                description="Hata durumunda kullanılan şablon",
                template="""Aşağıdaki soruya, verilen bağlam bilgilerine dayanarak yanıt verin.
Bağlam bilgilerinde bulamazsan "Bu soruya yanıt vermek için yeterli bilgi bulunamadı" diyebilirsin.

Bağlam:
{{context}}

Soru: {{query}}

Kaynaklara referans vererek yanıtlayın. Örneğin: "... [1]" veya "... [2]". Yanıtınız Markdown formatında olmalıdır.""",
                template_type="fallback",
                is_active=True
            )