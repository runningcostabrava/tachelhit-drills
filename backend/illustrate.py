"""Flashcard illustrations for drills.

A learner sees the picture while hearing the sentence, so the picture has to show the
MEANING of the sentence — one clear scene, no written words (the words are the drill).
Gemini's image model draws from the Catalan sentence directly (no translation step) in
one consistent style, so a deck of drills looks like one deck.

The style is deliberately flat and warm so it sits on the app's sand palette, and it
asks for a Moroccan Amazigh setting when the scene allows (this is a Tachelhit app), so
"the mother bakes bread" does not come back as a Nordic kitchen.
"""
from __future__ import annotations

import base64
import io
import os

from gemini_client import _generate_content, gemini_available

IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

STYLE = (
    "Flat vector illustration for a language-learning flashcard. One clear scene that shows the meaning of "
    "the sentence so a learner could guess it from the picture alone. Warm earthy palette (sand, terracotta, "
    "indigo, olive), clean simple shapes, soft rounded forms, no outlines noise, plain light background. "
    "The people and places are Moroccan Amazigh (Souss, Atlas) whenever the scene allows: djellabas and "
    "headscarves, adobe houses, argan and olive trees, mint tea, tagine. "
    "Absolutely no text, letters, numbers, captions, labels, speech bubbles or signs anywhere in the image."
)


def illustration_available() -> bool:
    """Si hi ha algú que pugui dibuixar: Gemini, o un Space públic de FLUX amb el nostre token.

    El dia que el compte de Gemini es va quedar sense crèdit, l'app va deixar de poder dibuixar
    res. Tenir-ne dos vol dir que una cosa que no depèn de nosaltres no atura la feina."""
    import flux_space
    return gemini_available() or flux_space.available()


def illustration_prompt(text: str, hint: str | None = None) -> str:
    """The sentence may be Catalan (sometimes with an English/Arabic gloss); the model reads it as is.
    `hint` is an optional operator note on what to draw (e.g. "a bicycle, not a motorbike")."""
    sentence = " ".join((text or "").split())
    out = f"{STYLE}\n\nThe sentence: «{sentence}»"
    if hint and hint.strip():
        out += f"\nWhat to draw: {hint.strip()}"
    return out


def describe_scene(text: str, timeout: int = 40) -> str:
    """One concrete scene for the sentence, in English, chosen by the text model before
    drawing. The image model left short or abstract items ("Afilat", "Dibuixem") as a
    generic tea scene; naming the scene first ("a man sharpens a knife on a stone") keeps
    the meaning in the picture. Returns "" on any failure so drawing still goes ahead."""
    ask = (
        "A language-learning flashcard needs ONE picture that shows the meaning of this item so a learner "
        "can guess it from the picture alone. The item is in Catalan (sometimes with an English or Arabic "
        "gloss); it may be a single word, an imperative, a question or a sentence. "
        "Answer with one concrete scene in English, at most 30 words: who does what, with which object, where. "
        "Make the key meaning visually unmistakable (for a question or command, show the situation it is said in; "
        "for a quality like 'sharp' or 'far', show it on an object). No text in the scene.\n\n"
        f"Item: «{' '.join((text or '').split())}»"
    )
    payload = {"contents": [{"role": "user", "parts": [{"text": ask}]}],
               "generationConfig": {"temperature": 0.3, "maxOutputTokens": 80, "thinkingConfig": {"thinkingBudget": 0}}}
    try:
        data = _generate_content(payload, timeout)
        out = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
        return " ".join(out.split())[:300]
    except Exception:
        return ""


def shrink(png: bytes, side: int = 800) -> bytes:
    """Gemini returns ~1 MB PNGs; the card shows them at 320 px and the app caches them
    offline, so store an 800 px WebP (~60 KB). Falls back to the original bytes."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("RGB")
        im.thumbnail((side, side))
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=84)
        return buf.getvalue()
    except Exception:
        return png


def generate_illustration(text: str, hint: str | None = None, timeout: int = 120) -> bytes:
    """WebP bytes for the sentence (see shrink).

    Gemini first —it reads the Catalan sentence itself and draws the scene— and, if it cannot
    (no credit, a safety block, no key), a public FLUX Space with our Hugging Face token. Raises
    RuntimeError only when NOBODY could draw, so callers can fall back to another source.
    """
    import flux_space
    scene = hint or describe_scene(text)
    errors = []
    if gemini_available():
        payload = {
            "contents": [{"role": "user", "parts": [{"text": illustration_prompt(text, scene)}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        try:
            data = _generate_content(payload, timeout, model=IMAGE_MODEL)
            for cand in data.get("candidates") or []:
                for part in cand.get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        return shrink(base64.b64decode(inline["data"]))
            finish = ((data.get("candidates") or [{}])[0]).get("finishReason", "?")
            errors.append(f"Gemini returned no image (finishReason={finish})")
        except Exception as e:
            errors.append(f"Gemini: {type(e).__name__}: {str(e)[:160]}")
    if flux_space.available():
        try:
            # Sense escena, el dibuix l'ha de treure de la frase mateixa: li donem el text tal qual.
            return shrink(flux_space.draw(illustration_prompt(text, scene)))
        except Exception as e:
            errors.append(str(e)[:200])
    raise RuntimeError("; ".join(errors) or "no hi ha cap manera de dibuixar")
