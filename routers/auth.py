from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from models import UserDB
from auth.auth import create_access_token, pwd_context,get_current_user

router = APIRouter(
    prefix="/login",
    tags=["auth"]
)


# Login
@router.post("/")
def login(form_data:OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
  db_user = db.query(UserDB).filter(UserDB.name == form_data.username).first()
  if not db_user:
    raise HTTPException(status_code=400, detail='Invalid username or password')
  if not pwd_context.verify(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail='Invalid username or password')
  
  access_token = create_access_token(data={"sub": db_user.name, "role":db_user.role})
  return {"access_token": access_token, "token_type": "bearer"}

@router.get("/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, you have access!"}
