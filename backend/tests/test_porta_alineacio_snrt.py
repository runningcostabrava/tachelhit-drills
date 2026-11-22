# -*- coding: utf-8 -*-
"""Porta d'alineació so<->text (tools/snrt/fabrica/porta_alineacio.py, #601): el ritme (cps) fora de la mediana del capítol,
els buits a les vores i els talls massa curts passen a «dubtosa»; el transcriptor només agafa els «ok»."""
import json
import os
import sys
import wave

import pytest

np = pytest.importorskip("numpy")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "snrt", "fabrica"))
sys.path.insert(0, os.path.join(ROOT, "tools", "lm"))
import porta_alineacio as pa  # noqa: E402


def escriu_wav(cami, segons, buit_ini=0.0, buit_fi=0.0):
    n = int(16000 * segons)
    a = (np.sin(np.arange(n) * 0.2) * 8000).astype(np.int16)
    a[:int(16000 * buit_ini)] = 0
    if buit_fi:
        a[-int(16000 * buit_fi):] = 0
    with wave.open(cami, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(a.tobytes())


def fila(i, t, ch):
    return {"id": i, "t_ini": 0, "t_fi": t, "tifinag": "\u2d30" * ch, "tall": "talls/%s.wav" % i}


def capitol(tmp_path, specs):
    os.makedirs(tmp_path / "talls")
    files = []
    for i, (t, ch, bi, bf) in enumerate(specs):
        escriu_wav(str(tmp_path / "talls" / ("r%d.wav" % i)), t + 0.5, bi, bf)
        files.append(fila("r%d" % i, t, ch))
    return files


def test_ritme_i_buit_i_curt(tmp_path):
    # ritme típic 8 cps: 5 talls normals, un massa lent (2 cps), un massa ràpid (16 cps), un amb 1,5 s de silenci, un amb 2 lletres
    specs = [(3, 24, 0, 0)] * 5 + [(4, 8, 0, 0), (3, 48, 0, 0), (3, 24, 1.5, 0), (3, 2, 0, 0)]
    files = capitol(tmp_path, specs)
    out, med = pa.porta_capitol(str(tmp_path), files)
    assert med == pytest.approx(8.0, abs=0.5)
    assert [out["r%d" % i]["v"] for i in range(5)] == ["ok"] * 5
    assert out["r5"]["v"] == "dubtosa" and out["r5"]["motius"][0].startswith("ritme")
    assert out["r6"]["v"] == "dubtosa"
    assert out["r7"]["motius"] == ["buit"]
    assert out["r8"]["motius"] == ["curt"]


def test_transcriptor_nomes_agafa_ok(tmp_path):
    import transcriptor_bucle as tb
    files = capitol(tmp_path, [(3, 24, 0, 0)] * 5 + [(4, 8, 0, 0)])
    out, med = pa.porta_capitol(str(tmp_path), files)
    pa.main_carpeta(str(tmp_path), files)
    assert tb.alineacio_ok({"id": "r0"}, str(tmp_path)) is True
    assert tb.alineacio_ok({"id": "r5"}, str(tmp_path)) is False
    assert tb.alineacio_ok({"id": "r0"}, str(tmp_path / "no_hi_es")) is False   # sense porta -> no apte
