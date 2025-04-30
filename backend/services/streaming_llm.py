# Last reviewed: 2025-04-30 07:12:47 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
import logging
import json
import asyncio

from openai import AsyncOpenAI
from fastapi import WebSocket
import re

logger = logging.getLogger(__name__)

class StreamingLLM:
    """
    Streaming LLM servisi.
    
    LLM yanıtlarını parça parça akışlı olarak ve kaynak referansları ile üretir.
    """
    
    def __init__(self, 
                model_name: str = "gpt-3.5-turbo",
                temperature: float = 0.7,
                max_tokens: int = 1000,
                stream_chunk_size: int = 20):
        """
        Args:
            model_name: LLM model adı
            temperature: Yanıt sıcaklığı (yaratıcılık)
            max_tokens: Maksimum token sayısı
            stream_chunk_size: Akış parça boyutu
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream_chunk_size = stream_chunk_size
        self.client = AsyncOpenAI()
    
    async def generate_streaming_answer(self, 
                                   query: str,
                                   search_results: List[Dict[str, Any]],
                                   system_prompt: Optional[str] = None,
                                   highlight_sources: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Akışlı LLM yanıtını oluşturur
        
        Args:
            query: Kullanıcı sorgusu
            search_results: Arama sonuçları
            system_prompt: Sistem promptu (opsiyonel)
            highlight_sources: Kaynak vurgulama etkin mi?
            
        Yields:
            Dict[str, Any]: Yanıt parçası ve ilgili metadata
        """
        try:
            # Kaynakları formatlı hale getir
            context, source_map = self._prepare_context_with_sources(search_results)
            
            # Varsayılan sistem promptu
            if not system_prompt:
                system_prompt = """
                Aşağıdaki soruya, verilen bağlam bilgilerine dayanarak yanıt verin.
                Bağlam bilgilerinde bulamazsan "Bu soruya yanıt vermek için yeterli bilgi bulunamadı" diyebilirsin.
                
                Önemli: Kaynak referansları kullan. Bir ifade için kaynak kullanırken [1], [2] gibi referanslar ekle.
                Yanıtının Markdown formatında olmalıdır.
                """
            
            # Kullanıcı mesajı
            user_message = f"""
            Bağlam:
            {context}
            
            Soru: {query}
            
            Kaynaklara referans vererek yanıtlayın. Örneğin: "... [1]" veya "... [2]". Yanıtınız Markdown formatında olmalıdır.
            """
            
            # Akış başlat
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True  # Akış modunda
            )
            
            # Akış işleyici
            current_references = set()
            buffer = ""
            current_source_id = None
            
            async for chunk in response:
                # Token parçası
                content = chunk.choices[0].delta.content or ""
                
                # Referans kontrolü
                if highlight_sources and content:
                    buffer += content
                    
                    # Referans eşleşmesi ara
                    new_refs, current_source = self._check_for_references(buffer, source_map)
                    
                    # Yeni referanslar varsa ekle
                    if new_refs:
                        current_references.update(new_refs)
                    
                    # Kaynak değişti mi?
                    if current_source != current_source_id:
                        current_source_id = current_source
                
                # Yanıt parçasını oluştur
                yield {
                    "content": content,
                    "done": False,
                    "source_id": current_source_id,
                    "current_references": list(current_references),
                    "metadata": {
                        "model": self.model_name,
                        "has_more": True
                    }
                }
            
            # Tamamlandı işareti
            yield {
                "content": "",
                "done": True,
                "source_id": None,
                "current_references": list(current_references),
                "metadata": {
                    "model": self.model_name,
                    "has_more": False,
                    "total_references": list(current_references)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating streaming answer: {str(e)}")
            # Hata mesajı
            yield {
                "content": f"\n\nÜzgünüm, bir hata oluştu: {str(e)}",
                "done": True,
                "source_id": None,
                "metadata": {
                    "model": self.model_name,
                    "has_more": False,
                    "error": str(e)
                }
            }
    
    async def handle_websocket(self, 
                            websocket: WebSocket,
                            query: str,
                            search_results: List[Dict[str, Any]],
                            system_prompt: Optional[str] = None) -> None:
        """
        WebSocket üzerinden akışlı yanıt oluşturur ve gönderir
        
        Args:
            websocket: WebSocket bağlantısı
            query: Kullanıcı sorgusu
            search_results: Arama sonuçları
            system_prompt: Sistem promptu (opsiyonel)
        """
        try:
            # WebSocket bağlantısını kabul et
            await websocket.accept()
            
            # İlk bilgilendirme mesajını gönder
            await websocket.send_json({
                "type": "info",
                "content": "Yanıt oluşturuluyor...",
                "metadata": {
                    "query": query,
                    "model": self.model_name,
                    "sources_count": len(search_results)
                }
            })
            
            # Streaming yanıt oluştur
            async for response_chunk in self.generate_streaming_answer(
                query=query,
                search_results=search_results,
                system_prompt=system_prompt
            ):
                # WebSocket üzerinden gönder
                await websocket.send_json({
                    "type": "chunk",
                    **response_chunk
                })
                
                # Küçük gecikme ekle (throttle)
                await asyncio.sleep(0.01)
            
            # Bağlantıyı kapat
            await websocket.close()
            
        except Exception as e:
            logger.error(f"Error handling WebSocket: {str(e)}")
            # Bağlantı halen açıksa hata gönder
            try:
                await websocket.send_json({
                    "type": "error",
                    "content": str(e),
                    "metadata": {
                        "error": str(e)
                    }
                })
                await websocket.close()
            except:
                pass
    
    def _prepare_context_with_sources(self, search_results: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Arama sonuçlarından metin içeriği ve kaynak haritası oluşturur
        
        Args:
            search_results: Arama sonuçları
            
        Returns:
            Tuple[str, Dict[str, Any]]: Bağlam metni ve kaynak haritası
        """
        source_map = {}
        context_parts = []
        
        # Her sonucu işle ve kaynak numarası ata
        for idx, result in enumerate(search_results):
            source_id = str(idx + 1)
            content = result.get("content", "")
            
            if content:
                # Bağlam parçası oluştur
                context_parts.append(f"[{source_id}] {content}")
                
                # Kaynak haritasına ekle
                source_map[source_id] = {
                    "document_id": result.get("document_id", ""),
                    "content": content,
                    "title": result.get("document_title", "Belge"),
                    "page_number": result.get("metadata", {}).get("page_number"),
                    "source_id": source_id
                }
        
        # Tüm bağlam parçalarını birleştir
        context = "\n\n".join(context_parts)
        
        return context, source_map
    
    def _check_for_references(self, text: str, source_map: Dict[str, Any]) -> Tuple[List[str], Optional[str]]:
        """
        Metindeki kaynak referanslarını kontrol eder
        
        Args:
            text: Kontrol edilecek metin
            source_map: Kaynak haritası
            
        Returns:
            Tuple[List[str], Optional[str]]: Bulunan referanslar ve aktif kaynak ID'si
        """
        # Referans deseni [1], [2] vb.
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        
        references = []
        current_source = None
        
        # Eşleşmeleri kontrol et
        for match in matches:
            source_id = match
            if source_id in source_map:
                references.append(source_id)
                current_source = source_id
        
        return references, current_source