# Last reviewed: 2025-04-29 11:06:31 UTC (User: Teekssseksiklikleri)

# _rerank_results metodunu güncelleyelim:

async def _rerank_results(
    self, 
    docs: List[Dict], 
    query: str, 
    language: str
) -> List[Dict]:
    """
    Sonuçları çeşitli faktörlere göre yeniden sıralar:
    - Gelişmiş cross-encoder reranking
    - İçerik kalite skoru
    - Sorgu terimleri yakınlık skoru
    """
    # Eğer doküman yoksa, doğrudan boş liste döndür
    if not docs:
        return []
    
    try:
        # 1. Cross-encoder reranker'ı kullan (varsa)
        try:
            from .reranker import reranker
            docs = await reranker.rerank(query, docs)
        except ImportError:
            logger.warning("Cross-encoder reranker import edilemedi, temel sıralama kullanılıyor.")
        except Exception as e:
            logger.error(f"Reranking işlemi sırasında hata: {e}")
    
        # 2. İçerik kalite faktörünü uygula
        for doc in docs:
            metadata = doc.get("metadata", {})
            quality_score = metadata.get("quality_score", 0.0)
            
            if quality_score > 0:
                # Belirli bir kalite skoru varsa, skoru boost et
                boost_factor = 1.0 + (quality_score * 0.2)  # 0.0-1.0 arası bir kalite skoru için %20'ye kadar boost
                doc["score"] *= boost_factor
                
                if "rerank_factors" not in doc:
                    doc["rerank_factors"] = []
                
                doc["rerank_factors"].append(f"quality:{boost_factor:.2f}")
        
        # 3. Sorgu terimleri yakınlık skoru
        query_terms = set(term.lower() for term in query.split() if len(term) > 2)
        
        # Eğer sorgu terimleri yeterince varsa, içerik eşleşmesine göre yeniden değerlendir
        if len(query_terms) >= 2:
            for doc in docs:
                content = doc.get("content", "").lower()
                title = doc.get("title", "").lower()
                
                # Başlıkta ve içerikte bulunan terim sayısı
                title_matches = sum(1 for term in query_terms if term in title)
                content_matches = sum(1 for term in query_terms if term in content)
                
                # Eşleşme oranları
                title_match_ratio = title_matches / len(query_terms) if query_terms else 0
                content_match_ratio = content_matches / len(query_terms) if query_terms else 0
                
                # Başlık daha önemli, 2x ağırlık ver
                term_score = (title_match_ratio * 2 + content_match_ratio) / 3
                
                # Eşleşme skoru yüksekse, boost uygula
                if term_score > 0.5:
                    boost_factor = 1.0 + (term_score * 0.15)  # En fazla %15 boost
                    doc["score"] *= boost_factor
                    
                    if "rerank_factors" not in doc:
                        doc["rerank_factors"] = []
                    
                    doc["rerank_factors"].append(f"term_match:{boost_factor:.2f}")
        
        # 4. Sonuçları skora göre yeniden sırala
        docs.sort(key=lambda x: x["score"], reverse=True)
        
    except Exception as e:
        logger.error(f"Reranking sırasında hata: {e}")
    
    return docs