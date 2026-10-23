import re
import logging
from typing import Any
from app.models.medical_entity import MedicalEntity

logger = logging.getLogger("healthcare_system")


class MedicalExtractionError(Exception):
    pass


class RuleBasedExtractor:
    DISEASES = [
        "pneumonia", "diabetes", "hypertension", "tumor", "fracture", "infection",
        "inflammation", "cancer", "asthma", "copd", "heart failure", "renal failure",
        "hepatitis", "anemia", "thrombosis", "embolism", "effusion", "consolidation",
        "cardiomegaly", "arrhythmia", "tachycardia", "bradycardia", "infarct", "infarction",
        "pneumothorax", "hemothorax", "edema", "lesion", "cyst", "nodule", "ulcer",
        "hematoma", "hemorrhage", "laceration", "contusion", "dislocation", "atelectasis",
        "infiltrate", "opacity", "mass", "abscess", "sepsis", "pericardial effusion",
        "pleural effusion", "pulmonary embolism", "myocardial infarction", "stroke",
        "cerebrovascular accident", "chronic kidney disease", "acute respiratory distress",
        "ARDS", "COVID-19", "coronavirus", "tuberculosis", "pulmonary edema",
        "myocarditis", "pericarditis", "endocarditis", "vasculitis", "osteomyelitis",
    ]

    ORGANS = [
        "lung", "lungs", "heart", "liver", "kidney", "kidneys", "brain", "chest",
        "abdomen", "spine", "vertebra", "left ventricle", "right ventricle", "aorta",
        "spleen", "pancreas", "intestine", "bowel", "bladder", "stomach", "ribs",
        "clavicle", "sternum", "pelvis", "femur", "humerus", "skull", "cervix",
        "uterus", "prostate", "thyroid", "adrenal", "gallbladder", "esophagus",
        "trachea", "bronchus", "bronchi", "pleura", "pericardium", "myocardium",
    ]

    SYMPTOMS = [
        "chest pain", "cough", "fever", "shortness of breath", "dyspnea", "nausea",
        "vomiting", "headache", "dizziness", "fatigue", "palpitations", "syncope",
        "edema", "weight loss", "night sweats", "hemoptysis", "dysphagia", "aphasia",
        "paresthesia", "numbness", "weakness", "tremor", "seizure", "confusion",
        "delirium", "anxiety", "depression", "insomnia", "rash", "pruritus", "jaundice",
        "ascites", "melena", "hematochezia", "hematuria", "dysuria", "frequency",
        "urgency", "incontinence", "constipation", "diarrhea", "bloating",
    ]

    FINDINGS = [
        "consolidation", "enlarged heart", "lesion", "fluid collection", "abnormal rhythm",
        "mass", "opacity", "infiltrate", "atelectasis", "pleural effusion", "pericardial effusion",
        "fracture", "dislocation", "hemorrhage", "hematoma", "cyst", "nodule", "ulcer",
        "laceration", "contusion", "cardiomegaly", "tachycardia", "bradycardia", "arrhythmia",
        "hypodensity", "hyperdensity", "hypointensity", "hyperintensity", "enhancement",
        "stricture", "stenosis", "obstruction", "perforation", "ischemia", "necrosis",
        "fibrosis", "calcification", "degeneration", "herniation", "prolapse",
    ]

    MEDICATIONS = [
        "aspirin", "metformin", "insulin", "lisinopril", "atorvastatin", "omeprazole",
        "amoxicillin", "ibuprofen", "paracetamol", "acetaminophen", "prednisone",
        "hydrocodone", "norvasc", "losartan", "simvastatin", "metoprolol", "warfarin",
        "clopidogrel", "furosemide", "spironolactone", "acetazolamide", "albuterol",
        "salbutamol", "fluticasone", "budesonide", "montelukast", "levothyroxine",
        "methotrexate", "azathioprine", "cyclosporine", "tacrolimus", "prednisolone",
        "dexamethasone", "hydrocortisone", "epinephrine", "norepinephrine",
        "dopamine", "dobutamine", "amiodarone", "digoxin", "heparin", "enoxaparin",
        "fondaparinux", "streptokinase", "alteplase", "tenecteplase", "nitroglycerin",
    ]

    SEVERITY = [
        "mild", "moderate", "severe", "minimal", "significant", "slight", "marked",
        "pronounced", "subtle", "extensive", "diffuse", "focal", "bilateral", "unilateral",
        "acute", "chronic", "subacute", "stable", "unstable", "worsening", "improving",
        "progressive", "regressive", "symmetric", "asymmetric", "small", "large",
        "tiny", "massive", "mild-to-moderate", "moderate-to-severe",
    ]

    NEGATION_PATTERNS = [
        r"\bno evidence of\b",
        r"\bno sign of\b",
        r"\bno signs of\b",
        r"\bwithout\b",
        r"\bnegative for\b",
        r"\babsent\b",
        r"\bdenies\b",
        r"\bno history of\b",
        r"\bruled out\b",
        r"\bnot consistent with\b",
        r"\bno findings of\b",
        r"\bno suggestion of\b",
        r"\bunlikely\b",
        r"\bfree of\b",
        r"\bclear of\b",
    ]

    MEASUREMENT_PATTERNS = [
        r"\b\d{1,3}/\d{1,3}\s*(?:mmHg|cm|mm|in|ft|lbs|kg|m|mL|L|%|bpm|°C|°F|mg|mcg|g|kg)\b",
        r"\b\d+\.?\d*\s*(?:mmHg|cm|mm|in|ft|lbs|kg|m|mL|L|%|bpm|°C|°F|mg|mcg|g|kg)\b",
        r"\b\d+\.?\d*\s*%",
        r"\b\d+\.?\d*\s*(?:mmHg)\b",
        r"\b\d+\.?\d*\s*(?:cm|mm)\b",
        r"\b\d+\s*bpm\b",
        r"\b\d+\.?\d*\s*(?:°C|°F)\b",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        self._negation_re = [re.compile(p, re.IGNORECASE) for p in self.NEGATION_PATTERNS]
        self._measurement_re = [re.compile(p, re.IGNORECASE) for p in self.MEASUREMENT_PATTERNS]
        self._disease_re = re.compile(
            r"\b(" + "|".join(re.escape(d) for d in self.DISEASES) + r")\b",
            re.IGNORECASE,
        )
        self._organ_re = re.compile(
            r"\b(" + "|".join(re.escape(o) for o in self.ORGANS) + r")\b",
            re.IGNORECASE,
        )
        self._symptom_re = re.compile(
            r"\b(" + "|".join(re.escape(s) for s in self.SYMPTOMS) + r")\b",
            re.IGNORECASE,
        )
        self._finding_re = re.compile(
            r"\b(" + "|".join(re.escape(f) for f in self.FINDINGS) + r")\b",
            re.IGNORECASE,
        )
        self._medication_re = re.compile(
            r"\b(" + "|".join(re.escape(m) for m in self.MEDICATIONS) + r")\b",
            re.IGNORECASE,
        )
        self._severity_re = re.compile(
            r"\b(" + "|".join(re.escape(s) for s in self.SEVERITY) + r")\b",
            re.IGNORECASE,
        )

    def _is_negated(self, text: str, start: int, end: int) -> bool:
        window = text[max(0, start - 60): start].lower()
        for pattern in self._negation_re:
            if pattern.search(window):
                return True
        return False

    def _get_context(self, text: str, start: int, end: int, window: int = 80) -> str:
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        return text[ctx_start:ctx_end].strip()

    def _extract_entities(self, text: str, pattern: re.Pattern, entity_type: str, normalize_map: dict[str, str]) -> list[MedicalEntity]:
        entities = []
        seen = set()
        for match in pattern.finditer(text):
            start, end = match.span()
            raw_text = match.group(0)
            normalized = normalize_map.get(raw_text.lower(), raw_text.lower())
            if raw_text.lower() in seen:
                continue
            seen.add(raw_text.lower())
            severity = None
            ctx = self._get_context(text, start, end)
            sev_match = self._severity_re.search(ctx)
            if sev_match:
                severity = sev_match.group(0).lower()
            entities.append(MedicalEntity(
                type=entity_type,
                text=raw_text,
                normalized_text=normalized,
                severity=severity,
                negated=self._is_negated(text, start, end),
                context=ctx,
                confidence=0.8 if not self._is_negated(text, start, end) else 0.9,
                source_text=ctx,
            ))
        return entities

    def _extract_measurements(self, text: str) -> list[MedicalEntity]:
        entities = []
        seen = set()
        unit_suffixes = ("mmHg", "cm", "mm", "in", "ft", "lbs", "kg", "m", "mL", "L", "%", "bpm", "°C", "°F", "mg", "mcg", "g")
        sorted_suffixes = sorted(unit_suffixes, key=len, reverse=True)
        for pattern in self._measurement_re:
            for match in pattern.finditer(text):
                raw_text = match.group(0).strip()
                if raw_text.lower() in seen:
                    continue
                seen.add(raw_text.lower())
                value = None
                unit = None
                if "/" in raw_text:
                    value = raw_text.split()[0] if " " in raw_text else raw_text
                    parts = raw_text.split()
                    if len(parts) >= 2:
                        unit = parts[-1]
                else:
                    for suffix in sorted_suffixes:
                        if raw_text.endswith(suffix):
                            value = raw_text[: -len(suffix)].strip()
                            unit = suffix
                            break
                    if value is None:
                        parts = raw_text.split()
                        value = parts[0]
                        if len(parts) >= 2:
                            unit = parts[-1]
                entities.append(MedicalEntity(
                    type="measurement",
                    text=raw_text,
                    normalized_text=raw_text,
                    value=value,
                    unit=unit,
                    negated=False,
                    context=self._get_context(text, match.start(), match.end()),
                    confidence=0.9,
                    source_text=raw_text,
                ))
        return entities

    def extract(self, text: str) -> list[dict[str, Any]]:
        if not text or not text.strip():
            return []
        entities = []
        entities.extend(self._extract_entities(text, self._disease_re, "disease", {}))
        entities.extend(self._extract_entities(text, self._organ_re, "organ", {}))
        entities.extend(self._extract_entities(text, self._symptom_re, "symptom", {}))
        entities.extend(self._extract_entities(text, self._finding_re, "finding", {}))
        entities.extend(self._extract_entities(text, self._medication_re, "medication", {}))
        entities.extend(self._extract_measurements(text))
        return [e.model_dump() for e in entities]
