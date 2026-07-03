from pydantic import BaseModel,EmailStr


class RegisterRequest(BaseModel):
    email:EmailStr
    password:str
    full_name:str
    phone:str | None=None
    role:str="patient"


class LoginRequest(BaseModel):
    email:EmailStr
    password:str


class TokenResponse(BaseModel):
    access_token:str
    token_type:str="bearer"
