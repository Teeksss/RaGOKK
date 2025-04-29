# Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
# (Mevcut auth.py koduna ekleyeceğimiz yeni fonksiyon)

async def get_current_user_ws(token: str, db: AsyncSession):
    """
    WebSocket'ler için kimlik doğrulama
    WebSocket route dependency olarak çalışması için 
    HttpException yerine ValueError fırlatır
    """
    credentials_exception = ValueError("Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await crud.user.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise ValueError("Inactive user")
    
    return UserInDB.from_orm(user)