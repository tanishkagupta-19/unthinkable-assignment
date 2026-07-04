import json
import logging

from openai import OpenAI

from app.config import settings

logger=logging.getLogger(__name__)

client=None
if settings.OPENAI_API_KEY:
    client=OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_pre_visit_summary(symptoms_text:str)-> dict:
    """Analyse symptoms and return urgency,chief complaint,suggested questions."""
    if not client:
        logger.warning("OpenAI not configured,skipping pre-visit summary")
        return _fallback_pre_visit(symptoms_text)

    prompt=(
"You are a medical triage assistant. Analyse the following patient symptoms"
"and return a JSON object with exactly these fields:\n"
"- urgency_level:one of 'Low','Medium',or 'High'\n"
"- chief_complaint:a one-line summary of the main issue\n"
"- suggested_questions:a list of exactly 3 questions the doctor should ask\n\n"
        f"Patient symptoms:{symptoms_text}\n\n"
"Respond with ONLY the JSON object,no markdown formatting."
)

    try:
        response=client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3,
            timeout=10,
)

        raw_text=response.choices[0].message.content.strip()

        # strip markdown fencing if present
        cleaned=raw_text.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned=cleaned[4:].strip()

        parsed=json.loads(cleaned)

        return {
"urgency_level":parsed.get("urgency_level","Medium"),
"chief_complaint":parsed.get("chief_complaint","See symptoms"),
"suggested_questions":parsed.get("suggested_questions",[]),
"raw_text":raw_text,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON:{e}")
        logger.error(f"Raw response was:{raw_text}")
        return {
"urgency_level":"Medium",
"chief_complaint":"See raw symptoms below",
"suggested_questions":[],
"raw_text":raw_text,
        }

    except Exception as e:
        logger.error(f"LLM pre-visit summary failed:{e}")
        return _fallback_pre_visit(symptoms_text)


def generate_post_visit_summary(doctor_notes:str,prescription_text:str="")-> str:
    """Convert clinical notes to a patient-friendly summary."""
    if not client:
        logger.warning("OpenAI not configured,skipping post-visit summary")
        return _fallback_post_visit(doctor_notes)

    prompt=(
"You are a helpful medical assistant. Convert the following clinical notes"
"into a patient-friendly summary that a non-medical person can understand."
"Include:\n"
"- What the doctor found(in simple language)\n"
"- Medication schedule(if any prescription is provided)\n"
"- Follow-up steps and when to come back\n"
"- Any warning signs to watch for\n\n"
        f"Clinical Notes:{doctor_notes}\n"
)

    if prescription_text:
        prompt +=f"\nPrescription:{prescription_text}\n"

    prompt +="\nWrite in a warm,reassuring tone. Use simple language."

    try:
        response=client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.5,
            timeout=10,
)

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"LLM post-visit summary failed:{e}")
        return _fallback_post_visit(doctor_notes)


def _fallback_pre_visit(symptoms_text:str)-> dict:
    return {
"urgency_level":None,
"chief_complaint":"AI summary unavailable,review raw symptoms",
"suggested_questions":[],
"raw_text":f"[LLM unavailable] Raw symptoms:{symptoms_text}",
    }


def _fallback_post_visit(doctor_notes:str)-> str:
    return(
"[AI summary unavailable]\n\n"
"Your doctor's notes are recorded below. Contact the clinic"
"if you have questions about your visit.\n\n"
        f"Doctor's notes:{doctor_notes}"
)
