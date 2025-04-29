# Placeholder for response Pydantic models (if needed)
from pydantic import BaseModel
from typing import List, Optional, Dict

class QueryResponse(BaseModel):
    answer: str
    retrieved_ids: List[str]
    sources: Optional[List[Dict]] = None # Kaynak detayları