# -*- coding: utf-8 -*-
"""tools/snrt/fabrica/nit.py (#601): un capítol fet «sense àrab» es refà per llegir l'àrab (i les etapes següents es repassen), i la baixada
va pel replay directe de forja.ma. Sense vídeo ni xarxa: les etapes són un `subprocess.run` fals."""
import argparse
import os
import sys

import pytest

pytest.importorskip("scipy.ndimage")
FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import comu  # noqa: E402
import nit  # noqa: E402


def _args(**k):
    return argparse.Namespace(**{"refes": False, "fils": 2, "un_per_segon": False, "lector_arab": "propi", **k})


def _simula(monkeypatch, tmp_path, estat):
    """Estat del capítol = `estat`; torna la llista de les etapes que s'han executat."""
    executades = []
    monkeypatch.setattr(comu, "etapa_feta", lambda c, e: e in estat)
    monkeypatch.setattr(comu, "estat_llegeix", lambda c: estat)

    class R:
        returncode = 0
    monkeypatch.setattr(nit.subprocess, "run", lambda cmd, *a, **k: (executades.append(os.path.basename(cmd[3])), R())[1])
    return executades


def test_capitol_fet_sense_arab_refa_02_i_repassa_les_seguents(monkeypatch, tmp_path):
    estat = {e: {"comptes": {}} for e in nit.ETAPES}
    estat["02_llegeix"]["comptes"] = {"sense_arab": True}
    fetes = _simula(monkeypatch, tmp_path, estat)
    be, motiu = nit.corre(str(tmp_path), _args(), None)
    assert be and not motiu
    assert fetes == ["02_llegeix.py", "03_talla.py", "04_tradueix.py", "05_informe.py"]


def test_capitol_fet_amb_arab_no_es_refa(monkeypatch, tmp_path):
    estat = {e: {"comptes": {}} for e in nit.ETAPES}
    fetes = _simula(monkeypatch, tmp_path, estat)
    nit.corre(str(tmp_path), _args(), None)
    assert fetes == []


def test_etapa_pendent_nomes_repassa_les_seguents(monkeypatch, tmp_path):
    estat = {"02_llegeix": {"comptes": {}}}
    fetes = _simula(monkeypatch, tmp_path, estat)
    nit.corre(str(tmp_path), _args(), None)
    assert fetes == ["03_talla.py", "04_tradueix.py", "05_informe.py"]


def test_la_fitxa_porta_la_url_de_forja_i_la_baixada_la_fa_servir(monkeypatch, tmp_path):
    f = nit.fitxa({"slug_forja": "abc", "url_snrt": "https://www.snrt.ma/fr/x", "youtube_id": "yt", "programa": "p", "qualitats_replay": ["1920x1080"]})
    assert f["forja"] == "https://forja.ma/player/abc?lang=ar" and f["programa"] == "p"
    crides = []
    monkeypatch.setattr(nit.subprocess, "run", lambda cmd, *a, **k: (crides.append(cmd), type("R", (), {"returncode": 1})())[1])
    monkeypatch.setattr(nit, "te_video", lambda c: False)
    assert nit.baixa(f, str(tmp_path), None, amb_1080=False) is False
    assert any("forja.ma/player/abc" in " ".join(map(str, c)) for c in crides)       # replay directe de forja.ma
    assert not any("yt_dlp" in " ".join(map(str, c)) for c in crides)               # mai YouTube (IP bloquejada a l'ECS)
