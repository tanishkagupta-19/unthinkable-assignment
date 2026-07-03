from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.doctor import(
    DoctorProfileCreate,DoctorProfileUpdate,
    DoctorProfileResponse,DoctorLeaveCreate,DoctorLeaveResponse,
)
from app.schemas.appointment import AppointmentResponse
from app.services import doctor_service,appointment_service

router=APIRouter(prefix="/api/admin",tags=["Admin"])


@router.post("/doctors",response_model=DoctorProfileResponse)
def create_doctor(
    request:DoctorProfileCreate,
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    try:
        profile=doctor_service.create_doctor_profile(
            db=db,
            user_id=request.user_id,
            specialisation=request.specialisation,
            qualification=request.qualification,
            slot_duration_minutes=request.slot_duration_minutes,
            working_hours_start=request.working_hours_start,
            working_hours_end=request.working_hours_end,
            working_days=request.working_days,
)
        response=DoctorProfileResponse.model_validate(profile)
        response.doctor_name=profile.user.full_name
        response.doctor_email=profile.user.email
        return response
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.get("/doctors",response_model=list[DoctorProfileResponse])
def list_doctors(
    specialisation:str=None,
    admin:User=Depends(require_role("admin")),
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


@router.put("/doctors/{profile_id}",response_model=DoctorProfileResponse)
def update_doctor(
    profile_id:int,
    request:DoctorProfileUpdate,
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    try:
        update_data=request.model_dump(exclude_unset=True)
        profile=doctor_service.update_doctor_profile(db,profile_id,**update_data)
        resp=DoctorProfileResponse.model_validate(profile)
        resp.doctor_name=profile.user.full_name
        resp.doctor_email=profile.user.email
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.delete("/doctors/{profile_id}")
def delete_doctor(
    profile_id:int,
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    success=doctor_service.delete_doctor_profile(db,profile_id)
    if not success:
        raise HTTPException(status_code=404,detail="Doctor profile not found")
    return {"message":"Doctor profile deleted"}


@router.post("/doctors/{doctor_id}/leave")
def add_leave(
    doctor_id:int,
    request:DoctorLeaveCreate,
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    try:
        result=doctor_service.add_doctor_leave(
            db,doctor_id,request.leave_date,request.reason
)
        leave=result["leave"]
        return {
"message":f"Leave marked for {request.leave_date}",
"leave_id":leave.id,
"cancelled_appointments":result["cancelled_appointments"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))


@router.get("/doctors/{doctor_id}/leave",response_model=list[DoctorLeaveResponse])
def get_leaves(
    doctor_id:int,
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    return doctor_service.get_doctor_leaves(db,doctor_id)


@router.get("/appointments")
def list_all_appointments(
    admin:User=Depends(require_role("admin")),
    db:Session=Depends(get_db),
):
    appointments=appointment_service.list_all_appointments(db)
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
