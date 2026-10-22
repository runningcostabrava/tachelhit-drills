"""Where each word is spoken inside the recordings we already have.

The library teaches sentences. Somebody studying a grammar unit, or reading the word-by-word
gloss under a sentence, could not hear ONE word on its own — and a word heard inside a fast
sentence is not the same as a word heard.

Forced alignment gives that for nothing. Our ASR Space takes a recording and the text it says,
and answers when each word is spoken (`POST /align`, NeMo forced aligner). So "hear this word"
becomes a drill id and two timestamps: no new audio files, no uploads, nothing to store but
numbers. The player seeks into the recording that already exists.

**Our own speakers first.** A word said by Halima or Driss carries a name and a place, which is
what this library is for. The open corpus is a fallback for words nobody here has said yet, and
whatever uses it says so.
"""
from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from typing import Dict, List, Optional

import requests

import transliteration

SPACE_DEFAULT = "https://josepabloucr-huggingface-asr-space.hf.space"
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_state: Dict[str, object] = {"running": False, "done": 0, "words": 0, "failed": 0, "last": None}
_lock = threading.Lock()


def state() -> dict:
    return dict(_state)


def key_of(word: str) -> str:
    """One word, one key across spellings and scripts.

    «afus», «afous» and «ⴰⴼⵓⵙ» are the same word said by three people who write differently, and a
    learner asking to hear it does not care which of the three they typed.
    """
    forms = transliteration.to_forms(word or "")
    loose = (forms.get("loose") or forms.get("clean_latin") or "").strip().lower()
    return loose or (word or "").strip().lower()


def _space() -> str:
    url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", SPACE_DEFAULT).strip()
    # the Space is addressed by its host, not by its huggingface.co page
    if "huggingface.co/spaces/" in url:
        owner, name = url.rsplit("/", 2)[-2:]
        return f"https://{owner}-{name}".replace("_", "-").lower() + ".hf.space"
    return url.rstrip("/")


def align_one(audio_url: str, text: str, timeout: int = 300) -> Optional[List[dict]]:
    """The words of `text` with their times inside `audio_url`, or None if it cannot be done.

    Best effort on purpose: a recording that will not align is simply a sentence whose words
    cannot be played yet, never an error anybody has to see.
    """
    if not (audio_url or "").strip() or not (text or "").strip():
        return None
    token = os.getenv("HUGGINGFACE_API_KEY", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        got = requests.get(audio_url, timeout=120)
        got.raise_for_status()
        resp = requests.post(f"{_space()}/align", headers=headers,
                             files={"audio_file": ("clip", got.content, "application/octet-stream")},
                             data={"text": text.strip(), "split_on_newline": "false"}, timeout=timeout)
        if resp.status_code != 200:
            return None
        out = resp.json() or {}
    except Exception:
        return None
    words = out.get("words") or [w for s in (out.get("segments") or []) for w in (s.get("words") or [])]
    clean = []
    for w in words:
        text_of = (w.get("word") or w.get("text") or "").strip()
        start, end = w.get("start"), w.get("end")
        if not text_of or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        if end <= start:
            continue
        clean.append({"word": text_of, "start": float(start), "end": float(end)})
    return clean or None


def store(db, drill, words: List[dict], source: str = "library") -> int:
    """Keep the times of one recording's words, replacing whatever that recording had."""
    from models import WordAudio
    db.query(WordAudio).filter(WordAudio.drill_id == drill.id).delete(synchronize_session=False)
    kept = 0
    for w in words:
        bare = WORD_RE.findall(w["word"])
        if not bare:
            continue
        written = "".join(bare) if len(bare) == 1 else bare[0]
        key = key_of(written)
        if not key:
            continue
        db.add(WordAudio(key=key, word=written, drill_id=drill.id,
                         start_ms=int(w["start"] * 1000), end_ms=int(w["end"] * 1000),
                         speaker=(getattr(drill, "speaker", None) or getattr(drill, "author", None)),
                         source=source, updated_at=datetime.utcnow()))
        kept += 1
    db.commit()
    return kept


def clips_for(db, word: str, limit: int = 6) -> List[dict]:
    """Where this word can be heard, the people we can name first.

    A word said by somebody with a name and a place is worth more than the same word said by
    nobody in particular, so the open corpus only fills the gaps it leaves.
    """
    from models import Drill as DrillModel, WordAudio
    key = key_of(word)
    if not key:
        return []
    rows = (db.query(WordAudio).filter(WordAudio.key == key)
            .order_by(WordAudio.source.asc(), WordAudio.id.asc()).limit(limit * 3).all())
    out = []
    for r in rows:
        drill = db.query(DrillModel).filter(DrillModel.id == r.drill_id).first()
        audio = (getattr(drill, "audio_url", "") or "").strip() if drill else ""
        if not audio:
            continue
        out.append({"word": r.word, "drill_id": r.drill_id, "audio_url": audio,
                    "start": r.start_ms / 1000.0, "end": r.end_ms / 1000.0,
                    "speaker": r.speaker, "source": r.source or "library",
                    "sentence": getattr(drill, "text_tachelhit", None),
                    "meaning": getattr(drill, "text_catalan", None)})
        if len(out) >= limit:
            break
    return out


def run(session_factory, limit: int = 200, redo: bool = False) -> None:
    """Align the library's recorded sentences, so their words can be played one by one.

    Slow and polite: the Space is one CPU and takes one request at a time, so this runs on a
    thread, and a recording that will not align is skipped rather than retried into the ground.
    """
    from models import Drill as DrillModel, WordAudio

    with _lock:
        if _state["running"]:
            return
        _state.update({"running": True, "done": 0, "words": 0, "failed": 0, "last": None})

    def work():
        db = session_factory()
        try:
            done_ids = set() if redo else {r[0] for r in db.query(WordAudio.drill_id).distinct().all()}
            rows = (db.query(DrillModel)
                    .filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "",
                            DrillModel.text_tachelhit.isnot(None), DrillModel.text_tachelhit != "")
                    .order_by(DrillModel.id.desc()).all())
            todo = [d for d in rows if d.id not in done_ids][:max(1, limit)]
            for drill in todo:
                words = align_one(drill.audio_url, drill.text_tachelhit)
                if not words:
                    _state["failed"] = int(_state["failed"]) + 1
                    continue
                _state["words"] = int(_state["words"]) + store(db, drill, words)
                _state["done"] = int(_state["done"]) + 1
                _state["last"] = drill.text_tachelhit
            print(f"[WORDS] aligned {_state['done']} recordings, {_state['words']} words "
                  f"({_state['failed']} could not be aligned)")
        except Exception as e:
            print(f"[WORDS] pass stopped: {e}")
        finally:
            db.close()
            _state["running"] = False

    threading.Thread(target=work, daemon=True).start()
