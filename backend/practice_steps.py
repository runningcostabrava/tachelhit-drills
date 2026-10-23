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

# Speaking stayed; MARKING it went, on 2026-10-22. Our transcriber gets a CER of 0.78 on our own
# recordings (docs/ASR_EVAL_NOSTRA_2026-10-22.md), so a score built on it would be noise dressed
# up as a mark -- and it was feeding the review schedule. A learner now records themselves, hears
# the speaker and themselves one after the other, and says for themselves whether they have it.
# The take never leaves the page.
#
# `record` is gone for another reason: it asked for a voice to KEEP in the library, which is a
# different act with different consequences (a name, a place, a licence). That lives in Veus.
RETIRED = {"record": "listen_pick"}

# kind -> (needs a drill, what it asks of the learner)
KINDS: Dict[str, tuple] = {
    "listen_pick":  (True,  "escolta la frase i tria què vol dir"),
    "write_heard":  (True,  "escolta i escriu el que sents"),
    "say_it":       (True,  "digues-ho i compara't amb la veu de debò (ningú no et posa nota)"),
    "look_say":     (True,  "mira la imatge i digues-ho"),
    "fill_gap":     (True,  "omple el tros que s'ensenya"),
    "word_by_word": (True,  "lliga cada paraula amb el que vol dir"),
    "script_swap":  (True,  "llegeix-ho en l'altra escriptura"),
    "pick_spelling": (True, "tria quina de les dues maneres de dir-ho és la d'aquest parlant"),
    "note":         (False, "llegeix: una explicació, un títol, una imatge"),
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
        # A heading alone is a note: «Saludar» over the next three sentences teaches where you are.
        # Only one with nothing at all in it is refused -- and the editor keeps those to itself
        # rather than sending them, because refusing one used to refuse the whole sequence with it.
        d = payload if isinstance(payload, dict) else {}
        if not (d.get("text") or "").strip() and not (d.get("heading") or "").strip():
            raise StepError("una nota sense títol ni text no ensenya res")
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
    from models import Drill as DrillModel, PracticeStep
    cleaned = [validate(s) for s in (steps or [])]
    # A step towards a sentence that no longer exists cannot be written: `drill_id` is a foreign
    # key and Postgres enforces it. Caught here it is a sentence in words the editor can show;
    # caught by the database it is a 500 after the old steps have already been deleted.
    wanted = {s["drill_id"] for s in cleaned if s["drill_id"]}
    if wanted:
        alive = {d[0] for d in db.query(DrillModel.id).filter(DrillModel.id.in_(wanted)).all()}
        gone = sorted(wanted - alive)
        if gone:
            raise StepError("aquests passos apunten a frases que ja no existeixen: "
                            + ", ".join(str(g) for g in gone[:8]))
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
    steps is left alone, so this can live on startup without doubling anything.

    Two things this has to survive, and did not:

    A sentence on the old flat list may be **gone**. `drill_ids` is just a list of numbers, and
    numbers stop meaning anything as a library grows: nine of the first two hundred on practice
    28 pointed at drills deleted since. `practice_steps.drill_id` is a foreign key, which
    Postgres enforces, so a step towards one of those cannot be written at all.

    And a failure must not spread. This used to commit ONCE, after every practice: one
    impossible row at the end took the whole batch with it, the caller logged «conversion
    skipped», and NO practice was ever converted — which is why a practice with 511 sentences
    opened empty. Now each one is saved on its own and the one that fails says its name.
    """
    from models import Drill as DrillModel, PracticeStep, Test as TestModel
    db = session_factory()
    done, made, failed = 0, 0, []
    try:
        with_steps = {r[0] for r in db.query(PracticeStep.test_id).distinct().all()}
        alive = {d[0] for d in db.query(DrillModel.id).all()}
        for test in db.query(TestModel).order_by(TestModel.id.asc()).limit(limit).all():
            if test.id in with_steps:
                continue
            steps = [s for s in from_legacy(test) if s["drill_id"] in alive]
            if not steps:
                continue
            try:
                for i, s in enumerate(steps):
                    db.add(PracticeStep(test_id=test.id, position=i, kind=s["kind"],
                                        drill_id=s["drill_id"], payload=None))
                db.commit()
            except Exception as e:                    # noqa: BLE001 — one bad practice, not all
                db.rollback()
                failed.append((test.id, str(e)[:120]))
                continue
            done += 1
            made += len(steps)
        if done:
            print(f"[PRACTICE] {done} practices converted to steps ({made} steps)")
        for tid, why in failed:
            print(f"[PRACTICE] practice {tid} could not be converted: {why}")
        return {"practices": done, "steps": made, "failed": [t for t, _ in failed]}
    finally:
        db.close()


def retire_spoken_steps(session_factory) -> int:
    """Turn the steps that asked a learner to speak into ones we can honestly run.

    Nothing is deleted: a step keeps its place and its sentence, and only the tool changes
    (see RETIRED). Safe to run again -- once no step carries a retired kind, it does nothing.
    """
    from models import PracticeStep
    db = session_factory()
    try:
        rows = db.query(PracticeStep).filter(PracticeStep.kind.in_(tuple(RETIRED))).all()
        for r in rows:
            r.kind = RETIRED[r.kind]
        if rows:
            db.commit()
            print(f"[PRACTICE] {len(rows)} spoken steps turned into listening ones")
        return len(rows)
    finally:
        db.close()


def repair_pointless_steps(session_factory) -> int:
    """Turn steps that point at no sentence into notes that say so.

    Two ways one appears: the old editor let a note be switched to a tool that needs a sentence
    (it then showed as «frase #», with nothing to do), and a step keeps its drill_id after the
    drill itself is deleted. Either way the step cannot run.

    Nothing is deleted, so a practice never silently loses its shape: the step stays in place as
    a note, and whoever opens it reads what happened.
    """
    from models import Drill as DrillModel, PracticeStep
    db = session_factory()
    try:
        rows = db.query(PracticeStep).all()
        alive = {d[0] for d in db.query(DrillModel.id).all()}
        fixed = 0
        for r in rows:
            needs_drill = KINDS.get(r.kind, (False, ""))[0]
            if not needs_drill:
                continue
            if r.drill_id and r.drill_id in alive:
                continue
            why = ("La frase d'aquest pas s'ha esborrat."
                   if r.drill_id else "Aquest pas demanava una frase i no en tenia cap.")
            r.kind = "note"
            r.payload = json.dumps({"heading": "Pas per refer", "text": why}, ensure_ascii=False)
            r.drill_id = None
            fixed += 1
        if fixed:
            db.commit()
            print(f"[PRACTICE] {fixed} steps pointed at no sentence; turned into notes")
        return fixed
    finally:
        db.close()
