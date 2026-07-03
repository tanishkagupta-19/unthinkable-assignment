import logging
from datetime import datetime,timedelta,date

from sqlalchemy.orm import Session

from app.models.medication_reminder import MedicationReminder
from app.models.appointment import Appointment
from app.models.user import User
from app.services import email_service

logger=logging.getLogger(__name__)

FREQUENCY_HOURS={
"once_daily":24,
"twice_daily":12,
"thrice_daily":8,
"every_8_hours":8,
"every_6_hours":6,
}


def create_medication_reminders(db:Session,appointment_id:int,
                                 medications:list[dict]):
    appointment=db.query(Appointment).filter(Appointment.id==appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    for med in medications:
        freq=med.get("frequency","once_daily")
        hours=FREQUENCY_HOURS.get(freq,24)

        start=med.get("start_date",date.today())
        if isinstance(start,str):
            start=date.fromisoformat(start)

        end=med.get("end_date",start + timedelta(days=7))
        if isinstance(end,str):
            end=date.fromisoformat(end)

        first_reminder=datetime.combine(start,datetime.min.time().replace(hour=8))

        reminder=MedicationReminder(
            appointment_id=appointment_id,
            patient_id=appointment.patient_id,
            medication_name=med["medication_name"],
            dosage=med.get("dosage",""),
            frequency=freq,
            start_date=start,
            end_date=end,
            next_reminder_at=first_reminder,
            is_active=True,
)
        db.add(reminder)

    db.commit()
    logger.info(f"Created {len(medications)} medication reminders for appointment {appointment_id}")


def check_and_send_medication_reminders(db:Session):
    now=datetime.utcnow()

    due_reminders=(
        db.query(MedicationReminder)
        .filter(
            MedicationReminder.is_active==True,
            MedicationReminder.next_reminder_at <=now,
)
        .all()
)

    for reminder in due_reminders:
        if date.today()> reminder.end_date:
            reminder.is_active=False
            db.commit()
            continue

        patient=db.query(User).filter(User.id==reminder.patient_id).first()
        if not patient:
            continue

        try:
            email_service.send_medication_reminder_email(
                db=db,
                email=patient.email,
                patient_name=patient.full_name,
                medication_name=reminder.medication_name,
                dosage=reminder.dosage,
)
        except Exception as e:
            logger.error(f"Failed to send medication reminder {reminder.id}:{e}")

        hours=FREQUENCY_HOURS.get(reminder.frequency,24)
        reminder.next_reminder_at=now + timedelta(hours=hours)
        db.commit()

    if due_reminders:
        logger.info(f"Processed {len(due_reminders)} medication reminders")


def check_and_send_appointment_reminders(db:Session):
"""Send reminders for appointments ~24h from now."""
    now=datetime.utcnow()
    tomorrow_start=now + timedelta(hours=23)
    tomorrow_end=now + timedelta(hours=25)

    upcoming=(
        db.query(Appointment)
        .filter(
            Appointment.status=="booked",
            Appointment.appointment_date==tomorrow_start.date(),
)
        .all()
)

    for appt in upcoming:
        appt_datetime=datetime.combine(appt.appointment_date,appt.start_time)
        if not(tomorrow_start <=appt_datetime <=tomorrow_end):
            continue

        patient=db.query(User).filter(User.id==appt.patient_id).first()
        from app.models.doctor_profile import DoctorProfile
        doctor_profile=db.query(DoctorProfile).filter(
            DoctorProfile.id==appt.doctor_id
).first()
        doctor_user=doctor_profile.user if doctor_profile else None

        date_str=str(appt.appointment_date)
        time_str=str(appt.start_time)

        if patient:
            try:
                email_service.send_appointment_reminder(
                    db,patient.email,patient.full_name,
                    f"Dr. {doctor_user.full_name}"if doctor_user else"your doctor",
                    date_str,time_str,
)
            except Exception as e:
                logger.error(f"Failed to send patient reminder:{e}")

        if doctor_user:
            try:
                email_service.send_appointment_reminder(
                    db,doctor_user.email,doctor_user.full_name,
                    patient.full_name if patient else"a patient",
                    date_str,time_str,
)
            except Exception as e:
                logger.error(f"Failed to send doctor reminder:{e}")

    if upcoming:
        logger.info(f"Checked {len(upcoming)} upcoming appointments for reminders")
