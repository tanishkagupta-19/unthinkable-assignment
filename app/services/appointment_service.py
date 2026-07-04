import logging
from datetime import date,time,datetime,timedelta

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_leave import DoctorLeave
from app.models.slot_hold import SlotHold,HOLD_DURATION_MINUTES
from app.models.medication_reminder import MedicationReminder
from app.models.user import User
from app.services import llm_service,email_service,calendar_service

logger=logging.getLogger(__name__)


def generate_available_slots(db:Session,doctor_id:int,
                              requested_date:date)-> list[dict]:
    profile=db.query(DoctorProfile).filter(DoctorProfile.id==doctor_id).first()
    if not profile:
        raise ValueError("Doctor not found")

    day_name=requested_date.strftime("%a")
    working_days=[d.strip()for d in profile.working_days.split(",")]
    if day_name not in working_days:
        return []

    on_leave=(
        db.query(DoctorLeave)
        .filter(
            DoctorLeave.doctor_id==doctor_id,
            DoctorLeave.leave_date==requested_date,
)
        .first()
)
    if on_leave:
        return []

    all_slots=[]
    current_time=datetime.combine(requested_date,profile.working_hours_start)
    end_of_day=datetime.combine(requested_date,profile.working_hours_end)
    slot_delta=timedelta(minutes=profile.slot_duration_minutes)

    while current_time + slot_delta <=end_of_day:
        slot_start=current_time.time()
        slot_end=(current_time + slot_delta).time()
        all_slots.append({"start_time":slot_start,"end_time":slot_end})
        current_time +=slot_delta

    booked_slots=(
        db.query(Appointment.start_time)
        .filter(
            Appointment.doctor_id==doctor_id,
            Appointment.appointment_date==requested_date,
            Appointment.status.notin_(["cancelled"]),
)
        .all()
)
    booked_times={row.start_time for row in booked_slots}

    now=datetime.utcnow()
    held_slots=(
        db.query(SlotHold.hold_start_time)
        .filter(
            SlotHold.doctor_id==doctor_id,
            SlotHold.hold_date==requested_date,
            SlotHold.expires_at > now,
)
        .all()
)
    held_times={row.hold_start_time for row in held_slots}

    available_slots=[]
    for slot in all_slots:
        is_booked=slot["start_time"] in booked_times
        is_held=slot["start_time"] in held_times
        available_slots.append({
"start_time":slot["start_time"],
"end_time":slot["end_time"],
"is_available":not is_booked and not is_held,
        })

    return available_slots


def hold_slot(db:Session,doctor_id:int,appointment_date:date,
              start_time:time,patient_id:int)-> SlotHold:
    profile=db.query(DoctorProfile).filter(DoctorProfile.id==doctor_id).first()
    if not profile:
        raise ValueError("Doctor not found")

    start_dt=datetime.combine(appointment_date,start_time)
    end_dt=start_dt + timedelta(minutes=profile.slot_duration_minutes)
    end_time=end_dt.time()

    existing_booking=(
        db.query(Appointment)
        .filter(
            Appointment.doctor_id==doctor_id,
            Appointment.appointment_date==appointment_date,
            Appointment.start_time==start_time,
            Appointment.status.notin_(["cancelled"]),
)
        .first()
)
    if existing_booking:
        raise ValueError("Slot already booked")

    now=datetime.utcnow()
    existing_hold=(
        db.query(SlotHold)
        .filter(
            SlotHold.doctor_id==doctor_id,
            SlotHold.hold_date==appointment_date,
            SlotHold.hold_start_time==start_time,
            SlotHold.expires_at > now,
            SlotHold.patient_id!=patient_id,
)
        .first()
)
    if existing_hold:
        raise ValueError("Slot is held by another patient")

    # clear any previous hold this patient has for this doctor
    db.query(SlotHold).filter(
        SlotHold.patient_id==patient_id,
        SlotHold.doctor_id==doctor_id,
).delete()

    hold=SlotHold(
        doctor_id=doctor_id,
        patient_id=patient_id,
        hold_date=appointment_date,
        hold_start_time=start_time,
        hold_end_time=end_time,
        expires_at=datetime.utcnow()+ timedelta(minutes=HOLD_DURATION_MINUTES),
)
    db.add(hold)
    db.commit()
    db.refresh(hold)

    logger.info(f"Slot held:doctor={doctor_id},date={appointment_date},"
                f"time={start_time},patient={patient_id}")
    return hold


def book_appointment(db:Session,hold_id:int,symptoms_text:str,
                      patient_id:int)-> Appointment:
    """Confirm booking from a held slot. Uses SELECT FOR UPDATE to prevent races."""
    hold=db.query(SlotHold).filter(SlotHold.id==hold_id).first()
    if not hold:
        raise ValueError("Hold not found or expired,try again")
    if hold.patient_id!=patient_id:
        raise ValueError("This hold belongs to another patient")
    if hold.expires_at < datetime.utcnow():
        db.delete(hold)
        db.commit()
        raise ValueError("Hold expired,select the slot again")

    # row lock to serialize concurrent bookings
    existing=(
        db.query(Appointment)
        .filter(
            Appointment.doctor_id==hold.doctor_id,
            Appointment.appointment_date==hold.hold_date,
            Appointment.start_time==hold.hold_start_time,
            Appointment.status.notin_(["cancelled"]),
)
        .with_for_update()
        .first()
)

    if existing:
        db.delete(hold)
        db.commit()
        raise ValueError("Slot was just booked by someone else")

    summary_data=llm_service.generate_pre_visit_summary(symptoms_text)

    appointment=Appointment(
        patient_id=patient_id,
        doctor_id=hold.doctor_id,
        appointment_date=hold.hold_date,
        start_time=hold.hold_start_time,
        end_time=hold.hold_end_time,
        status="booked",
        symptoms_text=symptoms_text,
        pre_visit_summary=summary_data["raw_text"],
        urgency_level=summary_data["urgency_level"],
)
    db.add(appointment)
    db.delete(hold)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Booking failed(likely duplicate):{e}")
        raise ValueError("Slot was just booked,pick another time")

    db.refresh(appointment)

    # confirmation emails(best-effort)
    try:
        patient=db.query(User).filter(User.id==patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==hold.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        if patient and doctor_user:
            email_service.send_booking_confirmation(
                db=db,
                patient_email=patient.email,
                doctor_email=doctor_user.email,
                patient_name=patient.full_name,
                doctor_name=doctor_user.full_name,
                date_str=str(appointment.appointment_date),
                time_str=str(appointment.start_time),
)
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email:{e}")

    # calendar events(best-effort)
    try:
        patient=db.query(User).filter(User.id==patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==appointment.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        start_dt=datetime.combine(appointment.appointment_date,appointment.start_time)
        end_dt=datetime.combine(appointment.appointment_date,appointment.end_time)

        if patient:
            patient_event_id=calendar_service.create_calendar_event(
                user=patient,
                summary=f"Doctor Appointment - Dr. {doctor_user.full_name if doctor_user else 'N/A'}",
                description=f"Appointment at the clinic",
                start_datetime=start_dt,
                end_datetime=end_dt,
                db=db,
)
            if patient_event_id:
                appointment.patient_cal_event_id=patient_event_id

        if doctor_user:
            doctor_event_id=calendar_service.create_calendar_event(
                user=doctor_user,
                summary=f"Patient:{patient.full_name if patient else 'N/A'}",
                description=f"Patient appointment",
                start_datetime=start_dt,
                end_datetime=end_dt,
                db=db,
)
            if doctor_event_id:
                appointment.doctor_cal_event_id=doctor_event_id

        db.commit()
    except Exception as e:
        logger.error(f"Failed to create calendar events:{e}")

    return appointment


def cancel_appointment(db:Session,appointment_id:int,user_id:int)-> Appointment:
    appointment=db.query(Appointment).filter(Appointment.id==appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    user=db.query(User).filter(User.id==user_id).first()
    if user.role=="patient"and appointment.patient_id!=user_id:
        raise ValueError("You can only cancel your own appointments")

    if appointment.status!="booked":
        raise ValueError(f"Can't cancel,appointment is already {appointment.status}")

    appointment.status="cancelled"
    db.commit()

    try:
        patient=db.query(User).filter(User.id==appointment.patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==appointment.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        if patient:
            email_service.send_cancellation_notice(
                db,patient.email,patient.full_name,
                str(appointment.appointment_date),str(appointment.start_time),
)
        if doctor_user:
            email_service.send_cancellation_notice(
                db,doctor_user.email,doctor_user.full_name,
                str(appointment.appointment_date),str(appointment.start_time),
)
    except Exception as e:
        logger.error(f"Failed to send cancellation emails:{e}")

    try:
        patient=db.query(User).filter(User.id==appointment.patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==appointment.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        if patient and appointment.patient_cal_event_id:
            calendar_service.delete_calendar_event(
                patient,appointment.patient_cal_event_id,db
)
        if doctor_user and appointment.doctor_cal_event_id:
            calendar_service.delete_calendar_event(
                doctor_user,appointment.doctor_cal_event_id,db
)

        appointment.patient_cal_event_id=None
        appointment.doctor_cal_event_id=None
        db.commit()
    except Exception as e:
        logger.error(f"Failed to delete calendar events:{e}")

    return appointment


def reschedule_appointment(db:Session,appointment_id:int,patient_id:int,
                            new_date:date,new_start_time:time)-> Appointment:
    old_appt=db.query(Appointment).filter(Appointment.id==appointment_id).first()
    if not old_appt:
        raise ValueError("Appointment not found")
    if old_appt.patient_id!=patient_id:
        raise ValueError("You can only reschedule your own appointments")
    if old_appt.status!="booked":
        raise ValueError(f"Can't reschedule,appointment is {old_appt.status}")

    profile=db.query(DoctorProfile).filter(
        DoctorProfile.id==old_appt.doctor_id
).first()
    if not profile:
        raise ValueError("Doctor profile not found")

    existing=(
        db.query(Appointment)
        .filter(
            Appointment.doctor_id==old_appt.doctor_id,
            Appointment.appointment_date==new_date,
            Appointment.start_time==new_start_time,
            Appointment.status.notin_(["cancelled"]),
)
        .with_for_update()
        .first()
)
    if existing:
        raise ValueError("New slot is not available")

    start_dt=datetime.combine(new_date,new_start_time)
    end_dt=start_dt + timedelta(minutes=profile.slot_duration_minutes)

    old_appt.status="cancelled"

    new_appt=Appointment(
        patient_id=patient_id,
        doctor_id=old_appt.doctor_id,
        appointment_date=new_date,
        start_time=new_start_time,
        end_time=end_dt.time(),
        status="booked",
        symptoms_text=old_appt.symptoms_text,
        pre_visit_summary=old_appt.pre_visit_summary,
        urgency_level=old_appt.urgency_level,
)
    db.add(new_appt)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise ValueError(f"Reschedule failed:{e}")

    db.refresh(new_appt)

    try:
        patient=db.query(User).filter(User.id==patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==old_appt.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        if patient and old_appt.patient_cal_event_id:
            calendar_service.delete_calendar_event(
                patient,old_appt.patient_cal_event_id,db
)
        if doctor_user and old_appt.doctor_cal_event_id:
            calendar_service.delete_calendar_event(
                doctor_user,old_appt.doctor_cal_event_id,db
)

        new_start_dt=datetime.combine(new_date,new_start_time)
        new_end_dt=datetime.combine(new_date,end_dt.time())

        if patient:
            event_id=calendar_service.create_calendar_event(
                user=patient,
                summary=f"Doctor Appointment(Rescheduled)",
                description="Rescheduled appointment",
                start_datetime=new_start_dt,
                end_datetime=new_end_dt,
                db=db,
)
            if event_id:
                new_appt.patient_cal_event_id=event_id

        if doctor_user:
            event_id=calendar_service.create_calendar_event(
                user=doctor_user,
                summary=f"Patient:{patient.full_name if patient else 'N/A'}(Rescheduled)",
                description="Rescheduled appointment",
                start_datetime=new_start_dt,
                end_datetime=new_end_dt,
                db=db,
)
            if event_id:
                new_appt.doctor_cal_event_id=event_id

        db.commit()
    except Exception as e:
        logger.error(f"Failed to update calendar events on reschedule:{e}")

    try:
        patient=db.query(User).filter(User.id==patient_id).first()
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==old_appt.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        if patient and doctor_user:
            email_service.send_booking_confirmation(
                db=db,
                patient_email=patient.email,
                doctor_email=doctor_user.email,
                patient_name=patient.full_name,
                doctor_name=doctor_user.full_name,
                date_str=str(new_date),
                time_str=str(new_start_time),
)
    except Exception as e:
        logger.error(f"Failed to send reschedule emails:{e}")

    return new_appt


def complete_appointment(db:Session,appointment_id:int,doctor_user_id:int,
                          doctor_notes:str,prescription_text:str=None)-> Appointment:
    appointment=db.query(Appointment).filter(Appointment.id==appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    doctor_profile=db.query(DoctorProfile).filter(
        DoctorProfile.user_id==doctor_user_id
).first()
    if not doctor_profile or appointment.doctor_id!=doctor_profile.id:
        raise ValueError("You can only complete your own appointments")

    if appointment.status!="booked":
        raise ValueError(f"Can't complete,appointment is {appointment.status}")

    appointment.doctor_notes=doctor_notes
    appointment.prescription_text=prescription_text
    appointment.status="completed"

    post_summary=llm_service.generate_post_visit_summary(
        doctor_notes,prescription_text or""
)
    appointment.post_visit_summary=post_summary

    db.commit()
    db.refresh(appointment)

    logger.info(f"Appointment {appointment_id} completed by doctor {doctor_user_id}")
    return appointment


def get_appointment(db:Session,appointment_id:int)-> Appointment | None:
    return db.query(Appointment).filter(Appointment.id==appointment_id).first()


def list_patient_appointments(db:Session,patient_id:int,
                               status:str=None)-> list[Appointment]:
    query=db.query(Appointment).filter(Appointment.patient_id==patient_id)
    if status:
        query=query.filter(Appointment.status==status)
    return query.order_by(Appointment.appointment_date.desc()).all()


def list_doctor_appointments(db:Session,doctor_user_id:int,
                              status:str=None,
                              appointment_date:date=None)-> list[Appointment]:
    doctor_profile=db.query(DoctorProfile).filter(
        DoctorProfile.user_id==doctor_user_id
).first()
    if not doctor_profile:
        return []

    query=db.query(Appointment).filter(Appointment.doctor_id==doctor_profile.id)
    if status:
        query=query.filter(Appointment.status==status)
    if appointment_date:
        query=query.filter(Appointment.appointment_date==appointment_date)
    return query.order_by(Appointment.appointment_date,Appointment.start_time).all()


def list_all_appointments(db:Session)-> list[Appointment]:
    return db.query(Appointment).order_by(Appointment.created_at.desc()).all()


def cleanup_expired_holds(db:Session):
    now=datetime.utcnow()
    expired_count=(
        db.query(SlotHold)
        .filter(SlotHold.expires_at <=now)
        .delete()
)
    if expired_count > 0:
        db.commit()
        logger.info(f"Cleaned up {expired_count} expired slot holds")
