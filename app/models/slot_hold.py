from datetime import datetime

from sqlalchemy import Column,Integer,Date,Time,ForeignKey,DateTime
from sqlalchemy.orm import relationship

from app.database import Base

HOLD_DURATION_MINUTES=5


class SlotHold(Base):
    __tablename__="slot_holds"

    id=Column(Integer,primary_key=True,index=True)
    doctor_id=Column(Integer,ForeignKey("doctor_profiles.id"),nullable=False)
    patient_id=Column(Integer,ForeignKey("users.id"),nullable=False)

    hold_date=Column(Date,nullable=False)
    hold_start_time=Column(Time,nullable=False)
    hold_end_time=Column(Time,nullable=False)

    expires_at=Column(DateTime,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow)

    doctor=relationship("DoctorProfile",back_populates="slot_holds")
