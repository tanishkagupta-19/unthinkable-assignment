from datetime import datetime

from sqlalchemy import Column,Integer,String,DateTime,Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__="users"

    id=Column(Integer,primary_key=True,index=True)
    email=Column(String(255),unique=True,nullable=False,index=True)
    password_hash=Column(String(255),nullable=False)
    full_name=Column(String(255),nullable=False)
    phone=Column(String(20),nullable=True)
    role=Column(String(20),nullable=False,default="patient")

    google_access_token=Column(Text,nullable=True)
    google_refresh_token=Column(Text,nullable=True)

    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

    doctor_profile=relationship("DoctorProfile",back_populates="user",uselist=False)
    patient_appointments=relationship(
"Appointment",
        back_populates="patient",
        foreign_keys="Appointment.patient_id",
)

    def __repr__(self):
        return f"<User {self.email}({self.role})>"
