from pydantic import BaseModel


class SymptomInput(BaseModel):
    symptoms_text:str


class PreVisitSummary(BaseModel):
    urgency_level:str
    chief_complaint:str
    suggested_questions:list[str]
    raw_text:str
