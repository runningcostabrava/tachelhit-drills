"""
Minimal Gemini REST client (no SDK — same convention as the rest of app2:
Python 3.14 breaks the official google-generativeai SDK, so we call the REST
endpoints with `requests`).
"""
import os
import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class BudgetExceeded(RuntimeError):
    """The monthly Gemini budget is spent (or a person's daily cap is reached)."""


# The usage meter (ai_budget.Meter) is attached by the app at import time; every call goes
# through it: before_call(model) may raise BudgetExceeded, after_call records the tokens.
_meter = None


def set_meter(meter) -> None:
    global _meter
    _meter = meter


def gemini_available() -> bool:
    # Available if we can reach Gemini directly (key) OR via the egress proxy.
    # (Render's free-tier IP is blocked by Google, so prod routes through a
    #  small Vercel function set via GEMINI_PROXY_URL.)
    return bool((os.getenv("GEMINI_API_KEY") or "").strip()
                or (os.getenv("GEMINI_PROXY_URL") or "").strip())


# The egress proxy lives on the web app, so renaming its domain used to take every AI feature
# down until someone edited GEMINI_PROXY_URL. These are the project's own hosts: when the configured
# one answers «deployment not found» (404/410), the next is tried and the one that works is
# remembered for the rest of the process. Nothing else is ever called.
_PROXY_HOSTS = ("tamazight-drills.vercel.app", "tachelhit-drills.vercel.app", "amazigh-drills.vercel.app", "tamazigh-drills.vercel.app")
_proxy_ok: str | None = None


def _proxy_candidates() -> list:
    """The configured proxy URL first, then the same path on the project's other hosts."""
    import re as _re
    conf = (os.getenv("GEMINI_PROXY_URL") or "").strip()
    if not conf:
        return []
    if _proxy_ok:
        return [_proxy_ok] + [c for c in _candidates_from(conf) if c != _proxy_ok]
    return _candidates_from(conf)


def _candidates_from(conf: str) -> list:
    import re as _re
    m = _re.match(r"(https?://)([^/]+)(/.*)?$", conf)
    if not m:
        return [conf]
    scheme, host, path = m.group(1), m.group(2), m.group(3) or "/api/gemini"
    out = [conf]
    for h in _PROXY_HOSTS:
        if h != host:
            out.append(f"{scheme}{h}{path}")
    return out


def _generate_content(payload: dict, timeout: int, model: str | None = None) -> dict:
    """
    POST a generateContent payload to Gemini and return the parsed JSON.
    `model` overrides GEMINI_MODEL (e.g. the image model); the proxy forwards it as-is.
    If GEMINI_PROXY_URL is set, forward through that proxy (which holds the
    API key and calls Google from an un-blocked IP); otherwise call Google
    directly with GEMINI_API_KEY. Raises on non-200.
    """
    used_model = model or GEMINI_MODEL
    if _meter is not None:
        _meter.before_call(used_model)
    global _proxy_ok
    candidates = _proxy_candidates()
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    try:
        resp = None
        last = ""
        for i, proxy in enumerate(candidates):
            headers = {"Content-Type": "application/json"}
            secret = (os.getenv("GEMINI_PROXY_SECRET") or "").strip()
            if secret:
                headers["X-Proxy-Secret"] = secret
            try:
                r = requests.post(proxy, json={"model": used_model, "payload": payload}, headers=headers, timeout=timeout)
            except Exception as e:
                last = f"{proxy}: {e}"; continue
            # a proxy that is not deployed at this host: try the project's next host
            if r.status_code in (404, 410) or (r.status_code == 400 and "DEPLOYMENT_NOT_FOUND" in r.text):
                last = f"{proxy}: {r.status_code}"
                print(f"[GEMINI] proxy not found at {proxy}; trying the next host")
                continue
            resp = r
            if _proxy_ok != proxy:
                _proxy_ok = proxy
                print(f"[GEMINI] using the proxy at {proxy}")
            break
        if resp is None:
            # no proxy answered (or none configured): Google directly when we hold a key
            if not key:
                raise RuntimeError(f"No Gemini proxy reachable and GEMINI_API_KEY not configured ({last})")
            url = f"{GEMINI_BASE}/models/{used_model}:generateContent?key={key}"
            resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    except Exception:
        if _meter is not None:
            _meter.after_call(used_model, None, False)
        raise
    if _meter is not None:
        _meter.after_call(used_model, data, True)
    return data


def gemini_generate(system_instruction: str, contents: list, *,
                    max_output_tokens: int = 1024, temperature: float = 0.4,
                    thinking_budget: int = 0, timeout: int = 90) -> str:
    """
    Call Gemini generateContent.
    - system_instruction: persistent grounding/role text.
    - contents: [{"role": "user"|"model", "text": "..."}] conversation turns.
    Returns the model's text answer. Raises on API error.
    """
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
    try:
        data = _generate_content(payload, timeout)
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {str(data)[:300]}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            finish = candidates[0].get("finishReason", "?")
            raise RuntimeError(f"Gemini returned empty text (finishReason={finish})")
        return text
    except BudgetExceeded:
        # El nostre propi límit de despesa: aquest no es tomba canviant de proveïdor.
        raise
    except Exception as err:
        # Quan el que falla és el PROVEÏDOR i no la pregunta —sense crèdit, massa peticions,
        # la porta tancada— es prova el segon de la fila. El 24-10-2026 l'assistent de l'app
        # responia «Gemini API 402: Your prepayment credits are depleted» a tothom qui
        # preguntava què vol dir una frase, i qui obre l'app no ha de saber ni què és un
        # crèdit ni de qui és.
        #
        # Davant de qualsevol altre error NO es canvia: repetir una pregunta mal feta a un
        # altre model dona la mateixa resposta mal feta, i amaga l'errada de debò.
        import deepseek_client
        if not (deepseek_client.is_quota_error(err) and deepseek_client.deepseek_available()):
            raise
        print(f"[AI] Gemini no pot ({str(err)[:80]}); ho demano a DeepSeek")
        return deepseek_client.deepseek_generate(
            system_instruction, contents, max_output_tokens=max_output_tokens,
            temperature=temperature, timeout=timeout)


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
        cand = (_generate_content(payload, timeout).get("candidates") or [{}])[0]
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
