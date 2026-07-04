"""
Minimal Gemini REST client (no SDK — same convention as the rest of app2:
Python 3.14 breaks the official google-generativeai SDK, so we call the REST
endpoints with `requests`).
"""
import os
import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def gemini_available() -> bool:
    return bool((os.getenv("GEMINI_API_KEY") or "").strip())


def gemini_generate(system_instruction: str, contents: list, *,
                    max_output_tokens: int = 1024, temperature: float = 0.4,
                    thinking_budget: int = 0, timeout: int = 90) -> str:
    """
    Call Gemini generateContent.
    - system_instruction: persistent grounding/role text.
    - contents: [{"role": "user"|"model", "text": "..."}] conversation turns.
    Returns the model's text answer. Raises on API error.
    """
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    url = f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [
            {"role": ("model" if c.get("role") == "model" else "user"),
             "parts": [{"text": c.get("text", "")}]}
            for c in contents
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "temperature": temperature,
            # 2.5 models "think" by default, which spends the output budget and
            # adds latency; disable for snappy chat (grounding does the work).
            "thinkingConfig": {"thinkingBudget": thinking_budget},
        },
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {str(data)[:300]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        finish = candidates[0].get("finishReason", "?")
        raise RuntimeError(f"Gemini returned empty text (finishReason={finish})")
    return text
