# -*- coding: utf-8 -*-
"""Quan Gemini no pot, contesta DeepSeek — i només quan el problema és del proveïdor."""
import pytest

import deepseek_client
import gemini_client


def test_coneix_els_errors_que_son_del_proveidor():
    """Sense crèdit, massa peticions o la porta tancada: això es resol canviant de proveïdor."""
    for text in ("Gemini API 402: prepayment credits are depleted",
                 "HTTP 429 rate limit exceeded",
                 "RESOURCE_EXHAUSTED: quota",
                 "This authentication method does not have sufficient permissions"):
        assert deepseek_client.is_quota_error(RuntimeError(text)), text


def test_i_els_que_no_ho_son():
    """Una pregunta mal feta la contestarà igual de malament el segon model: no s'hi canvia."""
    for text in ("Gemini returned empty text (finishReason=SAFETY)",
                 "invalid argument: contents must not be empty",
                 "connection reset by peer"):
        assert not deepseek_client.is_quota_error(RuntimeError(text)), text


def test_sense_credit_a_gemini_contesta_deepseek(monkeypatch):
    """És el cas que va passar de debò: l'assistent de l'app responia «402» a tothom."""
    def sense_credit(payload, timeout, model=None):
        raise RuntimeError('Gemini API 402: {"error": {"message": "prepayment credits are depleted"}}')

    monkeypatch.setattr(gemini_client, "_generate_content", sense_credit)
    monkeypatch.setattr(deepseek_client, "deepseek_available", lambda: True)
    monkeypatch.setattr(deepseek_client, "deepseek_generate",
                        lambda system, contents, **kw: "ho diu DeepSeek")

    out = gemini_client.gemini_generate("ets un professor", [{"role": "user", "text": "hola"}])
    assert out == "ho diu DeepSeek"


def test_sense_deepseek_configurat_l_error_de_gemini_arriba_sencer(monkeypatch):
    """Si no hi ha segon, no s'amaga el primer: qui mira els registres ha de saber què passa."""
    def sense_credit(payload, timeout, model=None):
        raise RuntimeError("Gemini API 402: credits depleted")

    monkeypatch.setattr(gemini_client, "_generate_content", sense_credit)
    monkeypatch.setattr(deepseek_client, "deepseek_available", lambda: False)
    with pytest.raises(RuntimeError, match="402"):
        gemini_client.gemini_generate("ets un professor", [{"role": "user", "text": "hola"}])


def test_un_error_normal_no_es_torna_a_demanar(monkeypatch):
    """I una pregunta que Gemini rebutja per contingut no es passa al segon model."""
    def mal_feta(payload, timeout, model=None):
        raise RuntimeError("Gemini returned empty text (finishReason=SAFETY)")

    cridat = {"deepseek": False}

    def no_hi_hauria_de_ser(*a, **k):
        cridat["deepseek"] = True
        return "no"

    monkeypatch.setattr(gemini_client, "_generate_content", mal_feta)
    monkeypatch.setattr(deepseek_client, "deepseek_available", lambda: True)
    monkeypatch.setattr(deepseek_client, "deepseek_generate", no_hi_hauria_de_ser)
    with pytest.raises(RuntimeError, match="SAFETY"):
        gemini_client.gemini_generate("ets un professor", [{"role": "user", "text": "hola"}])
    assert not cridat["deepseek"]
