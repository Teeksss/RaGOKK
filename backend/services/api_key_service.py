    async def is_api_key_valid(
        self, 
        db: AsyncSession, 
        provider: Union[ApiProvider, str],
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> bool:
        """
        Belirtilen sağlayıcı için API anahtarının var ve aktif olup olmadığını kontrol eder
        """
        key_record = await self.repository.get_key_by_provider(db, provider)
        is_valid = key_record is not None and key_record.is_active and key_record.api_key is not None
        
        # Güvenlik logu: API anahtarı doğrulama
        if user_id:
            provider_str = provider if isinstance(provider, str) else provider.value
            await self._log_api_key_access(
                db, provider_str, user_id, "validate", is_valid,
                request=request,
                details={"reason": "not_found" if not key_record else 
                        "not_active" if not key_record.is_active else 
                        "no_key" if not key_record.api_key else 
                        "success"}
            )
        
        return is_valid
    
    async def verify_api_key(
        self,
        db: AsyncSession,
        provider: Union[ApiProvider, str],
        level: Optional[VerificationLevel] = VerificationLevel.STANDARD,
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        API anahtarının sağlayıcı servisine karşı doğrulamasını yapar
        """
        provider_str = provider if isinstance(provider, str) else provider.value
        
        try:
            # Anahtarı getir
            api_key = await self.get_api_key(db, provider, user_id=user_id, request=request)
            
            if not api_key:
                result = {
                    "provider": provider_str,
                    "is_valid": False,
                    "message": "API anahtarı bulunamadı veya aktif değil",
                    "details": None,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
            else:
                # API doğrulayıcısını kullanarak anahtarı doğrula
                result = await api_key_verifier.verify_key(provider_str, api_key, level)
            
            # Güvenlik logu: API anahtarı doğrulama
            if user_id:
                await self._log_api_key_access(
                    db, provider_str, user_id, "verify", result["is_valid"],
                    request=request,
                    details={
                        "message": result["message"],
                        "level": level.value if level else VerificationLevel.STANDARD.value
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"API anahtarı doğrulama hatası ({provider_str}): {e}")
            
            # Güvenlik logu: başarısız API anahtarı doğrulama
            if user_id:
                await self._log_api_key_access(
                    db, provider_str, user_id, "verify", False,
                    request=request,
                    details={"error": str(e)}
                )
                
            return {
                "provider": provider_str,
                "is_valid": False,
                "message": f"Doğrulama sırasında hata: {str(e)}",
                "details": None,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
    
    async def get_key_status(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """
        Tüm API anahtarlarının durumunu döndürür
        """
        keys = await self.repository.get_all_keys(db)
        
        status = {}
        
        # Enum değerlerini tarar ve tüm olası sağlayıcıları ekler
        for provider in ApiProvider:
            provider_str = provider.value.upper()
            key_record = next((k for k in keys if k.provider == provider), None)
            
            status[provider_str] = {
                "is_configured": key_record is not None,
                "is_active": key_record.is_active if key_record else False,
                "is_available": key_record is not None and key_record.is_active,
                "last_used": key_record.last_used if key_record else None,
                "last_updated": key_record.updated_at if key_record else None
            }
            
        return status
    
    async def _log_api_key_access(
        self,
        db: AsyncSession,
        provider: str,
        user_id: str,
        action: str,  # access, validate, verify
        success: bool,
        request: Optional[Request] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        API anahtarına erişimi güvenlik loguna kaydeder
        """
        try:
            # IP ve User-Agent bilgilerini al (varsa)
            ip_address = None
            user_agent = None
            
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            # Güvenlik logu kaydı oluştur
            await self.security_log_repo.create_log(
                db=db,
                log_type="api_key",
                action=action,
                user_id=user_id,
                resource_type="provider",
                resource_id=provider,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                success=success,
                severity="info" if success else "warning"
            )
            
        except Exception as e:
            logger.error(f"API anahtarı erişim günlüğü kaydedilemedi: {e}")
    
    async def create_api_key(
        self,
        db: AsyncSession,
        provider: Union[ApiProvider, str],
        api_key: str,
        description: Optional[str] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> ApiKey:
        """
        Yeni bir API anahtarı oluşturur ve güvenlik logunu kaydeder
        """
        provider_str = provider if isinstance(provider, str) else provider.value
        
        try:
            # Anahtarı oluştur
            new_key = await self.repository.create_key(
                db=db,
                provider=provider,
                api_key=api_key,
                description=description,
                is_active=is_active,
                metadata=metadata
            )
            
            # Önbelleği temizle
            await self.clear_cache(provider)
            
            # Güvenlik logu
            if user_id:
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="create",
                    success=True,
                    request=request,
                    details={
                        "description": description,
                        "is_active": is_active
                    }
                )
            
            # Webhook/Email bildirimi
            try:
                await notification_service.notify_api_key_change(
                    provider=provider_str,
                    change_type="create",
                    changed_by=user_id or "system",
                    details={
                        "description": description,
                        "is_active": is_active,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"API anahtarı oluşturma bildirimi gönderilemedi: {e}")
                
            return new_key
            
        except Exception as e:
            logger.error(f"API anahtarı oluşturma hatası: {e}")
            
            # Güvenlik logu
            if user_id:
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="create",
                    success=False,
                    request=request,
                    details={"error": str(e)}
                )
                
            raise
    
    async def update_api_key(
        self,
        db: AsyncSession,
        provider: Union[ApiProvider, str],
        update_data: Dict[str, Any],
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> ApiKey:
        """
        API anahtarını günceller ve güvenlik logunu kaydeder
        """
        provider_str = provider if isinstance(provider, str) else provider.value
        
        try:
            # Anahtarı güncelle
            updated_key = await self.repository.update_key(
                db=db,
                provider=provider,
                update_data=update_data
            )
            
            # Önbelleği temizle
            await self.clear_cache(provider)
            
            # Güvenlik logu
            if user_id:
                # API anahtarı değeri güncellendiyse log'da gizle
                safe_update_data = update_data.copy()
                if "api_key" in safe_update_data:
                    safe_update_data["api_key"] = "********"
                
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="update",
                    success=True,
                    request=request,
                    details={"updated_fields": list(update_data.keys())}
                )
            
            # Webhook/Email bildirimi
            try:
                # API anahtarı değeri güncellendiyse bildirimde gizle
                safe_update_data = update_data.copy()
                if "api_key" in safe_update_data:
                    safe_update_data["api_key"] = "********"
                
                await notification_service.notify_api_key_change(
                    provider=provider_str,
                    change_type="update",
                    changed_by=user_id or "system",
                    details={
                        "updated_fields": list(update_data.keys()),
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"API anahtarı güncelleme bildirimi gönderilemedi: {e}")
                
            return updated_key
            
        except Exception as e:
            logger.error(f"API anahtarı güncelleme hatası: {e}")
            
            # Güvenlik logu
            if user_id:
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="update",
                    success=False,
                    request=request,
                    details={"error": str(e)}
                )
                
            raise
    
    async def delete_api_key(
        self,
        db: AsyncSession,
        provider: Union[ApiProvider, str],
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> bool:
        """
        API anahtarını siler ve güvenlik logunu kaydeder
        """
        provider_str = provider if isinstance(provider, str) else provider.value
        
        try:
            # Anahtarı sil
            success = await self.repository.delete_key(
                db=db,
                provider=provider
            )
            
            # Önbelleği temizle
            await self.clear_cache(provider)
            
            # Güvenlik logu
            if user_id:
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="delete",
                    success=success,
                    request=request,
                    details=None
                )
            
            # Webhook/Email bildirimi
            if success:
                try:
                    await notification_service.notify_api_key_change(
                        provider=provider_str,
                        change_type="delete",
                        changed_by=user_id or "system",
                        details={
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"API anahtarı silme bildirimi gönderilemedi: {e}")
                    
            return success
            
        except Exception as e:
            logger.error(f"API anahtarı silme hatası: {e}")
            
            # Güvenlik logu
            if user_id:
                await self._log_api_key_access(
                    db=db,
                    provider=provider_str,
                    user_id=user_id,
                    action="delete",
                    success=False,
                    request=request,
                    details={"error": str(e)}
                )
                
            raise

# API Key Service singleton
api_key_service = ApiKeyService()