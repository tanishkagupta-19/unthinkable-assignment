from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.services import llm_service

router=APIRouter(prefix="/api/appointments",tags=["Appointments"])


@router.post("/{appointment_id}/retry-summary")
def retry_llm_summary(
    appointment_id:int,
    summary_type:str="pre_visit",
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db),
):
    if current_user.role not in("admin","doctor"):
        raise HTTPException(status_code=403,detail="Only doctors and admins can retry summaries")

    appt=db.query(Appointment).filter(Appointment.id==appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404,detail="Appointment not found")

    if summary_type=="pre_visit":
        if not appt.symptoms_text:
            raise HTTPException(status_code=400,detail="No symptoms to analyse")

        result=llm_service.generate_pre_visit_summary(appt.symptoms_text)
        appt.pre_visit_summary=result["raw_text"]
        appt.urgency_level=result["urgency_level"]
        db.commit()

        return {
"message":"Pre-visit summary regenerated",
"urgency_level":result["urgency_level"],
"summary":result["raw_text"],
        }

    elif summary_type=="post_visit":
        if not appt.doctor_notes:
            raise HTTPException(status_code=400,detail="No doctor notes available")

        summary=llm_service.generate_post_visit_summary(
            appt.doctor_notes,appt.prescription_text or""
)
        appt.post_visit_summary=summary
        db.commit()

        return {
"message":"Post-visit summary regenerated",
"summary":summary,
        }

    else:
        raise HTTPException(status_code=400,detail="summary_type must be 'pre_visit' or 'post_visit'")
