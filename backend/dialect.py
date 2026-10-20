"""Dialect-aware transcription of a recording.

One recogniser does not fit every variety. Measured 2026-10-20 (character error rate on
phonemic keys; scratchpad dialect_eval.json):

                                   NeMo zgh   Gemini plain   Gemini + profile + NeMo hint
  Beni Mellal clips (n=40, truth)    0.35        0.54              0.29
  Halima's recordings (n=32)         0.55        0.41              0.42

So: standard Tamazight (zgh) keeps the NeMo model; the Tadla/Azilal transitional variety
(tdl) and Central Atlas (tzm) use Gemini listening with a profile of the variety, example
sentences of the same speakers, the NeMo hypothesis as a hint and dictionary candidates;
Tachelhit (shi) and Tarifit (rif) use Gemini listening with their profile (the NeMo model is
noise there). Machine output only: callers write it to *_suggested, never to the gold text.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import requests

from transliteration import to_forms

ASR_SPACE_DEFAULT = "https://huggingface.co/spaces/josepabloucr/huggingface-asr-space"

PROFILES: Dict[str, Dict[str, str]] = {
    "zgh": {
        "label": "Amazic estàndard marroquí (IRCAM)",
        "engine": "nemo",
        "desc": "Standard Moroccan Amazigh as taught by IRCAM (Tamazight For All, school material): clear, "
                "slow, standard vocabulary, no Arabic dialect words.",
    },
    "tzm": {
        "label": "Tamazight de l'Atles Central",
        "engine": "ensemble",
        "desc": "Central Atlas Tamazight (Khenifra, Azrou, Midelt, Errachidia): spirantised t/d/k are common "
                "(θ ð x), g often palatalised, aspect prefix 'da' for the habitual, 'is' for yes/no questions, "
                "'mani' for where, negation 'ur', many Arabic loans with the article l-.",
    },
    "tdl": {
        "label": "Taixelhit de transició (Tadla–Azilal: Beni Mellal, Azilal, Demnate)",
        "engine": "ensemble",
        "desc": "A TRANSITIONAL variety between Tachelhit and Central Atlas Tamazight (Tadla-Azilal: Beni "
                "Mellal, Azilal, Demnate). Traits: g is often palatalised to j (iga -> ija), spirantised stops "
                "are rare, aspect prefix 'da' for the habitual (da nsaɣ), 'is' for yes/no questions, 'mani(j)' "
                "for where, negative 'ur', frequent Arabic loans with the article l- (lxdmt, ṭṭumubil, lpirmi), "
                "'baba' and 'ma' for father/mother, 'ayt ma' / 'ultma' for siblings.",
    },
    "shi": {
        "label": "Taixelhit (Tashelhit)",
        "engine": "gemini",
        "desc": "Tachelhit of the Souss and High Atlas (Agadir, Taroudant, Tiznit): no spirantisation, "
                "'ad' + aorist for the future, 'ar' for the habitual, 'is' for yes/no questions, 'mani' for "
                "where, 'ur' negation, labialised gʷ/kʷ, many words with the feminine t-…-t frame.",
    },
    "rif": {
        "label": "Tarifit (Rif)",
        "engine": "gemini",
        "desc": "Tarifit (Nador, Al Hoceima): l often becomes r (ul -> ur), ll becomes dj/ǧ, k often š, "
                "spirantised t/d, negation 'ur … ša/bu', many Spanish and Arabic loans.",
    },
    "kab": {
        "label": "Cabilenc (Kabyle)",
        "engine": "gemini",
        "desc": "Kabyle (Algeria): spirantised consonants, negation 'ur … ara', 'anda' for where.",
    },
}

_BASE_SYSTEM = ("You transcribe Moroccan Amazigh (Tamazight / Tachelhit) speech faithfully, in academic Berber "
                "Latin: ɣ ḍ ḥ ṭ ẓ ṣ ṛ ɛ š (write š, not c or sh), x for the uvular fricative, double consonants "
                "written twice, e only for the schwa. Keep the speaker's variety: do not standardise or "
                "translate, do not add words that are not spoken.")


def profile(variety: Optional[str]) -> Optional[Dict[str, str]]:
    return PROFILES.get((variety or "").strip().lower())


def _space_host() -> str:
    url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
    if "huggingface.co/spaces/" in url:
        owner, _, name = url.split("huggingface.co/spaces/")[-1].strip("/").partition("/")
        if owner and name:
            return f"https://{owner}-{name}".lower().replace("_", "-").replace(".", "-") + ".hf.space"
    return url.rstrip("/")


def _prepare_wav(src: str, out_dir: str, tempo: float) -> str:
    """Local path or URL -> mono 16 kHz wav, slowed (Gemini hears 0.85 better than 1.0)."""
    local = src
    if re.match(r"^https?://", src):
        local = os.path.join(out_dir, "clip.src")
        with requests.get(src, timeout=120, stream=True) as r:
            r.raise_for_status()
            with open(local, "wb") as fh:
                for chunk in r.iter_content(1 << 16):
                    fh.write(chunk)
    wav = os.path.join(out_dir, "clip16.wav")
    afilter = ["-filter:a", f"atempo={tempo}"] if 0.5 <= tempo < 1.0 else []
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", local, "-vn", "-ac", "1", "-ar", "16000", *afilter, wav],
                   check=True, capture_output=True, timeout=180)
    return wav


def _duration(path: str) -> float:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out or 0)
    except Exception:
        return 0.0


def _nemo(wav: str) -> str:
    """Hypothesis of the NeMo Space (Tifinagh); '' on any failure."""
    try:
        headers = {}
        tok = os.getenv("HUGGINGFACE_API_KEY")
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        with open(wav, "rb") as fh:
            r = requests.post(_space_host() + "/transcribe", files={"audio_file": ("clip.wav", fh, "audio/wav")},
                              headers=headers, timeout=600)
        return (r.json().get("text") or "").strip() if r.status_code == 200 else ""
    except Exception as e:
        print(f"[DIALECT] NeMo hint failed: {e}")
        return ""


def _dictionary_lines(hint: str) -> List[str]:
    try:
        import lexicon
        if not lexicon.status()["loaded"]:
            return []
        return lexicon.grounding_lines(hint)[:8]
    except Exception:
        return []


def dedupe_takes(text: str) -> str:
    """A recording often holds the sentence twice (two takes): keep one."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return t
    parts = [p.strip() for p in re.split(r"[.\n]|(?<=\?)\s", t) if p and p.strip()]
    seen, out = set(), []
    for p in parts:
        k = re.sub(r"[^\w]", "", p.lower())
        if k and k not in seen:
            seen.add(k)
            out.append(p)
    joined = " ".join(out)
    words = joined.split()
    half = len(words) // 2
    if half >= 2 and words[:half] == words[half:2 * half] and len(words) == 2 * half:
        joined = " ".join(words[:half])
    return joined


def _gemini_listen(wav: str, system: str, prompt: str, timeout: int = 150) -> str:
    from gemini_client import _generate_content
    data = base64.b64encode(open(wav, "rb").read()).decode()
    payload = {"systemInstruction": {"parts": [{"text": system}]},
               "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": data}}, {"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": 300, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    out = _generate_content(payload, timeout)
    text = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip().strip('"')
    return text


def transcribe(source: str, variety: Optional[str], *, meaning: Optional[str] = None,
               speaker_text: Optional[str] = None, examples: Optional[List[str]] = None,
               max_secs: float = 30.0, tempo: float = 0.85) -> Optional[Dict[str, Any]]:
    """Transcribe one recording (local path or URL) with the engine of its variety.
    Returns {latin, tifinagh, engine, hint} or None (too long, no profile, failure)."""
    prof = profile(variety)
    if prof is None:
        return None
    with tempfile.TemporaryDirectory() as d:
        try:
            wav = _prepare_wav(source, d, tempo)
        except Exception as e:
            print(f"[DIALECT] cannot prepare audio: {e}")
            return None
        dur = _duration(wav) * tempo
        if dur and dur > max_secs:
            return None
        hint = _nemo(wav) if prof["engine"] in ("nemo", "ensemble") else ""
        if prof["engine"] == "nemo":
            if not hint:
                return None
            f = to_forms(hint)
            return {"latin": f["clean_latin"], "tifinagh": hint, "engine": "nemo", "hint": hint}
        from gemini_client import gemini_available
        if not gemini_available():
            return None
        system = _BASE_SYSTEM + "\n\nVARIETY: " + prof["desc"]
        if examples:
            system += "\n\nSentences by speakers of this variety (how they talk and write):\n" + "\n".join(f"- {e}" for e in examples[:24])
        parts = ["Transcribe exactly the words spoken, in academic Berber Latin. If the sentence is said twice, write it once."]
        if hint:
            parts.append(f"A recogniser trained on standard Tamazight heard: «{hint}» (often wrong on this variety; use it only as a hint).")
        if meaning:
            parts.append(f"The sentence means, in Catalan: «{meaning}».")
        if speaker_text:
            parts.append(f"The speaker wrote it in their own informal spelling as: «{speaker_text}». Keep their words; only fix the orthography.")
        dict_lines = _dictionary_lines(hint or speaker_text or "")
        if dict_lines:
            parts.append("Dictionary candidates for words you may hear:\n" + "\n".join(dict_lines))
        parts.append("Answer with the transcription only.")
        try:
            latin = dedupe_takes(_gemini_listen(wav, system, "\n\n".join(parts)))
        except Exception as e:
            print(f"[DIALECT] Gemini listening failed: {e}")
            return None
        if not latin or len(latin) > 400:
            return None
        f = to_forms(latin)
        return {"latin": latin, "tifinagh": f["tifinagh"], "engine": prof["engine"], "hint": hint}
