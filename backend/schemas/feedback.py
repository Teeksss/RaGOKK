# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional
from datetime import datetime

class FeedbackCreate(BaseModel):
    """Geri bildirim oluşturma şeması"""
    rating: int = Field(..., ge=1, le=5, description="Derecelendirme puanı (1-5)")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Geri bildirim açıklaması")
    feedback_type: str = Field("answer_quality", description="Geri bildirim türü")
    query_data: Optional[Dict[str, Any]] = Field(None, description="Sorgu ile ilgili ek veriler")

class FeedbackResponse(BaseModel):
    """Geri bildirim yanıt şeması"""
    id: str
    query_id: str
    user_id: Optional[str]
    rating: int
    feedback: Optional[str]
    feedback_type: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class FeedbackList(BaseModel):
    """Geri bildirim listesi şeması"""
    total: int
    items: List[FeedbackResponse]