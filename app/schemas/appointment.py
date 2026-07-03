from datetime import date,time,datetime
from pydantic import BaseModel


class SlotHoldRequest(BaseModel):
    doctor_id:int
    appointment_date:date
    start_time:time


class SlotHoldResponse(BaseModel):
    hold_id:int
    doctor_id:int
    appointment_date:date
    start_time:time
    end_time:time
    expires_at:datetime
    message:str="Slot held for 5 minutes. Please confirm booking."


class BookAppointmentRequest(BaseModel):
    hold_id:int
    symptoms_text:str


class RescheduleRequest(BaseModel):
    new_date:date
    new_start_time:time


class AppointmentResponse(BaseModel):
    id:int
    patient_id:int
    patient_name:str | None=None
    patient_email:str | None=None
    doctor_id:int
    doctor_name:str | None=None
    specialisation:str | None=None
    appointment_date:date
    start_time:time
    end_time:time
    status:str
    symptoms_text:str | None=None
    pre_visit_summary:str | None=None
    urgency_level:str | None=None
    doctor_notes:str | None=None
    prescription_text:str | None=None
    post_visit_summary:str | None=None
    created_at:datetime

    class Config:
        from_attributes=True


class CompleteAppointmentRequest(BaseModel):
    doctor_notes:str
    prescription_text:str | None=None
