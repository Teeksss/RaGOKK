# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.database import User, UserToken
from ..auth import get_password_hash, verify_password
from ..schemas import UserCreate, UserUpdate  # Bunlar oluşturulmalı
from ..utils.logger import get_logger

logger = get_logger(__name__)

def get_user(db: Session, username: str):
    """Kullanıcı adına göre kullanıcıyı getirir"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    """ID'ye göre kullanıcıyı getirir"""
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Tüm kullanıcıları getirir (sayfalama ile)"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate, roles: list = None):
    """Yeni kullanıcı oluşturur"""
    if roles is None:
        roles = ["user"]
        
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        roles=roles
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Yeni kullanıcı oluşturuldu: {user.username}")
        return db_user
    except IntegrityError:
        db.rollback()
        logger.error(f"Kullanıcı oluşturma hatası: {user.username} kullanıcı adı veya email zaten mevcut")
        return None

def update_user(db: Session, user_id: int, user_update):
    """Kullanıcı bilgilerini günceller"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
        
    # Dict'ten işlenecek alanları çıkar
    update_data = {}
    if hasattr(user_update, "dict"):
        update_data = user_update.dict(exclude_unset=True)
    else:
        update_data = {k: v for k, v in user_update.items() if v is not None}
        
    # Password varsa hash'le
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]
    
    for key, value in update_data.items():
        if hasattr(db_user, key):
            setattr(db_user, key, value)
            
    db.commit()
    db.refresh(db_user)
    logger.info(f"Kullanıcı güncellendi: ID {user_id}")
    return db_user

def delete_user(db: Session, user_id: int):
    """Kullanıcıyı siler"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
        
    db.delete(db_user)
    db.commit()
    logger.info(f"Kullanıcı silindi: ID {user_id}")
    return True

def get_user_token(db: Session, user_id: int, service: str):
    """Kullanıcıya ait servis token'ını getirir"""
    return db.query(UserToken).filter(
        UserToken.user_id == user_id,
        UserToken.service == service
    ).first()

def save_user_token(db: Session, user_id: int, service: str, encrypted_token: str, expires_at=None):
    """Kullanıcıya ait servis token'ını kaydeder/günceller"""
    token = get_user_token(db, user_id, service)
    
    if token:
        token.encrypted_token = encrypted_token
        if expires_at:
            token.expires_at = expires_at
    else:
        token = UserToken(
            user_id=user_id,
            service=service,
            encrypted_token=encrypted_token,
            expires_at=expires_at
        )
        db.add(token)
    
    try:
        db.commit()
        logger.info(f"{service} token kaydedildi: User ID {user_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"{service} token kaydedilirken hata: {e}", exc_info=True)
        return False

def delete_user_token(db: Session, user_id: int, service: str):
    """Kullanıcıya ait servis token'ını siler"""
    token = get_user_token(db, user_id, service)
    if not token:
        return False
    
    db.delete(token)
    db.commit()
    logger.info(f"{service} token silindi: User ID {user_id}")
    return True