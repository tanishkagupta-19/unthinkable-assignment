from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest,LoginRequest,TokenResponse
from app.schemas.user import UserResponse
from app.services import auth_service
from app.config import settings

router=APIRouter(prefix="/api/auth",tags=["Authentication"])


@router.post("/register",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
def register(request:RegisterRequest,db:Session=Depends(get_db)):
    try:
        user=auth_service.register_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            phone=request.phone,
            role=request.role,
)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.post("/login",response_model=TokenResponse)
def login(request:LoginRequest,db:Session=Depends(get_db)):
    user=auth_service.authenticate_user(db,request.email,request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
)

    token=auth_service.create_access_token(user.id,user.role)
    return TokenResponse(access_token=token)


@router.get("/me",response_model=UserResponse)
def get_me(current_user:User=Depends(get_current_user)):
    return current_user


@router.get("/google/connect")
def google_connect(current_user:User=Depends(get_current_user)):
"""Redirect to Google OAuth consent screen for calendar access."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503,detail="Google OAuth not configured")

    params={
"client_id":settings.GOOGLE_CLIENT_ID,
"redirect_uri":settings.GOOGLE_REDIRECT_URI,
"response_type":"code",
"scope":"https://www.googleapis.com/auth/calendar",
"access_type":"offline",
"prompt":"consent",
"state":str(current_user.id),
    }
    auth_url="https://accounts.google.com/o/oauth2/v2/auth"
    query="&".join(f"{k}={v}"for k,v in params.items())

    return RedirectResponse(url=f"{auth_url}?{query}")


@router.get("/google/callback")
def google_callback(code:str,state:str,db:Session=Depends(get_db)):
"""Exchange OAuth code for tokens and store them."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503,detail="Google OAuth not configured")

    token_url="https://oauth2.googleapis.com/token"
    data={
"code":code,
"client_id":settings.GOOGLE_CLIENT_ID,
"client_secret":settings.GOOGLE_CLIENT_SECRET,
"redirect_uri":settings.GOOGLE_REDIRECT_URI,
"grant_type":"authorization_code",
    }

    try:
        response=httpx.post(token_url,data=data)
        response.raise_for_status()
        tokens=response.json()
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Token exchange failed:{e}")

    user_id=int(state)
    user=db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404,detail="User not found")

    user.google_access_token=tokens.get("access_token")
    if"refresh_token"in tokens:
        user.google_refresh_token=tokens["refresh_token"]
    db.commit()

    return {
"message":"Google Calendar connected successfully",
"user_id":user_id,
    }
