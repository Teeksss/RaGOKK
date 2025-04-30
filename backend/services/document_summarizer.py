# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timezone
import asyncio
import json
import traceback

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.document import Document
from ..repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

class DocumentSummarizer:
    """
    Belge özetleme servisi.
    
    Yüklenen belgeler için otomatik özet oluşturur.
    """
    
    def __init__(self, 
                use_openai: bool = True,
                model_name: str = "gpt-3.5-turbo",
                max_content_length: int = 8192):
        """
        Args:
            use_openai: OpenAI modellerini kullanmak için
            model_name: Kullanılacak model adı
            max_content_length: Özetlenecek maksimum içerik uzunluğu
        """
        self.use_openai = use_openai
        self.model_name = model_name
        self.max_content_length = max_content_length
        self.document_repository = DocumentRepository()
        
        # OpenAI API istemcisi
        if use_openai:
            self.client = AsyncOpenAI()
    
    async def generate_summary(self, 
                            content: str,
                            document_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Belge içeriği için özet oluşturur
        
        Args:
            content: Belge içeriği
            document_metadata: Belge metadataları
            
        Returns:
            Dict[str, Any]: Özet ve metadata
        """
        if not content or len(content) < 100:
            return {
                "success": False,
                "error": "Content too short for summarization",
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        try:
            # İçeriği kırp
            trimmed_content = content[:self.max_content_length]
            
            # Belge türü ve adı
            document_type = document_metadata.get("file_type", "document") if document_metadata else "document"
            document_title = document_metadata.get("title", "Document") if document_metadata else "Document"
            
            # Özet oluştur
            if self.use_openai:
                summary_data = await self._generate_with_openai(
                    content=trimmed_content,
                    document_type=document_type,
                    document_title=document_title
                )
            else:
                summary_data = await self._generate_with_local_model(
                    content=trimmed_content,
                    document_type=document_type,
                    document_title=document_title
                )
            
            return {
                "success": True,
                "summary": summary_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_with_openai(self,
                                 content: str,
                                 document_type: str,
                                 document_title: str) -> Dict[str, Any]:
        """
        OpenAI modeli ile özet oluşturur
        
        Args:
            content: Belge içeriği
            document_type: Belge türü
            document_title: Belge başlığı
            
        Returns:
            Dict[str, Any]: Özet verileri
        """
        try:
            # Sistem mesajı
            system_message = """
            Sen bir belge özetleme uzmanısın. Verilen belgenin kapsamlı bir özetini çıkarman gerekiyor.

            Özetinde şu unsurları oluşturmalısın:
            1. Genel İçerik: Belgenin ana konusu ve temel fikirler (2-4 cümle)
            2. Anahtar Kavramlar: Belgede sıkça geçen veya önem taşıyan terimler/kavramlar (madde işaretli liste)
            3. Yazarın Amacı: Belgeyi hazırlayan kişi/kuruluşun temel amacı ve hedef kitlesi (1-2 cümle)
            
            Yanıtını JSON formatında yapılandır:
            {
              "general_content": "Belgenin genel içeriğinin özeti...",
              "key_concepts": ["Kavram 1", "Kavram 2", "Kavram 3"],
              "author_purpose": "Yazarın amacını anlatan özet..."
            }

            Sadece bu JSON formatında cevap ver.
            """
            
            # Kullanıcı mesajı
            user_message = f"""
            Belge Türü: {document_type}
            Belge Adı: {document_title}
            
            Belge İçeriği:
            {content}
            """
            
            # Yanıt oluştur
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            # Yanıtı işle
            if response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                # JSON olarak ayrıştır
                try:
                    summary_data = json.loads(result)
                    return summary_data
                except json.JSONDecodeError:
                    logger.warning(f"Error parsing JSON response: {result}")
                    
                    # Doğrudan yanıt
                    return {
                        "general_content": result[:500],
                        "key_concepts": ["Özet mevcut değil"],
                        "author_purpose": "Amaç belirlenemedi"
                    }
            else:
                return {
                    "general_content": "Özet oluşturulamadı",
                    "key_concepts": ["Özet mevcut değil"],
                    "author_purpose": "Amaç belirlenemedi"
                }
                
        except Exception as e:
            logger.error(f"Error with OpenAI summarization: {str(e)}")
            
            return {
                "general_content": f"Özet oluşturulamadı: {str(e)}",
                "key_concepts": ["Hata oluştu"],
                "author_purpose": "Belirlenemedi"
            }
    
    async def _generate_with_local_model(self,
                                      content: str,
                                      document_type: str,
                                      document_title: str) -> Dict[str, Any]:
        """
        Yerel özet modeli ile özet oluşturur (OpenAI olmadığında fallback)
        
        Args:
            content: Belge içeriği
            document_type: Belge türü
            document_title: Belge başlığı
            
        Returns:
            Dict[str, Any]: Özet verileri
        """
        try:
            # Basit özet oluşturma (gerçek uygulamada BART veya T5 gibi özetleme modelleri kullanılabilir)
            sentences = content.split(".")[:10]
            general_content = ". ".join(sentences) + "."
            
            # Kelime frekansı analizi
            word_counts = {}
            for word in content.lower().split():
                if len(word) > 3:  # Kısa kelimeleri atla
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # En çok geçen kelimeler
            key_concepts = [word for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            
            # Basit amaç tahmini
            author_purpose = f"{document_title} içerisinde bilgi paylaşımı amaçlanmıştır."
            
            return {
                "general_content": general_content,
                "key_concepts": key_concepts,
                "author_purpose": author_purpose
            }
            
        except Exception as e:
            logger.error(f"Error with local summarization: {str(e)}")
            
            return {
                "general_content": f"Özet oluşturulamadı: {str(e)}",
                "key_concepts": ["Hata oluştu"],
                "author_purpose": "Belirlenemedi"
            }
    
    async def process_document(self, 
                            db: AsyncSession, 
                            document_id: str) -> Dict[str, Any]:
        """
        Veritabanındaki belgeyi özet için işler
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID
            
        Returns:
            Dict[str, Any]: İşlem sonucu
        """
        try:
            # Belgeyi getir
            document = await self.document_repository.get_document_by_id(db, document_id)
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}",
                    "document_id": document_id
                }
            
            # Metadataları hazırla
            document_metadata = {
                "file_type": document.file_type,
                "title": document.title,
                "file_name": document.file_name
            }
            
            # Özet oluştur
            summary_result = await self.generate_summary(
                content=document.content,
                document_metadata=document_metadata
            )
            
            # Belgenin metadatasını güncelle
            if summary_result["success"]:
                # Mevcut metadatayı al
                existing_metadata = document.metadata or {}
                
                # Özet bilgilerini ekle
                existing_metadata["summary"] = summary_result["summary"]
                existing_metadata["summary_generated_at"] = datetime.now(timezone.utc).isoformat()
                
                # Metadatayı güncelle
                await self.document_repository.update_document(
                    db=db,
                    document_id=document_id,
                    metadata=existing_metadata
                )
                
                # Özet ID'si eklenmeli
                summary_result["document_id"] = document_id
                summary_result["document_title"] = document.title
            
            return summary_result
            
        except Exception as e:
            logger.error(f"Error processing document for summarization: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }