# Last reviewed: 2025-04-30 07:59:11 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Union
import logging
import base64
import time
import os
import io
from PIL import Image
import json
import traceback

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.document_repository import DocumentRepository
from ..services.vector_store import VectorStore
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class MultimodalRAG:
    """
    Multimodal RAG (Retrieval-Augmented Generation) servisi.
    
    Metin sorularını hem metin hem de görsel içeriği anlayarak yanıtlar.
    """
    
    def __init__(self, 
                model_name: str = "gpt-4-vision-preview",
                embedding_model: str = "text-embedding-ada-002",
                max_tokens: int = 1024,
                temperature: float = 0.7):
        """
        Args:
            model_name: VLM model ismi 
            embedding_model: Embedding model ismi
            max_tokens: Maksimum token sayısı
            temperature: Yanıt sıcaklığı
        """
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = AsyncOpenAI()
        
        # Diğer servisler
        self.document_repository = DocumentRepository()
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        
    async def process_query_with_images(self, 
                                   query_text: str,
                                   image_paths: List[str],
                                   document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Görsel ve metin tabanlı bir sorguyu işler
        
        Args:
            query_text: Metin sorgusu
            image_paths: Görsel dosya yolları
            document_ids: Belirli belgeleri filtrelemek için ID listesi (opsiyonel)
            
        Returns:
            Dict[str, Any]: İşlem sonucu
        """
        try:
            # Görselleri encode et
            encoded_images = []
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        with open(img_path, "rb") as image_file:
                            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                            encoded_images.append(encoded_image)
                    except Exception as e:
                        logger.error(f"Error encoding image {img_path}: {str(e)}")
                        continue
            
            # En az bir görsel var mı kontrol et
            if not encoded_images:
                return {
                    "success": False,
                    "error": "No valid images provided",
                    "query": query_text
                }
            
            # İlgili metin içeriği getir
            relevant_texts = await self._retrieve_relevant_text(query_text, document_ids)
            
            # VLM ile yanıt oluştur
            response = await self._generate_multimodal_response(query_text, encoded_images, relevant_texts)
            
            return {
                "success": True,
                "query": query_text,
                "answer": response,
                "image_count": len(encoded_images),
                "retrieved_text_count": len(relevant_texts)
            }
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"Error processing multimodal query: {str(e)}\n{error_detail}")
            
            return {
                "success": False,
                "error": str(e),
                "query": query_text
            }
    
    async def process_document_with_images(self, 
                                     document_id: str,
                                     query_text: str,
                                     db: AsyncSession) -> Dict[str, Any]:
        """
        Belge ID'ye göre belgeden görsel ve metinle işleme yapar
        
        Args:
            document_id: Belge ID
            query_text: Sorgu metni
            db: Veritabanı oturumu
            
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
                    "query": query_text
                }
            
            # Belge metadatasında resim bilgisi var mı kontrol et
            image_paths = []
            if document.metadata and "images" in document.metadata:
                images_info = document.metadata["images"]
                
                # Her bir resmi alarak işlemeye hazırla
                for img_info in images_info:
                    if "path" in img_info:
                        image_paths.append(img_info["path"])
            
            # Resim yoksa hata döndür
            if not image_paths:
                return {
                    "success": False,
                    "error": "No images found in document",
                    "query": query_text,
                    "document_id": document_id
                }
            
            # Sorguyu işle
            result = await self.process_query_with_images(
                query_text=query_text,
                image_paths=image_paths,
                document_ids=[document_id]
            )
            
            # Belge bilgisi ekle
            result["document_id"] = document_id
            result["document_title"] = document.title
            
            return result
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"Error processing document with images: {str(e)}\n{error_detail}")
            
            return {
                "success": False,
                "error": str(e),
                "query": query_text,
                "document_id": document_id
            }
    
    async def _retrieve_relevant_text(self, 
                                  query_text: str,
                                  document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Sorgu için ilgili metin içeriğini getirir
        
        Args:
            query_text: Metin sorgusu
            document_ids: Belirli belgeleri filtrelemek için ID listesi (opsiyonel)
            
        Returns:
            List[Dict[str, Any]]: İlgili metin segmentleri
        """
        filters = {}
        if document_ids:
            filters["document_ids"] = document_ids
        
        # Vektör depoda arama yap
        search_results = await self.vector_store.search(
            query_text=query_text,
            limit=5,
            filters=filters
        )
        
        return search_results.get("results", [])
    
    async def _generate_multimodal_response(self,
                                       query_text: str,
                                       encoded_images: List[str],
                                       relevant_texts: List[Dict[str, Any]]) -> str:
        """
        VLM ile çok modlu yanıt oluşturur
        
        Args:
            query_text: Metin sorgusu
            encoded_images: Base64 encoded görsel verileri
            relevant_texts: İlgili metin segmentleri
            
        Returns:
            str: Oluşturulan yanıt
        """
        try:
            # Metin bağlamı oluştur
            context_parts = []
            for idx, result in enumerate(relevant_texts):
                content = result.get("content", "")
                if content:
                    context_parts.append(f"[{idx+1}] {content}")
            
            context = "\n\n".join(context_parts) if context_parts else ""
            
            # Sistem mesajı
            system_message = f"""
            Sen bir görsel ve metin verilerini analiz eden yardımcısın.
            Sana bir soru ve beraberinde görsel(ler) verildi. 
            Ayrıca, sorguyla ilgili metin bağlamı da sağlandı.
            
            Görseli analiz et ve metinsel bilgilerle birleştirerek yanıt oluştur.
            Görsel içerikten tespit edebildiğin her şeyi açıkla, ancak kesin olmadığın noktalarda 
            bunu belirt ve metin bağlamına daha fazla güven.
            
            Yanıtını Markdown formatında ver.
            """
            
            # Kullanıcı mesajı içeriği
            content = [
                {"type": "text", "text": f"Soru: {query_text}"}
            ]
            
            # Bağlam bilgisi varsa ekle
            if context:
                content.append({
                    "type": "text", 
                    "text": f"\nBağlam Bilgisi:\n{context}"
                })
            
            # Görselleri ekle
            for img_base64 in encoded_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                })
            
            # API çağrısı
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": content}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Yanıt metnini döndür
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            
            return "Yanıt oluşturulamadı."
            
        except Exception as e:
            logger.error(f"Error generating multimodal response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    async def process_image_content(self, 
                               image_path: str,
                               extraction_type: str = "text_and_content") -> Dict[str, Any]:
        """
        Görsel içeriğini işleyerek metin ve içerik çıkarır
        
        Args:
            image_path: Görsel dosya yolu
            extraction_type: Çıkarım tipi (text_only, content_only, text_and_content)
            
        Returns:
            Dict[str, Any]: Çıkarım sonucu
        """
        try:
            # Görsel varlığını kontrol et
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }
            
            # Görseli encode et
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # İstek tipine göre sistem mesajı
            if extraction_type == "text_only":
                system_message = "Görselde gördüğün tüm metinleri aynen çıkar ve listele. Sadece metinleri ver."
            elif extraction_type == "content_only":
                system_message = "Görselde ne olduğunu detaylıca açıkla. Metin içeriğine odaklanma, görsel içeriğe odaklan."
            else:  # text_and_content
                system_message = "Görselde gördüğün metinleri çıkar ve görselin içeriğini detaylıca açıkla."
            
            # API çağrısı
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Bu görseli analiz et:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]}
                ],
                max_tokens=self.max_tokens,
                temperature=0.5  # Daha deterministik sonuçlar için düşük sıcaklık
            )
            
            # Yanıtı parse et
            if response.choices and len(response.choices) > 0:
                extracted_content = response.choices[0].message.content
                
                # Görsel bilgilerini al
                try:
                    img = Image.open(image_path)
                    image_info = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "size_kb": os.path.getsize(image_path) / 1024
                    }
                except:
                    image_info = {"error": "Could not extract image metadata"}
                
                return {
                    "success": True,
                    "extraction_type": extraction_type,
                    "extracted_content": extracted_content,
                    "image_path": image_path,
                    "image_info": image_info
                }
            
            return {
                "success": False,
                "error": "No response generated from the model",
                "image_path": image_path
            }
            
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"Error processing image content: {str(e)}\n{error_detail}")
            
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path
            }