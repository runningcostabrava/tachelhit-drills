"""Whole stories and songs, instead of loose sentences (#189).

Most of the library is single sentences: true, useful, and nothing to hold on to. But some of
what has been captured is a whole thing — a fable told start to finish, a song with its lyrics —
and those were sitting in the library broken into pieces, each piece a drill like any other.

A story is not a new kind of row. It is what a group of drills already is when they share a
source and carry the time they are spoken at: put them back in that order and you have the text
again, with every line's voice, meaning and word-by-word gloss attached.

What makes a group a story, and not just a pile from the same video:
  - six lines or more, so there is something to follow;
  - most of them say when they are spoken, which is what puts them back in order;
  - most of them have a voice, because a story you cannot hear is a page of text.

A line with no Amazigh words written down is kept in its place and marked: a story with holes is
still a story, and the hole says what is missing instead of hiding it.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional

MIN_LINES = 6


def slug_of(title: str) -> str:
    """A short name for a story, stable enough to put in a URL."""
    text = unicodedata.normalize("NFKD", (title or "").strip().lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9ⴰ-⵿]+", "-", text).strip("-")
    return text[:60] or "historia"


#: «Baba Ali · episodi 15 · 29:40»: una sèrie de televisió retallada a partir dels seus subtítols
#: (#535). Cada línia porta l'episodi i el minut dins del títol, i cap no porta `video_start_time`
#: perquè no ve de YouTube sinó d'una plataforma on el vídeo no es pot incrustar. El títol de la
#: història és la part sense el minut; el minut és l'ordre.
_EPISODI = re.compile(r"^(?P<serie>.+?)\s*·\s*episodi\s+(?P<n>\d{1,3})\s*·\s*(?P<m>\d{1,3}):(?P<s>\d{2})\s*$")


def _title_of(drill) -> str:
    title = (getattr(drill, "source_title", None) or "").strip() or (getattr(drill, "tag", None) or "").strip()
    m = _EPISODI.match(title)
    return f"{m.group('serie')} · episodi {int(m.group('n'))}" if m else title


def _at(drill) -> Optional[float]:
    """Quan es diu una línia: el segon dins del vídeo, o el minut que porta al títol."""
    t = getattr(drill, "video_start_time", None)
    if t is not None:
        return t
    m = _EPISODI.match((getattr(drill, "source_title", None) or "").strip())
    return int(m.group("m")) * 60 + int(m.group("s")) if m else None


#: «The Traveller -2- …», «The Rivals - 1 - …», «The Last Warrior- 2 -…», «… Red Rock … - 1 -».
#: El número entre guions és el capítol; el que va davant és el nom de la sèrie.
_CAPITOL = re.compile(r"^(?P<nom>.+?)\s*-\s*(?P<n>\d{1,2})\s*-\s*(?P<resta>.*)$")


def series_of(title: str) -> tuple[Optional[str], Optional[int]]:
    """De quina sèrie és aquest títol, i quin capítol.

    Els títols del canal porten la sèrie, el capítol, el nom en tifinag i el nom en llatí tot
    junt: «The Traveller -2- ⴰⵏⵎⴰⴷⴷⵓ - Anmaddu». Partir-los deixa ensenyar els set capítols
    seguits i del primer a l'últim, que és l'única cosa que la pàgina ha de fer fàcil, en comptes
    d'escampar-los per la graella segons quantes línies té cada un.

    Torna `(None, None)` quan el títol no porta cap capítol: un conte sol és un conte sol.
    """
    e = re.match(r"^(?P<serie>.+?)\s*·\s*episodi\s+(?P<n>\d{1,3})\s*$", (title or "").strip())
    if e:
        return e.group("serie").strip(), int(e.group("n"))
    m = _CAPITOL.match((title or "").strip())
    if not m:
        return None, None
    nom = m.group("nom").strip(" -–—")
    return (nom or None), int(m.group("n"))


def _video_id(url: Optional[str]) -> Optional[str]:
    """L'identificador del vídeo de YouTube, d'una adreça de les que desem."""
    m = re.search(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def cover_of(ordered: List) -> Optional[str]:
    """La portada d'una història.

    La portada d'un conte que ve d'un vídeo **és la portada d'aquell vídeo**: la va fer qui el va
    fer, va amb l'enllaç cap al seu canal, i és la que la gent reconeix. Per això mana sobre les
    il·lustracions soltes dels drills, que es van demanar per a una frase i no per al conte — una
    d'elles era una **carta d'ajust de televisió** treta de Wikimedia, que feia de portada de la
    faula del llop i la seva ombra i no hi deia absolutament res.

    Si la història no ve de cap vídeo, s'agafa la primera il·lustració que hi hagi, que almenys
    és nostra i és d'una de les seves línies.
    """
    vid = next((_video_id(getattr(d, "source_url", None) or getattr(d, "video_url", None))
                for d in ordered
                if _video_id(getattr(d, "source_url", None) or getattr(d, "video_url", None))), None)
    if vid:
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    return next((d.image_url for d in ordered if (getattr(d, "image_url", "") or "").strip()), None)


def _voiced(drill) -> bool:
    return bool((getattr(drill, "audio_url", "") or "").strip())


def _timed(drill) -> bool:
    return _at(drill) is not None


def _written(drill) -> bool:
    return bool((getattr(drill, "text_tachelhit", "") or "").strip())


def groups(db) -> Dict[str, List]:
    """Every group of drills that came from one source, keyed by its title."""
    from models import Drill as DrillModel
    out: Dict[str, List] = {}
    for drill in db.query(DrillModel).all():
        title = _title_of(drill)
        if title:
            out.setdefault(title, []).append(drill)
    return out


def is_story(drills: List) -> bool:
    """Enough lines, in an order we can recover, with voices to hear — and no two at once.

    The last condition came from a false story. Ten loose Aït Mraw sentences cut from one of the
    owner's own videos turned up on the Stories page as «October 2, 2023» — which is not a title
    but what YouTube puts when a video has none, so all ten shared a `source_title`. They all
    carried a time, so they passed. But three of them started at second 0.0: they were not a
    sequence, they were separate captures from the same video.

    **Two lines of one story never start at the same second**, so a repeated start time is the
    cheapest way to tell a text from a pile. Measured against the library before trusting it: of
    the 25 groups the page was showing, the 24 real stories had every start time distinct —
    776 lines, not one collision — and only the false one repeated.
    """
    if len(drills) < MIN_LINES:
        return False
    starts = [_at(d) for d in drills if _timed(d)]
    # Dues línies d'una història no comencen mai al mateix segon… quan el segon és exacte. El
    # minut del títol d'un episodi (29:40) és el mateix per a dues rèpliques seguides: allà la
    # repetició no diu res, i es mira que la sèrie tingui prou minuts diferents.
    per_titol = any(_EPISODI.match((getattr(d, "source_title", None) or "").strip()) for d in drills)
    if len(set(starts)) != len(starts) and not per_titol:
        return False
    if per_titol and len(set(starts)) < MIN_LINES:
        return False
    voiced = sum(1 for d in drills if _voiced(d))
    return len(starts) >= MIN_LINES and len(starts) >= len(drills) * 0.6 and voiced >= len(drills) * 0.6


def in_order(drills: List) -> List:
    """The lines as they are spoken. Anything untimed goes last, in the order it was added:
    it is usually a line somebody wrote later, and guessing where it belongs would be a lie."""
    timed = sorted((d for d in drills if _timed(d)), key=lambda d: (_at(d), d.id))
    rest = sorted((d for d in drills if not _timed(d)), key=lambda d: d.id)
    return timed + rest


def summary(title: str, drills: List) -> dict:
    """What a story looks like from the outside: how long, how complete, and a picture."""
    ordered = in_order(drills)
    cover = cover_of(ordered)
    series, chapter = series_of(title)
    video = next((d.video_url for d in ordered if (getattr(d, "video_url", "") or "").strip()), None)
    source = next((d.source_url for d in ordered if (getattr(d, "source_url", "") or "").strip()), None)
    written = sum(1 for d in ordered if _written(d))
    return {
        "slug": slug_of(title),
        "title": title,
        "lines": len(ordered),
        "written": written,
        "missing_words": len(ordered) - written,
        "voiced": sum(1 for d in ordered if _voiced(d)),
        "cover": cover,
        # De quina sèrie és i quin capítol, per ensenyar-los seguits i en ordre. `None` quan el
        # títol no en porta: un conte sol és un conte sol.
        "series": series,
        "chapter": chapter,
        "video_url": video,
        "source_url": source,
        "channel": next((d.source_channel for d in ordered if (getattr(d, "source_channel", "") or "").strip()), None),
        "speaker": next((getattr(d, "speaker", None) or getattr(d, "author", None) for d in ordered
                         if (getattr(d, "speaker", None) or getattr(d, "author", None))), None),
    }


def listing(db) -> List[dict]:
    """Every story in the library, in an order somebody can actually start from.

    Abans anava per nombre de línies de més a menys, i això escampava *The Traveller* 1 a 7 per
    tota la graella barrejat amb les altres sèries: ningú no podia començar un conte pel
    principi. Ara:

      - **cada sèrie va seguida i del primer capítol a l'últim**;
      - **primer el que es pot llegir** —les històries que tenen les paraules amazigues
        escrites—, perquè és el que respon la pregunta de qui arriba: què puc fer servir ara;
      - i una sèrie d'un sol capítol no és una sèrie, de manera que torna a ser un conte sol.
    """
    from collections import Counter
    out = [summary(title, drills) for title, drills in groups(db).items() if is_story(drills)]

    quants = Counter(s["series"] for s in out if s["series"])
    for s in out:
        if s["series"] and quants[s["series"]] < 2:
            s["series"], s["chapter"] = None, None

    # Què es pot llegir de cada secció (una sèrie, o el calaix dels contes sols): el màxim mana,
    # perquè una sèrie amb un capítol escrit ja val la pena d'ensenyar abans que una de muda.
    llegible: Dict[str, int] = {}
    for s in out:
        k = s["series"] or ""
        llegible[k] = max(llegible.get(k, 0), s["written"])

    out.sort(key=lambda s: (
        0 if llegible[s["series"] or ""] else 1,     # les seccions amb paraules escrites, primer
        -llegible[s["series"] or ""],
        s["series"] or "",                            # i cada sèrie, seguida
        0 if s["written"] else 1,                     # dins la secció, el que es pot llegir primer
        s["chapter"] if s["chapter"] is not None else 0,
        -s["lines"],
    ))
    return out


def one(db, slug: str) -> Optional[dict]:
    """A story: the same summary, plus its lines in the order they are spoken."""
    for title, drills in groups(db).items():
        if slug_of(title) != slug or not is_story(drills):
            continue
        ordered = in_order(drills)
        return {**summary(title, drills), "drill_ids": [d.id for d in ordered]}
    return None
