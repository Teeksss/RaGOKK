# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class VersionBase(BaseModel):
    """Versiyon temel şeması"""
    document_id: str
    version_number: int
    change_description: Optional[str] = None
    created_by: str
    created_at: datetime

class VersionContent(VersionBase):
    """İçerikli versiyon şeması"""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class VersionResponse(VersionBase):
    """Versiyon yanıt şeması"""
    id: str
    
    class Config:
        orm_mode = True

class VersionListResponse(BaseModel):
    """Versiyon listesi yanıt şeması"""
    document_id: str
    versions: List[VersionResponse]
    total: int

class VersionDiffResponse(BaseModel):
    """Versiyon farkı yanıt şeması"""
    document_id: str
    from_version: int
    to_version: Any  # int veya "current" string'i olabilir
    diff_text: str
    diff_html: str