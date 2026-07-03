from datetime import date
from pydantic import BaseModel


class MedicationReminderCreate(BaseModel):
    medication_name:str
    dosage:str
    frequency:str
    start_date:date
    end_date:date


class MedicationReminderResponse(BaseModel):
    id:int
    medication_name:str
    dosage:str
    frequency:str
    start_date:date
    end_date:date
    is_active:bool

    class Config:
        from_attributes=True
