import logging
from datetime import datetime,timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

logger=logging.getLogger(__name__)


def _get_calendar_service(user:User):
    if not user.google_access_token:
        return None

    try:
        creds=Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
)
        service=build("calendar","v3",credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build Calendar service for user {user.id}:{e}")
        return None


def create_calendar_event(
    user:User,
    summary:str,
    description:str,
    start_datetime:datetime,
    end_datetime:datetime,
    db:Session,
)-> str | None:
"""Create a Google Calendar event. Returns event ID or None."""
    service=_get_calendar_service(user)
    if not service:
        logger.info(f"User {user.id} hasn't connected Google Calendar,skipping")
        return None

    event_body={
"summary":summary,
"description":description,
"start":{
"dateTime":start_datetime.isoformat(),
"timeZone":"Asia/Kolkata",
        },
"end":{
"dateTime":end_datetime.isoformat(),
"timeZone":"Asia/Kolkata",
        },
"reminders":{
"useDefault":False,
"overrides":[
                {"method":"popup","minutes":60},
            ],
        },
    }

    try:
        event=service.events().insert(
            calendarId="primary",
            body=event_body,
).execute()

        event_id=event.get("id")
        logger.info(f"Calendar event created for user {user.id}:{event_id}")

        _update_tokens_if_refreshed(user,service,db)

        return event_id

    except Exception as e:
        logger.error(f"Failed to create calendar event for user {user.id}:{e}")
        return None


def update_calendar_event(
    user:User,
    event_id:str,
    summary:str,
    description:str,
    start_datetime:datetime,
    end_datetime:datetime,
    db:Session,
)-> bool:
    service=_get_calendar_service(user)
    if not service or not event_id:
        return False

    event_body={
"summary":summary,
"description":description,
"start":{
"dateTime":start_datetime.isoformat(),
"timeZone":"Asia/Kolkata",
        },
"end":{
"dateTime":end_datetime.isoformat(),
"timeZone":"Asia/Kolkata",
        },
    }

    try:
        service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event_body,
).execute()

        logger.info(f"Calendar event updated for user {user.id}:{event_id}")
        _update_tokens_if_refreshed(user,service,db)
        return True

    except Exception as e:
        logger.error(f"Failed to update calendar event:{e}")
        return False


def delete_calendar_event(user:User,event_id:str,db:Session)-> bool:
    service=_get_calendar_service(user)
    if not service or not event_id:
        return False

    try:
        service.events().delete(
            calendarId="primary",
            eventId=event_id,
).execute()

        logger.info(f"Calendar event deleted for user {user.id}:{event_id}")
        _update_tokens_if_refreshed(user,service,db)
        return True

    except Exception as e:
        logger.error(f"Failed to delete calendar event:{e}")
        return False


def _update_tokens_if_refreshed(user:User,service,db:Session):
"""Save refreshed access token back to DB if it changed."""
    try:
        creds=service._http.credentials
        if hasattr(creds,"token")and creds.token!=user.google_access_token:
            user.google_access_token=creds.token
            db.commit()
            logger.info(f"Refreshed Google token for user {user.id}")
    except Exception:
        pass
