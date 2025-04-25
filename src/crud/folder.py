from sqlalchemy.orm import Session
from src.models.folder import Folder
from src.schemas.folder import FolderCreate

def get_folders_by_user(db: Session, user_id: int):
    return db.query(Folder).filter(Folder.user_id == user_id).all()

def get_folder(db: Session, folder_id: int, user_id: int):
    return db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user_id).first()

def create_folder(db: Session, folder: FolderCreate, user_id: int):
    db_folder = Folder(
        name=folder.name,
        description=folder.description,
        user_id=user_id
    )
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

def delete_folder(db: Session, folder_id: int, user_id: int):
    folder = get_folder(db, folder_id, user_id)
    if folder:
        db.delete(folder)
        db.commit()
        return True
    return False