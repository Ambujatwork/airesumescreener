from typing import Optional

from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

      
class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str

class UserInDB(UserBase):
    pass

    
    class Config:
        orm_mode = True

class User(UserInDB):
    pass

class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class ProfileImageUpdate(BaseModel):
    profile_image: str

class BioUpdate(BaseModel):
    bio: str

class UserRead(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True
    