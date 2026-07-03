import logging
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_log import EmailLog

logger=logging.getLogger(__name__)


def send_email(db:Session,to_email:str,subject:str,html_body:str)-> bool:
"""Send via SendGrid and log the attempt. Returns True on success."""
    email_log=EmailLog(
        recipient_email=to_email,
        subject=subject,
        body=html_body,
        status="pending",
)
    db.add(email_log)
    db.commit()

    if not settings.SENDGRID_API_KEY:
        logger.warning(f"SendGrid not configured,email to {to_email} logged but not sent")
        email_log.status="failed"
        email_log.error_message="SendGrid API key not configured"
        email_log.last_attempted_at=datetime.utcnow()
        db.commit()
        return False

    try:
        message=Mail(
            from_email=settings.EMAIL_FROM,
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
)
        sg=SendGridAPIClient(settings.SENDGRID_API_KEY)
        response=sg.send(message)

        if response.status_code in(200,201,202):
            email_log.status="sent"
            email_log.last_attempted_at=datetime.utcnow()
            db.commit()
            logger.info(f"Email sent to {to_email}:{subject}")
            return True
        else:
            email_log.status="failed"
            email_log.error_message=f"SendGrid returned status {response.status_code}"
            email_log.retry_count +=1
            email_log.last_attempted_at=datetime.utcnow()
            db.commit()
            logger.error(f"SendGrid error for {to_email}:status {response.status_code}")
            return False

    except Exception as e:
        email_log.status="failed"
        email_log.error_message=str(e)[:500]
        email_log.retry_count +=1
        email_log.last_attempted_at=datetime.utcnow()
        db.commit()
        logger.error(f"Failed to send email to {to_email}:{e}")
        return False


def retry_failed_emails(db:Session):
"""Retry emails with status='failed' and retry_count < max_retries."""
    failed_emails=(
        db.query(EmailLog)
        .filter(
            EmailLog.status=="failed",
            EmailLog.retry_count < EmailLog.max_retries,
)
        .all()
)

    for email_log in failed_emails:
        logger.info(f"Retrying email {email_log.id} to {email_log.recipient_email}"
                     f"(attempt {email_log.retry_count + 1})")

        if not settings.SENDGRID_API_KEY:
            continue

        try:
            message=Mail(
                from_email=settings.EMAIL_FROM,
                to_emails=email_log.recipient_email,
                subject=email_log.subject,
                html_content=email_log.body,
)
            sg=SendGridAPIClient(settings.SENDGRID_API_KEY)
            response=sg.send(message)

            if response.status_code in(200,201,202):
                email_log.status="sent"
                logger.info(f"Retry successful for email {email_log.id}")
            else:
                email_log.retry_count +=1
                email_log.error_message=f"Retry:status {response.status_code}"

        except Exception as e:
            email_log.retry_count +=1
            email_log.error_message=f"Retry failed:{str(e)[:500]}"
            logger.error(f"Retry failed for email {email_log.id}:{e}")

        email_log.last_attempted_at=datetime.utcnow()
        db.commit()


def send_booking_confirmation(db:Session,patient_email:str,doctor_email:str,
                               patient_name:str,doctor_name:str,
                               date_str:str,time_str:str):
    patient_html=f"""
    <h2>Appointment Confirmed</h2>
    <p>Hi {patient_name},</p>
    <p>Your appointment has been booked:</p>
    <ul>
        <li><strong>Doctor:</strong> {doctor_name}</li>
        <li><strong>Date:</strong> {date_str}</li>
        <li><strong>Time:</strong> {time_str}</li>
    </ul>
    <p>Please arrive 10 minutes early. You can cancel or reschedule
    from your dashboard.</p>
"""
    send_email(db,patient_email,"Appointment Confirmed",patient_html)

    doctor_html=f"""
    <h2>New Appointment Booked</h2>
    <p>Hi Dr. {doctor_name},</p>
    <p>A new appointment has been booked:</p>
    <ul>
        <li><strong>Patient:</strong> {patient_name}</li>
        <li><strong>Date:</strong> {date_str}</li>
        <li><strong>Time:</strong> {time_str}</li>
    </ul>
    <p>The patient's symptom summary will be available before the visit.</p>
"""
    send_email(db,doctor_email,f"New Appointment:{patient_name}",doctor_html)


def send_cancellation_notice(db:Session,email:str,name:str,
                              date_str:str,time_str:str,reason:str=""):
    html=f"""
    <h2>Appointment Cancelled</h2>
    <p>Hi {name},</p>
    <p>The following appointment has been cancelled:</p>
    <ul>
        <li><strong>Date:</strong> {date_str}</li>
        <li><strong>Time:</strong> {time_str}</li>
    </ul>
    {"<p><strong>Reason:</strong>"+ reason +"</p>"if reason else""}
    <p>Please book a new appointment if needed.</p>
"""
    send_email(db,email,"Appointment Cancelled",html)


def send_appointment_reminder(db:Session,email:str,name:str,
                               doctor_or_patient:str,date_str:str,time_str:str):
    html=f"""
    <h2>Appointment Reminder</h2>
    <p>Hi {name},</p>
    <p>This is a reminder that you have an appointment tomorrow:</p>
    <ul>
        <li><strong>With:</strong> {doctor_or_patient}</li>
        <li><strong>Date:</strong> {date_str}</li>
        <li><strong>Time:</strong> {time_str}</li>
    </ul>
"""
    send_email(db,email,"Appointment Tomorrow",html)


def send_medication_reminder_email(db:Session,email:str,patient_name:str,
                                    medication_name:str,dosage:str):
    html=f"""
    <h2>Medication Reminder</h2>
    <p>Hi {patient_name},</p>
    <p>Time to take your medication:</p>
    <ul>
        <li><strong>Medication:</strong> {medication_name}</li>
        <li><strong>Dosage:</strong> {dosage}</li>
    </ul>
    <p>Stay consistent with your medication for the best results.</p>
"""
    send_email(db,email,f"Medication Reminder:{medication_name}",html)
