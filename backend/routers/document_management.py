# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)

# add_document_tag fonksiyonunun tamamlanması
@router.post("/{document_id}/tags")
async def add_document_tag(
    document_id: int,
    tag_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_active_user)
):
    """Dokümana etiket ekle"""
    try:
        # Dokümanı getir
        document = await document_repo.get_document_by_id(db, document_id, False)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doküman bulunamadı"
            )
        
        # Erişim kontrolü - sadece sahibi veya write izni olanlar etiket ekleyebilir
        if document.owner_id != current_user["id"]:
            has_permission = await document_repo.check_user_permission(
                db=db,
                document_id=document_id,
                user_id=current_user["id"],
                required_permission="write"
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bu dokümana etiket ekleme izniniz yok"
                )
        
        # Etiket verilerini al
        tag_name = tag_data.get("tag_name")
        
        if not tag_name or not isinstance(tag_name, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçerli bir etiket adı gerekli"
            )
        
        # Etiket adını temizle
        tag_name = tag_name.strip().lower()
        
        if not tag_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçerli bir etiket adı gerekli"
            )
        
        # Etiket uzunluğu kontrolü
        if len(tag_name) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Etiket adı çok uzun (maksimum 50 karakter)"
            )
            
        # Etiketi ekle
        try:
            tag = await document_repo.add_document_tag(
                db=db,
                document_id=document_id,
                tag_name=tag_name,
                user_id=current_user["id"]
            )
            
            return {
                "success": True,
                "message": "Etiket başarıyla eklendi",
                "tag_id": tag.id,
                "document_id": document_id,
                "tag_name": tag_name
            }
        except Exception as e:
            # Mükerrer etiket kontrolü
            if "duplicate" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu etiket zaten eklenmiş"
                )
            else:
                raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Etiket ekleme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Etiket eklenirken hata oluştu: {str(e)}"
        )

# Etiket silme endpointi eklenmesi
@router.delete("/{document_id}/tags/{tag_name}")
async def remove_document_tag(
    document_id: int,
    tag_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_active_user)
):
    """Doküman etiketini kaldır"""
    try:
        # Dokümanı getir
        document = await document_repo.get_document_by_id(db, document_id, False)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doküman bulunamadı"
            )
        
        # Erişim kontrolü - sadece sahibi veya write izni olanlar etiket silebilir
        if document.owner_id != current_user["id"]:
            has_permission = await document_repo.check_user_permission(
                db=db,
                document_id=document_id,
                user_id=current_user["id"],
                required_permission="write"
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bu dokümandan etiket silme izniniz yok"
                )
        
        # URL'den gelen etiket adını temizle
        tag_name = tag_name.strip().lower()
        
        # Etiketi kaldır
        removed = await document_repo.remove_document_tag(
            db=db,
            document_id=document_id,
            tag_name=tag_name
        )
        
        if not removed:
            return {
                "success": False,
                "message": "Etiket bulunamadı veya kaldırılamadı"
            }
            
        return {
            "success": True,
            "message": "Etiket başarıyla kaldırıldı",
            "document_id": document_id,
            "tag_name": tag_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Etiket kaldırma hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Etiket kaldırılırken hata oluştu: {str(e)}"
        )