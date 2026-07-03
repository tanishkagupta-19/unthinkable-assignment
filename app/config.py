from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL:str="postgresql://postgres:postgres@localhost:5432/healthcare_db"

    SECRET_KEY:str="change-me-in-production"
    ALGORITHM:str="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:int=60

    ADMIN_EMAIL:str="admin@clinic.com"
    ADMIN_PASSWORD:str="admin123"

    OPENAI_API_KEY:str=""
    SENDGRID_API_KEY:str=""
    EMAIL_FROM:str="noreply@clinic.com"

    GOOGLE_CLIENT_ID:str=""
    GOOGLE_CLIENT_SECRET:str=""
    GOOGLE_REDIRECT_URI:str="http://localhost:8000/api/auth/google/callback"

    class Config:
        env_file=".env"
        extra="ignore"


settings=Settings()
