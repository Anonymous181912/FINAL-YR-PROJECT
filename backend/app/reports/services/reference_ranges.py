"""Reference-range data table for lab value flagging (Phase 1).

EDUCATIONAL DATASET — NOT CLINICAL ADVICE. These are widely published adult
reference intervals compiled for a student project. They must never be used
for diagnosis or treatment decisions. The app only flags whether a value is
inside/outside the range and always advises discussing results with a doctor.

All ranges are stored in the test's STANDARD unit (see ``standard_unit``).
``lab_parser`` converts reported values into the standard unit before
comparing. Sex-specific entries carry ``male``/``female`` ranges plus a
general ``adult`` fallback used when gender is unknown.
"""

# Canonical test key -> definition.
# ranges: {"adult": (low, high)} or {"male": ..., "female": ..., "adult": ...}
REFERENCE_RANGES = {
    "hemoglobin": {
        "display_name": "Hemoglobin",
        "synonyms": [
            "hemoglobin", "haemoglobin", "hgb", "hb", "hbg",
            "hemoglobin (hb)", "hb%",
        ],
        "standard_unit": "g/dL",
        "ranges": {"male": (13.0, 17.0), "female": (12.0, 15.5), "adult": (12.0, 16.0)},
    },
    "rbc": {
        "display_name": "RBC (Red Blood Cells)",
        "synonyms": [
            "rbc", "rbcs", "rbcs count", "rbc count", "total rbc count",
            "total red blood cell count", "red blood cell count",
            "red blood cells", "red blood cell", "red cell count",
            "r.b.c", "tec", "total erythrocyte count",
        ],
        "standard_unit": "million/uL",
        "ranges": {"male": (4.5, 5.5), "female": (4.0, 5.0), "adult": (4.0, 5.5)},
    },
    "wbc": {
        "display_name": "WBC (White Blood Cells)",
        "synonyms": [
            "wbc", "tlc", "total leukocyte count", "total leucocyte count",
            "totalleucocyte count", "total leucocyte count (tlc)",
            "totalleucocyte count (tlc)", "total leukocytes",
            "total leucocytes", "leukocyte count", "leucocyte count",
            "white blood cell count", "white blood cells", "white blood cell",
            "total wbc", "w.b.c",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (4.0, 11.0)},
    },
    "platelets": {
        "display_name": "Platelets",
        "synonyms": [
            "platelet count", "platelet counts", "platelets counts",
            "platelets count", "platelets", "platelet", "plt",
            "thrombocyte count", "thrombocytes", "thrombocyte",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (150.0, 450.0)},
    },
    "hematocrit": {
        "display_name": "Hematocrit",
        "synonyms": [
            "hematocrit", "haematocrit", "hct", "pcv", "p.c.v", "p.c.v.",
            "packed cell volume", "hematocrit value", "haematocrit value",
        ],
        "standard_unit": "%",
        "ranges": {"male": (40.0, 50.0), "female": (36.0, 46.0), "adult": (36.0, 50.0)},
    },
    "fasting_glucose": {
        "display_name": "Fasting Glucose",
        "synonyms": [
            "fasting glucose", "fasting blood sugar", "fasting sugar",
            "fasting blood glucose", "fbs", "fbg", "glucose fasting",
            "blood sugar fasting", "blood sugar (fasting)",
            "blood sugar(fasting)", "sugar fasting",
        ],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (70.0, 100.0)},
    },
    "random_glucose": {
        "display_name": "Random Glucose",
        "synonyms": [
            "random glucose", "random blood sugar", "random sugar",
            "random blood glucose", "rbs", "rbg", "glucose random",
            "blood sugar random", "sugar random",
        ],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (70.0, 140.0)},
    },
    "post_prandial_glucose": {
        "display_name": "Post-Prandial Glucose",
        "synonyms": [
            "post prandial glucose", "post-prandial glucose",
            "post prandial blood sugar", "post-prandial blood sugar",
            "blood sugar (post prandial)", "blood sugar(post prandial)",
            "blood sugar post prandial", "post prandial sugar",
            "post-prandial sugar", "post prandial", "post-prandial",
            "ppbs", "ppbg", "2 hour post prandial", "2-hour post prandial",
            "2h post prandial", "glucose post prandial",
        ],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (70.0, 140.0)},
    },
    "hba1c": {
        "display_name": "HbA1c",
        "synonyms": [
            "hba1c", "hb a1c", "a1c", "glycosylated hemoglobin",
            "glycated hemoglobin", "glycohemoglobin", "glycosylated haemoglobin",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (4.0, 5.6)},
    },
    "total_cholesterol": {
        "display_name": "Total Cholesterol",
        "synonyms": [
            "total cholesterol", "cholesterol total", "serum cholesterol",
            "cholesterol",
        ],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (125.0, 200.0)},
    },
    "ldl": {
        "display_name": "LDL Cholesterol",
        "synonyms": ["ldl cholesterol", "ldl", "ldl-c", "low density lipoprotein"],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (0.0, 100.0)},
    },
    "hdl": {
        "display_name": "HDL Cholesterol",
        "synonyms": ["hdl cholesterol", "hdl", "hdl-c", "high density lipoprotein"],
        "standard_unit": "mg/dL",
        "ranges": {"male": (40.0, 100.0), "female": (50.0, 100.0), "adult": (40.0, 100.0)},
    },
    "triglycerides": {
        "display_name": "Triglycerides",
        "synonyms": ["triglycerides", "triglyceride", "trig", "tgs", "tg", "triacylglycerol"],
        "standard_unit": "mg/dL",
        "ranges": {"adult": (0.0, 150.0)},
    },
    "creatinine": {
        "display_name": "Creatinine",
        "synonyms": ["serum creatinine", "creatinine", "creat", "s creat", "s. creat"],
        "standard_unit": "mg/dL",
        "ranges": {"male": (0.7, 1.3), "female": (0.6, 1.1), "adult": (0.6, 1.3)},
    },
    "urea_bun": {
        "display_name": "Urea / BUN",
        "synonyms": [
            "blood urea nitrogen", "urea nitrogen", "blood urea", "bun",
            "urea", "b.u.n", "serum urea",
        ],
        # NOTE: table range below is the BUN interval. Many labs print "Urea"
        # (roughly 2x BUN); printed report ranges always win over this table,
        # so explicit lab ranges are unaffected by this simplification.
        "standard_unit": "mg/dL",
        "ranges": {"adult": (7.0, 20.0)},
    },
    "alt": {
        "display_name": "ALT",
        "synonyms": ["alanine aminotransferase", "alanine transaminase", "sgpt", "alt"],
        "standard_unit": "U/L",
        "ranges": {"adult": (7.0, 56.0)},
    },
    "ast": {
        "display_name": "AST",
        "synonyms": ["aspartate aminotransferase", "aspartate transaminase", "sgot", "ast"],
        "standard_unit": "U/L",
        "ranges": {"adult": (10.0, 40.0)},
    },
    "tsh": {
        "display_name": "TSH",
        "synonyms": ["thyroid stimulating hormone", "thyrotropin", "tsh", "thyroid-stimulating hormone"],
        "standard_unit": "mIU/L",
        "ranges": {"adult": (0.4, 4.0)},
    },
    "sodium": {
        "display_name": "Sodium",
        "synonyms": ["serum sodium", "sodium", "na+"],
        "standard_unit": "mEq/L",
        "ranges": {"adult": (135.0, 145.0)},
    },
    "potassium": {
        "display_name": "Potassium",
        "synonyms": ["serum potassium", "potassium", "k+"],
        "standard_unit": "mEq/L",
        "ranges": {"adult": (3.5, 5.0)},
    },
    # CBC differential and red-cell indices. These are the values printed as
    # separate table rows in common Indian lab reports (e.g. "Basophils 0.00
    # 0 - 1", "MCV 80.00 81 - 101"). Adding them prevents the parser from
    # silently discarding most of a CBC when OCR puts each column on its own line.
    "neutrophil_percent": {
        "display_name": "Neutrophils",
        "synonyms": [
            "neutrophil percent", "neutrophils percent", "neutrophil %", "neutrophils %",
            "neutrophiles", "neutrophile", "neutrophils", "neutrophil",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (40.0, 80.0)},
    },
    "lymphocyte_percent": {
        "display_name": "Lymphocytes",
        "synonyms": [
            "lymphocyte percent", "lymphocytes percent", "lymphocyte %", "lymphocytes %",
            "lymphocyte(s)", "lymphocyte (s)", "lymphocytes", "lymphocyte",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (20.0, 40.0)},
    },
    "eosinophil_percent": {
        "display_name": "Eosinophils",
        "synonyms": [
            "eosinophil percent", "eosinophils percent", "eosinophil %", "eosinophils %",
            "eosinophils", "eosinophil",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (1.0, 6.0)},
    },
    "monocyte_percent": {
        "display_name": "Monocytes",
        "synonyms": [
            "monocyte percent", "monocytes percent", "monocyte %", "monocytes %",
            "monocytes", "monocyte",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (2.0, 10.0)},
    },
    "basophil_percent": {
        "display_name": "Basophils",
        "synonyms": [
            "basophil percent", "basophils percent", "basophil %", "basophils %",
            "basophils", "basophil",
        ],
        "standard_unit": "%",
        "ranges": {"adult": (0.0, 1.0)},
    },
    "absolute_neutrophils": {
        "display_name": "Absolute Neutrophils",
        "synonyms": [
            "absolute neutrophil count", "absolute neutrophils", "absolute neutrophil",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (2.0, 7.0)},
    },
    "absolute_lymphocytes": {
        "display_name": "Absolute Lymphocytes",
        "synonyms": [
            "absolute lymphocyte count", "absolute lymphocytes", "absolute lymphocyte",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (1.0, 3.0)},
    },
    "absolute_eosinophils": {
        "display_name": "Absolute Eosinophils",
        "synonyms": [
            "absolute eosinophil count", "absolute eosinophils", "absolute eosinophil",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (0.0, 0.5)},
    },
    "absolute_monocytes": {
        "display_name": "Absolute Monocytes",
        "synonyms": [
            "absolute monocyte count", "absolute monocytes", "absolute monocyte",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (0.2, 1.0)},
    },
    "absolute_basophils": {
        "display_name": "Absolute Basophils",
        "synonyms": [
            "absolute basophil count", "absolute basophils", "absolute basophil",
        ],
        "standard_unit": "x10^3/uL",
        "ranges": {"adult": (0.0, 0.2)},
    },
    "mcv": {
        "display_name": "MCV",
        "synonyms": [
            "mean corpuscular volume", "m.c.v.", "m.c.v", "mcv",
        ],
        "standard_unit": "fL",
        "ranges": {"adult": (81.0, 101.0)},
    },
    "mch": {
        "display_name": "MCH",
        "synonyms": [
            "mean corpuscular hemoglobin", "mean corpuscular haemoglobin",
            "mean cell hemoglobin", "mean cell haemoglobin",
            "m.c.h.", "m.c.h", "mch",
        ],
        "standard_unit": "pg",
        "ranges": {"adult": (27.0, 32.0)},
    },
    "mchc": {
        "display_name": "MCHC",
        "synonyms": [
            "mean corpuscular hemoglobin concentration",
            "mean corpuscular haemoglobin concentration",
            "mean cell hemoglobin concentration",
            "mean cell haemoglobin concentration",
            "mean cell hemoglobin con", "mean cell haemoglobin con",
            "m.c.h.c.", "m.c.h.c", "mchc",
        ],
        "standard_unit": "g/dL",
        "ranges": {"adult": (31.5, 34.5)},
    },
    "rdw_cv": {
        "display_name": "RDW-CV",
        "synonyms": ["rdw-cv", "rdw cv", "rdw"],
        "standard_unit": "%",
        "ranges": {"adult": (11.6, 14.0)},
    },
    "rdw_sd": {
        "display_name": "RDW-SD",
        "synonyms": ["rdw-sd", "rdw sd"],
        "standard_unit": "fL",
        "ranges": {"adult": (39.0, 46.0)},
    },
    "esr": {
        "display_name": "ESR",
        "synonyms": [
            "erythrocyte sedimentation rate", "sedimentation rate", "esr",
        ],
        "standard_unit": "mm/hr",
        "ranges": {"male": (0.0, 15.0), "female": (0.0, 20.0), "adult": (0.0, 20.0)},
    },
    "vitamin_d": {
        "display_name": "Vitamin D",
        "synonyms": [
            "25-hydroxy vitamin d", "25 hydroxy vitamin d", "25-oh vitamin d",
            "vitamin d", "vit d", "calcidiol", "25(oh)d",
        ],
        "standard_unit": "ng/mL",
        "ranges": {"adult": (20.0, 50.0)},
    },
}

# synonym (lowercased) -> canonical key, built longest-first for matching.
SYNONYM_TO_CANONICAL: dict[str, str] = {}
for _canon, _def in REFERENCE_RANGES.items():
    for _syn in _def["synonyms"]:
        SYNONYM_TO_CANONICAL[_syn.lower()] = _canon

# Unit alias (normalised: lowercase, no spaces, µ/μ→u) -> (family, factor).
# value_in_standard_unit = reported_value * factor, except the "mmol" family
# (factor resolved per test via MMOL_PER_TEST_FACTOR) and "count_raw"
# (divisor resolved per test: wbc/platelets ÷1e3, rbc ÷1e6).
UNIT_ALIASES: dict[str, tuple[str, float]] = {
    "mg/dl": ("mgdl", 1.0),
    "mg%": ("mgdl", 1.0),
    "mg/l": ("mg_per_l", 0.1),  # only valid for creatinine (checked per test)
    "mmol/l": ("mmol", 0.0),  # factor per test; 0.0 = "resolve me"
    "umol/l": ("creat_umol", 1.0 / 88.4),
    "µmol/l": ("creat_umol", 1.0 / 88.4),
    "μmol/l": ("creat_umol", 1.0 / 88.4),
    "g/dl": ("hb", 1.0),
    "gm/dl": ("hb", 1.0),
    "g%": ("hb", 1.0),
    "gm%": ("hb", 1.0),
    "g/l": ("hb_gl", 0.1),
    # OCR often renders "g/dL" as "gldL"/"gldl", or "Gm%" as "Gmie".
    "gldl": ("hb", 1.0),
    "gmie": ("hb", 1.0),
    "gmle": ("hb", 1.0),
    "gmi": ("hb", 1.0),
    "fl": ("fl", 1.0),
    "femtoliter": ("fl", 1.0),
    "femtoliters": ("fl", 1.0),
    "pg": ("pg", 1.0),
    "picogram": ("pg", 1.0),
    "picograms": ("pg", 1.0),
    "x10^3/ul": ("count_k", 1.0),
    "x10^3/µl": ("count_k", 1.0),
    "x10^3/μl": ("count_k", 1.0),
    "10^3/ul": ("count_k", 1.0),
    "x103/ul": ("count_k", 1.0),
    "x10^3/cumm": ("count_k", 1.0),
    "x10^3/cmm": ("count_k", 1.0),
    "x103/cumm": ("count_k", 1.0),
    "x103/cmm": ("count_k", 1.0),
    "10^3/cumm": ("count_k", 1.0),
    "10^3/cmm": ("count_k", 1.0),
    "k/ul": ("count_k", 1.0),
    "k/cumm": ("count_k", 1.0),
    "k/cmm": ("count_k", 1.0),
    "thou/ul": ("count_k", 1.0),
    "thousand/ul": ("count_k", 1.0),
    "thou/cumm": ("count_k", 1.0),
    "thou/cmm": ("count_k", 1.0),
    "thousand/cumm": ("count_k", 1.0),
    "thousand/cmm": ("count_k", 1.0),
    "cells/ul": ("count_raw", 1.0),
    "cells/cumm": ("count_raw", 1.0),
    "cells/cmm": ("count_raw", 1.0),
    "/cumm": ("count_raw", 1.0),
    "/cmm": ("count_raw", 1.0),
    "/ul": ("count_raw", 1.0),
    "/mm3": ("count_raw", 1.0),
    "mm3": ("count_raw", 1.0),
    "cmm3": ("count_raw", 1.0),
    # OCR commonly drops the leading slash: "Icumm", "(cumm" -> "cumm".
    "cumm": ("count_raw", 1.0),
    "cmm": ("count_raw", 1.0),
    "icumm": ("count_raw", 1.0),
    "icmm": ("count_raw", 1.0),
    "percumm": ("count_raw", 1.0),
    "percmm": ("count_raw", 1.0),
    "perul": ("count_raw", 1.0),
    "permm3": ("count_raw", 1.0),
    "million/ul": ("count_m", 1.0),
    "million/cumm": ("count_m", 1.0),
    "million/cmm": ("count_m", 1.0),
    "million/mm3": ("count_m", 1.0),
    "mill/ul": ("count_m", 1.0),
    "mill/cumm": ("count_m", 1.0),
    "mill/cmm": ("count_m", 1.0),
    "mil/ul": ("count_m", 1.0),
    "mil/cumm": ("count_m", 1.0),
    "mil/cmm": ("count_m", 1.0),
    "milcumm": ("count_m", 1.0),
    "milcmm": ("count_m", 1.0),
    "millcumm": ("count_m", 1.0),
    "millcmm": ("count_m", 1.0),
    "millioncumm": ("count_m", 1.0),
    "millioncmm": ("count_m", 1.0),
    "x10^6/ul": ("count_m", 1.0),
    "10^6/ul": ("count_m", 1.0),
    "m/ul": ("count_m", 1.0),
    "lakh/cumm": ("count_lakh", 100.0),
    "lakhs/cumm": ("count_lakh", 100.0),
    "lakh/cmm": ("count_lakh", 100.0),
    "lakhs/cmm": ("count_lakh", 100.0),
    "lac/cumm": ("count_lakh", 100.0),
    "lac/cmm": ("count_lakh", 100.0),
    "lacs/cumm": ("count_lakh", 100.0),
    "lacs/cmm": ("count_lakh", 100.0),
    "lacsicmm": ("count_lakh", 100.0),
    "lacsicum": ("count_lakh", 100.0),
    "lathscumm": ("count_lakh", 100.0),
    "lathscmm": ("count_lakh", 100.0),
    "lakhscumm": ("count_lakh", 100.0),
    "%": ("percent", 1.0),
    "percent": ("percent", 1.0),
    "pct": ("percent", 1.0),
    "u/l": ("enzyme", 1.0),
    "iu/l": ("enzyme", 1.0),
    "miu/l": ("tsh", 1.0),
    "uiu/ml": ("tsh", 1.0),
    "μiu/ml": ("tsh", 1.0),
    "miu/ml": ("tsh", 1.0),
    "meq/l": ("lyte", 1.0),
    "mm/hr": ("sed_rate", 1.0),
    "mm/1hr": ("sed_rate", 1.0),
    "mm/h": ("sed_rate", 1.0),
    "mmhr": ("sed_rate", 1.0),
    "ng/ml": ("vitd", 1.0),
    "nmol/l": ("vitd_nmol", 1.0 / 2.496),
}

# Which unit families each canonical test accepts. A reported unit whose
# family is not listed -> flag "unknown" (never guess).
TEST_UNIT_FAMILIES: dict[str, set[str]] = {
    "hemoglobin": {"hb", "hb_gl"},
    "rbc": {"count_m", "count_raw"},
    "wbc": {"count_k", "count_raw", "count_lakh"},
    "platelets": {"count_k", "count_raw", "count_lakh"},
    "hematocrit": {"percent"},
    "neutrophil_percent": {"percent"},
    "lymphocyte_percent": {"percent"},
    "eosinophil_percent": {"percent"},
    "monocyte_percent": {"percent"},
    "basophil_percent": {"percent"},
    "absolute_neutrophils": {"count_k", "count_raw"},
    "absolute_lymphocytes": {"count_k", "count_raw"},
    "absolute_eosinophils": {"count_k", "count_raw"},
    "absolute_monocytes": {"count_k", "count_raw"},
    "absolute_basophils": {"count_k", "count_raw"},
    "mcv": {"fl"},
    "mch": {"pg"},
    "mchc": {"hb", "hb_gl"},
    "rdw_cv": {"percent"},
    "rdw_sd": {"fl"},
    "esr": {"sed_rate"},
    "fasting_glucose": {"mgdl", "mmol"},
    "random_glucose": {"mgdl", "mmol"},
    "post_prandial_glucose": {"mgdl", "mmol"},
    "hba1c": {"percent", "hba1c_ifcc"},
    "total_cholesterol": {"mgdl", "mmol"},
    "ldl": {"mgdl", "mmol"},
    "hdl": {"mgdl", "mmol"},
    "triglycerides": {"mgdl", "mmol"},
    "creatinine": {"mgdl", "mg_per_l", "creat_umol"},
    "urea_bun": {"mgdl", "mmol"},
    "alt": {"enzyme"},
    "ast": {"enzyme"},
    "tsh": {"tsh"},
    "sodium": {"lyte", "mmol"},
    "potassium": {"lyte", "mmol"},
    "vitamin_d": {"vitd", "vitd_nmol"},
}

# mmol/L -> standard-unit factor per test (value_std = value * factor).
MMOL_PER_TEST_FACTOR = {
    "fasting_glucose": 18.0,
    "random_glucose": 18.0,
    "post_prandial_glucose": 18.0,
    "total_cholesterol": 38.67,
    "ldl": 38.67,
    "hdl": 38.67,
    "triglycerides": 88.57,
    "urea_bun": 2.8,
    "sodium": 1.0,
    "potassium": 1.0,
}

# HbA1c IFCC units need an affine (not multiplicative) conversion.
HBA1C_IFFC_ALIASES = {"mmol/mol", "mmol/molhb", "ifcc"}


def convert_hba1c_ifcc_to_percent(value: float) -> float:
    """IFCC (mmol/mol) -> NGSP (%) conversion (affine)."""
    return value / 10.929 + 2.15
