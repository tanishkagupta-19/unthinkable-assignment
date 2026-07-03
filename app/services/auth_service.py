from datetime import datetime,timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")


def hash_password(password:str)-> str:
    return pwd_context.hash(password)


def verify_password(plain_password:str,hashed_password:str)-> bool:
    return pwd_context.verify(plain_password,hashed_password)


def create_access_token(user_id:int,role:str)-> str:
    expire=datetime.utcnow()+ timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload={
"sub":user_id,
"role":role,
"exp":expire,
    }
    return jwt.encode(payload,settings.SECRET_KEY,algorithm=settings.ALGORITHM)


def register_user(db:Session,email:str,password:str,full_name:str,
                   phone:str=None,role:str="patient")-> User:
    existing=db.query(User).filter(User.email==email).first()
    if existing:
        raise ValueError("A user with this email already exists")

    if role not in("patient","doctor"):
        raise ValueError("Can only register as patient or doctor")

    user=User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db:Session,email:str,password:str)-> User | None:
    user=db.query(User).filter(User.email==email).first()
    if not user:
        return None
    if not verify_password(password,user.password_hash):
        return None
    return user


def seed_admin(db:Session):
"""Create default admin if it doesn't exist."""
    existing=db.query(User).filter(User.email==settings.ADMIN_EMAIL).first()
    if existing:
        return

    admin=User(
        email=settings.ADMIN_EMAIL,
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        full_name="System Admin",
        role="admin",
)
    db.add(admin)
    db.commit()
    print(f"[SEED] Admin account created:{settings.ADMIN_EMAIL}")
