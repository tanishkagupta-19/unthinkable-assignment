from datetime import datetime

from sqlalchemy import Column,Integer,String,Date,ForeignKey,DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class DoctorLeave(Base):
    __tablename__="doctor_leaves"

    id=Column(Integer,primary_key=True,index=True)
    doctor_id=Column(Integer,ForeignKey("doctor_profiles.id"),nullable=False)
    leave_date=Column(Date,nullable=False)
    reason=Column(String(255),nullable=True)

    created_at=Column(DateTime,default=datetime.utcnow)

    doctor=relationship("DoctorProfile",back_populates="leaves")
