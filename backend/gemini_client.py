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


def gemini_agent(system_instruction: str, contents: list, tools: list, executor,
                 *, max_rounds: int = 6, max_output_tokens: int = 1500,
                 temperature: float = 0.4, timeout: int = 90) -> dict:
    """
    Agentic loop with Gemini function-calling. The model can call the provided
    tools (functionDeclarations); `executor(name, args) -> dict` runs each one.
    Returns {"text": final answer, "actions": [{name, args, result}, ...]}.

    - contents: [{"role": "user"|"model", "text": "..."}] conversation turns.
    - tools: list of function declarations (name/description/parameters JSON schema).
    """
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    url = f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent?key={key}"

    g_contents = [
        {"role": ("model" if c.get("role") == "model" else "user"),
         "parts": [{"text": c.get("text", "")}]}
        for c in contents
    ]
    actions = []
    final_text = ""

    for _ in range(max_rounds):
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": g_contents,
            "tools": [{"functionDeclarations": tools}],
            "generationConfig": {
                "maxOutputTokens": max_output_tokens,
                "temperature": temperature,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:300]}")
        cand = (resp.json().get("candidates") or [{}])[0]
        parts = cand.get("content", {}).get("parts", [])
        fcalls = [p["functionCall"] for p in parts if "functionCall" in p]
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        if text:
            final_text = text

        if not fcalls:
            break

        # Record the model's tool-call turn, then run each tool and feed results back
        g_contents.append({"role": "model", "parts": parts})
        resp_parts = []
        for fc in fcalls:
            name = fc.get("name", "")
            args = fc.get("args", {}) or {}
            try:
                result = executor(name, args)
            except Exception as e:
                result = {"error": str(e)[:200]}
            actions.append({"name": name, "args": args, "result": result})
            resp_parts.append({"functionResponse": {
                "name": name,
                "response": result if isinstance(result, dict) else {"result": result},
            }})
        g_contents.append({"role": "user", "parts": resp_parts})

    return {"text": final_text, "actions": actions}
