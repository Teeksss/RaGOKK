# Mevcut document_filter.py dosyasına eklenecek metodlar

async def get_available_tags(self, 
                         db: AsyncSession,
                         organization_id: Optional[str] = None,
                         user_id: Optional[str] = None) -> List[str]:
    """
    Kullanıcının erişebildiği tüm belge etiketlerini getirir
    
    Args:
        db: Veritabanı oturumu
        organization_id: Organizasyon ID
        user_id: Kullanıcı ID
        
    Returns:
        List[str]: Etiket listesi
    """
    try:
        # Belgeleri al
        stmt = select(Document.metadata)
        
        # Filtreler
        conditions = []
        
        # Organizasyon filtresi
        if organization_id:
            conditions.append(Document.organization_id == organization_id)
            
        # Kullanıcı filtresi (organizasyon yoksa)
        elif user_id:
            conditions.append(Document.user_id == user_id)
        
        # Koşulları uygula
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Sorguyu çalıştır
        result = await db.execute(stmt)
        metadatas = result.scalars().all()
        
        # Tüm etiketleri topla
        all_tags = set()
        for metadata in metadatas:
            if metadata and "tags" in metadata:
                tags = metadata["tags"]
                if isinstance(tags, list):
                    all_tags.update(tags)
        
        return sorted(list(all_tags))
        
    except Exception as e:
        logger.error(f"Error getting available tags: {str(e)}")
        return []

async def get_available_document_types(self, 
                                   db: AsyncSession,
                                   organization_id: Optional[str] = None) -> List[str]:
    """
    Kullanıcının erişebildiği belge türlerini getirir
    
    Args:
        db: Veritabanı oturumu
        organization_id: Organizasyon ID
        
    Returns:
        List[str]: Belge türü listesi
    """
    try:
        # Belge türlerini al
        stmt = select(Document.file_type).distinct()
        
        # Organizasyon filtresi
        if organization_id:
            stmt = stmt.where(Document.organization_id == organization_id)
        
        # Sorguyu çalıştır
        result = await db.execute(stmt)
        file_types = result.scalars().all()
        
        return sorted(list(file_types))
        
    except Exception as e:
        logger.error(f"Error getting available document types: {str(e)}")
        return []