# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)

async def get_documents(
    self,
    db: AsyncSession,
    user_id: str,
    include_public: bool = True,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Kullanıcının erişim izni olan dokümanları getirir
    
    Args:
        db: Veritabanı oturumu
        user_id: Kullanıcı ID'si
        include_public: Tüm public dokümanları dahil et
        filters: Arama filtreleri (search, tags, source_type, vb.)
        sort_by: Sıralama alanı
        sort_order: Sıralama (asc/desc)
        page: Sayfa numarası
        limit: Sayfa başına kayıt sayısı
        
    Returns:
        Tuple[List[Dict[str, Any]], int]: Dokümanlar listesi ve toplam kayıt sayısı
    """
    try:
        filters = filters or {}
        
        # Base query - kullanıcının erişebileceği dokümanları seç
        from sqlalchemy import or_
        from ..db.models import Document, UserDocumentPermission, DocumentTag
        
        query = select(Document)
        
        # Erişim filtreleri
        access_conditions = [
            Document.owner_id == user_id  # Kullanıcının kendi dokümanları
        ]
        
        if include_public:
            access_conditions.append(Document.is_public == True)  # Public dokümanlar
            
        # İzin verilen dokümanlar
        permission_subquery = select(UserDocumentPermission.document_id).where(
            UserDocumentPermission.user_id == user_id
        ).scalar_subquery()
        
        access_conditions.append(Document.id.in_(permission_subquery))
        
        # Erişim koşullarını birleştir (OR)
        query = query.where(or_(*access_conditions))
        
        # Arama filtresi
        if "search" in filters and filters["search"]:
            search_term = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Document.title.ilike(search_term),
                    Document.content.ilike(search_term)
                )
            )
        
        # Etiket filtresi
        if "tags" in filters and filters["tags"]:
            tag_list = filters["tags"]
            
            # Her bir etiket için bir subquery oluştur
            for tag in tag_list:
                tag_subquery = select(DocumentTag.document_id).where(
                    DocumentTag.tag_name == tag
                ).scalar_subquery()
                
                query = query.where(Document.id.in_(tag_subquery))
        
        # Kaynak tipi filtresi
        if "source_type" in filters and filters["source_type"]:
            query = query.where(Document.source_type == filters["source_type"])
        
        # Toplam kayıt sayısını hesapla
        count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar() or 0
        
        # Sıralama
        if sort_by in ['title', 'created_at', 'updated_at', 'last_viewed', 'view_count']:
            sort_column = getattr(Document, sort_by)
            
            if sort_order.lower() == 'desc':
                sort_column = sort_column.desc()
            else:
                sort_column = sort_column.asc()
                
            query = query.order_by(sort_column)
        else:
            # Varsayılan sıralama
            query = query.order_by(Document.updated_at.desc())
        
        # Sayfalama
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Sonuçları getir
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # Doküman listesini formatla
        document_list = []
        for doc in documents:
            # Metadata'yı JSON'dan parse et
            metadata = json.loads(doc.metadata) if doc.metadata else {}
            
            # Doküman bilgilerini hazırla
            document_data = {
                "id": doc.id,
                "title": doc.title,
                "owner_id": doc.owner_id,
                "source_type": doc.source_type,
                "is_processed": doc.is_processed,
                "is_public": doc.is_public,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "last_viewed": doc.last_viewed.isoformat() if doc.last_viewed else None,
                "view_count": doc.view_count,
                "is_owner": doc.owner_id == user_id,
                "metadata": {
                    "description": metadata.get("description"),
                    "file_size": metadata.get("file_size"),
                    "language": metadata.get("language"),
                    "word_count": metadata.get("word_count")
                }
            }
            
            # Etiketleri getir
            tags = await self.get_document_tags(db, doc.id)
            document_data["tags"] = [tag["tag_name"] for tag in tags]
            
            document_list.append(document_data)
        
        return document_list, total_count
        
    except Exception as e:
        logger.error(f"Doküman listeleme hatası: {e}")
        raise