from app.models import User
from sqlalchemy.orm import Session

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()