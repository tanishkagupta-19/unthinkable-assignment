import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.doctor_profile import DoctorProfile
from app.models.doctor_leave import DoctorLeave
from app.models.appointment import Appointment
from app.models.user import User
from app.services import email_service

logger=logging.getLogger(__name__)


def create_doctor_profile(db:Session,user_id:int,specialisation:str,
                           qualification:str=None,slot_duration_minutes:int=30,
                           working_hours_start=None,working_hours_end=None,
                           working_days:str="Mon,Tue,Wed,Thu,Fri")-> DoctorProfile:
    user=db.query(User).filter(User.id==user_id).first()
    if not user:
        raise ValueError("User not found")
    if user.role!="doctor":
        raise ValueError("User is not registered as a doctor")

    existing=db.query(DoctorProfile).filter(DoctorProfile.user_id==user_id).first()
    if existing:
        raise ValueError("Doctor profile already exists for this user")

    profile=DoctorProfile(
        user_id=user_id,
        specialisation=specialisation,
        qualification=qualification,
        slot_duration_minutes=slot_duration_minutes,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end,
        working_days=working_days,
)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_doctor_profile(db:Session,profile_id:int,**kwargs)-> DoctorProfile:
    profile=db.query(DoctorProfile).filter(DoctorProfile.id==profile_id).first()
    if not profile:
        raise ValueError("Doctor profile not found")

    for key,value in kwargs.items():
        if value is not None and hasattr(profile,key):
            setattr(profile,key,value)

    db.commit()
    db.refresh(profile)
    return profile


def get_doctor_profile(db:Session,profile_id:int)-> DoctorProfile | None:
    return db.query(DoctorProfile).filter(DoctorProfile.id==profile_id).first()


def list_doctors(db:Session,specialisation:str=None)-> list[DoctorProfile]:
    query=db.query(DoctorProfile)
    if specialisation:
        query=query.filter(
            DoctorProfile.specialisation.ilike(f"%{specialisation}%")
)
    return query.all()


def add_doctor_leave(db:Session,doctor_id:int,leave_date:date,
                      reason:str=None)-> dict:
    """Cancel any booked appointments on the leave date and notify patients."""
    profile=db.query(DoctorProfile).filter(DoctorProfile.id==doctor_id).first()
    if not profile:
        raise ValueError("Doctor not found")

    existing_leave=(
        db.query(DoctorLeave)
        .filter(DoctorLeave.doctor_id==doctor_id,DoctorLeave.leave_date==leave_date)
        .first()
)
    if existing_leave:
        raise ValueError(f"Leave already marked for {leave_date}")

    leave=DoctorLeave(
        doctor_id=doctor_id,
        leave_date=leave_date,
        reason=reason,
)
    db.add(leave)

    affected=(
        db.query(Appointment)
        .filter(
            Appointment.doctor_id==doctor_id,
            Appointment.appointment_date==leave_date,
            Appointment.status=="booked",
)
        .all()
)

    cancelled_count=0
    doctor_user=profile.user

    for appt in affected:
        appt.status="cancelled"
        cancelled_count +=1

        patient=db.query(User).filter(User.id==appt.patient_id).first()
        if patient:
            email_service.send_cancellation_notice(
                db=db,
                email=patient.email,
                name=patient.full_name,
                date_str=str(leave_date),
                time_str=str(appt.start_time),
                reason=f"Dr. {doctor_user.full_name} is on leave on {leave_date}",
)
            logger.info(f"Cancelled appointment {appt.id}(doctor leave),notified {patient.email}")

    db.commit()

    return {
"leave":leave,
"cancelled_appointments":cancelled_count,
    }


def get_doctor_leaves(db:Session,doctor_id:int)-> list[DoctorLeave]:
    return(
        db.query(DoctorLeave)
        .filter(DoctorLeave.doctor_id==doctor_id)
        .order_by(DoctorLeave.leave_date)
        .all()
)


def delete_doctor_profile(db:Session,profile_id:int)-> bool:
    profile=db.query(DoctorProfile).filter(DoctorProfile.id==profile_id).first()
    if not profile:
        return False
    db.delete(profile)
    db.commit()
    return True
