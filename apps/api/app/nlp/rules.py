"""Rule-based baseline extractor: lexicons + regular expressions + NegEx-style negation.

Deterministic, offline, ~1 ms per note. Frozen as the v1 baseline (see eval/.rules_frozen.sha256); the shipped
extractor is app/nlp/local.py, which builds on these rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import MED_ALIASES, f_to_c, ft_in_to_cm, lb_to_kg, med_name, mmol_to_mgdl_glucose
from .schema import ExtractedCondition, ExtractedMedication, ExtractedObservation, NoteExtraction

# ----------------------------------------------------------------------------- lexicons
# (pattern, ICD-10, description). Earlier entries win when spans overlap. (?-i:...) = case-sensitive.
CONDITIONS: list[tuple[str, str, str]] = [
    (r"type\s*1\s*(?:dm|diabetes(?: mellitus)?)|\bt1dm\b|\bdm\s*(?:type\s*)?1\b", "E10.9", "Type 1 diabetes mellitus"),
    (r"diabetic nephropathy", "E11.21", "Type 2 diabetes with diabetic nephropathy"),
    (r"\bprediabet\w*|\bpre-diabet\w*|impaired fasting glucose", "R73.03", "Prediabetes"),
    (r"\bt2dm\b|\bdm\s*(?:type\s*)?2\b|type\s*2\s*(?:dm|diabetes(?: mellitus)?)|\bdiabetes(?: mellitus)?\b(?!\s*(?:educator|clinic|nurse))|\bdiabetic\b(?!\s*(?:clinic|educator|diet))",
     "E11.9", "Type 2 diabetes mellitus"),
    (r"\bhypoglyc(?:a)?emi\w*", "E16.2", "Hypoglycaemia"),
    (r"\bhtn\b|\bhypertension\b|\bhypertensive\b", "I10", "Essential hypertension"),
    (r"hyperlipid(?:a)?emia|dyslipid(?:a)?emia|hypercholesterol(?:a)?emia", "E78.5", "Hyperlipidaemia"),
    (r"\bnstemi\b|\bstemi\b|myocardial infarction|(?-i:\bMI\b)", "I21.4", "Myocardial infarction"),
    (r"\bangina\b", "I20.9", "Angina pectoris"),
    (r"\bcad\b|coronary artery disease|\bihd\b|ischa?emic heart disease|s/p pci", "I25.10", "Coronary artery disease"),
    (r"heart failure|\bchf\b|\bhfref\b|\bhfpef\b|(?-i:\bHF\b)", "I50.9", "Heart failure"),
    (r"atrial fibrillation|(?-i:\bAF\b)", "I48.91", "Atrial fibrillation"),
    (r"isch(?:a)?emic stroke|\bstroke\b|\bcva\b", "I63.9", "Ischaemic stroke"),
    (r"\bckd\b|chronic kidney disease", "N18.9", "Chronic kidney disease"),
    (r"\bcopd\b|chronic obstructive pulmonary", "J44.9", "Chronic obstructive pulmonary disease"),
    (r"\basthma\b", "J45.909", "Asthma"),
    (r"pneumonia", "J18.9", "Pneumonia"),
    (r"\bgerd\b|\bgord\b|gastro-?o?esophageal reflux|acid reflux", "K21.9", "Gastro-oesophageal reflux disease"),
    (r"gastroenteritis", "A09", "Gastroenteritis"),
    (r"cirrhosis|alcohol(?:ic| related) liver disease|\bald\b", "K70.30", "Alcoholic cirrhosis of liver"),
    (r"(?:o)?esophageal varices|\bvarices\b", "I85.10", "Oesophageal varices"),
    (r"knee (?:oa|osteoarthritis)|osteoarthritis of (?:the )?knee", "M17.9", "Osteoarthritis of knee"),
    (r"osteoarthritis|(?-i:\bOA\b)", "M19.90", "Osteoarthritis"),
    # "SpO2 96% RA" / "on RA" = room air, not rheumatoid arthritis.
    (r"rheumatoid arthritis|(?<!%)(?<!% )(?<!on )(?-i:\bRA\b)", "M06.9", "Rheumatoid arthritis"),
    (r"\bgout\b", "M10.9", "Gout"),
    (r"\bobes(?:e|ity)\b", "E66.9", "Obesity"),
    (r"hypothyroid\w*", "E03.9", "Hypothyroidism"),
    (r"hyperthyroid\w*|thyrotoxicosis", "E05.90", "Hyperthyroidism"),
    (r"\bdepression\b|depressive", "F32.A", "Depression"),
    (r"\banxiety\b", "F41.9", "Anxiety"),
    (r"dementia|alzheimer", "F03.90", "Dementia"),
    (r"parkinson", "G20", "Parkinson's disease"),
    (r"migraine", "G43.909", "Migraine"),
    (r"epilepsy|seizure disorder", "G40.909", "Epilepsy"),
    (r"cystitis", "N30.00", "Acute cystitis"),
    (r"\buti\b|urinary tract infection", "N39.0", "Urinary tract infection"),
    (r"dengue", "A90", "Dengue fever"),
    (r"malaria", "B54", "Malaria"),
    (r"tuberculosis|(?-i:\bTB\b)", "A15.9", "Tuberculosis"),
    (r"hyponat(?:r)?(?:a)?emia", "E87.1", "Hyponatraemia"),
    (r"(?:fracture|#)\s*(?:of\s*)?(?:the\s*)?neck of femur|\bnof fracture|hip fracture", "S72.009A", "Fracture of neck of femur"),
    (r"psoriasis", "L40.0", "Psoriasis"),
    (r"an(?:a)?emia", "D64.9", "Anaemia"),
    (r"\bosa\b|obstructive sleep apn(?:o)?ea", "G47.33", "Obstructive sleep apnoea"),
]
_COND = [(re.compile(p, re.I), code, desc) for p, code, desc in CONDITIONS]

GENERICS = {
    "metformin", "glimepiride", "gliclazide", "glipizide", "sitagliptin", "vildagliptin", "linagliptin", "teneligliptin",
    "empagliflozin", "dapagliflozin", "pioglitazone", "insulin glargine", "insulin aspart", "insulin lispro", "insulin",
    "telmisartan", "losartan", "olmesartan", "amlodipine", "cilnidipine", "enalapril", "ramipril", "lisinopril",
    "hydrochlorothiazide", "chlorthalidone", "indapamide", "metoprolol", "bisoprolol", "carvedilol", "atenolol",
    "propranolol", "furosemide", "torsemide", "spironolactone", "atorvastatin", "rosuvastatin", "aspirin",
    "clopidogrel", "ticagrelor", "apixaban", "rivaroxaban", "warfarin", "heparin", "isosorbide mononitrate",
    "nitroglycerin", "levothyroxine", "pantoprazole", "omeprazole", "rabeprazole", "ondansetron", "domperidone",
    "paracetamol", "ibuprofen", "diclofenac", "tramadol", "colchicine", "febuxostat", "allopurinol", "methotrexate",
    "folic acid", "hydroxychloroquine", "prednisolone", "sertraline", "escitalopram", "fluoxetine", "amitriptyline",
    "zolpidem", "alprazolam", "sumatriptan", "levodopa-carbidopa", "salbutamol", "tiotropium", "budesonide-formoterol",
    "fluticasone-salmeterol", "montelukast", "amoxicillin", "amoxicillin-clavulanate", "azithromycin", "ceftriaxone",
    "doxycycline", "ciprofloxacin", "nitrofurantoin", "metronidazole", "erythropoietin", "iron sucrose",
    "alendronate", "calcium-vitamin d", "thiamine", "vitamin d", "clobetasol", "alteplase", "levetiracetam",
}

# Surface forms -> generic. Combination forms like "budesonide/formoterol" are listed explicitly.
_SURFACE = {g: g for g in GENERICS}
_SURFACE.update({k: v for k, v in MED_ALIASES.items() if v in GENERICS})
_SURFACE.update({
    "budesonide/formoterol": "budesonide-formoterol", "formoterol/budesonide": "budesonide-formoterol",
    "fluticasone/salmeterol": "fluticasone-salmeterol", "salmeterol/fluticasone": "fluticasone-salmeterol",
    "levodopa/carbidopa": "levodopa-carbidopa", "carbidopa/levodopa": "levodopa-carbidopa",
    "calcium + vitamin d": "calcium-vitamin d", "calcium and vitamin d": "calcium-vitamin d",
    "calcium with vitamin d": "calcium-vitamin d", "vit d": "vitamin d", "isosorbide mononitrate": "isosorbide mononitrate",
})
_MED_RE = re.compile(r"(?<![\w-])(" + "|".join(sorted((re.escape(s) for s in _SURFACE), key=len, reverse=True)) + r")(?![\w-])", re.I)

FREQ = [
    (r"\b(?:tds|tid|thrice daily|three times (?:a day|daily))\b", "three_times_daily"),
    (r"\b(?:qid|qds|four times (?:a day|daily))\b", "four_times_daily"),
    (r"\b(?:bd|bid|twice (?:a day|daily))\b", "twice_daily"),
    (r"\b(?:hs|at night|nightly|at bedtime|bedtime|qhs)\b", "at_night"),
    (r"\b(?:once (?:a )?week(?:ly)?|weekly)\b", "weekly"),
    (r"\b(?:od|qd|once (?:a day|daily)|daily|every day)\b", "once_daily"),
    (r"\b(?:prn|sos|as needed|as required|when required)\b", "as_needed"),
    (r"\bwith (?:each )?meals\b", "with_meals"),
]
_FREQ = [(re.compile(p, re.I), c) for p, c in FREQ]

ACTIONS = [
    (r"\b(?:stop(?:ped)?|discontinu\w*|d/c|hold|held|withh[oe]ld\w*|withdraw\w*|cease\w*)\b", "stopped"),
    (r"\b(?:increas\w*|up-?titrat\w*|escalat\w*|↑)\b", "dose_increased"),
    (r"\b(?:reduc\w*|decreas\w*|taper\w*|lower\w*|↓)\b", "dose_decreased"),
    (r"\b(?:continu\w*|cont\.?|unchanged|same dose|resume\w*|maintain\w*)\b", "continued"),
    (r"\b(?:start(?:ed)?|add(?:ed)?|initiat\w*|commenc\w*|begin|began|new|rx|prescrib\w*|given|switch(?:ed)? to)\b", "started"),
]
_ACT = [(re.compile(p, re.I), a) for p, a in ACTIONS]
_ON = re.compile(r"\b(?:on|using|taking|takes)\s+$", re.I)
PRIORITY = {"stopped": 4, "dose_increased": 3, "dose_decreased": 3, "started": 2, "continued": 1}

NEG_PRE = re.compile(r"\b(?:no|not|denies|denied|without|negative for|ruled out|rule out|r/o|absence of|free of|"
                     r"nor|never|fam(?:ily)? (?:hx|history) of)\b|\?\s*$", re.I)
# Extra triggers that negate a *medication* mention only ("avoid NSAIDs given CKD" still records CKD).
NEG_PRE_MED = re.compile(r"\b(?:avoid|allerg\w* to|intoleran\w* to|contraindicat\w*)\b", re.I)
NEG_POST = re.compile(r"^\W{0,3}(?:-\s*)?(?:not present|ruled out|unlikely|excluded|negative)\b", re.I)
SCOPE_BREAK = re.compile(r"\b(?:but|however|although|except|presents?|presenting|with)\b|[;:]", re.I)

_DOSE = re.compile(r"^\W{0,3}(?:(?:inhaler|tab(?:let)?s?|caps?(?:ule)?s?|cream|ointment|inj(?:ection)?|syrup|po|iv|sc|oral)\.?\s+)?(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)\s*(mg|mcg|µg|g|gm|units?|u|iu|ml)?\b", re.I)


@dataclass
class _Mention:
    start: int
    end: int
    text: str


def _sentences(note: str) -> list[_Mention]:
    out, pos = [], 0
    # Split on newlines, ';' and '.' — but not on decimal points ("A1c 6.1") or abbreviations like "Sr."
    for m in re.finditer(r"(?:[^\n;.]|\.(?=\d)|(?<=\b[A-Za-z])\.|(?<=\bSr)\.|(?<=\bDr)\.)+[.;\n]?", note):
        s = m.group(0)
        if s.strip():
            out.append(_Mention(m.start(), m.end(), s))
        pos = m.end()
    return out


def _negated(sentence: str, rel_start: int, rel_end: int, medication: bool = False) -> bool:
    before = sentence[:rel_start]
    # Scope runs from the trigger to the term unless a scope breaker intervenes.
    last_break = max((m.end() for m in SCOPE_BREAK.finditer(before)), default=0)
    window = before[last_break:][-60:]
    if NEG_PRE.search(window) or (medication and NEG_PRE_MED.search(window)):
        return True
    return bool(NEG_POST.match(sentence[rel_end:]))


class RuleExtractor:
    name = "rules"

    def extract(self, note: str) -> NoteExtraction:
        sents = _sentences(note)
        return NoteExtraction(
            conditions=self._conditions(sents),
            medications=self._medications(sents),
            observations=self._observations(note),
            follow_up_days=self._follow_up(note),
        )

    # ------------------------------------------------------------------ conditions
    def _conditions(self, sents: list[_Mention]) -> list[ExtractedCondition]:
        found: dict[str, ExtractedCondition] = {}
        for s in sents:
            taken: list[tuple[int, int]] = []
            for rx, code, desc in _COND:
                for m in rx.finditer(s.text):
                    if any(a < m.end() and m.start() < b for a, b in taken):
                        continue
                    taken.append((m.start(), m.end()))
                    if _negated(s.text, m.start(), m.end()):
                        continue
                    cat = code[:3]
                    # Prefer the more specific code for the same category (e.g. E11.21 over E11.9).
                    if cat not in found or len(code) > len(found[cat].icd10_code):
                        stage = re.search(r"(?:stage\s*|ckd\s*)([1-5])", s.text[m.start():m.end() + 12], re.I)
                        if code.startswith("N18") and stage:
                            code = f"N18.{stage.group(1)}"
                        found[cat] = ExtractedCondition(icd10_code=code, description=desc,
                                                        evidence=s.text.strip()[:200])
        return list(found.values())

    # ------------------------------------------------------------------ medications
    def _medications(self, sents: list[_Mention]) -> list[ExtractedMedication]:
        best: dict[str, tuple[int, int, ExtractedMedication]] = {}
        order = 0
        for s in sents:
            mentions = list(_MED_RE.finditer(s.text))
            for i, m in enumerate(mentions):
                if _negated(s.text, m.start(), m.end(), medication=True):
                    continue
                generic = _SURFACE.get(m.group(1).lower(), med_name(m.group(1)))
                nxt = mentions[i + 1].start() if i + 1 < len(mentions) else len(s.text)
                tail = s.text[m.end():nxt]
                prev_end = mentions[i - 1].end() if i > 0 else 0
                head = s.text[prev_end:m.start()]

                dose, tail_for_freq = self._dose(tail)
                freq = next((c for rx, c in _FREQ if rx.search(tail_for_freq)), None)
                action = self._action(head, tail, s.text[:m.start()], dose_change=self._dose_change(tail))
                order += 1
                med = ExtractedMedication(name=generic, dose=dose, frequency=freq, action=action,
                                          evidence=s.text.strip()[:200])
                prev = best.get(generic)
                # Keep the most decisive mention (stop > dose change > start > continue); ties -> later mention.
                if prev is None or PRIORITY[action] >= prev[0]:
                    if prev is not None:
                        med.dose = med.dose or prev[2].dose
                        med.frequency = med.frequency or prev[2].frequency
                    best[generic] = (PRIORITY[action], order, med)
        return [v[2] for v in sorted(best.values(), key=lambda v: v[1])]

    @staticmethod
    def _dose(tail: str) -> tuple[str | None, str]:
        # "from 40 mg OD to 40 mg BD" / "from 5 to 10 mg" / "40 -> 80 mg": the new dose is what counts.
        to = re.search(r"(?:\bto\b|->|→)\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)\s*(mg|mcg|µg|g|gm|units?|u|iu)?", tail, re.I)
        if to:
            unit = to.group(2) or re.search(r"(mg|mcg|units?)", tail, re.I) and re.search(r"(mg|mcg|units?)", tail, re.I).group(1) or "mg"
            return f"{to.group(1)} {_unit(unit)}", tail[to.end():] + " " + tail[:to.start()]
        m = _DOSE.match(tail)
        if not m:
            return None, tail
        unit = _unit(m.group(2)) if m.group(2) else ("mcg" if "/" in m.group(1) else "mg")
        return f"{m.group(1).replace(' ', '')} {unit}", tail[m.end():]

    @staticmethod
    def _dose_change(tail: str) -> str | None:
        m = re.search(r"(?:from\s*)?(\d+(?:\.\d+)?)\s*(?:mg|mcg|units?)?\s*(?:\w+\s*)?(?:to|->|→)\s*(\d+(?:\.\d+)?)", tail, re.I)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            if b > a:
                return "dose_increased"
            if b < a:
                return "dose_decreased"
        return None

    @staticmethod
    def _action(head: str, tail: str, before: str, dose_change: str | None) -> str:
        # 1) verb right after the drug ("Metformin STOPPED", "Amlong increased to 10", "(new)", "- continue")
        first_tail = re.split(r"[,]|\band\b", tail, maxsplit=1)[0]
        for rx, a in _ACT:
            if rx.search(first_tail):
                return a
        # 2) nearest governing verb earlier in the sentence ("Continue aspirin 75 OD, clopidogrel 75 OD")
        hits = [(m.end(), a) for rx, a in _ACT for m in rx.finditer(before)]
        if hits:
            a = max(hits)[1]
            if a in ("dose_increased", "dose_decreased") and dose_change:
                return dose_change
            return a
        if dose_change:
            return dose_change
        # 3) "on X" / "using X" describes an existing medication
        if _ON.search(head) or re.search(r"\b(?:on|using|taking)\s+[\w\s,/+-]{0,40}$", before, re.I):
            return "continued"
        return "started"

    # ------------------------------------------------------------------ observations
    def _observations(self, note: str) -> list[ExtractedObservation]:
        out: list[ExtractedObservation] = []

        def add(code: str, value: float, m: re.Match) -> None:
            out.append(ExtractedObservation(code=code, value=value, evidence=m.group(0).strip()))

        for m in re.finditer(r"\bBP\b[^0-9\n]{0,20}(\d{2,3})\s*/\s*(\d{2,3})", note, re.I):
            add("bp_systolic", float(m.group(1)), m)
            add("bp_diastolic", float(m.group(2)), m)
        for m in re.finditer(r"\b(?:HR|PR|pulse(?: rate)?|heart rate)\b[\s:=-]*(\d{2,3})\b", note, re.I):
            add("heart_rate", float(m.group(1)), m)
        for m in re.finditer(r"\bSpO2\b[\s:=-]*(\d{2,3})\s*%?", note, re.I):
            add("spo2", float(m.group(1)), m)
        for m in re.finditer(r"\b(?:T|temp(?:erature)?)\b[\s:=-]*(\d{2,3}(?:\.\d)?)\s*°?\s*([CF])?\b", note, re.I):
            v = float(m.group(1))
            if (m.group(2) or "").upper() == "F" or v > 45:
                v = f_to_c(v)
            if 30 <= v <= 45:
                add("temperature", v, m)
        for m in re.finditer(r"\b(?:wt|weight)\b[\s:=-]*(\d{2,3}(?:\.\d+)?)\s*(kg|kgs|lbs?|pounds)?", note, re.I):
            v = float(m.group(1))
            if (m.group(2) or "").lower().startswith(("lb", "pound")):
                v = lb_to_kg(v)
            add("weight", v, m)
        for m in re.finditer(r"\b(?:ht|height)\b[\s:=-]*(?:(\d)\s*'\s*(\d{1,2})\s*\"?|(\d{3}(?:\.\d)?)\s*cm)", note, re.I):
            v = ft_in_to_cm(float(m.group(1)), float(m.group(2))) if m.group(1) else float(m.group(3))
            add("height", v, m)
        for m in re.finditer(r"\bBMI\b[\s:=-]*(\d{2}(?:\.\d+)?)", note, re.I):
            add("bmi", float(m.group(1)), m)
        for m in re.finditer(r"\b(?:hba1c|a1c)\b[\s:=-]*(?:of\s*)?(\d{1,2}(?:\.\d+)?)\s*%?", note, re.I):
            add("hba1c", float(m.group(1)), m)
        glucose = [("glucose_fasting", r"\b(?:FBS|FBG|FPG|fasting (?:blood )?(?:sugar|glucose))\b"),
                   ("glucose_random", r"\b(?:RBS|RBG|random (?:blood )?(?:sugar|glucose))\b")]
        for code, label in glucose:
            for m in re.finditer(label + r"[\s:=-]*(\d{1,3}(?:\.\d+)?)\s*(mg/?dl|mmol/?l)?", note, re.I):
                v = float(m.group(1))
                if (m.group(2) or "").lower().startswith("mmol") or v < 30:
                    v = mmol_to_mgdl_glucose(v)
                add(code, v, m)
        labs = [
            ("cholesterol_total", r"\b(?:TC|total cholesterol|T\.?\s?chol)\b"), ("ldl", r"\bLDL(?:-C)?\b"),
            ("hdl", r"\bHDL(?:-C)?\b"), ("triglycerides", r"\b(?:TG|triglycerides?)\b"),
            ("creatinine", r"\b(?:s(?:r|erum)?\.?\s?creatinine|creatinine|s\.?\s?cr|cr)\b"), ("egfr", r"\beGFR\b"),
            ("hemoglobin", r"\b(?:Hb|h(?:a)?emoglobin)\b"),
        ]
        for code, label in labs:
            for m in re.finditer(label + r"[\s:=-]*(\d{1,3}(?:\.\d+)?)", note, re.I):
                add(code, float(m.group(1)), m)
        return out

    # ------------------------------------------------------------------ follow-up
    _NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a": 1}
    _UNIT_DAYS = {"d": 1, "day": 1, "wk": 7, "week": 7, "w": 7, "mo": 30, "month": 30, "m": 30, "yr": 365, "year": 365,
                  "hr": 1 / 24, "hour": 1 / 24, "h": 1 / 24}

    def _follow_up(self, note: str) -> int | None:
        primary = r"(?:review|f/?u|follow[- ]?up|rtc|return|next (?:visit|review|appointment)|\brv\b|see (?:again|back))"
        secondary = r"(?:repeat|recheck)"
        dur = r"(\d+|one|two|three|four|five|six|a)\s*(hours?|hrs?|h|days?|d|wks?|weeks?|w|mo(?:nths?)?|m|yrs?|years?)\b"
        for kw in (primary, secondary):
            m = re.search(kw + r"\b[^\n.]{0,40}?" + dur, note, re.I)
            if m:
                n = self._NUM.get(m.group(1).lower(), None) or int(m.group(1))
                unit = re.sub(r"s$", "", m.group(2).lower())
                unit = {"hrs": "hr", "mos": "mo", "wks": "wk", "yrs": "yr"}.get(unit, unit)
                days = n * self._UNIT_DAYS.get(unit, self._UNIT_DAYS.get(unit[:2], 1))
                return max(1, round(days))
            if kw == primary:
                if re.search(primary + r"\s+tomorrow", note, re.I):
                    return 1
                if re.search(r"\bannual (?:review|check|visit)|review (?:in )?(?:a|one) year", note, re.I):
                    return 365
        return None


def _unit(u: str | None) -> str:
    u = (u or "mg").lower()
    return {"u": "units", "iu": "units", "unit": "units", "units": "units", "µg": "mcg", "gm": "g"}.get(u, u)
