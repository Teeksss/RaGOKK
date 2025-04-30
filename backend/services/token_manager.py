# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
import tiktoken

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Token yönetimi servisi.
    
    LLM'e gönderilecek prompt ve bağlam boyutunu yönetir, token bütçesini optimize eder.
    """
    
    def __init__(self, 
                model_name: str = "gpt-3.5-turbo",
                max_tokens: int = 4096,
                reserved_output_tokens: int = 500,
                reserved_buffer_tokens: int = 150):
        """
        Args:
            model_name: LLM model adı
            max_tokens: Maksimum token sayısı
            reserved_output_tokens: Cevap için ayrılan token sayısı
            reserved_buffer_tokens: Güvenlik marjı için ayrılan token sayısı
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.reserved_output_tokens = reserved_output_tokens
        self.reserved_buffer_tokens = reserved_buffer_tokens
        
        # Kullanılabilir bağlam token'ları
        self.available_context_tokens = max_tokens - reserved_output_tokens - reserved_buffer_tokens
        
        # Encoding
        self.encoding = self._get_encoding()
    
    def _get_encoding(self):
        """Model token encoder'ını döndürür"""
        try:
            if "gpt-3.5" in self.model_name or "gpt-4" in self.model_name:
                # OpenAI modelleri için cl100k_base
                return tiktoken.encoding_for_model(self.model_name)
            else:
                # Genel amaçlı encoding
                return tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Error loading tiktoken encoding: {str(e)}. Falling back to approximation.")
            return None
    
    def count_tokens(self, text: str) -> int:
        """
        Metindeki token sayısını sayar
        
        Args:
            text: Token sayısı sayılacak metin
            
        Returns:
            int: Token sayısı
        """
        if not text:
            return 0
            
        if self.encoding:
            # Tiktoken kullanarak doğru sayım
            return len(self.encoding.encode(text))
        else:
            # Yaklaşık hesaplama (tiktoken yoksa)
            # GPT ailesinde yaklaşık olarak 4 karakter = 1 token
            return len(text) // 4
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Mesajlar listesindeki token sayısını sayar
        
        Args:
            messages: Mesajlar listesi (role/content dict'lerden oluşan)
            
        Returns:
            int: Token sayısı
        """
        if not messages:
            return 0
            
        tokens = 0
        
        for message in messages:
            # Her mesaj 4 token temel maliyete sahip
            tokens += 4
            
            # Role ve content'deki token'lar
            if "role" in message:
                tokens += self.count_tokens(message["role"])
            
            if "content" in message:
                tokens += self.count_tokens(message["content"])
        
        # Son olarak, completion için 3 token ekle
        tokens += 3
        
        return tokens
    
    def optimize_context(self, 
                       query: str, 
                       search_results: List[Dict[str, Any]],
                       system_prompt: str = "",
                       chat_history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        LLM'e gönderilecek bağlamı token bütçesine göre optimize eder
        
        Args:
            query: Kullanıcı sorgusu
            search_results: Arama sonuçları
            system_prompt: Sistem promptu
            chat_history: Opsiyonel sohbet geçmişi
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: Optimize edilmiş bağlam ve kullanılan sonuçlar
        """
        # Mevcut token kullanımını hesapla
        query_tokens = self.count_tokens(query)
        system_tokens = self.count_tokens(system_prompt)
        history_tokens = 0
        
        if chat_history:
            history_tokens = self.count_messages_tokens(chat_history)
        
        # Sabit bileşenler için token toplamı
        fixed_tokens = query_tokens + system_tokens + history_tokens
        
        # Arama sonuçları için kullanılabilir token bütçesi
        available_for_results = self.available_context_tokens - fixed_tokens
        
        if available_for_results <= 0:
            logger.warning(f"Not enough tokens for search results. Available: {available_for_results}")
            # En azından bir sonucu dahil edebilmek için chat geçmişinden kısaltma yapılabilir
            return "", []
        
        # Sonuçları en alakalıdan en az alakalıya sırala
        sorted_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)
        
        # Token bütçesine sığacak kadar sonuç seç
        used_results = []
        total_result_tokens = 0
        context_parts = []
        
        for i, result in enumerate(sorted_results):
            content = result.get("content", "")
            content_tokens = self.count_tokens(content)
            
            # Bu içeriği ekleyebilir miyiz?
            if total_result_tokens + content_tokens <= available_for_results:
                # Belge başlık ve meta bilgilerini formatla
                document_title = result.get("document_title", "Belge")
                page_number = result.get("metadata", {}).get("page_number", "")
                page_info = f", Sayfa: {page_number}" if page_number else ""
                
                # İçeriği formatlı olarak ekle
                context_parts.append(f"[{i+1}] Kaynak: {document_title}{page_info}\n{content}\n")
                
                # Token sayısını güncelle
                total_result_tokens += content_tokens
                
                # Kullanılan sonucu kaydet
                used_results.append(result)
            else:
                # İçerik çok büyük, kısaltmayı dene
                if i < 3:  # İlk 3 sonuç için özel işlem
                    # İçeriği kısalt
                    max_allowed_tokens = available_for_results - total_result_tokens
                    truncated_content = self._truncate_text_to_token_limit(content, max_allowed_tokens)
                    
                    if truncated_content:
                        # Belge başlık ve meta bilgilerini formatla
                        document_title = result.get("document_title", "Belge")
                        page_number = result.get("metadata", {}).get("page_number", "")
                        page_info = f", Sayfa: {page_number}" if page_number else ""
                        
                        # Kısaltılmış içeriği ekle
                        context_parts.append(f"[{i+1}] Kaynak: {document_title}{page_info}\n{truncated_content}\n")
                        
                        # Token sayısını güncelle
                        truncated_tokens = self.count_tokens(truncated_content)
                        total_result_tokens += truncated_tokens
                        
                        # Kısaltılmış içeriği sonuca ekle
                        truncated_result = result.copy()
                        truncated_result["content"] = truncated_content
                        truncated_result["truncated"] = True
                        used_results.append(truncated_result)
                        
                        # Bütçe tükendiyse döngüden çık
                        if total_result_tokens >= available_for_results:
                            break
        
        # İşlenen sonuçları birleştir
        context = "\n\n".join(context_parts)
        
        # Debug log
        logger.debug(f"Context optimization: {len(search_results)} results reduced to {len(used_results)}. Tokens: {total_result_tokens}/{available_for_results}")
        
        return context, used_results
    
    def _truncate_text_to_token_limit(self, text: str, token_limit: int) -> str:
        """
        Metni belirli bir token limitine kadar kısaltır
        
        Args:
            text: Kısaltılacak metin
            token_limit: Maksimum token sayısı
            
        Returns:
            str: Kısaltılmış metin
        """
        if not text or token_limit <= 0:
            return ""
            
        # Zaten limiti aşmıyorsa aynısını döndür
        text_token_count = self.count_tokens(text)
        if text_token_count <= token_limit:
            return text
        
        # Encoding varsa, tiktoken ile doğrudan belirli sayıda token al
        if self.encoding:
            tokens = self.encoding.encode(text)
            truncated_tokens = tokens[:token_limit-3]  # "..." için 3 token rezerve et
            truncated_text = self.encoding.decode(truncated_tokens) + "..."
            return truncated_text
            
        # Encoding yoksa, yaklaşık bir kısaltma yap
        # 1 token yaklaşık 4 karakter
        char_limit = token_limit * 4
        if len(text) <= char_limit:
            return text
        
        # Kısaltılmış metni döndür
        return text[:char_limit-3] + "..."