from fastapi import FastAPI, HTTPException, status, Path,  Depends, Security, Query
from typing import Optional,List
from pydantic import BaseModel
from sqlalchemy.orm  import Session
from database import SessionLocal, Base, engine
from models import UserDB
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

Base.metadata.create_all(bind=engine)

SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


oauth2_scheme= OAuth2PasswordBearer(tokenUrl="login", scheme_name="JWT",auto_error=True,)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

def get_db():
 db = SessionLocal()
 try:
  yield db
 finally:
  db.close()


# Base pydantic model
class User(BaseModel):
 name:str
 age:int
 role:str = "user"
 password: str

class UserResponse(BaseModel):
 id: int
 name: str
 age: int
 role: str

class Config:
  orm_mode = True

class UpdateUser(BaseModel):
 name: Optional[str] = None
 age: Optional[int] = None
 role: Optional[str] = None

class UserLogin(BaseModel):
  name:str
  password:str


# creating tokens
def create_access_token(data:dict, expires_delta: Optional[timedelta]= None):
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



# get all users
@app.get("/users/", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    db:Session=Depends(get_db),
    current_user: str = Depends(get_current_user)
):
  
  if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
  if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
  allowed_sort_fields = {"id", "name", "age", "role"}

  # only allow sorting on safe columns
  if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {sorted(allowed_sort_fields)}")

  if order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")
  
  sort_column = getattr(UserDB, sort_by)

  if order == "desc":
        sort_column = sort_column.desc() 
  
    # --- build query, apply sort, pagination ---
  query = db.query(UserDB).order_by(sort_column)
  users = query.offset(skip).limit(limit).all()  # offset then limit === pagination

  return users
  


# Search user
@app.get("/users/search", response_model=List[UserResponse])
def search_users(filters: UpdateUser= Depends(), db: Session= Depends(get_db),current_user: str = Depends(get_current_user)):
 query = db.query(UserDB)
 
 if filters.name:
  query = query.filter(UserDB.name.ilike(f"%{filters.name}%"))
 if filters.age:
  query = query.filter(UserDB.age == filters.age)
 if filters.role:
  query = query.filter(UserDB.role.ilike(f"%{filters.role}%"))

 results = query.all()

 if not results:
  raise HTTPException(status_code=404,  detail="No users found matching the filters")
 
 return results

# Get users
@app.get("/users/{user_id}", response_model=UserResponse,)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),admin_user: dict=Depends(admin_or_user)):
 user = db.query(UserDB).filter(UserDB.id == user_id).first()

 if not user:
   raise HTTPException(status_code=404, detail="User not exists.")
 
 return user



#  Create user
@app.post("/users/",status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user(user: User, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user),admin_user: dict = Depends(admin_required)):
 existing_user = db.query(UserDB).filter(UserDB.name == user.name).first()
 if existing_user:
  raise HTTPException(status_code=400, detail="User already exists.")

 hashed_password = pwd_context.hash(user.password)  

 # Create a new UserDB object
 new_user = UserDB(
   name= user.name,
   age= user.age,
   role= user.role,
   hashed_password= hashed_password
  )

 # Add to the session and commit
 db.add(new_user)
 db.commit()
 db.refresh(new_user)

 return new_user


# Login
@app.post("/login/")
def login(form_data:OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
  db_user = db.query(UserDB).filter(UserDB.name == form_data.username).first()
  if not db_user:
    raise HTTPException(status_code=400, detail='Invalid username or password')
  if not pwd_context.verify(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail='Invalid username or password')
  
  access_token = create_access_token(data={"sub": db_user.name, "role":db_user.role})
  return {"access_token": access_token, "token_type": "bearer"}


#  Update user 
@app.put("/users/{user_id}", status_code= status.HTTP_200_OK, response_model=UserResponse)
def update_user(user_id:int, updated_user:UpdateUser,db:Session=Depends(get_db), current_user: str = Depends(get_current_user),permission:bool = Depends(admin_or_user)):
  # Find the user in the database
  user= db.query(UserDB).filter(UserDB.id == user_id).first()

  if not user:
   raise HTTPException(status_code=404, detail="user not found")
  
  if updated_user.name is not None:
   user.name = updated_user.name
  if updated_user.age is not None:
   user.age = updated_user.age
  if updated_user.role is not None:
   if current_user["role"].lower() != "admin":
     raise HTTPException(status_code=403, detail="Only admin can change user roles")
   user.role = updated_user.role

  db.commit()
  db.refresh(user)

  return user

 
# Delete user
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user), permission: bool = Depends(admin_or_user)):
 user = db.query(UserDB).filter(UserDB.id == user_id).first()

 if not user:
  raise HTTPException(status_code=404, detail="User not found")

 db.delete(user)
 db.commit()

 return {"message": f"User with id {user_id} has been deleted"}

#  protected
@app.get("/protected")
def protected_route(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello {current_user}, you have access!"}

# creating default admin
@app.on_event("startup")
def create_default_admin():
  db = SessionLocal()
  try:
    admin_user = db.query(UserDB).filter(UserDB.role == "admin").first()
    if not admin_user:
      default_admin = UserDB(
        name = "admin",
        age= 30,
        role = 'admin',
        hashed_password =pwd_context.hash("admin123")
      )
      db.add(default_admin)
      db.commit()
      print("Default admin created: username: 'admin', password:'admin124'")
    else:
      print("Admin already exists, skipping creation.")
  finally:
    db.close()
