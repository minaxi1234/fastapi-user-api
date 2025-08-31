from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.orm import Session

from database import get_db
from models import UserDB
from schemas.user import User, UserResponse, UpdateUser
from auth.auth import get_current_user, admin_required,admin_or_user, pwd_context

router = APIRouter(
  prefix="/users",
  tags=['users']
)

# get all users
@router.get("/users/", response_model=List[UserResponse],summary="Get all users")
def get_all_users(
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    db:Session=Depends(get_db),
    current_user: dict = Depends(get_current_user)
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
@router.get("/users/search", response_model=List[UserResponse],summary="Search all users")
def search_users(filters: UpdateUser= Depends(), db: Session= Depends(get_db),current_user: dict = Depends(get_current_user)):
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
@router.get("/users/{user_id}", response_model=UserResponse,summary="Get  users by id")
def get_user(user_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),admin_user: dict=Depends(admin_or_user)):
 user = db.query(UserDB).filter(UserDB.id == user_id).first()

 if not user:
   raise HTTPException(status_code=404, detail="User not exists.")
 
 return user

#  Create user
@router.post("/users/",status_code=status.HTTP_201_CREATED, response_model=UserResponse, summary="Create a new user")
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

#  Update user 
@router.put("/users/{user_id}", status_code= status.HTTP_200_OK, response_model=UserResponse,summary="Update users")
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
@router.delete("/users/{user_id}",summary="Delete users")
def delete_user(user_id: int, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user), permission: bool = Depends(admin_or_user)):
 user = db.query(UserDB).filter(UserDB.id == user_id).first()

 if not user:
  raise HTTPException(status_code=404, detail="User not found")

 db.delete(user)
 db.commit()

 return {"message": f"User with id {user_id} has been deleted"}