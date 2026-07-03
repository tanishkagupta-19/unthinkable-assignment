from datetime import date

from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.doctor import DoctorProfileResponse,TimeSlot
from app.schemas.appointment import(
    SlotHoldRequest,SlotHoldResponse,
    BookAppointmentRequest,AppointmentResponse,
    RescheduleRequest,
)
from app.services import doctor_service,appointment_service

router=APIRouter(prefix="/api/patients",tags=["Patients"])


@router.get("/doctors",response_model=list[DoctorProfileResponse])
def search_doctors(
    specialisation:str=Query(None,description="Filter by specialisation"),
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    profiles=doctor_service.list_doctors(db,specialisation)
    results=[]
    for p in profiles:
        resp=DoctorProfileResponse.model_validate(p)
        resp.doctor_name=p.user.full_name
        resp.doctor_email=p.user.email
        results.append(resp)
    return results


@router.get("/doctors/{doctor_id}/slots",response_model=list[TimeSlot])
def get_available_slots(
    doctor_id:int,
    appointment_date:date=Query(...,description="Date to check(YYYY-MM-DD)"),
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    try:
        slots=appointment_service.generate_available_slots(db,doctor_id,appointment_date)
        return slots
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.post("/appointments/hold",response_model=SlotHoldResponse)
def hold_slot(
    request:SlotHoldRequest,
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    try:
        hold=appointment_service.hold_slot(
            db=db,
            doctor_id=request.doctor_id,
            appointment_date=request.appointment_date,
            start_time=request.start_time,
            patient_id=patient.id,
)
        return SlotHoldResponse(
            hold_id=hold.id,
            doctor_id=hold.doctor_id,
            appointment_date=hold.hold_date,
            start_time=hold.hold_start_time,
            end_time=hold.hold_end_time,
            expires_at=hold.expires_at,
)
    except ValueError as e:
        raise HTTPException(status_code=409,detail=str(e))


@router.post("/appointments/book",response_model=AppointmentResponse)
def book_appointment(
    request:BookAppointmentRequest,
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    try:
        appointment=appointment_service.book_appointment(
            db=db,
            hold_id=request.hold_id,
            symptoms_text=request.symptoms_text,
            patient_id=patient.id,
)
        return _enrich_response(appointment,db)
    except ValueError as e:
        raise HTTPException(status_code=409,detail=str(e))


@router.get("/appointments",response_model=list[AppointmentResponse])
def list_my_appointments(
    status:str=Query(None,description="Filter by status(booked/completed/cancelled)"),
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    appointments=appointment_service.list_patient_appointments(db,patient.id,status)
    return [_enrich_response(a,db)for a in appointments]


@router.get("/appointments/{appointment_id}",response_model=AppointmentResponse)
def get_appointment(
    appointment_id:int,
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    appt=appointment_service.get_appointment(db,appointment_id)
    if not appt or appt.patient_id!=patient.id:
        raise HTTPException(status_code=404,detail="Appointment not found")
    return _enrich_response(appt,db)


@router.put("/appointments/{appointment_id}/cancel",response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id:int,
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    try:
        appt=appointment_service.cancel_appointment(db,appointment_id,patient.id)
        return _enrich_response(appt,db)
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.put("/appointments/{appointment_id}/reschedule",response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id:int,
    request:RescheduleRequest,
    patient:User=Depends(require_role("patient")),
    db:Session=Depends(get_db),
):
    try:
        new_appt=appointment_service.reschedule_appointment(
            db=db,
            appointment_id=appointment_id,
            patient_id=patient.id,
            new_date=request.new_date,
            new_start_time=request.new_start_time,
)
        return _enrich_response(new_appt,db)
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


def _enrich_response(appt,db:Session)-> AppointmentResponse:
    resp=AppointmentResponse.model_validate(appt)
    if appt.patient:
        resp.patient_name=appt.patient.full_name
        resp.patient_email=appt.patient.email
    if appt.doctor and appt.doctor.user:
        resp.doctor_name=appt.doctor.user.full_name
        resp.specialisation=appt.doctor.specialisation
    return resp
