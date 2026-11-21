# -*- coding: utf-8 -*-
"""La fàbrica no baixa res si el disc va just (tools/snrt/fabrica/nit.py, #729).

El 21-11 el disc de l'ECS es va omplir del tot i la fàbrica va petar amb «No space left on
device», i va estar una hora aturada sense que ningú ho sabés. El supervisor té guàrdia de
disc però mira cada 15 minuts, i entremig `nit.py` baixa sis capítols alhora i **dos vídeos
de cadascun**. La guàrdia ha de ser on es baixa.

El que es comprova aquí: que no baixa amb poc espai, que **deixa el capítol pendent i no en
error**, i que amb espai de sobres no molesta.
"""
import os
import sys
import types

import pytest

FABRICA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import nit  # noqa: E402


def _disc(gb):
    """Un `disk_usage` fals que diu que queden `gb` lliures."""
    return lambda _c: types.SimpleNamespace(total=int(100e9), used=0, free=int(gb * 1e9))


def test_prou_espai_diu_que_si_quan_nhi_ha(monkeypatch):
    monkeypatch.setattr(nit.shutil if hasattr(nit, "shutil") else os, "disk_usage",
                        _disc(50), raising=False)
    import shutil
    monkeypatch.setattr(shutil, "disk_usage", _disc(50))
    assert nit.prou_espai(15) is True


def test_prou_espai_diu_que_no_quan_falta(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "disk_usage", _disc(3))
    assert nit.prou_espai(15) is False


def test_amb_el_disc_just_no_baixa_i_no_es_un_error(monkeypatch, tmp_path):
    """La clau: torna False sense haver intentat baixar.

    Tornar False deixa el capítol **pendent**, no en error: es tornarà a provar quan hi hagi
    lloc. Si baixés i fallés a mitges, quedaria un fitxer trencat i el capítol en error.
    """
    import shutil
    monkeypatch.setattr(shutil, "disk_usage", _disc(2))

    cridat = []
    monkeypatch.setattr(nit.subprocess, "run",
                        lambda *a, **k: cridat.append(a) or types.SimpleNamespace(returncode=0))
    monkeypatch.setattr(nit, "te_video", lambda _c: False)

    fora = []
    monkeypatch.setattr(nit.comu, "diu", lambda log, m: fora.append(m))

    be = nit.baixa({"font": "replay", "url": "https://exemple/x", "forja": None,
                    "youtube": None, "te_1080": True}, str(tmp_path), None)

    assert be is False, "amb el disc just ha de tornar False"
    assert not cridat, "no ha d'haver intentat baixar res"
    assert any("GB" in m for m in fora), f"ha de dir per què: {fora}"


def test_el_1080p_se_salta_abans_que_el_720p(monkeypatch, tmp_path):
    """El 1080p és opcional —sense ell el tifinag es llegeix a 720p— i per això demana més
    marge. Amb 20 GB s'ha de baixar el 720p i saltar el 1080p."""
    import shutil
    monkeypatch.setattr(shutil, "disk_usage", _disc(20))
    assert nit.MIN_GB < 20 < nit.MIN_GB_1080, (
        f"la prova dona per fet {nit.MIN_GB} < 20 < {nit.MIN_GB_1080}")

    monkeypatch.setattr(nit, "te_video", lambda _c: True)   # el 720p ja hi és
    fora = []
    monkeypatch.setattr(nit.comu, "diu", lambda log, m: fora.append(m))
    cridat = []
    monkeypatch.setattr(nit.subprocess, "run",
                        lambda *a, **k: cridat.append(a) or types.SimpleNamespace(returncode=1))

    nit.baixa({"font": "replay", "url": "u", "forja": None, "youtube": None,
               "te_1080": True}, str(tmp_path), None, amb_1080=True)

    assert any("1080" in m and "salto" in m for m in fora), f"havia de saltar el 1080p: {fora}"
