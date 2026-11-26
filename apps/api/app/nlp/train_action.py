"""Train and evaluate the medication-action classifier.

    python -m app.nlp.train_action            # leave-one-note-out CV of rules vs hybrid vs model, then fit + save
    python -m app.nlp.train_action --no-cv    # just fit + save

Training data (the holdout split is never used):
  * every medication mention in the dev/test/stress notes, labelled with the gold action;
  * synthetic contexts generated from phrasing templates (incl. common Hinglish), to cover verb variety.
Model selection is done on the full extraction pipeline, so the reported numbers are what the API would produce.
"""

from __future__ import annotations

import argparse
import json
import random

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .action_model import MODEL_PATH, ActionModel, load_action_model
from .evaluate import evaluate, load
from .local import LocalExtractor, action_context
from .normalize import med_key
from .rules import _sentences

TUNING_SPLITS = ("dev", "test", "stress")
LABELS = ("started", "continued", "dose_increased", "dose_decreased", "stopped")

VERBS = {
    "started": ["start", "started", "add", "added", "initiate", "initiated", "commence", "begin", "rx", "prescribed",
                "new", "put on", "advised", "trial of", "shuru karo", "de diya", "give", "given"],
    "continued": ["continue", "cont", "continued", "unchanged", "same dose", "maintain", "resume", "already on",
                  "continuing", "chalu rakho", "le rahe hain", "keep on"],
    "dose_increased": ["increase", "increased", "uptitrate", "up-titrated", "step up", "increased", "bump up", "raise",
                       "badha diya", "escalate"],
    "dose_decreased": ["reduce", "reduced", "decrease", "decreased", "taper", "step down", "cut down", "lower",
                       "kam kar diya", "wean"],
    "stopped": ["stop", "stopped", "discontinue", "discontinued", "d/c", "hold", "withhold", "cease", "band kar do",
                "omit", "stop taking"],
}
BACKGROUND_ON = ["known htn on", "pt is on", "currently on", "taking", "using", "background: dm on", "on regular",
                 "current meds:", "maintained on", "h/o ihd on"]
PLAN_HEADS = ["plan:", "rx:", "advice:", "discharge meds:", "tab", "", "imp: gerd. rx:", "meds:"]
DOSES = ["0 mg", "0 mg od", "0 mg bd", "0 units hs", "0 mcg daily", "0 mg tds", "", "0 mg once daily", "0/0 bd"]
NOISE = ["", "bp 0/0. ", "review in 0 weeks. ", "no chest pain. ", "sugars better. ", "c/o cough. ", "labs ok. "]


def synthetic(n: int = 1500, seed: int = 0) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        label = rng.choice(LABELS)
        verb, dose, noise = rng.choice(VERBS[label]), rng.choice(DOSES), rng.choice(NOISE)
        shape = rng.random()
        if label == "continued" and shape < 0.35:
            head, tail = f"{noise}{rng.choice(BACKGROUND_ON)} ", f" {dose}"
        elif label == "started" and shape < 0.3:
            head, tail = f"{noise}{rng.choice(PLAN_HEADS)} ", f" {dose}"
        elif label in ("dose_increased", "dose_decreased") and shape < 0.3:
            head, tail = f"{noise}", f" {verb} from 0 to 0 mg"
        elif label == "stopped" and shape < 0.2:
            head, tail = f"{noise}switch ", " -> "
        elif shape < 0.65:
            head, tail = f"{noise}{verb} ", f" {dose}"
        else:
            head, tail = f"{noise}", f" {dose} {verb}" if rng.random() < 0.7 else f" {dose} ({verb})"
        out.append((action_context(head, tail), label))
    return out


def gold_mentions(rows: list[dict]) -> list[tuple[str, str, str]]:
    """(note_id, context, label) for the decisive mention of every gold medication."""
    ex = LocalExtractor(action_model=False)
    out = []
    for r in rows:
        text, _ = ex.preprocess(r["note"])
        found = {med_key(m.name): mentions for m, mentions in ex.medication_mentions(_sentences(text))}
        for g in r["gold"]["medications"]:
            mentions = found.get(med_key(g["name"]))
            if mentions:
                out.append((r["id"], mentions[-1]["context"], g["action"]))
    return out


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
    ])
    return Pipeline([("features", features),
                     ("clf", LogisticRegression(max_iter=3000, C=4.0, class_weight="balanced"))])


def fit(gold: list[tuple[str, str, str]], synth: list[tuple[str, str]], gold_weight: float = 3.0) -> Pipeline:
    X = [c for _, c, _ in gold] + [c for c, _ in synth]
    y = [lab for _, _, lab in gold] + [lab for _, lab in synth]
    w = [gold_weight] * len(gold) + [1.0] * len(synth)
    pipe = build_pipeline()
    pipe.fit(X, y, clf__sample_weight=w)
    return pipe


def cross_validate(rows: list[dict], gold: list[tuple[str, str, str]], synth) -> dict:
    """Leave-one-note-out: train on every other note (+ synthetic), extract the held-out note, score it."""
    totals = {m: [0, 0] for m in ("rules", "hybrid", "model")}
    entity_f1 = {}
    for mode in totals:
        preds = {}
        for r in rows:
            if mode == "rules":
                ex = LocalExtractor(action_model=False)
            else:
                model = ActionModel(fit([g for g in gold if g[0] != r["id"]], synth), mode=mode)
                ex = LocalExtractor(action_model=model, action_mode=mode)
            preds[r["id"]] = ex.extract(r["note"])
        res = evaluate(lambda note, _p=preds, _rows={x["note"]: x["id"] for x in rows}: _p[_rows[note]], rows)
        a = res["attributes"]["action"]
        totals[mode] = [round(a["accuracy"] * a["n"]), a["n"]]
        entity_f1[mode] = res["entities"]["all"]["f1"]
    return {m: {"action_accuracy": c / n if n else None, "n": n, "entity_f1": entity_f1[m]} for m, (c, n) in totals.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-cv", action="store_true")
    args = ap.parse_args()
    rows = [r for s in TUNING_SPLITS for r in load(s)]
    gold, synth = gold_mentions(rows), synthetic()
    print(f"gold mentions: {len(gold)} from {len(rows)} notes · synthetic: {len(synth)}")
    mode = "hybrid"
    report = {}
    if not args.no_cv:
        report = cross_validate(rows, gold, synth)
        for m, v in report.items():
            print(f"  LONO-CV {m:<7} action accuracy {v['action_accuracy']:.3f} (n={v['n']})  entity F1 {v['entity_f1']:.3f}")
        mode = max(report, key=lambda m: (report[m]["action_accuracy"], m == "rules"))
        print(f"selected mode: {mode}")
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"pipeline": fit(gold, synth), "mode": mode, "min_confidence": 0.0,
                 "trained_on": list(TUNING_SPLITS), "n_gold": len(gold), "n_synthetic": len(synth), "cv": report},
                MODEL_PATH, compress=3)
    load_action_model.cache_clear()
    (MODEL_PATH.parent / "action_clf_cv.json").write_text(json.dumps(report, indent=2))
    print(f"saved {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
