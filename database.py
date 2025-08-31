DATABASE_URL = "sqlite:///./app.db"

from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL, connect_args = {"check_same_thread": False})

from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass

Base.metadata.create_all(bind=engine)

def get_db():
 db = SessionLocal()
 try:
  yield db
 finally:
  db.close()