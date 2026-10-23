from pydantic import BaseModel
from typing import Optional


class LLMKeyFinding(BaseModel):
    finding: str
    explanation: str
    severity: Optional[str] = None
    negated: bool = False
    # Phase 4a: verbatim quote from the report + backend verification.
    source_quote: Optional[str] = None
    verified: bool = False


class LLMMeasurement(BaseModel):
    name: str
    value: str
    unit: Optional[str] = ""
    explanation: Optional[str] = None


class LLMMedicalTerm(BaseModel):
    term: str
    simple_explanation: str


class LLMInterpretationResponse(BaseModel):
    summary: str
    key_findings: list[LLMKeyFinding] = []
    measurements: list[LLMMeasurement] = []
    medical_terms: list[LLMMedicalTerm] = []
    limitations: list[str] = []
    safety_note: str = "This is an explanation of the supplied report and not a diagnosis."
    # Phase 4c: requested language for patient-facing text.
    language: str = "en"
