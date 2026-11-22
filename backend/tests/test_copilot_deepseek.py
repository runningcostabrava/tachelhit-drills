"""El copilot amb DeepSeek (#550).

L'amo: «vull que possis el copilot amb deepseek». El text ja hi anava quan Gemini es quedava
sense crèdit, però les EINES no, i el copilot és justament la part que en fa servir. Aquí es
comprova la forma de la conversa amb eines —que és on els dos proveïdors no s'assemblen— sense
trucar enlloc.
"""
import json

import deepseek_client
import gemini_client


class _Resposta:
    def __init__(self, cos):
        self.status_code = 200
        self._cos = cos
        self.text = json.dumps(cos)

    def json(self):
        return self._cos


def _missatge(content=None, tool_calls=None):
    m = {"content": content}
    if tool_calls:
        m["tool_calls"] = tool_calls
    return {"choices": [{"message": m}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


def test_el_copilot_crida_una_eina_i_contesta_amb_el_resultat(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "prova")
    enviats = []
    tandes = [
        _missatge(tool_calls=[{"id": "c1", "type": "function",
                               "function": {"name": "cerca", "arguments": '{"q": "pa"}'}}]),
        _missatge(content="N'he trobada una: aɣrum."),
    ]

    def fals_post(url, headers=None, json=None, timeout=None):
        enviats.append(json)
        return _Resposta(tandes[len(enviats) - 1])

    monkeypatch.setattr(deepseek_client.requests, "post", fals_post)

    fetes = []

    def executor(nom, args):
        fetes.append((nom, args))
        return {"drills": [{"id": 1, "shi": "aɣrum"}]}

    out = deepseek_client.deepseek_agent(
        "ets el copilot", [{"role": "user", "text": "busca pa"}],
        [{"name": "cerca", "description": "cerca frases",
          "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}],
        executor)

    assert out["text"] == "N'he trobada una: aɣrum."
    assert fetes == [("cerca", {"q": "pa"})], "els arguments arriben com a text JSON i cal obrir-los"
    assert [a["name"] for a in out["actions"]] == ["cerca"]

    # L'eina s'envia amb l'embolcall d'OpenAI, que és el que DeepSeek entén.
    assert enviats[0]["tools"][0]["type"] == "function"
    assert enviats[0]["tools"][0]["function"]["name"] == "cerca"
    # I el resultat torna en un torn propi, lligat per l'identificador de la crida.
    torns = enviats[1]["messages"]
    assert torns[-1]["role"] == "tool" and torns[-1]["tool_call_id"] == "c1"
    assert "aɣrum" in torns[-1]["content"]


def test_una_eina_que_peta_no_tomba_la_conversa(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "prova")
    tandes = [
        _missatge(tool_calls=[{"id": "c1", "type": "function",
                               "function": {"name": "cerca", "arguments": "no és json"}}]),
        _missatge(content="No ho he pogut mirar."),
    ]
    n = {"i": 0}

    def fals_post(url, headers=None, json=None, timeout=None):
        n["i"] += 1
        return _Resposta(tandes[n["i"] - 1])

    monkeypatch.setattr(deepseek_client.requests, "post", fals_post)

    def executor(nom, args):
        raise RuntimeError("s'ha trencat")

    out = deepseek_client.deepseek_agent("x", [{"role": "user", "text": "y"}],
                                         [{"name": "cerca"}], executor)
    assert out["text"] == "No ho he pogut mirar."
    assert "error" in out["actions"][0]["result"], "l'error de l'eina torna al model, no a l'usuari"


def test_qui_fa_anar_el_copilot(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "prova")
    assert gemini_client.agent_provider() == "deepseek", "amb clau, el copilot va amb DeepSeek"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert gemini_client.agent_provider() == "gemini", "sense clau, es queda com estava"
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "prova")
    assert gemini_client.agent_provider() == "gemini", "es pot tornar enrere sense tocar codi"


def test_el_comptador_sap_llegir_les_fitxes_de_deepseek():
    import ai_budget
    u = ai_budget.usage_from_response({"usage": {"prompt_tokens": 120, "completion_tokens": 30}})
    assert u == {"prompt_tokens": 120, "output_tokens": 30, "images": 0}
    # I la de Gemini segueix igual.
    g = ai_budget.usage_from_response({"usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3}})
    assert g["prompt_tokens"] == 7 and g["output_tokens"] == 3
