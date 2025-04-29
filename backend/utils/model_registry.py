# Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
from typing import Dict, List, Any, Optional
import os
import json
import logging
from enum import Enum

from .config import MODEL_CONFIG, LOCAL_LLM_MODEL_NAME_OR_PATH
from .logger import get_logger

logger = get_logger(__name__)

class ModelType(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    FINETUNED = "finetuned"
    CUSTOM = "custom"

class ModelRegistry:
    """Farklı tipte LLM modellere tek noktadan erişim sağlar"""
    
    def __init__(self):
        self.models = {}
        self.default_model_id = "default"
        self._discover_models()
        
    def _discover_models(self):
        """Mevcut modelleri keşfet"""
        # Varsayılan/yerel model
        self.register_model(
            model_id="default",
            model_name="Varsayılan Model",
            model_type=ModelType.LOCAL,
            model_path=LOCAL_LLM_MODEL_NAME_OR_PATH,
            model_family=os.getenv("LLM_MODEL_FAMILY", "mistral"),
            is_active=True
        )
        
        # OpenAI modelleri
        self.register_model(
            model_id="gpt-3.5-turbo",
            model_name="GPT-3.5 Turbo",
            model_type=ModelType.OPENAI,
            model_path="gpt-3.5-turbo",
            model_family="gpt",
            is_active=True
        )
        
        self.register_model(
            model_id="gpt-4",
            model_name="GPT-4",
            model_type=ModelType.OPENAI,
            model_path="gpt-4",
            model_family="gpt",
            is_active=True,
            admin_only=True
        )
        
        # Yerel modeller
        local_models = [
            {
                "id": "mistral-7b",
                "name": "Mistral 7B Instruct",
                "type": ModelType.LOCAL,
                "path": "mistralai/Mistral-7B-Instruct-v0.1",
                "family": "mistral"
            },
            {
                "id": "llama-7b",
                "name": "LLaMA 2 7B Chat",
                "type": ModelType.LOCAL,
                "path": "meta-llama/Llama-2-7b-chat-hf",
                "family": "llama"
            },
            {
                "id": "phi-2",
                "name": "Phi-2",
                "type": ModelType.LOCAL,
                "path": "microsoft/phi-2",
                "family": "phi"
            },
            {
                "id": "falcon-7b",
                "name": "Falcon 7B Instruct",
                "type": ModelType.LOCAL,
                "path": "tiiuae/falcon-7b-instruct",
                "family": "falcon"
            }
        ]
        
        for model in local_models:
            self.register_model(
                model_id=model["id"],
                model_name=model["name"],
                model_type=model["type"],
                model_path=model["path"],
                model_family=model["family"],
                is_active=True
            )
        
        # Fine-tuned modelleri keşfet
        self._discover_finetuned_models()
    
    def _discover_finetuned_models(self):
        """Fine-tuned modelleri dosya sisteminden keşfet"""
        try:
            finetuned_dir = "finetuned-models"
            if os.path.exists(finetuned_dir):
                for model_name in os.listdir(finetuned_dir):
                    model_path = os.path.join(finetuned_dir, model_name)
                    
                    if os.path.isdir(model_path):
                        # Model bilgilerini config.json'dan oku
                        config_path = os.path.join(model_path, "config.json")
                        base_model = "unknown"
                        
                        if os.path.exists(config_path):
                            with open(config_path, "r") as f:
                                try:
                                    config = json.load(f)
                                    base_model = config.get("_name_or_path", "unknown")
                                except:
                                    pass
                        
                        # Model family belirle
                        family = "other"
                        for known_family in ["gpt", "t5", "llama", "mistral", "phi", "falcon"]:
                            if known_family in model_name.lower() or known_family in base_model.lower():
                                family = known_family
                                break
                        
                        self.register_model(
                            model_id=f"finetuned-{model_name}",
                            model_name=f"Fine-tuned: {model_name}",
                            model_type=ModelType.FINETUNED,
                            model_path=model_path,
                            model_family=family,
                            base_model=base_model,
                            is_active=True
                        )
        except Exception as e:
            logger.error(f"Fine-tuned model discovery error: {e}")
    
    def register_model(
        self, 
        model_id: str, 
        model_name: str, 
        model_type: ModelType, 
        model_path: str,
        model_family: str,
        is_active: bool = True,
        admin_only: bool = False,
        base_model: str = None
    ):
        """Modeli kaydet"""
        self.models[model_id] = {
            "id": model_id,
            "name": model_name,
            "type": model_type,
            "path": model_path,
            "family": model_family,
            "is_active": is_active,
            "admin_only": admin_only,
            "base_model": base_model
        }
        logger.info(f"Registered model: {model_name} (ID: {model_id}, Type: {model_type})")
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Model bilgilerini döndürür"""
        return self.models.get(model_id)
    
    def get_active_models(self, admin_access: bool = False) -> List[Dict[str, Any]]:
        """Aktif modelleri döndürür"""
        active_models = []
        for model_id, model_info in self.models.items():
            if model_info["is_active"] and (admin_access or not model_info.get("admin_only", False)):
                active_models.append(model_info)
        return active_models
    
    def get_model_instance(self, model_id: str, user_is_admin: bool = False):
        """Model ID'sine göre uygun model instance'ını döndürür"""
        model_info = self.get_model_info(model_id)
        
        if not model_info:
            logger.warning(f"Model bulunamadı: {model_id}, varsayılan model kullanılıyor")
            return self.get_model_instance(self.default_model_id)
            
        if model_info.get("admin_only", False) and not user_is_admin:
            logger.warning(f"Admin-only model erişim denemesi: {model_id}")
            return self.get_model_instance(self.default_model_id)
            
        if not model_info.get("is_active", False):
            logger.warning(f"İnaktif model erişim denemesi: {model_id}")
            return self.get_model_instance(self.default_model_id)
        
        model_type = model_info["type"]
        
        try:
            if model_type == ModelType.LOCAL or model_type == ModelType.FINETUNED:
                # Yerelden modeli yükle
                from .llm_manager import LLMManager
                
                # Model ailesine göre yapılandırma belirle
                family = model_info.get("family", "other")
                config = MODEL_CONFIG.get(family, {})
                
                return LLMManager(
                    model_path_or_name=model_info["path"],
                    model_family=family
                )
                
            elif model_type == ModelType.OPENAI:
                # OpenAI API modelini kullan
                from .openai_manager import OpenAIManager
                return OpenAIManager(model_name=model_info["path"])
                
            elif model_type == ModelType.ANTHROPIC:
                # Anthropic API modelini kullan
                from .anthropic_manager import AnthropicManager
                return AnthropicManager(model_name=model_info["path"])
                
            else:
                logger.warning(f"Desteklenmeyen model türü: {model_type}")
                return self.get_model_instance(self.default_model_id)
                
        except Exception as e:
            logger.error(f"Model instance oluşturma hatası: {e}")
            return self.get_model_instance(self.default_model_id)
            
# Model registry singleton
model_registry = ModelRegistry()