# documents.py dosyasına eklenecek kod

# Yükleme endpoint'ine auto_summarize parametresini ekle
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    apply_ocr: bool = Form(False),
    segmentation_strategy: str = Form("paragraph"),
    auto_summarize: bool = Form(True),  # Otomatik özet parametresi
    tags: List[str] = Form([]),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir belge yükler ve oluşturur
    - **title**: Belge başlığı
    - **file**: Yüklenecek dosya
    - **apply_ocr**: OCR işlemi uygulansın mı? (varsayılan: False)
    - **segmentation_strategy**: Segmentasyon stratejisi ('paragraph', 'sentence', 'heading', 'chunk')
    - **auto_summarize**: Belge için otomatik özet oluşturulsun mu? (varsayılan: True)
    - **tags**: Belge etiketleri (opsiyonel)
    """
    try:
        # ... [mevcut kod] ...
        
        # Belgeyi işle
        processed_document = await document_processor.process_document(
            file_path=file_path,
            title=title,
            user_id=current_user["id"],
            document_id=str(document.id),
            tags=tags,
            apply_ocr=apply_ocr,
            segmentation_strategy=segmentation_strategy,
            auto_summarize=auto_summarize  # Parametre ekle
        )
        
        # ... [mevcut kod] ...
        
        # Belge metadatası için summary_scheduled durumunu belirt
        if document.metadata is None:
            document.metadata = {}
            
        document.metadata["auto_summarize"] = auto_summarize
        
        # Eğer otomatik özet isteniyorsa, arka planda özet işlemini başlat
        if auto_summarize:
            # Belge işlendiği için burada summarize işlemini başlatabiliriz
            background_tasks.add_task(
                summarize_document_task,
                document_id=str(document.id),
                db=db
            )
        
        # ... [mevcut kod] ...
    
    except Exception as e:
        # ... [mevcut kod] ...

# Background task fonksiyonu
async def summarize_document_task(document_id: str, db: AsyncSession):
    """
    Arka planda özet oluşturma işlemi
    """
    try:
        logger.info(f"Starting background summarization for document {document_id}")
        
        # Özetleyici servisi oluştur
        document_summarizer = DocumentSummarizer()
        
        # Özet oluştur
        result = await document_summarizer.process_document(db, document_id)
        
        if result["success"]:
            logger.info(f"Summarization completed for document {document_id}")
        else:
            logger.error(f"Summarization failed for document {document_id}: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error in background summarization task: {str(e)}")