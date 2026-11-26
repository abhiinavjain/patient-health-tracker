"""Name, dose and unit normalisation shared by the extractors and the evaluation scorer."""

from __future__ import annotations

import re

# Brand / abbreviation -> generic. Indian brands are common in OPD notes.
MED_ALIASES = {
    "glycomet": "metformin", "glucophage": "metformin", "amlong": "amlodipine", "amlodac": "amlodipine",
    "telma": "telmisartan", "telmikind": "telmisartan", "thyronorm": "levothyroxine", "eltroxin": "levothyroxine",
    "ecosprin": "aspirin", "asa": "aspirin", "clopilet": "clopidogrel", "atorva": "atorvastatin", "rozavel": "rosuvastatin",
    "pan": "pantoprazole", "pantocid": "pantoprazole", "dolo": "paracetamol", "crocin": "paracetamol",
    "calpol": "paracetamol", "acetaminophen": "paracetamol", "pcm": "paracetamol", "albuterol": "salbutamol",
    "asthalin": "salbutamol", "hctz": "hydrochlorothiazide", "mtx": "methotrexate", "lasix": "furosemide",
    "frusemide": "furosemide", "glargine": "insulin glargine", "lantus": "insulin glargine", "basalog": "insulin glargine",
    "aspart": "insulin aspart", "novorapid": "insulin aspart", "lispro": "insulin lispro", "januvia": "sitagliptin",
    "hcq": "hydroxychloroquine", "epo": "erythropoietin", "ismn": "isosorbide mononitrate", "zofer": "ondansetron",
    "emeset": "ondansetron", "augmentin": "amoxicillin-clavulanate", "seroflo": "fluticasone-salmeterol",
    "foracort": "budesonide-formoterol", "symbicort": "budesonide-formoterol", "tiova": "tiotropium",
    "syndopa": "levodopa-carbidopa", "sinemet": "levodopa-carbidopa", "carbidopa-levodopa": "levodopa-carbidopa",
}

_SPLIT = re.compile(r"\s*(?:/|\+|-|\band\b|&)\s*")


def med_name(name: str) -> str:
    n = re.sub(r"\s+", " ", name.strip().lower())
    n = re.sub(r"\b(tab|tabs|tablet|cap|capsule|inj|injection|syp|syrup|inhaler|cream|oint|ointment)\b\.?", "", n).strip()
    return MED_ALIASES.get(n, n)


def med_key(name: str) -> frozenset[str]:
    """Order-insensitive components: 'formoterol/budesonide' == 'budesonide-formoterol'."""
    n = med_name(name)
    parts = [MED_ALIASES.get(p, p) for p in _SPLIT.split(n) if p]
    return frozenset(parts) if len(parts) > 1 else frozenset([n])


_UNIT = {"mg": "mg", "g": "mg", "gm": "mg", "gram": "mg", "grams": "mg", "mcg": "mcg", "µg": "mcg", "ug": "mcg",
         "u": "units", "iu": "units", "unit": "units", "units": "units", "ml": "ml"}


def dose_key(dose: str | None) -> str | None:
    """'1 g' -> '1000 mg'; '18 U' -> '18 units'; '200/6' stays a composite."""
    if not dose:
        return None
    d = dose.strip().lower().replace(" ", "")
    m = re.fullmatch(r"([\d.]+(?:/[\d.]+)*)([a-zµ]+)?", d)
    if not m:
        return dose.strip().lower()
    nums, unit = m.group(1), _UNIT.get(m.group(2) or "", m.group(2) or "")
    if (m.group(2) or "") in ("g", "gm", "gram", "grams") and "/" not in nums:
        nums = f"{float(nums) * 1000:g}"
    else:
        nums = "/".join(f"{float(x):g}" for x in nums.split("/"))
    return f"{nums} {unit}".strip()


def values_match(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.2, 0.02 * abs(b))


# Unit conversions to the catalog's canonical units.
def f_to_c(f: float) -> float:
    return round((f - 32) * 5 / 9, 1)


def lb_to_kg(lb: float) -> float:
    return round(lb * 0.45359237, 1)


def mmol_to_mgdl_glucose(v: float) -> float:
    return round(v * 18.0, 1)


def ft_in_to_cm(ft: float, inch: float) -> float:
    return round((ft * 12 + inch) * 2.54, 1)
