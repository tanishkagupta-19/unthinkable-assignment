import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services import appointment_service,email_service,reminder_service

logger=logging.getLogger(__name__)

scheduler=BackgroundScheduler()


def _run_cleanup_expired_holds():
    db=SessionLocal()
    try:
        appointment_service.cleanup_expired_holds(db)
    except Exception as e:
        logger.error(f"Error in cleanup_expired_holds:{e}")
    finally:
        db.close()


def _run_appointment_reminders():
    db=SessionLocal()
    try:
        reminder_service.check_and_send_appointment_reminders(db)
    except Exception as e:
        logger.error(f"Error in appointment_reminders:{e}")
    finally:
        db.close()


def _run_retry_failed_emails():
    db=SessionLocal()
    try:
        email_service.retry_failed_emails(db)
    except Exception as e:
        logger.error(f"Error in retry_failed_emails:{e}")
    finally:
        db.close()


def _run_medication_reminders():
    db=SessionLocal()
    try:
        reminder_service.check_and_send_medication_reminders(db)
    except Exception as e:
        logger.error(f"Error in medication_reminders:{e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        _run_cleanup_expired_holds,
"interval",
        minutes=1,
        id="cleanup_expired_holds",
        replace_existing=True,
)

    scheduler.add_job(
        _run_appointment_reminders,
"interval",
        minutes=30,
        id="appointment_reminders",
        replace_existing=True,
)

    scheduler.add_job(
        _run_retry_failed_emails,
"interval",
        minutes=5,
        id="retry_failed_emails",
        replace_existing=True,
)

    scheduler.add_job(
        _run_medication_reminders,
"interval",
        minutes=30,
        id="medication_reminders",
        replace_existing=True,
)

    scheduler.start()
    logger.info("Background scheduler started with 4 jobs")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
