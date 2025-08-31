from typing import Optional
from pydantic import BaseModel

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