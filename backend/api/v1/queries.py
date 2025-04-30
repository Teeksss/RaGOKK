# Last reviewed: 2025-04-30 06:23:58 UTC (User: Teeksss)
# ...mevcut importlar...

from ...services.multi_vector_retriever import MultiVectorRetriever
from ...schemas.query import QueryRequest, QueryResponse, QueryHistoryList, QueryOptions

# MultiVector Retriever hizmetini başlat
multi_vector_retriever = MultiVectorRetriever()

@router.post("/", response_model=QueryResponse)
async def create_query(
    query_request: QueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir sorgu oluşturur ve yanıt döndürür
    """
    try:
        # İstekteki arama türünü kontrol et ve gerekirse düzelt
        search_type = query_request.search_type.lower() if query_request.search_type else "hybrid"
        if search_type not in ["hybrid", "dense", "sparse"]:
            search_type = "hybrid"
            
        # Sorguyu arama motoru üzerinde çalıştır
        retrieval_results = await multi_vector_retriever.search(
            query_text=query_request.question,
            limit=10,  # Varsayılan değer, ayarlanabilir
            organization_id=current_user.get("organization_id"),
            filters=None,  # Ek filtreler eklenebilir
            search_type=search_type
        )
        
        # Sonuçları işle
        search_results = retrieval_results["results"]
        
        # LLM yanıtı oluştur
        query = await query_processor.process_query(
            db=db,
            query_request=query_request,
            search_results=search_results,
            user_id=current_user["id"],
            organization_id=current_user.get("organization_id")
        )
        
        # İleri düzey arama bilgilerini sonuca ekle
        if hasattr(query, 'metadata') and query.metadata:
            query.metadata["retriever_stats"] = {
                "search_type": retrieval_results["search_type"],
                "processing_time_ms": retrieval_results["processing_time_ms"],
                "most_effective_retriever": retrieval_results["most_effective_retriever"],
                "result_count": retrieval_results["count"],
                "hybrid_method": retrieval_results.get("hybrid_method", "")
            }
        
        # Audit log
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="query",
            resource_id=str(query.id),
            details={
                "question": query_request.question,
                "search_type": search_type,
                "result_count": retrieval_results["count"]
            },
            db=db
        )
        
        # Yanıtı döndür
        return query
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        
        # Audit log - başarısız
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="query",
            status="failure",
            details={"question": query_request.question, "error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )