# Import all models here so Alembic can discover them
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_leave import DoctorLeave
from app.models.appointment import Appointment
from app.models.slot_hold import SlotHold
from app.models.medication_reminder import MedicationReminder
from app.models.email_log import EmailLog
