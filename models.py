from database import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

class UserDB(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  name:Mapped[str] = mapped_column(String(50), nullable=False)
  age: Mapped[int] = mapped_column(Integer, nullable= False)
  role: Mapped[str] = mapped_column(String(30),nullable=False, default="user")
  hashed_password: Mapped[str] = mapped_column(String, nullable=False)

