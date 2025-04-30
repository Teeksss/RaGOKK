# Last reviewed: 2025-04-30 05:43:44 UTC (User: Teeksss)
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
import re
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import uuid
import secrets
from datetime import datetime, timedelta, timezone

from ..models.user import User
from ..models.organization import Organization
from ..models.role_permission import Role
from ..schemas.user import UserCreate, UserUpdate
from ..auth.jwt import get_password_hash, verify_password
from ..core.exceptions import ValidationError, NotFoundError, ConflictError, ErrorCode

class UserService:
    """Kullanıcı işlemleri servisi"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_registration_data(self, user_in: UserCreate) -> None:
        """
        Kullanıcı kayıt verilerinin geçerliliğini doğrular
        
        Args:
            user_in: Kullanıcı giriş verileri
            
        Raises:
            ValidationError: Geçersiz veriler
        """
        # Email kontrolü
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, user_in.email):
            raise ValidationError(
                message="Invalid email address",
                error_code=ErrorCode.INVALID_FORMAT,
                detail="Please enter a valid email address"
            )
        
        # Şifre karmaşıklık kontrolü
        if len(user_in.password) < 8:
            raise ValidationError(
                message="Password too short",
                error_code=ErrorCode.INVALID_INPUT,
                detail="Password must be at least 8 characters long"
            )
        
        # Şifre karmaşıklık gereksinimleri
        if not any(char.isdigit() for char in user_in.password):
            raise ValidationError(
                message="Password requires a number",
                error_code=ErrorCode.INVALID_INPUT,
                detail="Password must contain at least one number"
            )
            
        if not any(char.isupper() for char in user_in.password):
            raise ValidationError(
                message="Password requires an uppercase letter",
                error_code=ErrorCode.INVALID_INPUT,
                detail="Password must contain at least one uppercase letter"
            )
        
        # Email kullanılabilirlik kontrolü
        email_exists = await self._check_email_exists(user_in.email)
        if email_exists:
            raise ConflictError(
                message="Email already registered",
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                detail="This email is already in use"
            )
        
        # Kullanıcı adı kontrolü (boş değilse)
        if user_in.username:
            username_exists = await self._check_username_exists(user_in.username)
            if username_exists:
                raise ConflictError(
                    message="Username already taken",
                    error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                    detail="This username is already in use"
                )
    
    async def _check_email_exists(self, email: str) -> bool:
        """
        E-posta adresinin veritabanında olup olmadığını kontrol eder
        
        Args:
            email: E-posta adresi
            
        Returns:
            bool: E-posta adresi varsa True, yoksa False
        """
        stmt = select(User).filter(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
    
    async def _check_username_exists(self, username: str) -> bool:
        """
        Kullanıcı adının veritabanında olup olmadığını kontrol eder
        
        Args:
            username: Kullanıcı adı
            
        Returns:
            bool: Kullanıcı adı varsa True, yoksa False
        """
        stmt = select(User).filter(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
    
    async def create_user(self, user_in: UserCreate) -> User:
        """
        Yeni bir kullanıcı oluşturur
        
        Args:
            user_in: Kullanıcı oluşturma verileri
            
        Returns:
            User: Oluşturulan kullanıcı
            
        Raises:
            IntegrityError: Veritabanı bütünlük hatası
        """
        try:
            # Organizasyonu kontrol et
            organization = None
            if user_in.organization_id:
                stmt = select(Organization).filter(Organization.id == user_in.organization_id)
                result = await self.db.execute(stmt)
                organization = result.scalars().first()
                
                if not organization:
                    raise NotFoundError(
                        message="Organization not found",
                        detail=f"Organization with ID {user_in.organization_id} not found"
                    )
            
            # Şifreyi hashle
            hashed_password = get_password_hash(user_in.password)
            
            # Kullanıcı nesnesini oluştur
            new_user = User(
                email=user_in.email,
                username=user_in.username,
                password=hashed_password,
                full_name=user_in.full_name,
                is_active=True,
                is_verified=False,
                is_superuser=user_in.is_superuser if hasattr(user_in, 'is_superuser') else False,
                organization_id=user_in.organization_id if organization else None,
                verification_token=secrets.token_urlsafe(32)
            )
            
            # Varsayılan rolleri ata
            if not user_in.is_superuser:
                # Standart kullanıcı rolünü bul ve ata
                stmt = select(Role).filter(Role.code == "user")
                result = await self.db.execute(stmt)
                user_role = result.scalars().first()
                
                if user_role:
                    new_user.roles.append(user_role)
            else:
                # Süper kullanıcı rolünü bul ve ata
                stmt = select(Role).filter(Role.code == "admin")
                result = await self.db.execute(stmt)
                admin_role = result.scalars().first()
                
                if admin_role:
                    new_user.roles.append(admin_role)
            
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            
            return new_user
            
        except IntegrityError as e:
            await self.db.rollback()
            # Hata mesajından özel bir hata türü belirle
            if "unique constraint" in str(e).lower():
                if "email" in str(e).lower():
                    raise ConflictError(
                        message="Email already registered",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
                elif "username" in str(e).lower():
                    raise ConflictError(
                        message="Username already taken",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
            
            # Genel bütünlük hatası
            raise ConflictError(
                message="Database integrity error",
                error_code=ErrorCode.INTEGRITY_ERROR,
                detail=str(e)
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Kullanıcıyı ID'ye göre al
        
        Args:
            user_id: Kullanıcı ID
            
        Returns:
            Optional[User]: Kullanıcı nesnesi veya None
        """
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Kullanıcıyı e-posta adresine göre al
        
        Args:
            email: Kullanıcı e-posta adresi
            
        Returns:
            Optional[User]: Kullanıcı nesnesi veya None
        """
        stmt = select(User).filter(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> User:
        """
        Kullanıcı bilgilerini günceller
        
        Args:
            user_id: Kullanıcı ID
            user_update: Güncellenecek bilgiler
            
        Returns:
            User: Güncellenmiş kullanıcı
            
        Raises:
            NotFoundError: Kullanıcı bulunamazsa
            ConflictError: Veritabanı bütünlük hatası
        """
        try:
            # Kullanıcıyı bul
            stmt = select(User).filter(User.id == user_id)
            result = await self.db.execute(stmt)
            db_user = result.scalars().first()
            
            if not db_user:
                raise NotFoundError(
                    message="User not found",
                    detail=f"User with ID {user_id} not found"
                )
            
            # Güncelleme verilerini hazırla
            update_data = user_update.dict(exclude_unset=True)
            
            # Şifre güncellenmişse hashle
            if "password" in update_data:
                update_data["password"] = get_password_hash(update_data["password"])
            
            # Email güncelleniyorsa benzersizlik kontrolü yap
            if "email" in update_data and update_data["email"] != db_user.email:
                email_exists = await self._check_email_exists(update_data["email"])
                if email_exists:
                    raise ConflictError(
                        message="Email already registered",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
            
            # Kullanıcı adı güncelleniyorsa benzersizlik kontrolü yap
            if "username" in update_data and update_data["username"] != db_user.username:
                username_exists = await self._check_username_exists(update_data["username"])
                if username_exists:
                    raise ConflictError(
                        message="Username already taken", 
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
            
            # Organizasyon ID güncelleniyorsa organizasyonu kontrol et
            if "organization_id" in update_data and update_data["organization_id"] != db_user.organization_id:
                if update_data["organization_id"]:
                    stmt = select(Organization).filter(Organization.id == update_data["organization_id"])
                    result = await self.db.execute(stmt)
                    organization = result.scalars().first()
                    
                    if not organization:
                        raise NotFoundError(
                            message="Organization not found",
                            detail=f"Organization with ID {update_data['organization_id']} not found"
                        )
            
            # Kullanıcı bilgilerini güncelle
            for field, value in update_data.items():
                setattr(db_user, field, value)
            
            await self.db.commit()
            await self.db.refresh(db_user)
            
            return db_user
            
        except IntegrityError as e:
            await self.db.rollback()
            
            # Hata mesajından özel bir hata türü belirle
            if "unique constraint" in str(e).lower():
                if "email" in str(e).lower():
                    raise ConflictError(
                        message="Email already registered",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
                elif "username" in str(e).lower():
                    raise ConflictError(
                        message="Username already taken",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS
                    )
            
            # Genel bütünlük hatası
            raise ConflictError(
                message="Database integrity error",
                error_code=ErrorCode.INTEGRITY_ERROR,
                detail=str(e)
            )
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Kullanıcıyı siler
        
        Args:
            user_id: Kullanıcı ID
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            NotFoundError: Kullanıcı bulunamazsa
        """
        try:
            # Kullanıcıyı bul
            stmt = select(User).filter(User.id == user_id)
            result = await self.db.execute(stmt)
            db_user = result.scalars().first()
            
            if not db_user:
                raise NotFoundError(
                    message="User not found",
                    detail=f"User with ID {user_id} not found"
                )
            
            # Kullanıcıyı sil
            await self.db.delete(db_user)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            raise
    
    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """
        Kullanıcıya rol atar
        
        Args:
            user_id: Kullanıcı ID
            role_id: Rol ID
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            NotFoundError: Kullanıcı veya rol bulunamazsa
        """
        # Kullanıcıyı bul
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise NotFoundError(
                message="User not found",
                detail=f"User with ID {user_id} not found"
            )
        
        # Rolü bul
        stmt = select(Role).filter(Role.id == role_id)
        result = await self.db.execute(stmt)
        role = result.scalars().first()
        
        if not role:
            raise NotFoundError(
                message="Role not found", 
                detail=f"Role with ID {role_id} not found"
            )
        
        # Kullanıcının zaten bu rolü var mı kontrol et
        if role in user.roles:
            return True
        
        # Kullanıcıya rolü ata
        user.roles.append(role)
        await self.db.commit()
        
        return True
    
    async def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """
        Kullanıcıdan rol kaldırır
        
        Args:
            user_id: Kullanıcı ID
            role_id: Rol ID
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            NotFoundError: Kullanıcı veya rol bulunamazsa
        """
        # Kullanıcıyı bul
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise NotFoundError(
                message="User not found",
                detail=f"User with ID {user_id} not found"
            )
        
        # Rolü bul
        stmt = select(Role).filter(Role.id == role_id)
        result = await self.db.execute(stmt)
        role = result.scalars().first()
        
        if not role:
            raise NotFoundError(
                message="Role not found",
                detail=f"Role with ID {role_id} not found"
            )
        
        # Kullanıcının bu rolü var mı kontrol et
        if role not in user.roles:
            return True
        
        # Kullanıcıdan rolü kaldır
        user.roles.remove(role)
        await self.db.commit()
        
        return True
    
    async def get_user_roles(self, user_id: str) -> List[Role]:
        """
        Kullanıcının rollerini döndürür
        
        Args:
            user_id: Kullanıcı ID
            
        Returns:
            List[Role]: Kullanıcı rolleri
            
        Raises:
            NotFoundError: Kullanıcı bulunamazsa
        """
        # Kullanıcıyı bul
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise NotFoundError(
                message="User not found",
                detail=f"User with ID {user_id} not found"
            )
        
        return user.roles
    
    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """
        Kullanıcı şifresini değiştirir
        
        Args:
            user_id: Kullanıcı ID
            current_password: Mevcut şifre
            new_password: Yeni şifre
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            NotFoundError: Kullanıcı bulunamazsa
            ValidationError: Mevcut şifre hatalıysa veya yeni şifre gereksinimlere uymuyorsa
        """
        # Kullanıcıyı bul
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise NotFoundError(
                message="User not found",
                detail=f"User with ID {user_id} not found"
            )
        
        # Mevcut şifreyi kontrol et
        if not verify_password(current_password, user.password):
            raise ValidationError(
                message="Incorrect password",
                error_code=ErrorCode.INVALID_CREDENTIALS,
                detail="Current password is incorrect"
            )
        
        # Yeni şifre gereksinimleri kontrol et
        if len(new_password) < 8:
            raise ValidationError(
                message="Password too short",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must be at least 8 characters long"
            )
        
        if not any(char.isdigit() for char in new_password):
            raise ValidationError(
                message="Password requires a number",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must contain at least one number"
            )
        
        if not any(char.isupper() for char in new_password):
            raise ValidationError(
                message="Password requires an uppercase letter",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must contain at least one uppercase letter"
            )
        
        # Yeni şifreyi hashle ve güncelle
        user.password = get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        return True
    
    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Şifre sıfırlama talebi oluşturur
        
        Args:
            email: Kullanıcı e-posta adresi
            
        Returns:
            Optional[str]: Sıfırlama token'ı veya None
        """
        # Kullanıcıyı bul
        stmt = select(User).filter(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            # Kullanıcı bulunamasa bile hata döndürme (güvenlik)
            return None
        
        # Token oluştur
        reset_token = secrets.token_urlsafe(32)
        
        # Sona erme zamanı (24 saat)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # User veritabanında güncelle
        user.password_reset_token = reset_token
        user.password_reset_expires = expires
        
        await self.db.commit()
        
        return reset_token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Token ile şifre sıfırlar
        
        Args:
            token: Sıfırlama token'ı
            new_password: Yeni şifre
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            ValidationError: Token geçersiz veya süresi dolmuşsa
        """
        # Token ile kullanıcıyı bul
        stmt = select(User).filter(
            User.password_reset_token == token,
            User.password_reset_expires > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise ValidationError(
                message="Invalid or expired reset token",
                error_code=ErrorCode.INVALID_TOKEN,
                detail="The password reset token is invalid or has expired"
            )
        
        # Yeni şifre gereksinimleri kontrol et
        if len(new_password) < 8:
            raise ValidationError(
                message="Password too short",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must be at least 8 characters long"
            )
        
        if not any(char.isdigit() for char in new_password):
            raise ValidationError(
                message="Password requires a number",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must contain at least one number"
            )
        
        if not any(char.isupper() for char in new_password):
            raise ValidationError(
                message="Password requires an uppercase letter",
                error_code=ErrorCode.INVALID_INPUT,
                detail="New password must contain at least one uppercase letter"
            )
        
        # Şifreyi güncelle ve token bilgilerini temizle
        user.password = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        return True
    
    async def verify_email(self, token: str) -> bool:
        """
        E-posta doğrulama işlemi
        
        Args:
            token: Doğrulama token'ı
            
        Returns:
            bool: Başarılı ise True
            
        Raises:
            ValidationError: Token geçersizse
        """
        # Token ile kullanıcıyı bul
        stmt = select(User).filter(User.verification_token == token)
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise ValidationError(
                message="Invalid verification token",
                error_code=ErrorCode.INVALID_TOKEN,
                detail="The email verification token is invalid"
            )
        
        # Kullanıcıyı doğrulanmış olarak işaretle
        user.is_verified = True
        user.verification_token = None
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        return True
    
    async def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        organization_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Kullanıcıları listeler
        
        Args:
            skip: Atlanacak kayıt sayısı
            limit: Maksimum kayıt sayısı
            search: Arama terimi
            organization_id: Organizasyon filtresi
            is_active: Aktif/pasif filtresi
            
        Returns:
            Dict[str, Any]: Kullanıcılar ve toplam sayı
        """
        # Sorgu hazırla
        query = select(User)
        count_query = select(func.count(User.id))
        
        # Filtreleri uygula
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
            count_query = count_query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
            count_query = count_query.filter(User.organization_id == organization_id)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
            count_query = count_query.filter(User.is_active == is_active)
        
        # Toplam sayı
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Sayfalama
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        # Sonuçları hazırla
        user_list = []
        for user in users:
            user_data = user.to_dict()
            user_data["roles"] = [role.code for role in user.roles]
            user_list.append(user_data)
        
        return {
            "total": total,
            "items": user_list,
            "page": skip // limit + 1,
            "page_size": limit
        }