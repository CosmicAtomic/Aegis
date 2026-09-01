import uuid
from app.database import Base
from sqlalchemy import Column, UUID, String

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key= True, default=uuid.uuid4)
    email= Column(String, unique= True, nullable= False,)
    hashed_password = Column(String, nullable = False)
