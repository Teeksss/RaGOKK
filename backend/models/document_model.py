from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class Document(BaseModel):
    """Elasticsearch'te saklanacak temel belge modeli."""
    id: str = Field(..., description="Belgenin benzersiz ID'si")
    text: str = Field(..., description="Belgenin ana metin içeriği")
    source: Optional[str] = Field(None, description="Verinin kaynağı (örn: website, pdf, email)")
    metadata: Optional[Dict[str, Any]] = Field({}, description="Ek meta veriler (örn: url, filename, author)")

    # Elasticsearch mapping'ine eklenecek alanlar için buraya eklemeler yapılabilir
    # Örneğin:
    # filename: Optional[str] = None
    # url: Optional[str] = None
    # created_at: Optional[datetime] = None
    # text_vector: Optional[List[float]] = None # Bu genellikle indeksleme sırasında eklenir