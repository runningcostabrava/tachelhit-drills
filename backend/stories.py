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


def _title_of(drill) -> str:
    return (getattr(drill, "source_title", None) or "").strip() or (getattr(drill, "tag", None) or "").strip()


def _voiced(drill) -> bool:
    return bool((getattr(drill, "audio_url", "") or "").strip())


def _timed(drill) -> bool:
    return getattr(drill, "video_start_time", None) is not None


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
    """Enough lines, in an order we can recover, with voices to hear."""
    if len(drills) < MIN_LINES:
        return False
    timed = sum(1 for d in drills if _timed(d))
    voiced = sum(1 for d in drills if _voiced(d))
    return timed >= MIN_LINES and timed >= len(drills) * 0.6 and voiced >= len(drills) * 0.6


def in_order(drills: List) -> List:
    """The lines as they are spoken. Anything untimed goes last, in the order it was added:
    it is usually a line somebody wrote later, and guessing where it belongs would be a lie."""
    timed = sorted((d for d in drills if _timed(d)), key=lambda d: (d.video_start_time, d.id))
    rest = sorted((d for d in drills if not _timed(d)), key=lambda d: d.id)
    return timed + rest


def summary(title: str, drills: List) -> dict:
    """What a story looks like from the outside: how long, how complete, and a picture."""
    ordered = in_order(drills)
    cover = next((d.image_url for d in ordered if (getattr(d, "image_url", "") or "").strip()), None)
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
        "video_url": video,
        "source_url": source,
        "channel": next((d.source_channel for d in ordered if (getattr(d, "source_channel", "") or "").strip()), None),
        "speaker": next((getattr(d, "speaker", None) or getattr(d, "author", None) for d in ordered
                         if (getattr(d, "speaker", None) or getattr(d, "author", None))), None),
    }


def listing(db) -> List[dict]:
    """Every story in the library, the ones you can read all the way through first."""
    out = [summary(title, drills) for title, drills in groups(db).items() if is_story(drills)]
    out.sort(key=lambda s: (s["missing_words"] > 0, -s["lines"]))
    return out


def one(db, slug: str) -> Optional[dict]:
    """A story: the same summary, plus its lines in the order they are spoken."""
    for title, drills in groups(db).items():
        if slug_of(title) != slug or not is_story(drills):
            continue
        ordered = in_order(drills)
        return {**summary(title, drills), "drill_ids": [d.id for d in ordered]}
    return None
