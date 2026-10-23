import pytest
from app.reports.ai.rule_based_extractor import RuleBasedExtractor
from app.reports.ai.medical_nlp import MedicalNLPService, MedicalNLPError


@pytest.fixture
def extractor():
    return RuleBasedExtractor()


@pytest.fixture
def nlp_service():
    return MedicalNLPService()


class TestDiseaseExtraction:
    def test_pneumonia_present(self, extractor):
        text = "Pneumonia is present in the right lung."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "disease" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "disease"]
        assert "pneumonia" in texts

    def test_pneumonia_negated(self, extractor):
        text = "No evidence of pneumonia."
        entities = extractor.extract(text)
        pneumonias = [e for e in entities if e["type"] == "disease" and e["text"].lower() == "pneumonia"]
        assert len(pneumonias) == 1
        assert pneumonias[0]["negated"] is True

    def test_diabetes(self, extractor):
        text = "Patient has a history of diabetes."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "disease" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "disease"]
        assert "diabetes" in texts

    def test_hypertension(self, extractor):
        text = "Hypertension was noted."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "disease" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "disease"]
        assert "hypertension" in texts


class TestOrganExtraction:
    def test_lung(self, extractor):
        text = "The lung shows normal findings."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "organ" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "organ"]
        assert "lung" in texts

    def test_heart(self, extractor):
        text = "Heart size is normal."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "organ" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "organ"]
        assert "heart" in texts

    def test_left_ventricle(self, extractor):
        text = "Left ventricle is enlarged."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "organ" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "organ"]
        assert "left ventricle" in texts


class TestSymptomExtraction:
    def test_chest_pain(self, extractor):
        text = "Patient reports chest pain."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "symptom" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "symptom"]
        assert "chest pain" in texts

    def test_cough(self, extractor):
        text = "Persistent cough for 3 days."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "symptom" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "symptom"]
        assert "cough" in texts

    def test_fever(self, extractor):
        text = "Fever present."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "symptom" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "symptom"]
        assert "fever" in texts


class TestFindingExtraction:
    def test_consolidation(self, extractor):
        text = "Consolidation noted in the right lower lobe."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "finding" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "finding"]
        assert "consolidation" in texts

    def test_lesion(self, extractor):
        text = "A small lesion was detected."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "finding" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "finding"]
        assert "lesion" in texts

    def test_pleural_effusion(self, extractor):
        text = "Pleural effusion is present."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "finding" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "finding"]
        assert "pleural effusion" in texts


class TestMedicationExtraction:
    def test_aspirin(self, extractor):
        text = "Patient is taking aspirin."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "medication" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "medication"]
        assert "aspirin" in texts

    def test_metformin(self, extractor):
        text = "Metformin prescribed daily."
        entities = extractor.extract(text)
        types = [e["type"] for e in entities]
        assert "medication" in types
        texts = [e["text"].lower() for e in entities if e["type"] == "medication"]
        assert "metformin" in texts


class TestSeverityExtraction:
    def test_mild_severity(self, extractor):
        text = "Mild cardiomegaly is noted."
        entities = extractor.extract(text)
        cardiomegalies = [e for e in entities if e["type"] == "finding" and "cardiomegaly" in e["text"].lower()]
        assert len(cardiomegalies) == 1
        assert cardiomegalies[0]["severity"] == "mild"

    def test_severe_severity(self, extractor):
        text = "Severe consolidation observed."
        entities = extractor.extract(text)
        consolidations = [e for e in entities if e["type"] == "finding" and "consolidation" in e["text"].lower()]
        assert len(consolidations) == 1
        assert consolidations[0]["severity"] == "severe"


class TestMeasurementExtraction:
    def test_blood_pressure(self, extractor):
        text = "Blood pressure is 120/80 mmHg."
        entities = extractor.extract(text)
        measurements = [e for e in entities if e["type"] == "measurement"]
        assert len(measurements) >= 1
        bp = [m for m in measurements if "120/80" in m["text"]]
        assert len(bp) == 1
        assert bp[0]["unit"] == "mmHg"
        assert bp[0]["value"] == "120/80"

    def test_percentage(self, extractor):
        text = "Oxygen saturation is 98%."
        entities = extractor.extract(text)
        measurements = [e for e in entities if e["type"] == "measurement"]
        assert len(measurements) >= 1
        pct = [m for m in measurements if "98%" in m["text"]]
        assert len(pct) == 1
        assert pct[0]["unit"] == "%"
        assert pct[0]["value"] == "98"

    def test_temperature(self, extractor):
        text = "Temperature is 37.2 °C."
        entities = extractor.extract(text)
        measurements = [e for e in entities if e["type"] == "measurement"]
        assert len(measurements) >= 1
        temp = [m for m in measurements if "37.2" in m["text"]]
        assert len(temp) == 1
        assert temp[0]["unit"] == "°C"

    def test_heart_rate(self, extractor):
        text = "Heart rate is 72 bpm."
        entities = extractor.extract(text)
        measurements = [e for e in entities if e["type"] == "measurement"]
        assert len(measurements) >= 1
        hr = [m for m in measurements if "72" in m["text"] and "bpm" in m["text"]]
        assert len(hr) == 1
        assert hr[0]["unit"] == "bpm"

    def test_simple_value_unit(self, extractor):
        text = "Lesion size is 5.4 cm."
        entities = extractor.extract(text)
        measurements = [e for e in entities if e["type"] == "measurement"]
        assert len(measurements) >= 1
        size = [m for m in measurements if "5.4" in m["text"] and "cm" in m["text"]]
        assert len(size) == 1
        assert size[0]["value"] == "5.4"
        assert size[0]["unit"] == "cm"


class TestNegationHandling:
    def test_no_evidence_of_disease(self, extractor):
        text = "No evidence of pneumonia."
        entities = extractor.extract(text)
        pneumonias = [e for e in entities if e["type"] == "disease" and e["text"].lower() == "pneumonia"]
        assert len(pneumonias) == 1
        assert pneumonias[0]["negated"] is True

    def test_no_sign_of_finding(self, extractor):
        text = "No sign of pleural effusion."
        entities = extractor.extract(text)
        effusions = [e for e in entities if e["type"] == "finding" and "pleural effusion" in e["text"].lower()]
        assert len(effusions) == 1
        assert effusions[0]["negated"] is True

    def test_absent_finding(self, extractor):
        text = "Absent breath sounds on the left."
        entities = extractor.extract(text)
        assert len(entities) == 0

    def test_positive_disease(self, extractor):
        text = "Pneumonia is present."
        entities = extractor.extract(text)
        pneumonias = [e for e in entities if e["type"] == "disease" and e["text"].lower() == "pneumonia"]
        assert len(pneumonias) == 1
        assert pneumonias[0]["negated"] is False


class TestEmptyAndMalformedText:
    def test_empty_text(self, nlp_service):
        import asyncio
        result = asyncio.run(nlp_service.extract_entities(""))
        assert result == []

    def test_whitespace_only(self, nlp_service):
        import asyncio
        result = asyncio.run(nlp_service.extract_entities("   \n\n   "))
        assert result == []

    def test_none_input(self, nlp_service):
        import asyncio
        result = asyncio.run(nlp_service.extract_entities(None))
        assert result == []

    def test_gibberish_text(self, extractor):
        text = "xyzabc 12345 !@#$% qwerty"
        entities = extractor.extract(text)
        assert len(entities) == 0


class TestMedicalNLPServiceIntegration:
    def test_extract_entities_success(self, nlp_service):
        import asyncio
        text = "Mild cardiomegaly is noted. Blood pressure is 120/80 mmHg. No evidence of pneumonia."
        entities = asyncio.run(nlp_service.extract_entities(text))
        types = [e["type"] for e in entities]
        assert "finding" in types
        assert "measurement" in types
        assert "disease" in types
        pneumonias = [e for e in entities if e["type"] == "disease" and e["text"].lower() == "pneumonia"]
        assert len(pneumonias) == 1
        assert pneumonias[0]["negated"] is True
        measurements = [e for e in entities if e["type"] == "measurement" and "120/80" in e["text"]]
        assert len(measurements) == 1
        assert measurements[0]["unit"] == "mmHg"
