import uuid
from app.database import Base
from sqlalchemy import Column, UUID, String

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key= True, default=uuid.uuid4)
    email= Column(String, unique= True, nullable= False,)
    hashed_password = Column(String, nullable = True)
    github_id = Column(String, nullable= True, index= True, unique= True)
    username = Column(String, nullable = True)