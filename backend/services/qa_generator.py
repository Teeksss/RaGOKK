# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timezone
import json
import asyncio
import traceback

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.document_repository import DocumentRepository
from ..repositories.qa_pairs_repository import QAPairsRepository
from ..models.document import Document
from ..models.qa_pairs import QAPair

logger = logging.getLogger(__name__)

class QAGenerator:
    """
    Soru-Cevap Çifti Üretme servisi.
    
    Belge segmentlerinden otomatik soru-cevap çiftleri oluşturur.
    Bu çiftler, retriever ve prompt kalitesini test etmek için kullanılabilir.
    """
    
    def __init__(self, 
                use_openai: bool = True,
                model_name: str = "gpt-3.5-turbo",
                questions_per_segment: int = 2,
                max_segments: int = 10):
        """
        Args:
            use_openai: OpenAI modellerini kullanmak için
            model_name: Kullanılacak model adı
            questions_per_segment: Segment başına üretilecek soru sayısı
            max_segments: İşlenecek maksimum segment sayısı
        """
        self.use_openai = use_openai
        self.model_name = model_name
        self.questions_per_segment = questions_per_segment
        self.max_segments = max_segments
        self.document_repository = DocumentRepository()
        self.qa_pairs_repository = QAPairsRepository()
        
        # OpenAI API
        if use_openai:
            self.client = AsyncOpenAI()
    
    async def generate_qa_pairs(self, 
                             segments: List[Dict[str, Any]],
                             document_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Belge segmentlerinden soru-cevap çiftleri oluşturur
        
        Args:
            segments: Belge segmentleri
            document_metadata: Belge metadataları
            
        Returns:
            Dict[str, Any]: Oluşturulan soru-cevap çiftleri
        """
        if not segments:
            return {
                "success": False,
                "error": "No segments provided",
                "qa_pairs": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        try:
            all_qa_pairs = []
            segment_count = min(len(segments), self.max_segments)
            
            # Tüm segmentler için soru-cevap çiftleri oluştur
            for segment_idx in range(segment_count):
                segment = segments[segment_idx]
                
                # Segment içeriği ve metadata
                content = segment.get("content", "")
                metadata = segment.get("metadata", {})
                
                if not content or len(content) < 50:  # Kısa segmentleri atla
                    continue
                
                # Soru-cevap çiftleri oluştur
                if self.use_openai:
                    qa_pairs = await self._generate_with_openai(
                        content=content,
                        segment_metadata=metadata,
                        document_metadata=document_metadata
                    )
                else:
                    qa_pairs = await self._generate_with_local_model(
                        content=content,
                        segment_metadata=metadata,
                        document_metadata=document_metadata
                    )
                
                # Segment bilgilerini ekleyerek QA çiftleri oluştur
                for qa in qa_pairs:
                    qa["segment_id"] = metadata.get("segment_id", f"unknown_{segment_idx}")
                    qa["segment_index"] = metadata.get("segment_index", segment_idx)
                    qa["source"] = metadata.get("source_filename", "")
                    qa["page_number"] = metadata.get("page_number")
                    all_qa_pairs.extend(qa_pairs)
            
            return {
                "success": True,
                "qa_pairs": all_qa_pairs,
                "total": len(all_qa_pairs),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error generating QA pairs: {str(e)}\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "qa_pairs": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_with_openai(self,
                                 content: str,
                                 segment_metadata: Dict[str, Any],
                                 document_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        OpenAI modeli ile soru-cevap çiftleri oluşturur
        
        Args:
            content: Segment içeriği
            segment_metadata: Segment metadataları
            document_metadata: Belge metadataları
            
        Returns:
            List[Dict[str, Any]]: Soru-cevap çiftleri
        """
        try:
            # Sistem mesajı
            system_message = f"""
            Sen bir soru oluşturma uzmanısın. Görevin, verilen içeriğe dayalı olarak {self.questions_per_segment} adet soru-cevap çifti oluşturmak.
            
            Bu soru-cevap çiftleri şu özelliklere sahip olmalıdır:
            1. Sorular, içerikte bulunan bilgiye dayanmalı ve kesin bir cevap alabilmelidir
            2. En az bir soru verilen içeriğin ana fikrini hedeflemeli
            3. En az bir soru önemli bir detayı hedeflemeli
            4. Her soru açık, net ve tek bir doğru cevaba sahip olmalı
            5. Cevaplar yeterince kapsamlı ancak özlü olmalı (1-3 cümle)
            
            Yanıtını JSON formatında yapılandır:
            [
              {{
                "question": "Soru metni?",
                "answer": "Cevap metni.",
                "difficulty": "easy|medium|hard",
                "question_type": "factual|conceptual|analytical"
              }},
              // Diğer soru-cevap çiftleri
            ]

            Sadece belirtilen sayıda soru-cevap çifti içeren JSON formatında cevap ver, başka açıklama ekleme.
            """
            
            # İçerik bilgisini zenginleştir
            segment_info = ""
            if segment_metadata:
                if segment_metadata.get("section_title"):
                    segment_info += f"\nBölüm Başlığı: {segment_metadata['section_title']}"
                if segment_metadata.get("page_number"):
                    segment_info += f"\nSayfa: {segment_metadata['page_number']}"
            
            document_info = ""
            if document_metadata:
                document_info += f"\nBelge Adı: {document_metadata.get('title', '')}"
            
            # Kullanıcı mesajı
            user_message = f"""
            İçerik:
            {content}
            
            {segment_info}
            {document_info}
            
            Lütfen verilen içeriğe dayalı {self.questions_per_segment} adet soru-cevap çifti oluştur.
            """
            
            # Yanıt oluştur
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )
            
            # Yanıtı işle
            if response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                
                # JSON olarak ayrıştır
                try:
                    qa_pairs = json.loads(result)
                    # Tek bir QA çiftiyse dizi içine al
                    if isinstance(qa_pairs, dict):
                        qa_pairs = [qa_pairs]
                    return qa_pairs
                except json.JSONDecodeError:
                    logger.warning(f"Error parsing JSON response: {result}")
                    # Hata durumunda boş liste döndür
                    return []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error with OpenAI QA generation: {str(e)}")
            return []
    
    async def _generate_with_local_model(self,
                                      content: str,
                                      segment_metadata: Dict[str, Any],
                                      document_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Yerel model ile soru-cevap çiftleri oluşturur
        
        Args:
            content: Segment içeriği
            segment_metadata: Segment metadataları
            document_metadata: Belge metadataları
            
        Returns:
            List[Dict[str, Any]]: Soru-cevap çiftleri
        """
        # Gerçek uygulamada yerel bir soru oluşturma modeli kullanılabilir
        # Burada basit bir rule-based yaklaşım kullanıyoruz
        
        try:
            qa_pairs = []
            sentences = content.split(".")
            
            for i in range(min(self.questions_per_segment, len(sentences))):
                sentence = sentences[i].strip()
                if len(sentence) < 10:
                    continue
                
                # Basit soru oluştur
                words = sentence.split()
                if len(words) >= 3:
                    first_word = words[0].lower()
                    if first_word in ["bu", "şu", "o", "bunlar", "the", "these", "those", "this", "it", "he", "she", "they"]:
                        question = f"Ne hakkında konuşuluyor: \"{sentence}\"?"
                    else:
                        # İlk kelimeye göre soru başlangıcı seç
                        question = f"Parçada {words[0].lower()} ile ilgili ne söyleniyor?"
                    
                    # Soru tipini belirle
                    question_type = "factual"
                    difficulty = "medium"
                    
                    qa_pairs.append({
                        "question": question,
                        "answer": sentence,
                        "difficulty": difficulty,
                        "question_type": question_type
                    })
            
            return qa_pairs
            
        except Exception as e:
            logger.error(f"Error with local QA generation: {str(e)}")
            return []
    
    async def generate_qa_for_document(self, db: AsyncSession, document_id: str) -> Dict[str, Any]:
        """
        Belge için soru-cevap çiftleri üretir ve veritabanına kaydeder
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID
            
        Returns:
            Dict[str, Any]: Üretim sonucu
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
            
            # Belgeden segmentleri al - Bu projede segmentler veritabanında veya vektör depoda saklanmış olmalı
            # Burada segmentleri elde etmek için projeye özel kodlar gerekecektir
            # Örneğin:
            segments = []
            
            if document.metadata and "segment_count" in document.metadata:
                # Belge içeriğini segmentlere böl (basit bir yaklaşım)
                paragraphs = document.content.split("\n\n")
                for idx, paragraph in enumerate(paragraphs[:self.max_segments]):
                    if len(paragraph.strip()) < 50:  # Kısa paragrafları atla
                        continue
                        
                    segments.append({
                        "content": paragraph,
                        "metadata": {
                            "segment_id": f"{document_id}_{idx}",
                            "segment_index": idx,
                            "segment_type": "paragraph",
                            "source_filename": document.file_name,
                            "page_number": 1,  # Basitleştirme
                            "document_id": document_id,
                            "document_title": document.title
                        }
                    })
            
            if not segments:
                return {
                    "success": False,
                    "error": "No segments found for document",
                    "document_id": document_id
                }
            
            # Belge metadatalarını hazırla
            document_metadata = {
                "title": document.title,
                "file_name": document.file_name,
                "file_type": document.file_type
            }
            
            # Soru-cevap çiftleri üret
            qa_result = await self.generate_qa_pairs(
                segments=segments,
                document_metadata=document_metadata
            )
            
            if not qa_result["success"]:
                return qa_result
            
            # QA çiftlerini veritabanına kaydet
            saved_pairs = []
            for pair in qa_result["qa_pairs"]:
                qa_pair = QAPair(
                    document_id=document_id,
                    question=pair["question"],
                    answer=pair["answer"],
                    segment_id=pair.get("segment_id", ""),
                    segment_index=pair.get("segment_index", 0),
                    page_number=pair.get("page_number"),
                    difficulty=pair.get("difficulty", "medium"),
                    question_type=pair.get("question_type", "factual"),
                    metadata={
                        "source": pair.get("source", ""),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "generated": True
                    }
                )
                
                saved_pair = await self.qa_pairs_repository.create_qa_pair(db, qa_pair)
                saved_pairs.append(saved_pair)
            
            # Belge metadatasını güncelle
            if document.metadata is None:
                document.metadata = {}
                
            document.metadata["qa_pairs_generated"] = True
            document.metadata["qa_pairs_count"] = len(saved_pairs)
            document.metadata["qa_pairs_generated_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.document_repository.update_document(
                db=db,
                document_id=document_id,
                metadata=document.metadata
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "qa_pairs": [pair.to_dict() for pair in saved_pairs],
                "total": len(saved_pairs),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating QA pairs for document: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }