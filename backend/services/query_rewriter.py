# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import re

# OpenAI API için gerekli import
from openai import AsyncOpenAI, BadRequestError

# Hafif bir alternatif model için transformers
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Query Rewriter hizmeti.
    
    Kullanıcının sorgu girdisini daha açık, kapsamlı ve 
    bilgi alma açısından daha verimli hale getiren bir servis.
    """
    
    def __init__(self, 
                use_openai: bool = True,
                model_name: str = "gpt-3.5-turbo",
                context_window_size: int = 4096,
                use_chat_history: bool = True,
                max_chat_history: int = 5):
        """
        Args:
            use_openai: OpenAI modellerini kullanmak için
            model_name: Kullanılacak model adı
            context_window_size: Model bağlam penceresi boyutu
            use_chat_history: Yeniden yazma sırasında sohbet geçmişi kullan
            max_chat_history: Maksimum sohbet geçmişi öğesi
        """
        self.use_openai = use_openai
        self.model_name = model_name
        self.context_window_size = context_window_size
        self.use_chat_history = use_chat_history
        self.max_chat_history = max_chat_history
        
        # OpenAI API
        if use_openai:
            self.client = AsyncOpenAI()
        # Transformers (Yerel T5 modeli)
        elif HAS_TRANSFORMERS:
            try:
                self.t5_model = pipeline(
                    "text2text-generation", 
                    model="google/flan-t5-base",
                    device="cuda:0" if os.environ.get("USE_GPU", "false").lower() == "true" else "cpu",
                )
                logger.info("T5 model loaded for query rewriting")
            except Exception as e:
                logger.error(f"Error loading T5 model: {str(e)}")
                self.t5_model = None
        else:
            logger.warning("Neither OpenAI nor Transformers available for query rewriting")
    
    async def rewrite_query(self, 
                         original_query: str,
                         chat_history: Optional[List[Dict[str, str]]] = None,
                         user_context: Optional[Dict[str, Any]] = None,
                         active_document: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Kullanıcı sorgusunu yeniden yazar
        
        Args:
            original_query: Orijinal kullanıcı sorgusu
            chat_history: Sohbet geçmişi (opsiyonel)
            user_context: Kullanıcı bağlamı (aktif alanlar, tercihler, vb.)
            active_document: Kullanıcının aktif olarak görüntülediği belge
            
        Returns:
            Dict[str, Any]: Orijinal ve yeniden yazılmış sorgu
        """
        if not original_query.strip():
            return {
                "original_query": original_query,
                "rewritten_query": original_query,
                "improved": False
            }
        
        try:
            # Önceden işlenmiş sorgu durumlarını kontrol et
            if self._is_well_formed_query(original_query):
                logger.info("Query already well-formed, skipping rewriting")
                return {
                    "original_query": original_query,
                    "rewritten_query": original_query,
                    "improved": False
                }
            
            # Yakın zamanda aktif belge var mı kontrol et
            active_doc_info = ""
            if active_document:
                # Aktif belge bilgisini hazırla
                active_doc_info = f"""
                Kullanıcının aktif olarak baktığı belge: 
                - Ad: {active_document.get('title', 'Unknown')}
                - Dosya adı: {active_document.get('file_name', 'Unknown')}
                - Etiketler: {', '.join(active_document.get('tags', []))}
                """
            
            # Yeniden yazma metodu seç
            if self.use_openai:
                rewritten_query = await self._rewrite_with_openai(
                    original_query, 
                    chat_history if self.use_chat_history else None,
                    user_context,
                    active_doc_info
                )
            else:
                rewritten_query = await self._rewrite_with_t5(
                    original_query,
                    chat_history if self.use_chat_history else None,
                    active_doc_info
                )
            
            # İyileştirme olup olmadığını değerlendir
            improved = rewritten_query != original_query and len(rewritten_query) > len(original_query)
            
            return {
                "original_query": original_query,
                "rewritten_query": rewritten_query,
                "improved": improved
            }
        
        except Exception as e:
            logger.error(f"Error rewriting query: {str(e)}")
            # Hata durumunda orijinal sorguyu değiştirmeden döndür
            return {
                "original_query": original_query,
                "rewritten_query": original_query,
                "improved": False,
                "error": str(e)
            }
    
    def _is_well_formed_query(self, query: str) -> bool:
        """
        Sorgunun iyi biçimlendirilmiş olup olmadığını kontrol eder
        (gereksiz yeniden yazma işleminden kaçınmak için)
        
        Args:
            query: Kontrol edilecek sorgu
            
        Returns:
            bool: Sorgu iyi biçimlendirilmiş ise True
        """
        # 15 kelimeden uzun sorguları iyi biçimlendirilmiş kabul et
        words = query.split()
        if len(words) >= 15:
            return True
        
        # Soru işaretleriyle biten tam cümleleri kontrol et
        if re.search(r'[A-Z].*\?$', query):
            return True
        
        # "Ne zaman", "Nasıl", "Neden" gibi soru başlangıçları içeren sorguları kontrol et
        question_starters = [
            "ne zaman", "nasıl", "neden", "kim", "ne", "nerede", "hangi", 
            "açıkla", "anlat", "karşılaştır", "özetle", "listele", "göster"
        ]
        for starter in question_starters:
            if query.lower().startswith(starter) and len(words) > 3:
                return True
        
        return False
    
    async def _rewrite_with_openai(self, 
                                 query: str,
                                 chat_history: Optional[List[Dict[str, str]]] = None,
                                 user_context: Optional[Dict[str, Any]] = None,
                                 active_doc_info: str = "") -> str:
        """
        OpenAI modeli ile sorguyu yeniden yazar
        
        Args:
            query: Orijinal sorgu
            chat_history: Sohbet geçmişi
            user_context: Kullanıcı bağlamı
            active_doc_info: Aktif belge bilgileri
            
        Returns:
            str: Yeniden yazılmış sorgu
        """
        if not self.client:
            return query
        
        try:
            # Sistem mesajını hazırla
            system_message = """
            Sen bir sorgu iyileştirme uzmanısın. Görevin kullanıcının sorusunu belgelere dayalı bir RAG sisteminde en iyi yanıtları almak için geliştirmektir.
            
            Şu noktaları dikkate al:
            1. Belirsiz olan kısa sorguları genişlet
            2. Cevaplandırılabilir form oluştur
            3. Sohbet geçmişini dikkate al
            4. Bağlamdaki kişi, yer, zaman referanslarını netleştir
            5. Kullanıcı aktif olarak bir belgeye bakıyorsa, sorguyu o belgeye yönlendir
            
            Yeniden yazarken:
            - Orijinal soru anlamını koru
            - Gereksiz kelime ekleme
            - Özgün olmayan sorguları özelleştir
            - Kelimeleri değiştirirken anlamı değiştirme
            
            SADECE yeniden yazılmış sorguyu döndür, açıklama yapma.
            """
            
            # Sohbet geçmişini formatlama
            history_text = ""
            if chat_history and len(chat_history) > 0:
                history_items = []
                # En son mesajlardan başla (son N mesaj)
                for item in chat_history[-self.max_chat_history:]:
                    if "user" in item:
                        history_items.append(f"Kullanıcı: {item['user']}")
                    if "assistant" in item:
                        history_items.append(f"Asistan: {item['assistant']}")
                
                if history_items:
                    history_text = "Önceki Konuşma:\n" + "\n".join(history_items)
            
            # Kullanıcı bağlamını formatlama
            context_text = ""
            if user_context:
                context_items = []
                for key, value in user_context.items():
                    if isinstance(value, (list, tuple)):
                        value = ", ".join(map(str, value))
                    elif not isinstance(value, str):
                        value = str(value)
                    
                    context_items.append(f"{key}: {value}")
                
                if context_items:
                    context_text = "Kullanıcı Bağlamı:\n" + "\n".join(context_items)
            
            # Kullanıcı mesajını hazırla
            user_message = f"""
            Orijinal Sorgu: {query}
            
            {history_text}
            {context_text}
            {active_doc_info}
            
            Lütfen bu sorguyu daha kapsamlı ve RAG sisteminde kullanılabilir bir forma getir.
            """
            
            # OpenAI API çağrısı
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Yaratıcılığı sınırla
                max_tokens=150
            )
            
            # Yanıtı işle ve döndür
            if response.choices and len(response.choices) > 0:
                rewritten_query = response.choices[0].message.content.strip()
                
                # Fazla açıklamalar ve formatlamaları temizle
                rewritten_query = re.sub(r'^(Yeniden yazılmış sorgu:|İyileştirilmiş sorgu:|Sorgu:|Cevap:)', '', rewritten_query, flags=re.IGNORECASE).strip()
                rewritten_query = rewritten_query.strip('"\'')
                
                logger.info(f"Query rewritten: '{query}' -> '{rewritten_query}'")
                return rewritten_query
            else:
                return query
                
        except Exception as e:
            logger.error(f"Error with OpenAI query rewriting: {str(e)}")
            return query
    
    async def _rewrite_with_t5(self, 
                             query: str,
                             chat_history: Optional[List[Dict[str, str]]] = None,
                             active_doc_info: str = "") -> str:
        """
        T5 modeli ile sorguyu yeniden yazar (OpenAI'ya daha hafif bir alternatif)
        
        Args:
            query: Orijinal sorgu
            chat_history: Sohbet geçmişi
            active_doc_info: Aktif belge bilgileri
            
        Returns:
            str: Yeniden yazılmış sorgu
        """
        if not HAS_TRANSFORMERS or not self.t5_model:
            return query
        
        try:
            # Bağlam oluştur
            context_parts = []
            
            # Aktif belge bilgisi
            if active_doc_info:
                context_parts.append(active_doc_info)
            
            # Sohbet geçmişi
            if chat_history and len(chat_history) > 0:
                history = []
                for item in chat_history[-3:]:  # Son 3 mesajla sınırla (T5 bağlam penceresi sınırlı)
                    if "user" in item:
                        history.append(f"Kullanıcı: {item['user']}")
                    if "assistant" in item:
                        history.append(f"Asistan: {item['assistant']}")
                
                if history:
                    context_parts.append("\n".join(history))
            
            # Prompt oluştur
            context_text = " ".join(context_parts)
            input_text = f"sorguyu genişlet: {query}" + (f" bağlam: {context_text}" if context_text else "")
            
            # Girdiyi kırp (T5'in bağlam limitleri var)
            input_text = input_text[:512]  # T5-base için güvenli sınır
            
            # T5 modeli için async fonksiyon
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.t5_model(
                    input_text, 
                    max_length=100, 
                    num_return_sequences=1
                )
            )
            
            if result and len(result) > 0:
                rewritten_query = result[0]['generated_text'].strip()
                logger.info(f"T5 query rewritten: '{query}' -> '{rewritten_query}'")
                
                # Eğer T5 istenmeyen bir sonuç verirse orijinal sorguyu döndür
                if len(rewritten_query) < 3 or rewritten_query == "":
                    return query
                    
                return rewritten_query
            else:
                return query
                
        except Exception as e:
            logger.error(f"Error with T5 query rewriting: {str(e)}")
            return query