# Mevcut importlar...
from .prompt_engine import PromptEngine

class QueryProcessor:
    """
    Sorgu işleme servisi
    """
    
    def __init__(self):
        """Servis başlangıç ayarları"""
        # ...mevcut init kodu...
        
        # Prompt motoru
        self.prompt_engine = PromptEngine()
    
    async def process_query(
        self,
        db: AsyncSession,
        query_request: QueryRequest,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        active_document: Optional[Dict[str, Any]] = None
    ) -> Query:
        """Kullanıcı sorgusunu işler"""
        # Başlangıç zamanı
        start_time = time.time()
        
        try:
            # Yeni sorgu nesnesi oluştur
            query = Query(
                question=query_request.question,
                user_id=user_id,
                organization_id=organization_id,
                prompt_template_id=query_request.prompt_template_id,
                search_type=query_request.search_type or "semantic",
                metadata={}
            )
            
            db.add(query)
            await db.flush()  # ID almak için flush
            
            # Sorgu iyileştirme...
            rewritten = await self.query_rewriter.rewrite_query(
                original_query=query_request.question,
                chat_history=chat_history,
                user_context={"user_id": user_id},
                active_document=active_document
            )
            
            # ...
            
            # Prompt şablonu seçim adımı (yeni)
            if not query_request.prompt_template_id:
                # Kullanıcı şablon belirtmediyse, dinamik şablon seçimi uygula
                optimal_prompt_result = await self.prompt_engine.get_optimal_prompt(
                    db=db,
                    query=search_query,  # İyileştirilmiş sorguyu kullan
                    metadata={
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "original_query": query_request.question
                    }
                )
                
                # Seçilen şablonu kaydet
                query.prompt_template_id = optimal_prompt_result["prompt_template"].id
                query.metadata["query_type"] = optimal_prompt_result["query_type"]
                prompt_template = optimal_prompt_result["prompt_template"]
            else:
                # Kullanıcının belirttiği şablonu kullan
                prompt_template = await self.prompt_repo.get_prompt_template_by_id(
                    db, query_request.prompt_template_id
                )
            
            # Kalan kod aynı...