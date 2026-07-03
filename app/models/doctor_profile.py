from datetime import datetime

from sqlalchemy import Column,Integer,String,Time,ForeignKey,DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class DoctorProfile(Base):
    __tablename__="doctor_profiles"

    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"),unique=True,nullable=False)

    specialisation=Column(String(100),nullable=False,index=True)
    qualification=Column(String(255),nullable=True)
    slot_duration_minutes=Column(Integer,default=30)

    working_hours_start=Column(Time,nullable=False)
    working_hours_end=Column(Time,nullable=False)
    working_days=Column(String(100),default="Mon,Tue,Wed,Thu,Fri")

    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

    user=relationship("User",back_populates="doctor_profile")
    leaves=relationship("DoctorLeave",back_populates="doctor",cascade="all,delete-orphan")
    appointments=relationship("Appointment",back_populates="doctor")
    slot_holds=relationship("SlotHold",back_populates="doctor",cascade="all,delete-orphan")
