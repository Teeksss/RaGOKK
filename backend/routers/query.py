# Last reviewed: 2025-04-29 10:42:12 UTC (User: TeeksssRetrieval)
# query.py içine eklenecek yeni endpoint

@router.post("/query/prioritization-test", response_model=Dict[str, Any], tags=["Search"])
async def test_document_prioritization(
    query_data: Dict[str, Any] = Body(...),
    top_k: int = Query(5, ge=1, le=100),
    search_type: str = Query("hybrid"),
    expand_results: bool = Query(True),
    expand_query: bool = Query(True),
    current_user: User = Depends(get_current_active_user)
):
    """
    Belge önceliklendirme algoritmasını test eder ve sonuçların karşılaştırmasını gösterir
    """
    try:
        query = query_data.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is empty")
            
        # Standart arama (önceliklendirme olmadan)
        standard_results = await retrieval_system.retrieve(
            query=query,
            search_type=search_type,
            top_k=top_k,
            expand_top_k=expand_results,
            expand_query=expand_query
        )
        
        # Öncelikli belgeleri test etmek için örnek URL'ler oluştur
        for i, doc in enumerate(standard_results[:2]):
            if "url" not in doc or not doc["url"]:
                # Test için bu belgeye bir kurumsal URL ekleyelim
                corporate_domain = retrieval_system.priority_domains[0] if retrieval_system.priority_domains else "example.com"
                doc["url"] = f"https://{corporate_domain}/document-{i}"
        
        # Önceliklendirme için sonuçları kopyala
        prioritized_results = await retrieval_system._apply_document_prioritization(
            [doc.copy() for doc in standard_results]
        )
        
        # Sonuçları karşılaştır
        comparison = []
        
        for i, (std_doc, pri_doc) in enumerate(zip(standard_results, prioritized_results)):
            item = {
                "index": i,
                "title": std_doc.get("title", ""),
                "id": std_doc.get("id", ""),
                "url": std_doc.get("url", ""),
                "standard_score": std_doc.get("score", 0),
                "prioritized_score": pri_doc.get("score", 0),
                "boost_factor": pri_doc.get("priority_boost", 1.0),
                "priority_reasons": pri_doc.get("priority_reasons", []),
                "is_corporate": False,
                "is_recent": False,
                "is_reviewed": False
            }
            
            # Kurumsal domain kontrolü
            if "url" in std_doc and std_doc["url"] and retrieval_system.corporate_domain_pattern:
                item["is_corporate"] = bool(retrieval_system.corporate_domain_pattern.search(std_doc["url"]))
            
            # Yeni belge kontrolü (30 gün)
            if "created_at" in std_doc and std_doc["created_at"]:
                try:
                    now = datetime.datetime.now()
                    thirty_days_ago = now - datetime.timedelta(days=30)
                    
                    created_date = None
                    if isinstance(std_doc["created_at"], str):
                        created_date = datetime.datetime.fromisoformat(std_doc["created_at"].replace('Z', '+00:00'))
                    elif isinstance(std_doc["created_at"], datetime.datetime):
                        created_date = std_doc["created_at"]
                        
                    if created_date and created_date >= thirty_days_ago:
                        item["is_recent"] = True
                except:
                    pass
            
            # İncelenmiş belge kontrolü
            metadata = std_doc.get("metadata", {})
            if metadata.get("reviewed") == True:
                item["is_reviewed"] = True
            
            comparison.append(item)
        
        return {
            "query": query,
            "priority_settings": {
                "corporate_domains": retrieval_system.priority_domains,
                "corporate_boost": retrieval_system.priority_corporate_docs,
                "recent_boost": retrieval_system.priority_recent_docs,
                "reviewed_boost": retrieval_system.priority_reviewed_docs
            },
            "comparison_results": comparison
        }
    
    except Exception as e:
        logger.error(f"Error in document prioritization test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")