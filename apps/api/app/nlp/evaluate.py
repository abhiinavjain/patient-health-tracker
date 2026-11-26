"""Field-level evaluation of note extractors against the labelled set in eval/notes.jsonl.

    python -m app.nlp.evaluate --method rules-v1 --split dev --errors
    python -m app.nlp.evaluate --method local --split holdout

Scoring
* Conditions: ICD-10 category (first 3 characters); each gold item lists acceptable alternatives.
* Medications: generic-name match (brand aliases and combination order normalised). On matched items the
  action, dose and frequency are scored separately as attribute accuracy.
* Observations: (code, value) with tolerance max(0.2, 2%) after unit conversion.
* Follow-up: interval in days within 10% (a missing gold follow-up must also be predicted as missing).
* "optional" gold items are allowed extras: neither rewarded nor counted as false positives.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import dose_key, med_key, values_match
from .schema import NoteExtraction

EVAL_PATH = Path(__file__).resolve().parents[2] / "eval" / "notes.jsonl"


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, other: Counts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


@dataclass
class Attr:
    correct: int = 0
    total: int = 0

    @property
    def acc(self) -> float:
        return self.correct / self.total if self.total else 1.0


@dataclass
class NoteScore:
    conditions: Counts = field(default_factory=Counts)
    medications: Counts = field(default_factory=Counts)
    observations: Counts = field(default_factory=Counts)
    action: Attr = field(default_factory=Attr)
    dose: Attr = field(default_factory=Attr)
    frequency: Attr = field(default_factory=Attr)
    follow_up: Attr = field(default_factory=Attr)
    errors: list[str] = field(default_factory=list)


def score_note(pred: NoteExtraction, gold: dict) -> NoteScore:
    s = NoteScore()

    # Conditions
    pred_cats = [c.icd10_code.upper().replace(".", "")[:3] for c in pred.conditions]
    used = set()
    for alts in gold["conditions"]:
        hit = next((i for i, c in enumerate(pred_cats) if i not in used and c in alts), None)
        if hit is None:
            s.conditions.fn += 1
            s.errors.append(f"condition missed: {alts}")
        else:
            used.add(hit)
            s.conditions.tp += 1
    optional = set(gold["conditions_optional"]) | {a for alts in gold["conditions"] for a in alts}
    for i, c in enumerate(pred_cats):
        if i not in used and c not in optional:
            s.conditions.fp += 1
            s.errors.append(f"condition extra: {pred.conditions[i].icd10_code} {pred.conditions[i].description}")

    # Medications
    pkeys = [med_key(m.name) for m in pred.medications]
    matched_pred = set()
    for g in gold["medications"]:
        gk = med_key(g["name"])
        hit = next((i for i, k in enumerate(pkeys) if k == gk), None)
        if hit is None:  # a combination product can cover each of its components
            hit = next((i for i, k in enumerate(pkeys) if gk <= k), None)
        if hit is None:
            s.medications.fn += 1
            s.errors.append(f"medication missed: {g['name']}")
            continue
        matched_pred.add(hit)
        s.medications.tp += 1
        p = pred.medications[hit]
        s.action.total += 1
        if p.action == g["action"]:
            s.action.correct += 1
        else:
            s.errors.append(f"action {g['name']}: {p.action} != {g['action']}")
        if g["dose"]:
            s.dose.total += 1
            if dose_key(p.dose) == dose_key(g["dose"]):
                s.dose.correct += 1
            else:
                s.errors.append(f"dose {g['name']}: {p.dose!r} != {g['dose']!r}")
        if g["frequency"]:
            s.frequency.total += 1
            if p.frequency == g["frequency"]:
                s.frequency.correct += 1
            else:
                s.errors.append(f"frequency {g['name']}: {p.frequency} != {g['frequency']}")
    opt_keys = [med_key(n) for n in gold["medications_optional"]]
    for i, k in enumerate(pkeys):
        if i not in matched_pred and not any(k == o or o <= k for o in opt_keys):
            s.medications.fp += 1
            s.errors.append(f"medication extra: {pred.medications[i].name} ({pred.medications[i].action})")

    # Observations
    remaining = [tuple(o) for o in gold["observations"]]
    optional_obs = [tuple(o) for o in gold["observations_optional"]]
    for o in pred.observations:
        hit = next((g for g in remaining if g[0] == o.code and values_match(o.value, g[1])), None)
        if hit:
            remaining.remove(hit)
            s.observations.tp += 1
        elif any(g[0] == o.code and values_match(o.value, g[1]) for g in optional_obs):
            continue
        else:
            s.observations.fp += 1
            s.errors.append(f"observation extra/wrong: {o.code}={o.value:g}")
    s.observations.fn += len(remaining)
    s.errors += [f"observation missed: {c}={v}" for c, v in remaining]

    # Follow-up
    gf, pf = gold["follow_up_days"], pred.follow_up_days
    s.follow_up.total = 1
    ok = (gf is None and pf is None) or (gf is not None and pf is not None and abs(pf - gf) <= max(1, 0.1 * gf))
    s.follow_up.correct = int(ok)
    if not ok:
        s.errors.append(f"follow-up: {pf} != {gf}")
    return s


def load(split: str = "all") -> list[dict]:
    rows = [json.loads(line) for line in EVAL_PATH.read_text().splitlines() if line.strip()]
    return [r for r in rows if split == "all" or r["split"] == split]


def evaluate(extract, rows: list[dict]) -> dict:
    total = NoteScore()
    per_note = []
    latencies = []
    for r in rows:
        t0 = time.perf_counter()
        pred = extract(r["note"])
        latencies.append(time.perf_counter() - t0)
        s = score_note(pred, r["gold"])
        for f in ("conditions", "medications", "observations"):
            getattr(total, f).add(getattr(s, f))
        for f in ("action", "dose", "frequency", "follow_up"):
            a, b = getattr(total, f), getattr(s, f)
            a.correct += b.correct
            a.total += b.total
        per_note.append({"id": r["id"], "errors": s.errors})
    entity = Counts()
    for f in ("conditions", "medications", "observations"):
        entity.add(getattr(total, f))
    return {
        "n_notes": len(rows),
        "entities": {f: {"precision": c.precision, "recall": c.recall, "f1": c.f1, "tp": c.tp, "fp": c.fp, "fn": c.fn}
                     for f, c in [("conditions", total.conditions), ("medications", total.medications),
                                  ("observations", total.observations), ("all", entity)]},
        "attributes": {f: {"accuracy": getattr(total, f).acc, "n": getattr(total, f).total}
                       for f in ("action", "dose", "frequency", "follow_up")},
        "latency_s": {"mean": sum(latencies) / len(latencies), "max": max(latencies)},
        "per_note": per_note,
    }


def to_markdown(name: str, res: dict) -> str:
    lines = [f"**{name}** — {res['n_notes']} notes, mean latency {res['latency_s']['mean'] * 1000:.0f} ms", "",
             "| Field | Precision | Recall | F1 | TP / FP / FN |", "|---|---|---|---|---|"]
    for f, m in res["entities"].items():
        lines.append(f"| {f} | {m['precision']:.2f} | {m['recall']:.2f} | **{m['f1']:.2f}** | {m['tp']} / {m['fp']} / {m['fn']} |")
    lines += ["", "| Attribute (on matched items) | Accuracy | n |", "|---|---|---|"]
    for f, m in res["attributes"].items():
        lines.append(f"| {f.replace('_', '-')} | {m['accuracy']:.2f} | {m['n']} |")
    return "\n".join(lines)


def get_extractor(method: str):
    if method == "rules-v1":
        from .rules import RuleExtractor
        return RuleExtractor().extract
    if method == "local":
        from .local import LocalExtractor
        return LocalExtractor().extract
    raise ValueError(method)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", choices=["local", "rules-v1"], default="local")
    ap.add_argument("--split", choices=["dev", "test", "stress", "holdout", "field", "all"], default="dev")
    ap.add_argument("--errors", action="store_true", help="print per-note errors")
    ap.add_argument("--out", type=Path, help="write full results JSON here")
    args = ap.parse_args()
    res = evaluate(get_extractor(args.method), load(args.split))
    print(to_markdown(f"{args.method} / {args.split}", res))
    if args.errors:
        for n in res["per_note"]:
            if n["errors"]:
                print(f"\n[{n['id']}]")
                for e in n["errors"]:
                    print("  -", e)
    if args.out:
        args.out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
