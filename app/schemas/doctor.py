from datetime import time,date,datetime
from pydantic import BaseModel


class DoctorProfileCreate(BaseModel):
    user_id:int
    specialisation:str
    qualification:str | None=None
    slot_duration_minutes:int=30
    working_hours_start:time
    working_hours_end:time
    working_days:str="Mon,Tue,Wed,Thu,Fri"


class DoctorProfileUpdate(BaseModel):
    specialisation:str | None=None
    qualification:str | None=None
    slot_duration_minutes:int | None=None
    working_hours_start:time | None=None
    working_hours_end:time | None=None
    working_days:str | None=None


class DoctorProfileResponse(BaseModel):
    id:int
    user_id:int
    doctor_name:str | None=None
    doctor_email:str | None=None
    specialisation:str
    qualification:str | None=None
    slot_duration_minutes:int
    working_hours_start:time
    working_hours_end:time
    working_days:str
    created_at:datetime

    class Config:
        from_attributes=True


class DoctorLeaveCreate(BaseModel):
    leave_date:date
    reason:str | None=None


class DoctorLeaveResponse(BaseModel):
    id:int
    doctor_id:int
    leave_date:date
    reason:str | None=None
    created_at:datetime

    class Config:
        from_attributes=True


class TimeSlot(BaseModel):
    start_time:time
    end_time:time
    is_available:bool=True
