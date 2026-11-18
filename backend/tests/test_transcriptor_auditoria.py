# -*- coding: utf-8 -*-
"""tools/lm/transcriptor_auditoria.py (#601): chrF, tria de talls validats, cost, límit i full HTML. Sense xarxa: Gemini és un fals."""
import json
import os
import sys

import pytest

LM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "lm")
sys.path.insert(0, LM)
import transcriptor_auditoria as au  # noqa: E402
import transcriptor_bucle as tb  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_transcriptor_bucle import _capitol  # noqa: E402


def test_chrf_identic_zero_i_intermedi():
    assert au.chrf("bon dia a tothom", "bon dia a tothom") == pytest.approx(1.0)
    assert au.chrf("", "bon dia") == 0.0
    assert au.chrf("xyz", "bon dia") == 0.0
    assert 0 < au.chrf("bon dia a tots", "bon dia a tothom") < 1


def _arrel(tmp_path, n_caps):
    arrel = str(tmp_path / "tv")
    for k in range(n_caps):
        _capitol(arrel, f"cap{k}", 150)
    return arrel


def test_tria_reparteix_entre_capitols_i_es_reprodible(tmp_path):
    c = au.candidats(_arrel(tmp_path, 4), durada=(0, 99), conf=0)
    t = au.tria(c, n=20)
    assert len(t) == 20 and len({r["slug"] for r, _ in t}) == 4
    assert [r["id"] for r, _ in t] == [r["id"] for r, _ in au.tria(c, n=20)]
    assert [r["id"] for r, _ in au.tria(c, n=10)] == [r["id"] for r, _ in t][:10]    # el full és el principi de l'auditoria


def test_tria_falla_si_no_hi_ha_tres_capitols_validats(tmp_path):
    c = au.candidats(_arrel(tmp_path, 2), durada=(0, 99), conf=0)
    with pytest.raises(ValueError):
        au.tria(c, n=20)


def test_candidats_no_inclou_capitols_sense_intervals(tmp_path):
    arrel = _arrel(tmp_path, 3)
    _capitol(arrel, "vell", 150, intervals=False)
    assert "vell" not in {r["slug"] for r, _ in au.candidats(arrel, durada=(0, 99), conf=0)}


def _fals(text):
    def post(cos):
        assert b"inline_data" in cos
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(text)}]}}],
                "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 120}}
    return post


def test_audita_apunta_cost_i_chrf(tmp_path):
    c = au.candidats(_arrel(tmp_path, 3), durada=(0, 99), conf=0)
    t = au.tria(c, n=4)
    for r, _ in t:
        r["catala"] = "bon dia a tothom"
    res, cost = au.audita(t, "clau", post=_fals({"llengua": "amazic", "transcripcio": "x", "catala": "bon dia a tothom", "arab": "y", "segur": 0.9}))
    assert len(res) == 4 and cost == pytest.approx(sum(x["cost_eur"] for x in res), abs=1e-4) and cost < 0.01
    assert res[0]["chrf_gemini_vs_arab"] == 1.0
    s = au.resum(res)
    assert s["llengues"] == {"amazic": 4} and s["n"] == 4


def test_audita_s_atura_abans_del_limit(tmp_path):
    c = au.candidats(_arrel(tmp_path, 3), durada=(0, 99), conf=0)
    t = au.tria(c, n=10)
    res, cost = au.audita(t, "clau", post=_fals({"llengua": "amazic", "catala": "x"}), cost_max=0.0006)
    assert any(x.get("aturat") for x in res) and cost <= 0.0006


def test_resposta_que_no_es_json_no_trenca():
    resp, usage = au.crida(b"x", "k", post=lambda cos: {"candidates": [{"content": {"parts": [{"text": "no és json"}]}}], "usageMetadata": {"promptTokenCount": 5}})
    assert resp is None and usage["promptTokenCount"] == 5


def test_clau_no_va_ni_al_cos_ni_al_resultat(tmp_path):
    env = tmp_path / "e"
    env.write_text('X=1\nGEMINI_API_KEY="abc123"\n')
    assert au.clau_gemini(str(env)) == "abc123"
    assert b"abc123" not in json.dumps(au.cos_peticio(b"wav")).encode()


def test_full_html_es_autonom_i_escapa():
    h = au.full_html([{"id": "a_0001", "wav": b"RIFF", "tifinag": "ⴰⵣⵓⵍ <b>", "arab": "مرحبا", "catala": "hola & adéu"}])
    assert "data:audio/wav;base64," in h and "&lt;b&gt;" in h and "&amp;" in h and "concorda" in h and 'src="http' not in h
