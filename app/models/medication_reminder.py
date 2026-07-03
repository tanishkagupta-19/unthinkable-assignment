from datetime import datetime

from sqlalchemy import(
    Column,Integer,String,Date,Boolean,
    ForeignKey,DateTime
)
from sqlalchemy.orm import relationship

from app.database import Base


class MedicationReminder(Base):
    __tablename__="medication_reminders"

    id=Column(Integer,primary_key=True,index=True)
    appointment_id=Column(Integer,ForeignKey("appointments.id"),nullable=False)
    patient_id=Column(Integer,ForeignKey("users.id"),nullable=False)

    medication_name=Column(String(255),nullable=False)
    dosage=Column(String(100),nullable=False)
    frequency=Column(String(50),nullable=False)

    start_date=Column(Date,nullable=False)
    end_date=Column(Date,nullable=False)

    next_reminder_at=Column(DateTime,nullable=True)
    is_active=Column(Boolean,default=True)

    created_at=Column(DateTime,default=datetime.utcnow)

    appointment=relationship("Appointment",back_populates="medication_reminders")
