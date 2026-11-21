"""Qwen (Model Studio d'Alibaba), el segon auditor.

La regla de la casa per a les traduccions i les glosses és «dos auditors i només l'acord»
(docs/recerca/models-de-text.md): dues cases diferents, amb dades diferents, i només compta el que
diuen tots dos. Des que Gemini es va quedar sense crèdit (24-10-2026) només hi havia DeepSeek. El
16-11-2026 en Pablo obre un compte nou d'Alibaba Cloud i activa Model Studio: 70 models amb un
milió de fitxes gratuïtes cada un. Mesurat sobre 60 frases nostres, `qwen3.8-max` sense raonar
tradueix tan bé com `deepseek-flash` (chrF 0,47) sense deixar mai la resposta buida i en 2 segons.

Dues coses que no són òbvies:
  - La clau de Model Studio (`sk-ws-…`) només contesta pel **punt d'accés de l'espai de treball**
    que surt al diàleg de la clau (`DASHSCOPE_BASE_URL`), no pel genèric `dashscope-intl`.
  - Als Qwen se'ls apaga el raonament (`enable_thinking: false`): amb el raonament encès, un model
    que no coneix una paraula es pot gastar tot el sostre rumiant i tornar buit, que és el que
    fan els raonadors de DeepSeek 1-2 cops de 5.

Mateixa forma que `deepseek_client.deepseek_generate`, perquè es pugui posar a la fila sense
tocar res més. No és un traductor d'amazic: és una segona opinió que va a `*_suggested`.
"""
from __future__ import annotations

import os

import requests

#: El comptador de despesa (`ai_budget.Meter`); l'enganxa l'app en arrencar, com amb DeepSeek.
_meter = None


def set_meter(meter) -> None:
    global _meter
    _meter = meter


#: El model que ha guanyat la mesura del 16-11: bo, barat i sense buits. `qwen4-max` raonant és
#: una mica millor (0,50) però triga de 12 a 24 s i costa deu vegades més fitxes.
MODEL = os.getenv("QWEN_MODEL", "qwen3.8-max")
THINKERS = ("thinking", "reasoner")


def qwen_available() -> bool:
    return bool(os.getenv("DASHSCOPE_API_KEY")) and bool(os.getenv("DASHSCOPE_BASE_URL"))


def _chat(body: dict, timeout: int) -> dict:
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    base = os.getenv("DASHSCOPE_BASE_URL", "").rstrip("/")
    if not key or not base:
        raise RuntimeError("DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL not configured")
    used = body.get("model") or MODEL
    if _meter is not None:
        _meter.before_call(used)
    try:
        r = requests.post(f"{base}/chat/completions",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json=body, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"Qwen API {r.status_code}: {r.text[:300]}")
        data = r.json() or {}
    except Exception:
        if _meter is not None:
            _meter.after_call(used, None, False)
        raise
    if _meter is not None:
        _meter.after_call(used, data, True)
    return data


def qwen_generate(system_instruction: str, contents: list, *,
                  max_output_tokens: int = 1024, temperature: float = 0.4,
                  timeout: int = 90, model: str | None = None) -> str:
    """La mateixa crida que `gemini_generate` i `deepseek_generate`, contra Model Studio.

    `contents` són els torns [{"role": "user"|"model", "text": ...}], traduïts als noms de l'API
    d'OpenAI, que és la que Model Studio imita.
    """
    messages = [{"role": "system", "content": system_instruction}]
    for c in contents:
        messages.append({"role": "assistant" if c.get("role") == "model" else "user",
                         "content": c.get("text", "")})
    used = model or MODEL
    body = {"model": used, "messages": messages, "max_tokens": max_output_tokens, "temperature": temperature}
    if used.startswith("qwen"):
        body["enable_thinking"] = any(t in used.lower() for t in THINKERS)
    data = _chat(body, timeout)
    choices = data.get("choices") or []
    first = choices[0] if choices else {}
    text = (first.get("message", {}).get("content") or "").strip()
    if not text:
        raise RuntimeError(f"{used} no ha contestat (final «{first.get('finish_reason')}»)")
    return text
