# Mevcut auth.py dosyasına 2FA desteği ekle

@router.post("/login", response_model=TokenSchema)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    response: Response = None,
    background_tasks: BackgroundTasks = None
):
    """
    Email ve şifre ile giriş yapar
    """
    user = await user_repository.get_user_by_email(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.password):
        # Başarısız giriş kaydı
        if background_tasks:
            from backend.middleware.rate_limiter import LoginHandler, rate_limiter
            login_handler = LoginHandler(rate_limiter)
            background_tasks.add_task(
                login_handler.record_failed_login, 
                request
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Başarılı giriş sayacını sıfırla
    if background_tasks:
        from backend.middleware.rate_limiter import LoginHandler, rate_limiter
        login_handler = LoginHandler(rate_limiter)
        background_tasks.add_task(
            login_handler.reset_failed_logins, 
            request
        )
    
    # 2FA kontrolü
    if user.metadata and user.metadata.get("2fa_enabled", False):
        # Session'a kullanıcı ID'sini kaydet (2FA doğrulaması için)
        request.session["2fa_pending_user_id"] = str(user.id)
        
        # 2FA bekleniyor
        return {
            "require_2fa": True,
            "user_id": str(user.id),
            "email": user.email
        }
    
    # 2FA yoksa normal login
    user_data = {
        "sub": str(user.id),
        "id": str(user.id),
        "email": user.email,
        "roles": user.roles or ["user"],
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "permissions": user.metadata.get("permissions", []) if user.metadata else []
    }
    
    # Token oluştur
    access_token = EnhancedJWTHandler.create_access_token(data=user_data)
    refresh_token = EnhancedJWTHandler.create_refresh_token(data={"sub": str(user.id)})
    
    # Cookie'ye kaydet
    if response:
        EnhancedJWTHandler.setup_token_cookies(
            response=response, 
            access_token=access_token["token"],
            refresh_token=refresh_token["token"]
        )
    
    # Son giriş bilgilerini güncelle
    await user_repository.update_user(
        db=db,
        user_id=str(user.id),
        last_login=datetime.utcnow()
    )
    
    return {
        "access_token": access_token["token"],
        "refresh_token": refresh_token["token"],
        "token_type": "bearer",
        "expires_at": access_token["expires_at"]
    }