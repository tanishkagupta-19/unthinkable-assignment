from datetime import datetime

from sqlalchemy import(
    Column,Integer,String,Date,Time,Text,
    ForeignKey,DateTime,Index,text
)
from sqlalchemy.orm import relationship

from app.database import Base


class Appointment(Base):
    __tablename__="appointments"

    id=Column(Integer,primary_key=True,index=True)
    patient_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    doctor_id=Column(Integer,ForeignKey("doctor_profiles.id"),nullable=False)

    appointment_date=Column(Date,nullable=False)
    start_time=Column(Time,nullable=False)
    end_time=Column(Time,nullable=False)

    status=Column(String(20),default="booked",nullable=False)

    symptoms_text=Column(Text,nullable=True)

    # LLM-generated(nullable — LLM can fail)
    pre_visit_summary=Column(Text,nullable=True)
    urgency_level=Column(String(10),nullable=True)

    doctor_notes=Column(Text,nullable=True)
    prescription_text=Column(Text,nullable=True)
    post_visit_summary=Column(Text,nullable=True)

    patient_cal_event_id=Column(String(255),nullable=True)
    doctor_cal_event_id=Column(String(255),nullable=True)

    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

    patient=relationship("User",back_populates="patient_appointments")
    doctor=relationship("DoctorProfile",back_populates="appointments")
    medication_reminders=relationship(
"MedicationReminder",
        back_populates="appointment",
        cascade="all,delete-orphan",
)

    __table_args__=(
        Index(
"idx_no_double_booking",
"doctor_id","appointment_date","start_time",
            unique=True,
            postgresql_where=text("status!='cancelled'"),
),
)

    def __repr__(self):
        return f"<Appointment {self.id}({self.status})on {self.appointment_date}>"
