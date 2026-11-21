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

import json
import os

import requests

#: El comptador de despesa (`ai_budget.Meter`), el mateix que fa servir Gemini. L'enganxa l'app
#: en arrencar. Sense això, el que gasta DeepSeek no sortia a la factura de ningú.
_meter = None


def set_meter(meter) -> None:
    global _meter
    _meter = meter

BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

#: El model de xat de tota la vida. NO el de raonar.
#:
#: Amb `deepseek-flash` la reserva no escrivia res i produccio deia «DeepSeek returned empty
#: text» a cada lliçó. El motiu, mesurat: flash és un model que pensa abans de contestar, i el
#: que pensa surt per un camp a part (`reasoning_content`) pero es cobra del mateix sostre. Amb
#: max_tokens=1500 es gastava els 1.499 pensant, tornava `content: ""` i `finish_reason: length`.
#: El de xat contesta la mateixa pregunta amb 552 fitxes i sense pensar en veu alta.
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

#: Si algu torna a posar-hi un model que pensa, que almenys tingui lloc per contestar: el que
#: es demana es un sostre, i nomes es paga el que es genera.
THINKER_FLOOR = 6000
THINKERS = ("flash", "reasoner", "r1", "think")


def deepseek_available() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def _chat(body: dict, timeout: int) -> dict:
    """Una crida a `/chat/completions`, comptada pel mateix sostre de despesa que Gemini.

    El preu de DeepSeek no és a la taula d'`ai_budget`: s'hi aplica el preu de reserva, que és
    el de Gemini i és més car. Val més comptar de més que inventar-se una tarifa.
    """
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")
    used = body.get("model") or MODEL
    if _meter is not None:
        _meter.before_call(used)
    try:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"DeepSeek API {r.status_code}: {r.text[:300]}")
        data = r.json() or {}
    except Exception:
        if _meter is not None:
            _meter.after_call(used, None, False)
        raise
    if _meter is not None:
        _meter.after_call(used, data, True)
    return data


def deepseek_agent(system_instruction: str, contents: list, tools: list, executor,
                   *, max_rounds: int = 6, max_output_tokens: int = 1500,
                   temperature: float = 0.4, timeout: int = 90,
                   model: str | None = None) -> dict:
    """El copilot amb eines, contra DeepSeek. La mateixa forma que `gemini_agent`.

    L'amo (31-10): «vull que possis el copilot amb deepseek». El text ja hi anava quan Gemini
    es quedava sense crèdit, però les EINES no: el copilot és justament la part que en fa servir
    —cercar frases, obrir una unitat, proposar un canvi—, i sense elles no és el copilot.

    Les declaracions d'eina són les mateixes que les de Gemini (nom, descripció, esquema dels
    arguments); només canvia l'embolcall, perquè DeepSeek imita l'API d'OpenAI. Els arguments
    arriben com a text JSON i no com a objecte, i una resposta d'eina va en un torn propi amb
    el seu identificador.
    """
    messages = [{"role": "system", "content": system_instruction}]
    for c in contents:
        messages.append({"role": "assistant" if c.get("role") == "model" else "user",
                         "content": c.get("text", "")})
    oa_tools = [{"type": "function", "function": {
        "name": t.get("name", ""),
        "description": t.get("description", ""),
        "parameters": t.get("parameters") or {"type": "object", "properties": {}},
    }} for t in tools]

    used = model or MODEL
    room = max_output_tokens
    if any(t in used.lower() for t in THINKERS):
        room = max(room, THINKER_FLOOR)

    actions: list = []
    final_text = ""
    for _ in range(max_rounds):
        data = _chat({"model": used, "messages": messages, "tools": oa_tools,
                      "max_tokens": room, "temperature": temperature}, timeout)
        msg = ((data.get("choices") or [{}])[0].get("message")) or {}
        text = (msg.get("content") or "").strip()
        if text:
            final_text = text
        crides = msg.get("tool_calls") or []
        if not crides:
            break
        messages.append({"role": "assistant", "content": msg.get("content") or "",
                         "tool_calls": crides})
        for tc in crides:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {"valor": args}
            try:
                result = executor(name, args)
            except Exception as e:
                result = {"error": str(e)[:200]}
            actions.append({"name": name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.get("id") or name,
                             "content": json.dumps(result, ensure_ascii=False, default=str)[:4000]})
    return {"text": final_text, "actions": actions}


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
    used = model or MODEL
    room = max_output_tokens
    if any(t in used.lower() for t in THINKERS):
        room = max(room, THINKER_FLOOR)
    data = _chat({"model": used, "messages": messages,
                  "max_tokens": room, "temperature": temperature}, timeout)
    choices = data.get("choices") or []
    first = choices[0] if choices else {}
    text = (first.get("message", {}).get("content") or "").strip()
    if not text:
        # Dir QUE no ha contestat no serveix de res; cal dir PER QUE. El cas que ens va passar
        # es aquest: s'ha begut el sostre pensant i no ha arribat a escriure la resposta.
        spent = ((data.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
        why = f"{used} no ha contestat"
        if spent:
            why += f": s'ha gastat {spent} fitxes pensant i no n'hi ha quedat cap per escriure"
            why += f" (sostre {room}, final «{first.get('finish_reason')}»)"
        raise RuntimeError(why)
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
