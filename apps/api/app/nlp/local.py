"""Local (offline) clinical-note extractor — v2.

Everything runs on the server; no note text leaves it. Builds on the frozen v1 rules (app/nlp/rules.py) with:
  1. Text normalisation: number words -> digits ("one forty over ninety"), clinical/US abbreviations
     ("O2 sat", "A-fib", "tmrw"), common Hinglish phrasing, and spelling correction against the drug/condition
     vocabulary ("metfromin" -> metformin).
  2. An expanded lexicon (app/nlp/lexicon_ext.py) plus detection of unknown drug names from "<word> <dose><unit>".
  3. A trained medication-action classifier (app/nlp/action_model.py) — optional, used when its artifact exists.
Each layer can be switched off for ablation.
"""

from __future__ import annotations

import difflib
import re
from functools import lru_cache
from pathlib import Path

from .lexicon_ext import EXTRA_ALIASES, EXTRA_CONDITIONS, EXTRA_GENERICS, NON_DRUG_WORDS
from .normalize import MED_ALIASES
from .rules import (
    _ACT, _FREQ, CONDITIONS, GENERICS, PRIORITY, RuleExtractor, _Mention, _negated, _sentences, _SURFACE as V1_SURFACE,
)
from .schema import ExtractedCondition, ExtractedMedication, NoteExtraction

PROTECTED_WORDS_PATH = Path(__file__).with_name("protected_words.txt")

# ----------------------------------------------------------------------------- 1. text normalisation
_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_NUM_WORD = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|" \
            r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)"
_NUM_PHRASE = re.compile(rf"\b(?:a\s+)?{_NUM_WORD}(?:[\s-]+(?:and\s+)?{_NUM_WORD})*\b", re.I)


def _words_value(phrase: str) -> int | None:
    toks = [t for t in re.split(r"[\s-]+", phrase.lower()) if t and t != "and"]
    if toks and toks[0] == "a":
        toks = toks[1:] if len(toks) > 1 and toks[1] == "hundred" else toks
        if toks[0] == "a":
            return None
    if not toks:
        return None
    # Spoken clinical style: "one sixty" = 160, "one twenty five" = 125.
    if len(toks) >= 2 and toks[0] in _UNITS and _UNITS[toks[0]] <= 2 and (toks[1] in _TENS or toks[1] in _UNITS) \
            and toks[1] != "hundred":
        rest = _words_value(" ".join(toks[1:]))
        if rest is not None and 10 <= rest <= 99:
            return _UNITS[toks[0]] * 100 + rest
    total, current = 0, 0
    for t in toks:
        if t in _UNITS:
            current += _UNITS[t]
        elif t in _TENS:
            current += _TENS[t]
        elif t == "hundred":
            current = max(current, 1) * 100
        else:
            return None
    return total + current


def words_to_numbers(text: str) -> str:
    def repl(m: re.Match) -> str:
        v = _words_value(m.group(0))
        # Only rewrite phrases that are clearly numeric (avoid "one puff" -> "1 puff"? harmless, but keep "a").
        return str(v) if v is not None else m.group(0)

    text = _NUM_PHRASE.sub(repl, text)
    return re.sub(r"\b(\d{2,3})\s+over\s+(\d{2,3})\b", r"\1/\2", text, flags=re.I)


NORMALISE: list[tuple[str, str]] = [
    (r"\b(?:s[hu]?ug[ae]r|shugar|sugr)(s?)\b", r"sugar\1"),
    (r"\bh?b\s?1\s?a\s?c\b|\bhba\s?1\s?c\b|\bhbaic\b|\bglyc(?:at)?ed\s+h(?:a)?emoglobin\b", "HbA1c"),
    (r"\b(?:o2|oxygen)\s*sat(?:uration)?s?\b|\bsats\b|\bsat(?:uration)?\s+(?=\d)", "SpO2 "),
    (r"\ba-?fib\b|\batrial fib\b(?!rillation)", "atrial fibrillation"),
    (r"\btmrw?\b|\btom+or+ow\b", "tomorrow"),
    (r"\bfortnight\b", "2 weeks"),
    (r"\b(\d+)\s*haft(?:e|a|on)\b", r"\1 weeks"),
    (r"\b(\d+)\s*din\b", r"\1 days"),
    (r"\b(\d+)\s*mahin(?:e|a|on)\b", r"\1 months"),
    (r"\b(\d+(?:\.\d+)?)\s*percent\b", r"\1%"),
    (r"\b(?:bump(?:ed)?|step(?:ped)?|titrat(?:e|ed)|went|go(?:ne)?)\s+up\b|\bdoubl(?:e|ed|ing)\b|\bbadha\s*(?:diya|do|di)\b", "increased"),
    (r"\b(?:step(?:ped)?|cut|went|titrat(?:e|ed)|back(?:ed)?)\s+(?:down|off)\b|\bhalv(?:e|ed)\b|\bkam\s*kar\s*(?:diya|do|di)\b", "reduced"),
    (r"\bband\s*kar\s*(?:diya|do|di)\b|\brok\s*(?:do|diya)\b|\bfinished\b|\bcompleted\b|\bcourse over\b", "stopped"),
    (r"\ble\s*(?:rahi|raha|rahe)\s*(?:hai|hain|he|h)\b|\bchal\s*(?:rahi|raha|rahe)\b|\balready on\b", "continuing"),
    (r"\bde\s*(?:diya|di|do)\b|\bshuru\s*(?:kiya|karo|kar do)\b", "started"),
    (r"\bkar\s*(?:diya|di)\b", "changed"),
]
_NORMALISE = [(re.compile(p, re.I), r) for p, r in NORMALISE]

CONDITION_WORDS = {
    "hypertension", "hypertensive", "diabetes", "diabetic", "asthma", "asthmatic", "pneumonia", "hypothyroidism",
    "hypothyroid", "hyperthyroidism", "cirrhosis", "osteoarthritis", "depression", "dementia", "parkinson",
    "migraine", "psoriasis", "gastroenteritis", "hyponatraemia", "hyponatremia", "hypokalaemia", "hypokalemia",
    "osteoporosis", "dyspepsia", "gastritis", "tuberculosis", "dengue", "malaria", "typhoid", "anaemia", "anemia",
    "obesity", "angina", "fibrillation", "hyperlipidaemia", "hyperlipidemia", "dyslipidaemia", "dyslipidemia",
    "nephropathy", "neuropathy", "retinopathy", "cystitis", "sinusitis", "bronchitis", "urticaria", "eczema",
    "cellulitis", "insomnia", "vertigo", "glaucoma", "cataract", "conjunctivitis", "alzheimer", "prediabetes",
    "hypoglycaemia", "hypoglycemia", "hyperglycaemia", "hyperglycemia", "hyperkalaemia", "hyperkalemia",
    "hypernatraemia", "hypernatremia", "hypercalcaemia", "hypocalcaemia", "hyperuricaemia", "hypotension",
    "hypothermia", "hyperthermia", "pyelonephritis", "nephritis", "hepatitis", "pancreatitis", "appendicitis",
    "cholecystitis", "colitis", "diverticulitis", "arthritis", "spondylitis", "tendinitis", "dermatitis",
    "pharyngitis", "tonsillitis", "laryngitis", "rhinitis", "otitis", "meningitis", "encephalitis", "myocarditis",
    "pericarditis", "endocarditis", "bronchiolitis", "pneumothorax", "embolism", "thrombosis", "ischaemia",
    "ischemia", "infarction", "cardiomyopathy", "arrhythmia", "tachycardia", "bradycardia", "dyspnoea", "dyspnea",
    "tuberculous", "leukaemia", "leukemia", "lymphoma", "carcinoma", "malignancy", "metastasis", "schizophrenia",
}


@lru_cache(maxsize=1)
def _protected_words() -> frozenset[str]:
    if PROTECTED_WORDS_PATH.exists():
        return frozenset(w.strip() for w in PROTECTED_WORDS_PATH.read_text().split() if w.strip())
    return frozenset()


def spelling_candidates(vocab: frozenset[str], token: str) -> str | None:
    """Closest vocabulary word for a likely misspelling, or None. Conservative by design."""
    t = token.lower()
    if len(t) < 6 or t in vocab or t in _protected_words():
        return None
    pool = [v for v in vocab if v[:2] == t[:2] and abs(len(v) - len(t)) <= 2]
    best = difflib.get_close_matches(t, pool, n=1, cutoff=0.8)
    return best[0] if best else None


# ----------------------------------------------------------------------------- extractor
_EXTRA_ACT = [
    (re.compile(r"\b(?:continuing|already)\b", re.I), "continued"),
    (re.compile(r"\btold to stop\b|\bstopped\b", re.I), "stopped"),
]
_CHANGED = re.compile(r"\bchanged\b", re.I)
PRIO = {**PRIORITY, "_changed": 2}
_FREQ_V2 = _FREQ + [(re.compile(r"\b(?:before|after|with)\s+(?:each\s+)?(?:meals?|food)\b|\bac\b", re.I), "with_meals")]
_GLU_NUM = r"(\d{1,3}(?:\.\d+)?)\s*(mg/?dl|mmol/?l)?"
_MEAL = r"(?:after|post)\s+(?:lunch|meals?|food|breakfast|dinner|eating|khana)"
_GLUCOSE_PATTERNS = [
    # 2-hour post-meal sugar: "PPBS 210", "PP sugar 210", "post-prandial 210", "sugar after lunch 200", "sugar 200 after food"
    ("glucose_postprandial", re.compile(
        r"\b(?:ppbs|ppbg|pp\s?(?:blood\s)?(?:sugar|glucose)|post[- ]?prandial(?:\s(?:blood\s)?(?:sugar|glucose))?|"
        r"2\s?h(?:r|our)?s?\s?(?:pp|post[- ]?meal)|(?:blood\s)?(?:sugar|glucose)\s" + _MEAL + r")\b[\s:=-]*" + _GLU_NUM, re.I)),
    ("glucose_postprandial", re.compile(r"\b(?:blood\s)?(?:sugar|glucose)\s*[:=-]?\s*" + _GLU_NUM + r"\s*" + _MEAL, re.I)),
    # Unqualified "sugar 180" / "BSL 180" / "CBG 180" = a random reading.
    ("glucose_random", re.compile(r"\b(?:blood\s)?(?:sugar|glucose|bsl|cbg|grbs)\b\s*[:=-]?\s*" + _GLU_NUM, re.I)),
]
_WEIGHT_NOW = re.compile(r"\b(?:wt|weight)\b(?:[^.\n]|\.(?=\d)){0,40}?\b(?:now|currently|today)\s+(\d{2,3}(?:\.\d+)?)\s*kgs?\b", re.I)
_LAB_CONTEXT = re.compile(r"^\s*(?:\w+\s+){0,2}(?:low|high|levels?|deficien\w*|is low|was low)\b", re.I)
_INHALED = ("formoterol", "salmeterol", "fluticasone", "budesonide", "tiotropium", "salbutamol", "ipratropium",
            "levosalbutamol", "beclomethasone", "mometasone")
_SWITCH = re.compile(r"\b(?:switch\w*|chang(?:e|ed|ing)\s+(?:over\s+)?from|convert\w*|replac\w*)\b", re.I)
_TO_NEXT = re.compile(r"^\s*(?:->|→|to\b|with\b)", re.I)
_UNKNOWN_DRUG = re.compile(
    r"(?<![\w-])([A-Za-z][a-z]{4,}(?:\s+[a-z]{4,})?)\s+(\d+(?:\.\d+)?)\s*(mg|mcg|µg|units?|iu)\b(?!\s*/\s*(?:dl|l|kg|min))",
    re.I)


class LocalExtractor(RuleExtractor):
    name = "local"
    version = "local-2.0"

    def __init__(self, normalise_text: bool = True, expanded_lexicon: bool = True, action_model=True,
                 action_mode: str | None = None):
        """action_model: True = load the trained artifact, False/None = rules only, or an ActionModel instance.
        action_mode: "hybrid" (model decides only when no explicit cue), "model" (model always), "rules"."""
        self.normalise_text = normalise_text
        self.expanded_lexicon = expanded_lexicon
        conds = (EXTRA_CONDITIONS + CONDITIONS) if expanded_lexicon else CONDITIONS
        self._cond = [(re.compile(p, re.I), code, desc) for p, code, desc in conds]
        surface = dict(V1_SURFACE)
        if expanded_lexicon:
            generics = GENERICS | EXTRA_GENERICS
            surface.update({g: g for g in EXTRA_GENERICS})
            surface.update({k: v for k, v in {**MED_ALIASES, **EXTRA_ALIASES}.items()})
        else:
            generics = GENERICS
        self._surface = surface
        self._med_re = re.compile(
            r"(?<![\w-])(" + "|".join(sorted((re.escape(s) for s in surface), key=len, reverse=True)) + r")(?![\w-])", re.I)
        single = {w for s in surface for w in [s] if " " not in s and "-" not in s and "/" not in s}
        self._vocab = frozenset({w for w in single | set(generics) if re.fullmatch(r"[a-z]+", w)} | CONDITION_WORDS)
        self.action_model = None
        if action_model is True:
            from .action_model import load_action_model
            self.action_model = load_action_model()
        elif action_model:
            self.action_model = action_model
        self.action_mode = action_mode or getattr(self.action_model, "mode", "hybrid")
        if self.action_mode == "rules":
            self.action_model = None

    # ------------------------------------------------------------------ public
    def extract(self, note: str) -> NoteExtraction:
        text, pairs = self.preprocess(note)
        sents = _sentences(text)
        out = NoteExtraction(
            conditions=self._conditions(sents),
            medications=[m for m, _ in self.medication_mentions(sents)],
            observations=self._observations(text),
            follow_up_days=self._follow_up_v2(text),
        )
        return self._restore_evidence(out, pairs)

    # ------------------------------------------------------------------ preprocessing (per sentence, so evidence maps back)
    def normalise(self, s: str) -> str:
        if not self.normalise_text:
            return s
        s = words_to_numbers(s)
        for rx, rep in _NORMALISE:
            s = rx.sub(rep, s)

        def fix(m: re.Match) -> str:
            cand = spelling_candidates(self._vocab, m.group(0))
            return cand if cand else m.group(0)

        return re.sub(r"[A-Za-z]{6,}", fix, s)

    def preprocess(self, note: str) -> tuple[str, list[tuple[str, str]]]:
        pairs: list[tuple[str, str]] = []
        out, last = [], 0
        for s in _sentences(note):
            new = self.normalise(s.text)
            out.append(note[last:s.start])
            out.append(new)
            pairs.append((new, s.text))
            last = s.end
        out.append(note[last:])
        return "".join(out), pairs

    @staticmethod
    def _restore_evidence(ex: NoteExtraction, pairs: list[tuple[str, str]]) -> NoteExtraction:
        def original(evidence: str) -> str:
            e = re.sub(r"\s+", " ", evidence).strip().lower()[:60]
            for new, orig in pairs:
                if e and e in re.sub(r"\s+", " ", new).lower():
                    return orig.strip()[:200]
            return evidence

        for item in [*ex.conditions, *ex.medications, *ex.observations]:
            item.evidence = original(item.evidence)
        return ex

    # ------------------------------------------------------------------ conditions (instance lexicon)
    def _conditions(self, sents: list[_Mention]) -> list[ExtractedCondition]:
        found: dict[str, ExtractedCondition] = {}
        for s in sents:
            taken: list[tuple[int, int]] = []
            for rx, code, desc in self._cond:
                for m in rx.finditer(s.text):
                    if any(a < m.end() and m.start() < b for a, b in taken):
                        continue
                    taken.append((m.start(), m.end()))
                    if code is None or _negated(s.text, m.start(), m.end()):
                        continue
                    cat = code[:3]
                    if cat not in found or len(code) > len(found[cat].icd10_code):
                        stage = re.search(r"(?:stage\s*|ckd\s*)([1-5])", s.text[m.start():m.end() + 12], re.I)
                        if code.startswith("N18") and stage:
                            code = f"N18.{stage.group(1)}"
                        found[cat] = ExtractedCondition(icd10_code=code, description=desc, evidence=s.text.strip()[:200])
        return list(found.values())

    # ------------------------------------------------------------------ medications
    def _find_mentions(self, text: str) -> list[tuple[int, int, str]]:
        spans = [(m.start(), m.end(), self._surface.get(m.group(1).lower(), m.group(1).lower()))
                 for m in self._med_re.finditer(text)]
        if self.expanded_lexicon:
            for m in _UNKNOWN_DRUG.finditer(text):
                word = m.group(1).lower()
                first = word.split()[0]
                if first in NON_DRUG_WORDS or first in self._vocab or word in self._surface \
                        or re.search(r"(?:ed|ing|ly)$", first) or (" " in word and word.split()[1] in ("from", "to", "with")) \
                        or first in _protected_words() or any(a < m.end(1) and m.start(1) < b for a, b, _ in spans):
                    continue
                spans.append((m.start(1), m.end(1), word))
        return sorted(spans)

    def medication_mentions(self, sents: list[_Mention]) -> list[tuple[ExtractedMedication, list[dict]]]:
        """Returns one entry per drug plus the per-mention contexts (used for training the action model)."""
        best: dict[str, dict] = {}
        order = 0
        for s in sents:
            mentions = self._find_mentions(s.text)
            for i, (start, end, generic) in enumerate(mentions):
                if _negated(s.text, start, end, medication=True) or _LAB_CONTEXT.match(s.text[end:]):
                    continue
                nxt = mentions[i + 1][0] if i + 1 < len(mentions) else len(s.text)
                prev_end = mentions[i - 1][1] if i > 0 else 0
                tail, head, before = s.text[end:nxt], s.text[prev_end:start], s.text[:start]
                dose, tail_for_freq = self._dose(tail)
                if dose and "/" in dose and dose.endswith("mcg") and not re.search(r"\bmcg\b", tail, re.I) \
                        and not any(k in generic for k in _INHALED):
                    dose = dose.replace("mcg", "mg")  # "100/25" with no unit is mg unless it's an inhaler
                freq = next((c for rx, c in _FREQ_V2 if rx.search(tail_for_freq)), None)
                if freq is None and re.fullmatch(r"[\s\d.,/+()&-]*(?:mg|mcg|g|units?|iu)?[\s\d.,/+()&-]*(?:and)?\s*", tail, re.I):
                    # A frequency after a list applies to every drug in it: "(isoniazid 300, rifampicin 600) daily"
                    rest = s.text[mentions[-1][1]:]
                    freq = next((c for rx, c in _FREQ_V2 if rx.search(rest)), None)
                rule_action, explicit = self._action_v2(head, tail, before, self._dose_change(tail),
                                                        followed_by_drug=i + 1 < len(mentions))
                context = action_context(head, tail)
                action = rule_action
                if self.action_model is not None and (self.action_mode == "model" or not explicit) \
                        and rule_action != "_changed":
                    action = self.action_model.predict(context) or rule_action
                order += 1
                info = {"generic": generic, "context": context, "rule_action": rule_action, "explicit": explicit,
                        "action": action, "dose": dose, "freq": freq, "order": order, "evidence": s.text.strip()[:200]}
                prev = best.get(generic)
                if action == "_changed" or (prev is not None and action == "started" and not explicit):
                    # Same drug again with a different dose -> a dose change ("Telma 40 ... Telma 80 kar diya").
                    change = _compare_doses(prev["dose"], dose) if prev else None
                    if change:
                        action = change
                    elif prev is not None:
                        action = prev["action"]  # plain re-mention: keep what was decided before
                    else:
                        action = "started"
                    info["action"] = action
                if prev is None or PRIO[action] >= PRIO[prev["action"]]:
                    if prev is not None:
                        info["dose"] = info["dose"] or prev["dose"]
                        info["freq"] = info["freq"] or prev["freq"]
                        info["mentions"] = prev["mentions"] + [info]
                    else:
                        info["mentions"] = [info]
                    best[generic] = info
                else:
                    prev["mentions"].append(info)
        out = []
        for info in sorted(best.values(), key=lambda v: v["order"]):
            out.append((ExtractedMedication(name=info["generic"], dose=info["dose"], frequency=info["freq"],
                                            action=info["action"], evidence=info["evidence"]), info["mentions"]))
        return out

    def _action_v2(self, head: str, tail: str, before: str, dose_change: str | None,
                   followed_by_drug: bool) -> tuple[str, bool]:
        """Rule action plus whether it came from an explicit cue (explicit cues override the classifier)."""
        # "switch warfarin to apixaban": the drug before "to" is stopped, the one after is started.
        if _SWITCH.search(before + " " + head) and followed_by_drug and _TO_NEXT.match(tail):
            return "stopped", True
        if _SWITCH.search(before) and re.search(r"(?:->|→|\bto)\s*$", head):
            return "started", True
        first_tail = re.split(r"[,]|\band\b", tail, maxsplit=1)[0]
        if _CHANGED.search(first_tail):
            return "_changed", True
        for rx, a in _EXTRA_ACT + _ACT:
            if rx.search(first_tail):
                return a, True
        hits = [(m.end(), a) for rx, a in _EXTRA_ACT + _ACT for m in rx.finditer(before)]
        if hits:
            a = max(hits)[1]
            if a in ("dose_increased", "dose_decreased") and dose_change:
                return dose_change, True
            return a, True
        if dose_change:
            return dose_change, True
        if re.search(r"\b(?:on|using|taking)\s+[\w\s,/+-]{0,40}$", before, re.I):
            return "continued", False
        return "started", False

    def _observations(self, note: str):
        out = super()._observations(note)
        out += self._glucose(note, out)
        if not any(o.code == "weight" for o in out):
            from .schema import ExtractedObservation
            for m in _WEIGHT_NOW.finditer(note):  # "weight up 2.5 kg in a week (now 74 kg)"
                out.append(ExtractedObservation(code="weight", value=float(m.group(1)), evidence=m.group(0)))
        return out

    @staticmethod
    def _glucose(note: str, existing) -> list:
        """Post-meal and unlabelled glucose readings, without double-counting ones already labelled fasting/random."""
        from .normalize import mmol_to_mgdl_glucose
        from .schema import ExtractedObservation

        taken = []
        for o in existing:
            if o.code.startswith("glucose"):
                i = note.find(o.evidence)
                if i >= 0:
                    taken.append((i, i + len(o.evidence)))
        found = []
        for code, rx in _GLUCOSE_PATTERNS:
            for m in rx.finditer(note):
                if any(a < m.end() and m.start() < b for a, b in taken):
                    continue
                if code == "glucose_random" and re.search(r"(?:fasting|random|pp|post[- ]?prandial)\s*$", note[:m.start()], re.I):
                    continue
                v = float(m.group(1))
                mmol = (m.group(2) or "").lower().startswith("mmol")
                if v < 30 and not mmol:
                    continue  # "sugar 5 days" is not a reading; small values need an explicit mmol/L
                if mmol:
                    v = mmol_to_mgdl_glucose(v)
                taken.append((m.start(), m.end()))
                found.append(ExtractedObservation(code=code, value=v, evidence=m.group(0).strip()))
        return found

    # ------------------------------------------------------------------ follow-up
    def _follow_up_v2(self, note: str) -> int | None:
        m = re.search(r"(?:f/?u|review|rv|follow[- ]?up|next visit)\s*:?\s*(\d{1,2})\s*/\s*(12|52|7)\b", note, re.I)
        if m:  # clinical shorthand: 3/12 = 3 months, 6/52 = 6 weeks, 5/7 = 5 days
            return int(m.group(1)) * {"12": 30, "52": 7, "7": 1}[m.group(2)]
        v1 = self._follow_up(note)
        if v1 is not None:
            return v1
        if re.search(r"\b(?:review|recheck|repeat|see|f/?u|follow[- ]?up)\b[^.\n]{0,25}\btomorrow\b", note, re.I):
            return 1
        m = re.search(r"\bclinic\s+(?:in|after)\s+(\d+)\s*(days?|wks?|weeks?|months?)\b", note, re.I)
        if m:
            unit = m.group(2).lower()
            return int(m.group(1)) * (30 if unit.startswith("mo") else 7 if unit.startswith("w") else 1)
        m = re.search(r"\b(\d+)\s*(days?|weeks?|months?)\s*(?:baad|later|after|from now)\b|"
                      r"\bsee\s+(?:after|in)\s+(\d+)\s*(days?|d|wks?|weeks?|months?|mo)\b", note, re.I)
        if m:
            n = int(m.group(1) or m.group(3))
            unit = (m.group(2) or m.group(4)).lower()
            return n * (30 if unit.startswith("mo") else 7 if unit.startswith("w") else 1)
        return None


def action_context(head: str, tail: str) -> str:
    """Text around a medication mention, normalised for the action classifier."""
    ctx = f"{head[-60:]} DRUG {tail[:60]}"
    return re.sub(r"\d+(?:\.\d+)?", "0", ctx.lower()).strip()


def _compare_doses(old: str | None, new: str | None) -> str | None:
    def num(d):
        m = re.match(r"([\d.]+)", d or "")
        return float(m.group(1)) if m else None

    a, b = num(old), num(new)
    if a is None or b is None or a == b:
        return None
    return "dose_increased" if b > a else "dose_decreased"

