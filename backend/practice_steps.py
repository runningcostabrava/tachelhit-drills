"""The steps a practice is made of (ADR 0002).

A practice used to be a list of drill ids with one question type over all of it. Now it is an
ordered sequence where every step carries its own tool, drawn from what the library already
holds: the speakers' voices, the pictures, the piece each lesson marks, the word-by-word glosses,
Tifinagh, the other spellings of the same sentence, and the pronunciation scorer.

Two kinds change what the tool is FOR: `note` teaches instead of asking, and `record` asks the
person to say the sentence for the library — so the same practice can be the voice session handed
to a speaker.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

# kind -> (needs a drill, what it asks of the learner)
KINDS: Dict[str, tuple] = {
    "listen_pick":  (True,  "escolta la frase i tria què vol dir"),
    "write_heard":  (True,  "escolta i escriu el que sents"),
    "say_it":       (True,  "digues-ho (es puntua la pronúncia)"),
    "look_say":     (True,  "mira la imatge i digues-ho"),
    "fill_gap":     (True,  "omple el tros que s'ensenya"),
    "word_by_word": (True,  "lliga cada paraula amb el que vol dir"),
    "script_swap":  (True,  "llegeix-ho en l'altra escriptura"),
    "pick_spelling": (True, "tria quina de les dues maneres de dir-ho és la d'aquest parlant"),
    "note":         (False, "llegeix: una explicació, un títol, una imatge"),
    "record":       (True,  "grava aquesta frase amb la teva veu"),
}

# What an old practice becomes when it is converted (ADR 0002): the tool comes from the single
# question type the whole list used to carry.
FROM_LEGACY = {"text_input": "write_heard", "audio": "listen_pick", "video": "listen_pick",
               "combined": "listen_pick"}
DEFAULT_KIND = "listen_pick"


class StepError(ValueError):
    """What is wrong with a step, in words the editor can show."""


def validate(step: dict) -> dict:
    """One step, cleaned, or an error saying why it cannot be one."""
    kind = str(step.get("kind") or "").strip()
    if kind not in KINDS:
        raise StepError(f"«{kind or '—'}» no és una manera de practicar que coneguem")
    needs_drill, _ = KINDS[kind]
    drill_id = step.get("drill_id")
    if needs_drill and not drill_id:
        raise StepError(f"«{kind}» necessita una frase")
    payload = step.get("payload")
    if kind == "note":
        text = (payload or {}).get("text") if isinstance(payload, dict) else None
        if not (text or "").strip():
            raise StepError("una nota sense text no ensenya res")
    return {"kind": kind, "drill_id": int(drill_id) if drill_id else None,
            "payload": json.dumps(payload, ensure_ascii=False) if payload else None}


def steps_of(db, test_id: int) -> List[dict]:
    """A practice's steps, in the order a learner meets them."""
    from models import PracticeStep
    rows = (db.query(PracticeStep).filter(PracticeStep.test_id == test_id)
            .order_by(PracticeStep.position.asc(), PracticeStep.id.asc()).all())
    out = []
    for r in rows:
        try:
            payload = json.loads(r.payload) if r.payload else None
        except Exception:
            payload = None
        out.append({"id": r.id, "position": r.position, "kind": r.kind,
                    "drill_id": r.drill_id, "payload": payload})
    return out


def replace_steps(db, test_id: int, steps: List[dict]) -> List[dict]:
    """Rewrite a practice's steps from the order the editor sends. Everything is validated BEFORE
    anything is deleted: a practice is never left half-written because step nine was wrong."""
    from models import PracticeStep
    cleaned = [validate(s) for s in (steps or [])]
    db.query(PracticeStep).filter(PracticeStep.test_id == test_id).delete(synchronize_session=False)
    for i, s in enumerate(cleaned):
        db.add(PracticeStep(test_id=test_id, position=i, kind=s["kind"],
                            drill_id=s["drill_id"], payload=s["payload"]))
    db.commit()
    return steps_of(db, test_id)


def from_legacy(test) -> List[dict]:
    """The steps an old practice becomes: one per sentence, with the tool it used to carry."""
    kind = FROM_LEGACY.get((test.question_type or "").strip(), DEFAULT_KIND)
    ids = [x.strip() for x in (test.drill_ids or "").split(",") if x.strip().isdigit()]
    return [{"kind": kind, "drill_id": int(x), "payload": None} for x in ids]


def convert_missing(session_factory, limit: int = 500) -> dict:
    """Give steps to the practices that have none. Safe to run again: a practice that already has
    steps is left alone, so this can live on startup without doubling anything."""
    from models import PracticeStep, Test as TestModel
    db = session_factory()
    done, made = 0, 0
    try:
        with_steps = {r[0] for r in db.query(PracticeStep.test_id).distinct().all()}
        for test in db.query(TestModel).order_by(TestModel.id.asc()).limit(limit).all():
            if test.id in with_steps:
                continue
            steps = from_legacy(test)
            if not steps:
                continue
            for i, s in enumerate(steps):
                db.add(PracticeStep(test_id=test.id, position=i, kind=s["kind"],
                                    drill_id=s["drill_id"], payload=None))
            done += 1
            made += len(steps)
        db.commit()
        if done:
            print(f"[PRACTICE] {done} practices converted to steps ({made} steps)")
        return {"practices": done, "steps": made}
    finally:
        db.close()
