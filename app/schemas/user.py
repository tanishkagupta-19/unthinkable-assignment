from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    id:int
    email:str
    full_name:str
    phone:str | None=None
    role:str
    created_at:datetime

    class Config:
        from_attributes=True
