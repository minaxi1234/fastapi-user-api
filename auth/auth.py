from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta

from database import get_db
from models import UserDB
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme= OAuth2PasswordBearer(tokenUrl="login", scheme_name="JWT",auto_error=True,)

SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# creating tokens
def create_access_token(data:dict, expires_delta: timedelta= None):
  to_encode = data.copy()
  if expires_delta:
    expires = datetime.utcnow()+ expires_delta
  else:
    expires = datetime.utcnow()+ timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode.update({"exp":  expires})
  encoded_jwt = jwt.encode(to_encode, SECRET_KEY,algorithm=ALGORITHM)
  return encoded_jwt

# Create token verification
def get_current_user(token: str = Depends(oauth2_scheme)):
  try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
      username: str = payload.get("sub")
      role: str = payload.get("role")
      if username is None or role is None:
          raise HTTPException(status_code=401, detail="Invalid token")
      return {"username": username, "role": role}
  except JWTError:
      raise HTTPException(status_code=401, detail="Invalid token")
  
# Admin only access
def admin_required(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action"
        )
    return current_user

# admin or user
def admin_or_user(user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)):
  if current_user["role"] == "admin":
    return True
  target_user = db.query(UserDB).filter(UserDB.id == user_id).first()
  if target_user is None:
    raise HTTPException(status_code=404, detail="User not found")
  if target_user.name == current_user["username"]:
    return True
  raise HTTPException(status_code=403, detail="You do not have permission to perform this action")