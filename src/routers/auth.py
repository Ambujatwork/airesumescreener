from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..schemas.user import UserCreate, User, ProfileImageUpdate, BioUpdate
from ..models.user import User as UserModel
from ..crud.user import create_user, get_user_by_email, get_user_by_username
from ..dependencies.security import get_password_hash, create_access_token, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
from ..schemas.token import Token

router = APIRouter(tags=["Authentication"])

@router.post("/signup", response_model=User)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user)

# Update the LoginData model to only include username and password
class LoginData(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
): 
    # Fetch the user by username
    db_user = get_user_by_username(db, username=form_data.username)

    # Verify the user exists and the password is correct
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.put("/users/{user_id}/profile-image", response_model=User)
def update_profile_image(user_id: int, profile_image_update: ProfileImageUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.profile_image = profile_image_update.profile_image
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/bio", response_model=User)
def update_bio(user_id: int, bio_update: BioUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.bio = bio_update.bio
    db.commit()
    db.refresh(user)
    return user