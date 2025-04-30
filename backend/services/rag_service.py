# Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
import logging
import json
import re
from typing import Dict, Any, List, Optional, Union, Set, Tuple
import uuid
from datetime import datetime
import asyncio
import httpx

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import Document

from ..config import settings
from ..schemas.rag import RAGResponse, RAGSource, RAGQuery, PromptTemplate as DBPromptTemplate
from ..repositories.document_repository import DocumentRepository
from ..repositories.prompt_repository import PromptRepository
from ..services.vector_service import VectorService
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG (Retrieval Augmented Generation) servis sınıfı
    
    Bu servis şunları yapar:
    - Kullanıcı sorgularını alır
    - Uygun belgeleri getirir
    - LLM ile cevap oluşturur
    - Sonuçları kaynakları ile birlikte döndürür
    """
    
    def __init__(self):
        """RAG servisi başlatır"""
        self.vector_service = VectorService()
        self.search_service = SearchService()
        self.document_repository = DocumentRepository()
        self.prompt_repository = PromptRepository()
        
        # LLM yapılandırması
        self.llm = ChatOpenAI(
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        
        # Varsayılan prompt şablonları
        self.default_prompt_template = """
        Sen yardımcı bir yapay zeka asistanısın. Görevin, kullanıcı sorgusuna verilen bağlam bilgilerini kullanarak en doğru cevabı oluşturmak.
        
        Kurallar:
        - Sadece verilen bağlam içerisindeki bilgileri kullan.
        - Eğer bağlam içinde cevap yoksa, bilmediğini dürüstçe söyle.
        - Cevapları özlü ve anlaşılır tut. 
        - Sadece sorular için yanıtla; bağlam hakkında ekstra açıklamalar yapma.
        - Kullanılan kaynakları referans verme, bu otomatik olarak yapılacak.
        
        Bağlam:
        {context}
        
        Soru: {question}
        
        Cevap:
        """
        
        # Özel şablonlar ve yapılandırmalar
        self.max_documents = 5  # Birleştirilecek maksimum belge sayısı
        self.similarity_threshold = 0.7  # Minimum benzerlik skoru eşiği
    
    async def answer_query(
        self,
        query: RAGQuery,
        user_id: str,
        organization_id: Optional[str] = None,
        db = None
    ) -> RAGResponse:
        """
        Kullanıcı sorgusuna cevap oluşturur
        
        Args:
            query: Sorgu bilgileri
            user_id: Kullanıcı ID
            organization_id: Organizasyon ID (opsiyonel)
            db: Veritabanı bağlantısı (opsiyonel)
            
        Returns:
            RAGResponse: Oluşturulan cevap ve kaynaklar
        """
        try:
            # Sorgu ID'si oluştur
            query_id = str(uuid.uuid4())
            
            # Sorgu metnini al
            question = query.question.strip()
            
            # Sorgu türüne göre belgeleri getir
            if query.search_type == "semantic":
                # Vektör tabanlı arama
                relevant_docs = await self.vector_service.search_documents(
                    query=question,
                    user_id=user_id,
                    organization_id=organization_id,
                    limit=query.max_results or self.max_documents,
                    db=db
                )
            else:
                # Keyword tabanlı arama
                search_results = await self.search_service.search(
                    query=question,
                    user_id=user_id,
                    page=1,
                    page_size=query.max_results or self.max_documents,
                    db=db
                )
                
                relevant_docs = search_results.get("results", [])
            
            if not relevant_docs:
                # Hiç belge bulunamadı
                return RAGResponse(
                    query_id=query_id,
                    question=question,
                    answer="Üzgünüm, bu soru için ilgili belge bulamadım. Lütfen başka bir soru sorun veya sorgulama terimlerinizi değiştirin.",
                    sources=[],
                    created_at=datetime.utcnow().isoformat()
                )
            
            # Belgeleri bağlam metni olarak birleştir
            context_text, sources = self._prepare_context(relevant_docs)
            
            if not context_text:
                # Hiç kullanılabilir içerik yok
                return RAGResponse(
                    query_id=query_id,
                    question=question,
                    answer="Üzgünüm, ilgili belgelerden okuyabilir içerik çıkaramadım. Lütfen sistem yöneticiniz ile iletişime geçin.",
                    sources=[],
                    created_at=datetime.utcnow().isoformat()
                )
            
            # Kullanılacak prompt şablonunu belirle
            prompt_template = self.default_prompt_template
            if query.prompt_template_id:
                custom_template = await self.prompt_repository.get_prompt_template(
                    db=db, 
                    template_id=query.prompt_template_id,
                    user_id=user_id
                )
                
                if custom_template:
                    prompt_template = custom_template.template
            
            # Prompt şablonu hazırla
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # LLM zincirleme
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # Cevap oluştur
            response = await chain.arun(
                context=context_text,
                question=question
            )
            
            # Cevabı ve kaynakları hazırla
            return RAGResponse(
                query_id=query_id,
                question=question,
                answer=response.strip(),
                sources=sources,
                created_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {str(e)}")
            
            # Hata durumunda genel bir cevap döndür
            return RAGResponse(
                query_id=str(uuid.uuid4()),
                question=question,
                answer="Üzgünüm, bir hata oluştu ve şu anda cevap oluşturamıyorum. Lütfen daha sonra tekrar deneyin.",
                sources=[],
                error=str(e),
                created_at=datetime.utcnow().isoformat()
            )
    
    def _prepare_context(self, documents: List[Dict[str, Any]]) -> Tuple[str, List[RAGSource]]:
        """
        Belgeleri işleyip bağlam ve kaynaklar olarak hazırlar
        
        Args:
            documents: İlgili belgeler listesi
            
        Returns:
            Tuple[str, List[RAGSource]]: Bağlam metni ve kaynak listesi
        """
        context_parts = []
        sources = []
        
        # Her belgeyi işle
        for i, doc in enumerate(documents):
            # Belge içeriğini al (chunk veya tam içerik)
            content = doc.get("content") or doc.get("chunk_content") or ""
            
            # Belge başlığını al
            title = doc.get("title", "Belge")
            
            # Belge URL'sini oluştur
            document_id = doc.get("id")
            url = f"/documents/{document_id}" if document_id else None
            
            if content:
                # İçeriği temizle ve bağlama ekle
                cleaned_content = self._clean_text(content)
                if cleaned_content:
                    context_parts.append(f"# {title}\n{cleaned_content}")
                
                # Kaynakları ekle
                sources.append(RAGSource(
                    id=document_id,
                    title=title,
                    url=url,
                    snippet=self._get_snippet(cleaned_content, max_length=200),
                    relevance_score=doc.get("score", 1.0 - (0.1 * i))  # Skor yoksa sıraya göre düş
                ))
        
        # Tüm bağlamı birleştir
        context_text = "\n\n".join(context_parts)
        
        return context_text, sources
    
    def _clean_text(self, text: str) -> str:
        """
        Metin temizleme işlemleri yapar
        
        Args:
            text: İşlenecek metin
            
        Returns:
            str: Temizlenmiş metin
        """
        if not text:
            return ""
        
        # HTML etiketlerini temizle
        text = re.sub(r'<[^>]*>', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Ardışık satır sonlarını temizle
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _get_snippet(self, text: str, max_length: int = 200) -> str:
        """
        Metinden önizleme kesiti oluşturur
        
        Args:
            text: Kaynak metin
            max_length: Maksimum kesit uzunluğu
            
        Returns:
            str: Önizleme kesiti
        """
        if not text:
            return ""
        
        # Metin çok uzunsa kısalt
        if len(text) > max_length:
            return text[:max_length].rstrip() + "..."
        
        return text