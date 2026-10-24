"""DeepSeek, per quan Gemini no contesta.

El 24-10-2026 l'assistent de l'app va començar a respondre això a tothom:

    AI assistant error: Gemini API 402: Your prepayment credits are depleted.

Qui obre l'app no ha de saber quin proveïdor fem servir ni què és un crèdit: ha de poder
preguntar què vol dir una frase. Aquest mòdul és el segon de la fila, amb la mateixa forma que
`gemini_client.gemini_generate` perquè es pugui posar al darrere sense tocar res més.

**No és un traductor d'amazic.** Un model general en sap molt poc i inventa amb aplom. Serveix
per al català i per a l'àrab, i per a l'amazic només amb les fonts al davant (el diccionari i
les nostres frases) i amb el resultat tractat com el que és: una proposta.
"""
from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

#: El de pressa i barat per a lots; `deepseek-v4-pro` per al que demana pensar.
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")


def deepseek_available() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def deepseek_generate(system_instruction: str, contents: list, *,
                      max_output_tokens: int = 1024, temperature: float = 0.4,
                      timeout: int = 90, model: str | None = None) -> str:
    """La mateixa crida que `gemini_generate`, contra l'API de DeepSeek.

    `contents` són els torns de la conversa, [{"role": "user"|"model", "text": ...}], i es
    tradueixen als noms que fa servir l'API d'OpenAI, que és la que DeepSeek imita.
    """
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")
    messages = [{"role": "system", "content": system_instruction}]
    for c in contents:
        messages.append({"role": "assistant" if c.get("role") == "model" else "user",
                         "content": c.get("text", "")})
    r = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model or MODEL, "messages": messages,
              "max_tokens": max_output_tokens, "temperature": temperature},
        timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"DeepSeek API {r.status_code}: {r.text[:300]}")
    choices = (r.json() or {}).get("choices") or []
    text = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
    if not text:
        raise RuntimeError("DeepSeek returned empty text")
    return text


#: Els errors que volen dir «aquest proveïdor no et servirà avui», no «aquesta pregunta és
#: dolenta»: sense crèdit, massa peticions, o la porta tancada. Davant d'aquests es canvia de
#: proveïdor; davant de qualsevol altre, no, perquè repetir una pregunta mal feta a un altre
#: model dona la mateixa resposta mal feta.
QUOTA_SIGNS = ("402", "429", "quota", "credits", "rate limit", "resource_exhausted",
               "insufficient", "permission")


def is_quota_error(err: Exception) -> bool:
    text = str(err).lower()
    return any(s in text for s in QUOTA_SIGNS)
