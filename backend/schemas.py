# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
from typing import Optional, List
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    
class UserCreate(UserBase):
    password: str
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    
class UserInDB(UserBase):
    id: int
    disabled: bool = False
    roles: List[str] = ["user"]
    
    class Config:
        orm_mode = True
        
class UserResponse(UserBase):
    id: int
    disabled: bool
    roles: List[str]
    
    class Config:
        orm_mode = True