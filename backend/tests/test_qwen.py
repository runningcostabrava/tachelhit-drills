# -*- coding: utf-8 -*-
"""El client de Qwen (Model Studio): mateixa forma que el de DeepSeek, raonament apagat, i que
digui que no ha contestat en comptes de tornar buit."""
import json

import pytest

import qwen_client


class _Resposta:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._p


def _prepara(monkeypatch, resposta, captura):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-ws-prova")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://ws-prova.example/compatible-mode/v1")

    def post(url, headers=None, json=None, timeout=None):
        captura["url"] = url
        captura["body"] = json
        captura["auth"] = headers.get("Authorization")
        return resposta

    monkeypatch.setattr(qwen_client.requests, "post", post)


def test_tradueix_els_torns_i_apaga_el_raonament(monkeypatch):
    captura = {}
    _prepara(monkeypatch, _Resposta(200, {"choices": [{"message": {"content": "  Doneu-me la meva part.\n"}}]}), captura)
    text = qwen_client.qwen_generate("Ets traductor.", [{"role": "user", "text": "ⴼⴽⴰⵜ ⵉⵢⵉ ⴰⵎⵓⵔ ⵉⵏⵓ."},
                                                         {"role": "model", "text": "?"}, {"role": "user", "text": "segur"}],
                                     max_output_tokens=200, temperature=0)
    assert text == "Doneu-me la meva part."
    assert captura["url"].endswith("/compatible-mode/v1/chat/completions")
    assert captura["auth"] == "Bearer sk-ws-prova"
    b = captura["body"]
    assert b["model"] == "qwen3.8-max" and b["enable_thinking"] is False
    assert [m["role"] for m in b["messages"]] == ["system", "user", "assistant", "user"]
    assert b["max_tokens"] == 200 and b["temperature"] == 0


def test_sense_clau_o_sense_punt_dacces_no_esta_disponible(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://ws-prova.example/compatible-mode/v1")
    assert not qwen_client.qwen_available()
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-ws-prova")
    monkeypatch.delenv("DASHSCOPE_BASE_URL", raising=False)
    assert not qwen_client.qwen_available()
    with pytest.raises(RuntimeError, match="not configured"):
        qwen_client.qwen_generate("x", [{"role": "user", "text": "y"}])


def test_una_resposta_buida_es_un_error_que_diu_per_que(monkeypatch):
    captura = {}
    _prepara(monkeypatch, _Resposta(200, {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}), captura)
    with pytest.raises(RuntimeError, match="no ha contestat.*length"):
        qwen_client.qwen_generate("x", [{"role": "user", "text": "y"}])


def test_un_error_del_servidor_porta_el_codi(monkeypatch):
    captura = {}
    _prepara(monkeypatch, _Resposta(403, {"error": {"message": "Workspace endpoint access denied."}}), captura)
    with pytest.raises(RuntimeError, match="Qwen API 403"):
        qwen_client.qwen_generate("x", [{"role": "user", "text": "y"}])
