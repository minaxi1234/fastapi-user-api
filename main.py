from fastapi import FastAPI
from database import SessionLocal, Base, engine
from models import UserDB

from routers.users import router as users_router
from routers.auth import router as auth_router
from auth.auth import get_current_user, admin_required, admin_or_user, pwd_context

Base.metadata.create_all(bind=engine)


app = FastAPI(
  title="User Management API",
  description="""This is a **User Management System** built with FastAPI 

Features:
- User registration & login with JWT
- Role-Based Access Control (Admin / User)
- CRUD operations on users
- Password hashing & secure authentication
- Default admin created at startup""",
  version="1.0.0",
  contact={
    "name": "Meenakshi Sunil",
            "url": "",  
    "email": "meenakshisunil80@gmail.com"
  },
  license_info={
    "name": "MIT"
  }
)

app.include_router(users_router)
app.include_router(auth_router)

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
