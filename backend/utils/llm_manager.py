# Last reviewed: 2025-04-29 08:33:58 UTC (User: TeeksssGPT-3.5)
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
import time
import os
import torch
import numpy as np
from pydantic import BaseModel
import json
import asyncio
from enum import Enum
import re
import hashlib
import logging
import textwrap
from .config import (
    LOCAL_LLM_MODEL_NAME_OR_PATH, LOCAL_LLM_DEVICE, LOCAL_LLM_TYPE,
    LLM_API_KEY, LLM_QUANTIZATION, LLM_USE_TORCH_COMPILE,
    LLM_USE_FLASH_ATTENTION, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    LLM_MODEL_FAMILY, MODEL_CONFIG, HALLUCINATION_THRESHOLD,
    TOOL_USAGE_ENABLED, TOOL_EXECUTION_TIMEOUT
)
from .logger import get_logger

# Lazy imports
transformers = None
httpx = None

logger = get_logger(__name__)

class ModelFamily(str, Enum):
    GPT = "gpt"
    T5 = "t5"
    LLAMA = "llama"
    MISTRAL = "mistral"
    FALCON = "falcon"
    PHI = "phi"
    BERT = "bert"
    OTHER = "other"

class ResponseFormat(str, Enum):
    DEFAULT = "default"
    SHORT_SUMMARY = "short_summary"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    TABLE = "table"
    STEP_BY_STEP = "step_by_step"

class PromptTemplate(BaseModel):
    template: str
    input_variables: List[str]
    supports_tools: bool = False
    supports_format_instructions: bool = False

class LLMResponse(BaseModel):
    """LLM yanıt modeli"""
    text: str
    model: str
    elapsed_seconds: float
    token_count: int
    confidence_score: float
    metadata: Dict[str, Any] = {}
    hallucination_detected: bool = False
    citations: List[Dict[str, Any]] = []
    tool_calls: List[Dict[str, Any]] = []

class AsyncTool:
    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]], func: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func
        
    async def execute(self, **kwargs):
        return await self.func(**kwargs)
        
    def to_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {param["name"]: {"type": param["type"], "description": param["description"]} 
                                 for param in self.parameters},
                    "required": [param["name"] for param in self.parameters if param.get("required", False)]
                }
            }
        }

class LLMManager:
    """Farklı LLM tiplerini yönetmek için sınıf"""
    
    def __init__(self, model_path_or_name=LOCAL_LLM_MODEL_NAME_OR_PATH, model_family=LLM_MODEL_FAMILY):
        """
        Args:
            model_path_or_name: Model yolu veya HF model adı
            model_family: Modelin ailesi (GPT, T5, LLAMA, MISTRAL, BERT vb.)
        """
        self.model_path_or_name = model_path_or_name
        self.model_family = ModelFamily(model_family.lower())
        self.model = None
        self.tokenizer = None
        self.is_initialized = False
        self._init_config()
        
        # Araçlar (tools)
        self.tools = {}
        self._register_default_tools()
        
        # Prompt template'ler için registry
        self._prompt_templates = {
            "qa": PromptTemplate(
                template="""[SYSTEM]: Sana verilen belgelere dayalı olarak kullanıcının sorusunu yanıtla.
                Yanıtını sadece verilen belgelerdeki bilgilere dayandır.
                Eğer belgeler sorunun yanıtını içermiyorsa, açıkça bilmediğini belirt.
                
                [BELGE BAĞLAMLARI]:
                {context}
                
                [SORU]: {query}
                
                [YANIT]:""",
                input_variables=["context", "query"],
                supports_format_instructions=True
            ),
            
            "qa_with_sources": PromptTemplate(
                template="""[SYSTEM]: Sana verilen belgelere dayalı olarak kullanıcının sorusunu yanıtla.
                Yanıtını sadece verilen belgelerdeki bilgilere dayandır.
                Eğer belgeler sorunun yanıtını içermiyorsa, açıkça bilmediğini belirt.
                Yanıtında kullandığın kaynakları belirt.
                
                [BELGE BAĞLAMLARI]:
                {context}
                
                [SORU]: {query}
                
                [YANIT]:""",
                input_variables=["context", "query"],
                supports_format_instructions=True
            ),
            
            "qa_with_tools": PromptTemplate(
                template="""[SYSTEM]: Sana verilen belgelere dayalı olarak ve gerekirse harici araçları kullanarak kullanıcının sorusunu yanıtla.
                Yanıtını verilen belgelerdeki bilgilere dayandır.
                Eğer soruyu yanıtlamak için harici işlemler gerekiyorsa, uygun araçları kullan.
                İşlemlerini ve kaynaklarını açıkça belirt.
                
                [BELGE BAĞLAMLARI]:
                {context}
                
                [SORU]: {query}
                
                [YANIT]:""",
                input_variables=["context", "query"],
                supports_tools=True,
                supports_format_instructions=True
            ),
            
            "summarize": PromptTemplate(
                template="""[SYSTEM]: Aşağıdaki metni özetle. Özette önemli noktaları kapsa ve gereksiz detayları dışarda bırak.
                
                [METİN]:
                {text}
                
                [ÖZET]:""",
                input_variables=["text"],
                supports_format_instructions=True
            ),
            
            "chunk_stitch": PromptTemplate(
                template="""[SYSTEM]: Aşağıdaki metin parçalarından tutarlı ve bütünleşik bir belge oluştur.
                Her parça daha büyük bir belgenin bir kısmını içeriyor. Parçaları mantıklı bir şekilde birleştir.
                Belgenin yapısını koru ve tekrarları kaldır.
                
                [METİN PARÇALARI]:
                {chunks}
                
                [BİRLEŞTİRİLMİŞ METİN]:""",
                input_variables=["chunks"]
            )
        }
        
        # Yanıt format talimatları
        self._format_instructions = {
            ResponseFormat.SHORT_SUMMARY: "Yanıtını kısa ve öz bir özet olarak ver, en fazla 3 cümle kullan.",
            ResponseFormat.DETAILED: "Detaylı bir açıklama yap, tüm önemli noktaları açıkla ve örneklerle destekle.",
            ResponseFormat.BULLET_POINTS: "Yanıtını madde madde liste olarak formatla, her noktayı '•' işareti ile başlat.",
            ResponseFormat.TABLE: "Yanıtını tablo formatında organize et, başlıkları ve sütunları belirgin şekilde ayır.",
            ResponseFormat.STEP_BY_STEP: "Adım adım açıklama yap, her adımı numaralandır ve sıralı bir şekilde anlat."
        }
        
        # Hallucination kontrolü için hafıza
        self._context_memory = {}
    
    def _init_config(self):
        """Model yapılandırmasını başlatır"""
        # Cihaz belirleme
        self.device = LOCAL_LLM_DEVICE
        if not self.device:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        # Quantization
        self.quantization = LLM_QUANTIZATION
        
        # Optimizasyonlar
        self.use_torch_compile = LLM_USE_TORCH_COMPILE
        self.use_flash_attention = LLM_USE_FLASH_ATTENTION
        
        # Maksimum token sayısı
        self.max_tokens = LLM_MAX_TOKENS
        
        # Sıcaklık
        self.temperature = LLM_TEMPERATURE
        
        # Modellerin özel yapılandırmaları
        self.model_config = MODEL_CONFIG.get(self.model_family, {})
        
        # Hallucination eşik değeri
        self.hallucination_threshold = HALLUCINATION_THRESHOLD
        
        logger.info(f"LLM konfigürasyonu: {self.model_family} - {self.device} - Quantization: {self.quantization}")
    
    def _register_default_tools(self):
        """Varsayılan araçları kaydeder"""
        if TOOL_USAGE_ENABLED:
            # Hesap makinesi aracı
            self.register_tool(
                "calculator",
                "Matematiksel hesaplama yapar",
                [
                    {"name": "expression", "type": "string", "description": "Hesaplanacak matematiksel ifade", "required": True}
                ],
                self._tool_calculator
            )
            
            # Tarih/saat aracı
            self.register_tool(
                "get_current_time",
                "Mevcut tarih ve saati döndürür",
                [],
                self._tool_current_time
            )
            
            # Web sayfası içeriği aracı
            self.register_tool(
                "fetch_url",
                "Web sayfasının içeriğini getirir",
                [
                    {"name": "url", "type": "string", "description": "Getirilecek URL", "required": True}
                ],
                self._tool_fetch_url
            )
    
    async def _tool_calculator(self, expression: str):
        """Matematiksel ifadeleri hesaplayan araç"""
        try:
            # Güvenlik için eval kullanımını sınırla
            # Sadece sayılar, operatörler ve bazı matematiksel fonksiyonlar
            allowed_names = {"abs": abs, "round": round, "min": min, "max": max,
                            "pow": pow, "sum": sum, "len": len}
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Kullanımına izin verilmeyen isim: {name}")
                    
            result = eval(code, {"__builtins__": {}}, allowed_names)
            return {"result": result}
        except Exception as e:
            return {"error": f"Hesaplama hatası: {str(e)}"}
    
    async def _tool_current_time(self):
        """Mevcut tarih ve saati döndüren araç"""
        from datetime import datetime
        current_time = datetime.utcnow()
        return {
            "utc_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "iso_format": current_time.isoformat(),
            "unix_timestamp": int(current_time.timestamp())
        }
    
    async def _tool_fetch_url(self, url: str):
        """Web sayfası içeriğini getiren araç"""
        global httpx
        if httpx is None:
            import httpx
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Title ve meta description
                title = soup.title.string if soup.title else "No title"
                
                # Ana içerik (p ve h etiketlerinden)
                main_content = []
                for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10:
                        main_content.append(text)
                
                # İçeriği sınırla (çok uzun olabilir)
                content_text = "\n".join(main_content[:30])  # İlk 30 paragraf/başlık
                if len(content_text) > 4000:
                    content_text = content_text[:4000] + "...(devamı var)"
                
                return {
                    "title": title,
                    "url": url,
                    "content": content_text,
                    "status_code": response.status_code
                }
        except Exception as e:
            return {"error": f"URL getirme hatası: {str(e)}"}
    
    def register_tool(self, name: str, description: str, parameters: List[Dict], func: Callable):
        """Yeni bir araç kaydet"""
        if not TOOL_USAGE_ENABLED:
            logger.warning("Araç kullanımı devre dışı, araç kaydedilemedi")
            return
            
        self.tools[name] = AsyncTool(name, description, parameters, func)
        logger.info(f"Araç kaydedildi: {name}")
    
    def register_prompt(self, name: str, template: str, input_variables: List[str], supports_tools: bool = False, supports_format_instructions: bool = False):
        """Yeni bir prompt template kaydeder"""
        self._prompt_templates[name] = PromptTemplate(
            template=template,
            input_variables=input_variables,
            supports_tools=supports_tools,
            supports_format_instructions=supports_format_instructions
        )
        logger.info(f"Prompt template kaydedildi: {name}")
    
    def format_prompt(self, template_name: str, response_format: Optional[ResponseFormat] = None, **kwargs) -> str:
        """Kayıtlı şablona göre prompt formatlar"""
        if template_name not in self._prompt_templates:
            raise ValueError(f"Prompt template bulunamadı: {template_name}")
        
        template = self._prompt_templates[template_name]
        
        # Tüm gerekli değişkenlerin sağlandığını kontrol et
        missing_vars = [var for var in template.input_variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Eksik değişkenler: {missing_vars}")
        
        # Format instructionları ekle
        if template.supports_format_instructions and response_format and response_format != ResponseFormat.DEFAULT:
            format_instruction = self._format_instructions.get(response_format, "")
            if format_instruction:
                kwargs["format_instructions"] = format_instruction
                
        # Prompt'u formatla
        formatted_prompt = template.template
        for var_name, var_value in kwargs.items():
            if var_name in template.input_variables or var_name == "format_instructions":
                if var_name == "format_instructions":
                    # Format talimatını uygun bir noktaya ekle
                    if "[YANIT]:" in formatted_prompt:
                        formatted_prompt = formatted_prompt.replace("[YANIT]:", f"[FORMAT]: {format_instruction}\n\n[YANIT]:")
                    else:
                        formatted_prompt += f"\n\n[FORMAT]: {format_instruction}"
                else:
                    formatted_prompt = formatted_prompt.replace(f"{{{var_name}}}", str(var_value))
        
        # Retrieval-aware prompting: Belge içeriği otomatik olarak eklenir
        if "context" in kwargs:
            # Context hash değerini hesapla ve hafızaya kaydet
            context = kwargs["context"]
            context_hash = hashlib.md5(context.encode()).hexdigest()
            self._context_memory[context_hash] = context
        
        return formatted_prompt
    
    async def load_model(self):
        """Model ve tokenizer'ı async olarak yükler"""
        if self.is_initialized:
            return
        
        # transformers kütüphanesini lazy olarak import et
        global transformers
        if transformers is None:
            try:
                import transformers
            except ImportError:
                logger.error("transformers kütüphanesi bulunamadı. Yüklenmiş mi?")
                raise ImportError("transformers kütüphanesi bulunamadı.")
        
        # Yükleme süreci CPU-bound olduğu için thread pool'da çalıştır
        try:
            await asyncio.to_thread(self._load_model_sync)
            self.is_initialized = True
            logger.info(f"Model başarıyla yüklendi: {self.model_path_or_name}")
        except Exception as e:
            logger.error(f"Model yükleme hatası: {e}", exc_info=True)
            raise
    
    def _load_model_sync(self):
        """Model ve tokenizer'ı senkron olarak yükler"""
        # Quantization konfigürasyonu
        quantization_config = None
        if self.quantization and self.quantization != "none":
            logger.info(f"Quantization kullanılıyor: {self.quantization}")
            if self.quantization == "4bit":
                quantization_config = transformers.BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            elif self.quantization == "8bit":
                quantization_config = transformers.BitsAndBytesConfig(
                    load_in_8bit=True
                )
        
        # Model ailesine göre doğru yapılandırmayı seç
        try:
            start_time = time.time()
            
            # Tokenizer'ı yükle
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                self.model_path_or_name,
                trust_remote_code=True
            )
            
            # Modeli yükle - model ailesine göre
            if self.model_family in [ModelFamily.GPT, ModelFamily.LLAMA, ModelFamily.MISTRAL, ModelFamily.FALCON]:
                self.model = transformers.AutoModelForCausalLM.from_pretrained(
                    self.model_path_or_name,
                    device_map=self.device if self.device != "cpu" else None,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
                # Default tokenizer ayarları
                if not self.tokenizer.pad_token:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    
            elif self.model_family == ModelFamily.PHI:
                self.model = transformers.AutoModelForCausalLM.from_pretrained(
                    self.model_path_or_name,
                    device_map=self.device if self.device != "cpu" else None,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
                # Default tokenizer ayarları
                if not self.tokenizer.pad_token:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    
            elif self.model_family == ModelFamily.T5:
                self.model = transformers.T5ForConditionalGeneration.from_pretrained(
                    self.model_path_or_name,
                    device_map=self.device if self.device != "cpu" else None,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
                
            elif self.model_family == ModelFamily.BERT:
                self.model = transformers.AutoModelForMaskedLM.from_pretrained(
                    self.model_path_or_name,
                    device_map=self.device if self.device != "cpu" else None,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
                
            else: # OTHER
                self.model = transformers.AutoModelForCausalLM.from_pretrained(
                    self.model_path_or_name,
                    device_map=self.device if self.device != "cpu" else None,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
            
            # torch.compile optimizasyonu
            if self.use_torch_compile and hasattr(torch, "compile") and self.device != "cpu":
                logger.info("torch.compile optimizasyonu uygulanıyor")
                try:
                    self.model = torch.compile(self.model)
                    logger.info("Model compile edildi")
                except Exception as e:
                    logger.warning(f"Model compile edilemedi: {e}")
            
            # FlashAttention optimizasyonu
            if self.use_flash_attention and self.device != "cpu":
                logger.info("FlashAttention optimizasyonu uygulanıyor")
                try:
                    if hasattr(self.model.config, "attn_implementation"):
                        self.model.config.attn_implementation = "flash_attention_2"
                        logger.info("FlashAttention 2 etkinleştirildi")
                except Exception as e:
                    logger.warning(f"FlashAttention etkinleştirilemedi: {e}")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Model ve tokenizer yüklendi ({self.device}) - {elapsed_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Model yükleme hatası: {e}", exc_info=True)
            raise
    
    async def chunk_and_stitch(self, text: str, max_chunk_size: int = 1000, overlap: int = 200) -> str:
        """Uzun metni parçalara böler ve sonra tutarlı bir bütün oluşturmak için birleştirir"""
        if not text:
            return ""
            
        # Metin çok kısa ise direkt döndür
        if len(text) <= max_chunk_size:
            return text
            
        # Metni parçalara böl
        chunks = []
        start = 0
        while start < len(text):
            # Kesme noktasını belirle (tercihen nokta, paragraf sonu gibi doğal kesimler)
            end = min(start + max_chunk_size, len(text))
            
            # Eğer kesme noktası metnin sonunda değilse, doğal kesim noktası ara
            if end < len(text):
                # Paragraf sonu
                paragraph_end = text.rfind('\n\n', start, end)
                if paragraph_end != -1 and paragraph_end > start + max_chunk_size // 2:
                    end = paragraph_end + 2
                else:
                    # Cümle sonu
                    sentence_end = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if sentence_end != -1 and sentence_end > start + max_chunk_size // 2:
                        end = sentence_end + 2
            
            # Parçayı ekle
            chunks.append(text[start:end])
            
            # Sonraki parçanın başlangıcı (önceki parçayla örtüşme)
            start = end - overlap
        
        # Parça sayısı az ise (2-3) direkt birleştir
        if len(chunks) <= 3:
            return "\n\n".join(chunks)
        
        # Parça sayısı fazla ise LLM ile özetleme ve birleştirme
        stitched_text = await self.generate_from_template(
            "chunk_stitch", 
            chunks="\n\n---\n\n".join(chunks),
            max_new_tokens=max(1500, len(text) // 2)
        )
        
        return stitched_text
    
    async def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Metin içerisindeki araç çağrılarını saptar ve parse eder"""
        tool_calls = []
        
        # Araç çağrı formatı: "[[Tool:tool_name(param1=value1, param2=value2, ...)]]"
        tool_pattern = r'\[\[Tool:([a-zA-Z0-9_]+)\((.*?)\)\]\]'
        matches = re.finditer(tool_pattern, text)
        
        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Tool var mı kontrol et
            if tool_name not in self.tools:
                continue
                
            # Parametreleri parse et
            params = {}
            for param in re.finditer(r'([a-zA-Z0-9_]+)=([^,]+)(?:,|$)', params_str):
                param_name = param.group(1).strip()
                param_value = param.group(2).strip()
                
                # String değerlerden tırnak işaretlerini kaldır
                if (param_value.startswith('"') and param_value.endswith('"')) or \
                   (param_value.startswith("'") and param_value.endswith("'")):
                    param_value = param_value[1:-1]
                
                params[param_name] = param_value
            
            tool_calls.append({
                "tool": tool_name,
                "params": params,
                "full_match": match.group(0)
            })
        
        return tool_calls
    
    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Araç çağrılarını yürütür ve sonuçları döndürür"""
        results = []
        
        for call in tool_calls:
            tool_name = call["tool"]
            params = call["params"]
            full_match = call["full_match"]
            
            if tool_name not in self.tools:
                results.append({
                    "tool": tool_name,
                    "error": f"Bilinmeyen araç: {tool_name}",
                    "full_match": full_match
                })
                continue
            
            tool = self.tools[tool_name]
            
            try:
                # Zaman aşımı ile araç yürütme
                result = await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=TOOL_EXECUTION_TIMEOUT
                )
                
                results.append({
                    "tool": tool_name,
                    "result": result,
                    "full_match": full_match
                })
            except asyncio.TimeoutError:
                results.append({
                    "tool": tool_name,
                    "error": f"Araç çalışma zaman aşımı ({TOOL_EXECUTION_TIMEOUT}s)",
                    "full_match": full_match
                })
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "error": f"Araç çalışma hatası: {str(e)}",
                    "full_match": full_match
                })
        
        return results
    
    async def _replace_tool_calls_with_results(self, text: str, tool_results: List[Dict[str, Any]]) -> str:
        """Araç çağrılarını sonuçlarıyla değiştirir"""
        result = text
        
        for tool_result in tool_results:
            full_match = tool_result["full_match"]
            tool_name = tool_result["tool"]
            
            if "error" in tool_result:
                replacement = f"[[Error: {tool_result['error']}]]"
            else:
                result_data = tool_result["result"]
                if isinstance(result_data, dict):
                    replacement = json.dumps(result_data, ensure_ascii=False, indent=2)
                else:
                    replacement = str(result_data)
                    
                # Çok uzun sonuçları kısalt
                if len(replacement) > 500:
                    replacement = replacement[:500] + "...(sonuç kısaltıldı)"
                
                replacement = f"[[ToolResult: {tool_name}]]\n{replacement}\n[[/ToolResult]]"
            
            result = result.replace(full_match, replacement)
        
        return result
    
    def _detect_hallucination(self, response: str, context: str) -> Tuple[bool, float]:
        """Yanıttaki hallucination'ı algılar - belirli bilgiler belgede geçmiyorsa uyarı verir"""
        # Basit önemli ifadeleri çıkar (isimler, sayılar, özel terimler)
        entities_pattern = r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)|(?:\d+(?:[,.]\d+)?(?:\s*(?:%|milyon|milyar|bin))?)|(?:[A-Za-z]+\s*(?:API|SDK|V\d+))'
        response_entities = set(re.findall(entities_pattern, response))
        
        if not response_entities:
            return False, 1.0  # Özel terim bulunamadı
            
        # Bulunan terimlerin kontekst içinde olup olmadığını kontrol et
        missing_entities = []
        for entity in response_entities:
            if entity.strip() and len(entity) > 2 and entity not in context:
                missing_entities.append(entity)
        
        # Hallucination skoru hesapla
        if not missing_entities:
            return False, 1.0  # Tüm terimler belgede geçiyor
            
        hallucination_score = len(missing_entities) / len(response_entities)
        is_hallucination = hallucination_score > self.hallucination_threshold
        
        return is_hallucination, 1.0 - hallucination_score
    
    def _extract_citations(self, text: str, context: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Yanıttaki alıntıları saptar ve düzenler"""
        citations = []
        
        # [[1]], [1], [Kaynak 1] veya benzer formatları ara
        citation_pattern = r'\[\[(\d+)\]\]|\[(\d+)\]|\[(?:Kaynak|Ref)\s*(\d+)\]'
        
        # Referansları topla
        matches = re.finditer(citation_pattern, text)
        used_refs = set()
        
        for match in matches:
            ref_num = match.group(1) or match.group(2) or match.group(3)
            if ref_num:
                ref_id = int(ref_num)
                used_refs.add(ref_id)
        
        # Konteksti paragraf veya cümlelere böl
        context_parts = re.split(r'\n\n|\. ', context)
        
        # Her referans için bir kaynak oluştur
        for ref_id in used_refs:
            if ref_id <= len(context_parts):
                source_text = context_parts[ref_id - 1]
                citations.append({
                    "id": ref_id,
                    "text": source_text.strip(),
                })
        
        return text, citations
    
    def _check_exact_copy(self, text: str, context: str) -> Tuple[bool, float]:
        """Yanıtın bağlam içinden birebir kopyalanıp kopyalanmadığını kontrol eder"""
        if not text or not context:
            return False, 0.0
            
        # En uzun ortak alt dizi algoritması
        def longest_common_substring(s1, s2):
            m = [[0] * (1 + len(s2)) for _ in range(1 + len(s1))]
            longest, x_longest = 0, 0
            for x in range(1, 1 + len(s1)):
                for y in range(1, 1 + len(s2)):
                    if s1[x-1] == s2[y-1]:
                        m[x][y] = m[x-1][y-1] + 1
                        if m[x][y] > longest:
                            longest = m[x][y]
                            x_longest = x
                    else:
                        m[x][y] = 0
            return s1[x_longest - longest: x_longest]
        
        # Metin normalizasyonu
        def normalize(s):
            return re.sub(r'\s+', ' ', s.lower())
        
        norm_text = normalize(text)
        norm_context = normalize(context)
        
        # En uzun ortak metni bul
        common = longest_common_substring(norm_text, norm_context)
        
        # Yanıtın ne kadarı ortak
        similarity_ratio = len(common) / len(norm_text) if norm_text else 0
        
        # %70 üzeri benzerlik varsa birebir kopya sayılır
        return similarity_ratio > 0.7, similarity_ratio
    
    def _format_response_by_type(self, text: str, response_format: ResponseFormat) -> str:
        """Yanıtı istenilen formata göre düzenler"""
        if response_format == ResponseFormat.DEFAULT:
            return text
            
        elif response_format == ResponseFormat.SHORT_SUMMARY:
            # Metni kısalt
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) > 3:
                return " ".join(sentences[:3])
            return text
            
        elif response_format == ResponseFormat.BULLET_POINTS:
            # Metni madde işaretlerine dönüştür
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            result = []
            
            for line in lines:
                if not line.startswith("•") and not line.startswith("-"):
                    line = "• " + line
                result.append(line)
                
            return "\n".join(result)
            
        elif response_format == ResponseFormat.TABLE:
            # Tablo formatına dönüştür
            # (Basit tablo dönüşümü, gerçek uygulamalarda daha karmaşık olabilir)
            if "|" in text and "\n" in text:
                # Zaten tablo formatındaysa değiştirme
                return text
                
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if len(lines) < 2:
                return text
                
            # Başlıklar
            headers = ["Konu", "Açıklama"]
            table = [f"| {headers[0]} | {headers[1]} |", f"|------|------|"]
            
            # Veriler
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    table.append(f"| {parts[0].strip()} | {parts[1].strip()} |")
                else:
                    table.append(f"| {line} | |")
                    
            return "\n".join(table)
            
        elif response_format == ResponseFormat.STEP_BY_STEP:
            # Adım adım formata dönüştür
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            result = []
            
            counter = 1
            for line in lines:
                if not re.match(r"^\d+\.", line) and not re.match(r"^Adım \d+:", line):
                    line = f"{counter}. {line}"
                    counter += 1
                result.append(line)
                
            return "\n".join(result)
            
        elif response_format == ResponseFormat.DETAILED:
            # Detaylı format - paragrafları belirginleştir
            paragraphs = text.split("\n\n")
            result = []
            
            for i, para in enumerate(paragraphs):
                if i == 0:
                    # İlk paragraf özet olsun
                    result.append(f"ÖZET: {para}")
                else:
                    # Diğer paragraflar
                    result.append(para)
                    
            return "\n\n".join(result)
            
        return text
    
    async def generate(
        self, 
        prompt: str, 
        max_new_tokens=512, 
        context: Optional[str] = None,
        response_format: ResponseFormat = ResponseFormat.DEFAULT,
        use_tools: bool = False,
        prevent_hallucination: bool = True,
        **kwargs
    ) -> LLMResponse:
        """Prompt kullanarak metin üretir ve detaylı yanıt döndürür"""
        if not self.is_initialized:
            await self.load_model()
        
        if not self.model or not self.tokenizer:
            raise ValueError("Model ve tokenizer yüklenmemiş!")
        
        start_time = time.time()
        
        # Prompt içinde context yoksa ve context parametresi sağlanmışsa ekle
        if context and context not in prompt and "{context}" not in prompt:
            # Orijinal prompt içinde yer belirleyici (placeholder) yoksa uygun bir konum bul
            if "[BELGE BAĞLAMLARI]:" not in prompt:
                # Sorudan önce context ekleyelim
                if "[SORU]:" in prompt:
                    prompt = prompt.replace("[SORU]:", f"[BELGE BAĞLAMLARI]:\n{context}\n\n[SORU]:")
                else:
                    # En başa ekle
                    prompt = f"[BELGE BAĞLAMLARI]:\n{context}\n\n{prompt}"
        
        # Model ailesine göre doğru generation yaklaşımını seç
        try:
            # İlk önce araçları işle (eğer istenirse ve araçlar aktifse)
            interim_output = None
            tool_results = []
            
            if use_tools and TOOL_USAGE_ENABLED and self.tools:
                # Tokenize
                input_tokens = self.tokenizer(prompt, return_tensors="pt")
                input_ids = input_tokens.input_ids.to(self.model.device)
                
                # Bellek/token optimizasyonu - girdi çok uzunsa kısalt
                max_input_length = min(self.max_tokens, 4096)  # Daha güvenli bir limit
                if input_ids.shape[1] > max_input_length:
                    input_ids = input_ids[:, -max_input_length:]
                
                # Aracı belirlemek için ilk çağrı
                async def _generate_interim():
                    with torch.no_grad():
                        if self.model_family in [ModelFamily.GPT, ModelFamily.LLAMA, ModelFamily.MISTRAL, ModelFamily.FALCON, ModelFamily.PHI]:
                            # Causal LM için
                            output = self.model.generate(
                                input_ids,
                                max_new_tokens=max_new_tokens,
                                temperature=self.temperature,
                                do_sample=self.temperature > 0,
                                top_p=0.95,
                                pad_token_id=self.tokenizer.pad_token_id
                            )
                            return self.tokenizer.decode(
                                output[0][input_ids.shape[1]:], 
                                skip_special_tokens=True
                            ).strip()
                
                # İlk çıktıyı oluştur
                interim_output = await asyncio.to_thread(_generate_interim)
                
                # Araç çağrılarını işle
                if interim_output:
                    tool_calls = await self._parse_tool_calls(interim_output)
                    if tool_calls:
                        # Araçları çalıştır
                        tool_results = await self._execute_tool_calls(tool_calls)
                        
                        # Araç sonuçlarını çıktıya yerleştir
                        interim_output = await self._replace_tool_calls_with_results(
                            interim_output, tool_results
                        )
                        
                        # Yeni prompt oluştur
                        prompt += f"\n\n[SONUÇLAR]:\n{interim_output}"
            
            # Tokenize
            input_tokens = self.tokenizer(prompt, return_tensors="pt")
            input_ids = input_tokens.input_ids.to(self.model.device)
            
            # Bellek/token optimizasyonu - girdi çok uzunsa kısalt
            max_input_length = min(self.max_tokens, 4096)  # Daha güvenli bir limit
            if input_ids.shape[1] > max_input_length:
                logger.warning(f"Input çok uzun ({input_ids.shape[1]} tokens), kısaltılıyor...")
                input_ids = input_ids[:, -max_input_length:]
            
            # Generation parametreleri
            gen_kwargs = {
                "max_new_tokens": max_new_tokens,
                "temperature": self.temperature,
                "do_sample": self.temperature > 0,
                "top_p": 0.95,
                "pad_token_id": self.tokenizer.pad_token_id
            }
            
            # Kullanıcı parametreleri ekle
            gen_kwargs.update({k: v for k, v in kwargs.items() if k in [
                "max_new_tokens", "temperature", "do_sample", "top_p", 
                "top_k", "num_beams", "repetition_penalty"
            ]})
            
            # Generate - model ailesine göre uygun yaklaşım
            async def _generate_final():
                with torch.no_grad():
                    if self.model_family in [ModelFamily.GPT, ModelFamily.LLAMA, ModelFamily.MISTRAL, ModelFamily.FALCON, ModelFamily.PHI]:
                        # Causal LM için
                        output = self.model.generate(input_ids, **gen_kwargs)
                        return self.tokenizer.decode(
                            output[0][input_ids.shape[1]:], 
                            skip_special_tokens=True
                        ).strip()
                    
                    elif self.model_family == ModelFamily.T5:
                        # Encoder-Decoder model için
                        output = self.model.generate(input_ids, **gen_kwargs)
                        return self.tokenizer.decode(
                            output[0], 
                            skip_special_tokens=True
                        ).strip()
                    
                    elif self.model_family == ModelFamily.BERT:
                        # BERT için fill-mask yaklaşımı kullan
                        return "(BERT modeli generate için uygun değil)"
            
            # Final çıktıyı oluştur
            if interim_output and not tool_calls:
                # Eğer ara çıktı oluştuysa ve tool çağrısı yoksa direkt kullan
                output_text = interim_output
                token_count = len(self.tokenizer.encode(output_text))
            else:
                # Eğer ara çıktı yoksa veya tool çağrısı varsa yeniden generate et
                output_text = await asyncio.to_thread(_generate_final)
                token_count = len(self.tokenizer.encode(output_text))
            
            # Yanıtı istenen formata göre şekillendir
            formatted_output = self._format_response_by_type(output_text, response_format)
            
            # Alıntıları işle
            if context:
                formatted_output, citations = self._extract_citations(formatted_output, context)
            else:
                citations = []
            
            # Hallucination kontrolü
            hallucination_detected = False
            confidence_score = 1.0
            
            if prevent_hallucination and context:
                hallucination_detected, confidence_score = self._detect_hallucination(formatted_output, context)
                
                # Eğer hallucination tespit edilirse ve eşiğin üzerindeyse uyarı ekle
                if hallucination_detected:
                    formatted_output = "[⚠️ Bu yanıt, belgede olmayan bilgiler içeriyor olabilir] \n\n" + formatted_output
            
            # Birebir kopya kontrolü
            is_exact_copy = False
            copy_similarity = 0.0
            if context:
                is_exact_copy, copy_similarity = self._check_exact_copy(formatted_output, context)
            
            elapsed_time = time.time() - start_time
            
            return LLMResponse(
                text=formatted_output,
                model=self.model_path_or_name,
                elapsed_seconds=elapsed_time,
                token_count=token_count,
                confidence_score=confidence_score,
                metadata={
                    "is_exact_copy": is_exact_copy,
                    "copy_similarity": copy_similarity,
                    "response_format": response_format,
                    "tool_usage": use_tools and bool(tool_results),
                    "temperature": self.temperature
                },
                hallucination_detected=hallucination_detected,
                citations=citations,
                tool_calls=[{
                    "name": tr["tool"], 
                    "result": tr.get("result", {}), 
                    "error": tr.get("error")
                } for tr in tool_results]
            )
            
        except Exception as e:
            logger.error(f"Generation hatası: {e}", exc_info=True)
            raise
    
    async def generate_from_template(
        self, 
        template_name: str, 
        response_format: ResponseFormat = ResponseFormat.DEFAULT,
        use_tools: bool = False,
        prevent_hallucination: bool = True,
        **kwargs
    ) -> str:
        """Template kullanarak metin üretir ve sadece metin döndürür"""
        prompt = self.format_prompt(template_name, response_format, **kwargs)
        
        # Template'in tool desteği var mı kontrol et
        template = self._prompt_templates.get(template_name)
        has_tool_support = template and template.supports_tools
        
        # Context varsa al
        context = kwargs.get("context")
        
        response = await self.generate(
            prompt=prompt, 
            context=context,
            response_format=response_format,
            use_tools=use_tools and has_tool_support,
            prevent_hallucination=prevent_hallucination,
            **kwargs
        )
        
        return response.text
    
    async def process_document_chunks(self, chunks: List[str], max_tokens_per_chunk: int = 1000) -> str:
        """Belge parçalarını işler ve tek bir tutarlı metin oluşturur"""
        if not chunks:
            return ""
            
        # Parçaları birleştir
        combined_text = await self.chunk_and_stitch("\n\n".join(chunks))
        return combined_text

# LLM manager singleton
llm_manager = LLMManager()