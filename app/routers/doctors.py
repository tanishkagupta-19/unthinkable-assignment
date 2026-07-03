from datetime import date

from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from app.schemas.appointment import AppointmentResponse,CompleteAppointmentRequest
from app.schemas.doctor import DoctorProfileResponse
from app.schemas.prescription import MedicationReminderCreate
from app.services import appointment_service,reminder_service

router=APIRouter(prefix="/api/doctors",tags=["Doctors"])


@router.get("/profile",response_model=DoctorProfileResponse)
def get_my_profile(
    doctor_user:User=Depends(require_role("doctor")),
    db:Session=Depends(get_db),
):
    profile=(
        db.query(DoctorProfile)
        .filter(DoctorProfile.user_id==doctor_user.id)
        .first()
)
    if not profile:
        raise HTTPException(status_code=404,detail="Doctor profile not found")

    resp=DoctorProfileResponse.model_validate(profile)
    resp.doctor_name=doctor_user.full_name
    resp.doctor_email=doctor_user.email
    return resp


@router.get("/appointments",response_model=list[AppointmentResponse])
def list_my_appointments(
    status:str=Query(None,description="Filter by status"),
    appointment_date:date=Query(None,description="Filter by date"),
    doctor_user:User=Depends(require_role("doctor")),
    db:Session=Depends(get_db),
):
    appointments=appointment_service.list_doctor_appointments(
        db,doctor_user.id,status,appointment_date
)
    results=[]
    for appt in appointments:
        resp=AppointmentResponse.model_validate(appt)
        if appt.patient:
            resp.patient_name=appt.patient.full_name
            resp.patient_email=appt.patient.email
        if appt.doctor and appt.doctor.user:
            resp.doctor_name=appt.doctor.user.full_name
            resp.specialisation=appt.doctor.specialisation
        results.append(resp)
    return results


@router.get("/appointments/{appointment_id}",response_model=AppointmentResponse)
def get_appointment(
    appointment_id:int,
    doctor_user:User=Depends(require_role("doctor")),
    db:Session=Depends(get_db),
):
    appt=appointment_service.get_appointment(db,appointment_id)
    if not appt:
        raise HTTPException(status_code=404,detail="Appointment not found")

    profile=(
        db.query(DoctorProfile)
        .filter(DoctorProfile.user_id==doctor_user.id)
        .first()
)
    if not profile or appt.doctor_id!=profile.id:
        raise HTTPException(status_code=403,detail="Not your appointment")

    resp=AppointmentResponse.model_validate(appt)
    if appt.patient:
        resp.patient_name=appt.patient.full_name
        resp.patient_email=appt.patient.email
    resp.doctor_name=doctor_user.full_name
    resp.specialisation=profile.specialisation
    return resp


@router.put("/appointments/{appointment_id}/complete",response_model=AppointmentResponse)
def complete_appointment(
    appointment_id:int,
    request:CompleteAppointmentRequest,
    medications:list[MedicationReminderCreate]=None,
    doctor_user:User=Depends(require_role("doctor")),
    db:Session=Depends(get_db),
):
    try:
        appt=appointment_service.complete_appointment(
            db=db,
            appointment_id=appointment_id,
            doctor_user_id=doctor_user.id,
            doctor_notes=request.doctor_notes,
            prescription_text=request.prescription_text,
)

        if medications:
            try:
                med_dicts=[m.model_dump()for m in medications]
                reminder_service.create_medication_reminders(db,appointment_id,med_dicts)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to create medication reminders:{e}"
)

        resp=AppointmentResponse.model_validate(appt)
        if appt.patient:
            resp.patient_name=appt.patient.full_name
            resp.patient_email=appt.patient.email
        if appt.doctor and appt.doctor.user:
            resp.doctor_name=appt.doctor.user.full_name
            resp.specialisation=appt.doctor.specialisation
        return resp

    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))
