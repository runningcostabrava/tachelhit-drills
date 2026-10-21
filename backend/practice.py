"""Pràctica: short pronunciation sessions built from the library, Duolingo-style but centred on
saying the sentences the way our speakers do.

- `collections`: the ways the library is offered for practice: by recording day (one of our
  speakers' sessions), by subject (the topics catalogue), by grammar unit, and the hand-made lists
  (the old tests).
- `session_rows`: the drills of one session: real sentences (or words, in the units about words)
  with a voice, the recorded ones and the pictured ones first.
- `tips`: rule-based pronunciation advice for the sounds of a sentence that give Catalan speakers
  trouble (ɣ, ḥ, ɛ, q, x, the emphatics, long consonants…), with the spelling found in the text so
  the card can highlight it. The speakers spell freely (gh/ġ/ɣ, kh/x, 3/ɛ, sh/š): every spelling of
  a sound is recognised.
- `compare_words`: the learner's words against the speaker's, sound by sound, so the result card
  can colour the ones that came out different.
"""
from __future__ import annotations

from collections import Counter
import difflib
import re
from typing import Dict, List, Optional

import grammar
import topics as topics_catalog

# ---- the sounds and their advice (Catalan, for a learner who is not a linguist) ----
# (slug, regex over the lower-cased text, label shown, tip). Order = priority when a sentence has many.
SOUNDS = [
    ("gh", r"ɣ|ġ|gh|ğ|ɣ", "ɣ (gh)",
     "La ɣ (escrita gh, ġ o ɣ) es fa al fons de la gola, com la r francesa, suau i sense vibrar la llengua. No la diguis com una g catalana."),
    ("h-forta", r"ḥ|ħ|ḩ", "ḥ",
     "La ḥ és una h forta: deixa sortir aire de la gola com quan entelés un vidre, però amb veu neta. No és muda com la h catalana."),
    ("ain", r"ɛ|ʕ|3|ε|ԑ", "ɛ (3)",
     "La ɛ (escrita 3 o ɛ) és un so de gola que no tenim: estreny la gola com si fessis força i deixa passar la veu. Prova de dir «a» amb la gola tancada a mitges."),
    ("q", r"q", "q",
     "La q no és la nostra qu: és una k dita més endins, amb el darrere de la llengua tocant la campaneta. Més fonda que la k de «casa»."),
    ("kh", r"x|kh|ḫ", "x (kh)",
     "La x (escrita kh o x) sona com la j castellana de «jamón»: aire fregant al fons de la boca. No és la x catalana de «xocolata»."),
    ("emfatiques", r"ṭ|ḍ|ṣ|ẓ|ṛ|ḷ|[TDSZ](?=[a-zɣḥɛšč])", "ṭ ḍ ṣ ẓ",
     "Les lletres amb un punt a sota (ṭ, ḍ, ṣ, ẓ; a vegades en majúscula) són «grosses»: es diuen amb la llengua enrere i la boca més oberta, i la vocal del costat sona més fosca."),
    ("sh", r"š|sh|ch|ʃ", "š (sh)",
     "La š (escrita sh o ch) és la x catalana de «xocolata». Si va doble (šš) allarga-la."),
    ("j", r"ž|j|ʒ", "ž (j)",
     "La ž (escrita j) és la j catalana de «jove», mai la j castellana."),
    ("w", r"(?<![a-z])w|w(?=[a-zɣḥɛ])|ʷ|°", "w",
     "La w és una u consonant, com a «quatre» o l'anglès «we». Les lletres amb ʷ (gʷ, kʷ) es diuen arrodonint els llavis alhora."),
    ("geminada", r"(?i)([bcdfgjklmnpqrstvxzɣḥšžṭḍṣẓ])\1", "consonant doble",
     "Una consonant doble (ss, tt, nn, mm, rr, zz…) es diu més llarga i amb més força: aguanta-la un instant. Sovint és el que distingeix dues paraules."),
    ("cluster", r"(?i)(?<![aeiuoəâ])[bcdfgjklmnpqrstvxzɣḥšžṭḍṣẓ]{3,}(?![aeiuoəâ])", "consonants seguides",
     "Tres o més consonants seguides sense vocal: digues-les lligades amb una vocal molt curta i neutra enmig (com la e de «petit»), sense afegir-hi cap vocal clara."),
]

# spelling variants → one sound key, so that «ghur» and «ɣur» compare equal
_FOLD = [
    (r"gh|ġ|ğ|ɣ", "ɣ"), (r"kh|ḫ|x", "x"), (r"3|ʕ|ε|ԑ", "ɛ"), (r"sh|ch|ʃ|š", "š"), (r"ž|ʒ", "ž"),
    (r"ḥ|ħ|ḩ", "ḥ"), (r"ṭ|ṯ", "t"), (r"ḍ|ḏ", "d"), (r"ṣ", "s"), (r"ẓ", "z"), (r"ṛ", "r"), (r"ḷ", "l"),
    (r"ʷ|°", "w"), (r"q", "q"), (r"[eə]", "e"), (r"ou|u|o", "u"), (r"ii|i|y(?![aeiu])", "i"),
]


def sound_key(word: str) -> str:
    """A spelling-independent key of how a word sounds (loose: gh/ɣ, kh/x, 3/ɛ, emphatics folded)."""
    w = word.lower().strip("'’\"«»()[]¿?¡!.,;:-")
    for pat, rep in _FOLD:
        w = re.sub(pat, rep, w)
    w = re.sub(r"(.)\1+", r"\1", w)  # long consonants count once for the comparison
    return w


def words_of(text: str) -> List[str]:
    return [w for w in re.split(r"[\s/]+", (text or "").strip()) if re.search(r"[^\W\d_]", w)]


def compare_words(expected: str, heard: str) -> List[dict]:
    """The expected words, each with whether the learner's utterance had it (by sound), and the
    learner's words that matched nothing. Alignment by difflib on sound keys."""
    exp, got = words_of(expected), words_of(heard)
    ek, gk = [sound_key(w) for w in exp], [sound_key(w) for w in got]
    out = [{"word": w, "ok": False, "heard": None} for w in exp]
    sm = difflib.SequenceMatcher(a=ek, b=gk, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k]["ok"] = True; out[i1 + k]["heard"] = got[j1 + k]
        elif tag == "replace":
            for k in range(min(i2 - i1, j2 - j1)):
                e, g = ek[i1 + k], gk[j1 + k]
                close = difflib.SequenceMatcher(a=e, b=g).ratio() >= 0.75
                out[i1 + k]["ok"] = close; out[i1 + k]["heard"] = got[j1 + k]
    return out


def tips(text: str, limit: int = 3) -> List[dict]:
    """The pronunciation advice for a sentence: the sounds present that cost Catalan speakers,
    hardest first, each with the spelling found (for highlighting)."""
    t = (text or "")
    low = t.lower()
    found = []
    for slug, pat, label, tip in SOUNDS:
        m = re.search(pat, low if slug != "emfatiques" else t)
        if m:
            found.append({"sound": slug, "label": label, "found": m.group(0), "tip": tip})
        if len(found) >= limit:
            break
    return found


def highlights(text: str) -> List[str]:
    """The exact spellings in the text that carry a hard sound (the card bolds them)."""
    t = (text or ""); low = t.lower(); out = []
    for slug, pat, _label, _tip in SOUNDS:
        if slug in ("geminada", "cluster", "w"):
            continue
        for m in re.finditer(pat, low if slug != "emfatiques" else t):
            s = t[m.start():m.end()]
            if s and s not in out:
                out.append(s)
    return out


# ---- what a session is made of ----

def speaker_of(d) -> str:
    return grammar.our_speaker(d) or (d.author or "").strip() or grammar.origin(d) or "gravació"


def practicable(d, slug: Optional[str] = None) -> bool:
    """A drill a session can use: a quotable text with a Catalan meaning and some voice."""
    return bool((d.text_catalan or "").strip()) and grammar.quotable(d.text_tachelhit, slug) and bool(
        d.audio_url or getattr(d, "audio_tts_shi_url", None))


def order_key(d):
    return (not d.audio_url, not d.image_url, d.id)


def collections(db) -> dict:
    from models import Drill as DrillModel, Test as TestModel
    rows = grammar.not_excluded(db.query(DrillModel).filter(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != ""), DrillModel).all()
    # by recording day: our speakers' sessions (a recorded voice, grouped by day and speaker)
    days: Dict[tuple, int] = Counter()
    for d in rows:
        if d.audio_url and practicable(d) and grammar.origin(d) == grammar.AIT_MRAW and d.date_created:
            days[(d.date_created.strftime("%Y-%m-%d"), speaker_of(d))] += 1
    day_list = [{"day": k[0], "speaker": k[1], "count": n} for k, n in days.items() if n >= 3]
    day_list.sort(key=lambda x: (x["day"], x["speaker"]), reverse=True)
    # by subject
    tcount: Dict[str, int] = Counter()
    for d in rows:
        if practicable(d):
            for s in topics_catalog.parse(d.topics):
                tcount[s] += 1
    labels = {t["slug"]: t["label"] for t in topics_catalog.TOPICS}
    topic_list = [{"slug": s, "label": labels.get(s, s), "count": n} for s, n in tcount.items() if s in labels and n >= 3]
    topic_list.sort(key=lambda x: -x["count"])
    # by grammar unit
    ucount: Dict[str, int] = Counter()
    for d in rows:
        for s in grammar.parse(d.grammar):
            if practicable(d, s):
                ucount[s] += 1
    unit_list = [{"slug": u["slug"], "title": u["title"], "level": u["level"], "count": ucount.get(u["slug"], 0)} for u in grammar.UNITS]
    # hand-made lists
    tests = db.query(TestModel).order_by(TestModel.id.desc()).all()
    list_list = [{"id": t.id, "title": t.title, "count": len([x for x in (t.drill_ids or "").split(",") if x.strip()])} for t in tests]
    return {"days": day_list, "topics": topic_list, "units": unit_list, "lists": list_list}


def session_rows(db, day: Optional[str] = None, speaker: Optional[str] = None, topic: Optional[str] = None,
                 unit: Optional[str] = None, test_id: Optional[int] = None, ids: Optional[List[int]] = None,
                 limit: int = 10, offset: int = 0) -> List:
    from models import Drill as DrillModel, Test as TestModel
    q = grammar.not_excluded(db.query(DrillModel).filter(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != ""), DrillModel)
    if ids:
        rows = {d.id: d for d in q.filter(DrillModel.id.in_(ids)).all()}
        return [rows[i] for i in ids if i in rows and practicable(rows[i])][:max(1, min(limit, 50))]
    if test_id:
        t = db.query(TestModel).filter(TestModel.id == test_id).first()
        ids = [int(x) for x in (t.drill_ids or "").split(",") if x.strip().isdigit()] if t else []
        q = q.filter(DrillModel.id.in_(ids or [-1]))
    if topic:
        q = q.filter(DrillModel.topics.ilike(f"%{topic}%"))
    if unit:
        q = q.filter(DrillModel.grammar.ilike(f"%{unit}%"))
    rows = q.all()
    if day:
        rows = [d for d in rows if d.audio_url and d.date_created and d.date_created.strftime("%Y-%m-%d") == day]
    if speaker:
        rows = [d for d in rows if speaker_of(d) == speaker]
    if topic:
        rows = [d for d in rows if topic in topics_catalog.parse(d.topics)]
    if unit:
        rows = [d for d in rows if unit in grammar.parse(d.grammar)]
    rows = [d for d in rows if practicable(d, unit)]
    rows.sort(key=order_key if not test_id else (lambda d: d.id))
    return rows[offset:offset + max(1, min(limit, 50))]


def card(d) -> dict:
    """What a session card needs beyond the drill: who says it, the hard sounds, the advice."""
    return {"speaker": speaker_of(d), "origin": grammar.origin(d), "day": d.date_created.strftime("%Y-%m-%d") if d.date_created else None,
            "tips": tips(d.text_tachelhit), "highlights": highlights(d.text_tachelhit)}
