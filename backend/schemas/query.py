# Mevcut query.py dosyasına eklenecek şema

class DocumentFilters(BaseModel):
    """Belge filtreleri şeması"""
    tags: Optional[List[str]] = Field(None, description="Etiket filtreleri")
    document_types: Optional[List[str]] = Field(None, description="Belge türü filtreleri")
    document_ids: Optional[List[str]] = Field(None, description="Belge ID filtreleri")
    date_after: Optional[datetime] = Field(None, description="Bu tarihten sonra oluşturulan belgeler")
    date_before: Optional[datetime] = Field(None, description="Bu tarihten önce oluşturulan belgeler")

class FilteredQueryRequest(BaseModel):
    """Filtreli sorgu istek şeması"""
    question: str = Field(..., min_length=3, max_length=2000, description="Kullanıcı sorusu")
    document_filters: Optional[DocumentFilters] = Field(None, description="Belge filtreleme kriterleri")
    prompt_template_id: Optional[str] = Field(None, description="Prompt şablonu ID")
    search_type: Optional[str] = Field("hybrid", description="Arama türü: semantic, hybrid, keyword")
    use_multimodal: Optional[bool] = Field(False, description="Multimodal RAG kullan")
    
    @validator('question')
    def question_must_not_be_empty(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Question must be at least 3 characters long')
        return v