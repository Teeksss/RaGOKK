# Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EvaluationItem(BaseModel):
    """Tek bir değerlendirme örneği"""
    question: str = Field(..., description="Değerlendirilen soru")
    ground_truth: Optional[str] = Field(None, description="Referans cevap (varsa)")
    model_answer: str = Field(..., description="Model tarafından üretilen cevap")
    contexts: List[str] = Field(default_factory=list, description="Kullanılan bağlam belgeleri")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Metrik sonuçları")


class EvaluationResult(BaseModel):
    """Değerlendirme sonucu"""
    metrics: Dict[str, float] = Field(..., description="Ortalama metrik sonuçları")
    items: List[EvaluationItem] = Field(default_factory=list, description="Değerlendirilen öğeler")
    timestamp: str = Field(..., description="Değerlendirme zamanı")
    model_name: str = Field(..., description="Değerlendirilen model adı")
    
    
class EvaluationRequest(BaseModel):
    """Değerlendirme isteği"""
    examples: Optional[List[Dict]] = Field(None, description="Değerlendirilecek örnekler (yoksa rastgele oluşturulur)")
    metrics: Optional[List[str]] = Field(None, description="Kullanılacak metrikler")
    sample_size: Optional[int] = Field(5, ge=1, le=50, description="Rastgele örnek sayısı")
    model_name: Optional[str] = Field(None, description="Değerlendirilecek model adı")


class FineTuningExample(BaseModel):
    """Fine-tuning için örnek veri"""
    question: str = Field(..., description="Soru")
    context: Optional[str] = Field(None, description="Bağlam")
    answer: str = Field(..., description="Cevap")


class FineTuningRequest(BaseModel):
    """Fine-tuning isteği"""
    model_name: str = Field(..., description="Base model adı")
    examples: List[FineTuningExample] = Field(..., description="Eğitim örnekleri")
    output_model_name: Optional[str] = Field(None, description="Kaydedilecek model adı (varsayılan: otomatik)")
    epochs: Optional[int] = Field(3, ge=1, le=10, description="Eğitim epoch sayısı")
    use_lora: Optional[bool] = Field(True, description="LoRA kullanılıp kullanılmayacağı")
    use_8bit: Optional[bool] = Field(False, description="8-bit quantization kullanılıp kullanılmayacağı")
    learning_rate: Optional[float] = Field(3e-5, description="Öğrenme oranı")
    batch_size: Optional[int] = Field(8, ge=1, le=32, description="Batch boyutu")


class ModelInfo(BaseModel):
    """Model bilgisi"""
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model adı")
    base_model: str = Field(..., description="Base model adı")
    type: str = Field(..., description="Model tipi")
    created_at: str = Field(..., description="Oluşturulma zamanı")
    owner: Optional[str] = Field(None, description="Model sahibi")
    metrics: Optional[Dict[str, float]] = Field(None, description="Model metrikleri")
    description: Optional[str] = Field(None, description="Model açıklaması")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Model parametreleri")
    size_kb: Optional[int] = Field(None, description="Model boyutu (KB)")
    is_active: bool = Field(True, description="Model aktif mi")