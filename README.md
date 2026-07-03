# Healthcare Appointment & Follow-up Manager

Backend for a healthcare appointment platform — patients book appointments, doctors get AI-generated symptom summaries before visits, and everyone gets email/calendar notifications.

Built with FastAPI + PostgreSQL.

## What It Does

**Patients** can search doctors by specialisation, pick a time slot, fill a symptom form, and book. They get an AI summary of their visit afterwards in plain language. They can also cancel or reschedule.

**Doctors** see their upcoming appointments with an AI-generated pre-visit brief (urgency level, chief complaint, suggested questions). After the visit they submit notes and a prescription — the system converts their clinical notes into something the patient can actually understand.

**Admins** manage doctor profiles, mark leave days (which auto-cancels affected appointments and notifies patients), and have an overview of all appointments.

Other stuff: double-booking prevention with row locking + unique constraints, a 5-minute slot hold while the patient fills their symptom form, email retry queue, Google Calendar sync.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI 0.115 |
| Database | PostgreSQL + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| LLM | OpenAI API (gpt-3.5-turbo) |
| Email | SendGrid |
| Calendar | Google Calendar API |
| Background Jobs | APScheduler |

## Setup

**Prerequisites:** Python 3.11+, PostgreSQL 14+

```bash
git clone https://github.com/your-username/unthinkable-assignment.git
cd unthinkable-assignment

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

Create the database:
```bash
psql -U postgres -c "CREATE DATABASE healthcare_db;"
```

Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

Run it:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger docs at `http://localhost:8000/docs`.

Tables are auto-created on startup. For production, use Alembic:
```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register (patient/doctor) |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/auth/google/connect` | Start Google OAuth |
| GET | `/api/auth/google/callback` | OAuth callback |

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/doctors?specialisation=cardiology` | Search doctors |
| GET | `/api/patients/doctors/{id}/slots?appointment_date=2025-01-20` | Available slots |
| POST | `/api/patients/appointments/hold` | Hold a slot (5 min) |
| POST | `/api/patients/appointments/book` | Confirm booking |
| GET | `/api/patients/appointments` | My appointments |
| GET | `/api/patients/appointments/{id}` | Appointment detail |
| PUT | `/api/patients/appointments/{id}/cancel` | Cancel |
| PUT | `/api/patients/appointments/{id}/reschedule` | Reschedule |

### Doctors
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/doctors/profile` | Own profile |
| GET | `/api/doctors/appointments` | My appointments |
| GET | `/api/doctors/appointments/{id}` | Appointment + pre-visit summary |
| PUT | `/api/doctors/appointments/{id}/complete` | Submit notes & prescription |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/doctors` | Create doctor profile |
| GET | `/api/admin/doctors` | List all doctors |
| PUT | `/api/admin/doctors/{id}` | Update doctor |
| DELETE | `/api/admin/doctors/{id}` | Remove doctor |
| POST | `/api/admin/doctors/{id}/leave` | Mark leave |
| GET | `/api/admin/doctors/{id}/leave` | Leave calendar |
| GET | `/api/admin/appointments` | All appointments |

### Utility
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/appointments/{id}/retry-summary` | Retry failed LLM summary |
| GET | `/` | Health check |

## Google Calendar

You need a Google Cloud project with Calendar API enabled and an OAuth 2.0 client ID (Web application type). Set the redirect URI to `http://localhost:8000/api/auth/google/callback`.

Users connect via `GET /api/auth/google/connect` — after that, calendar events are created automatically on booking.

## License

Built as part of an assignment submission.
