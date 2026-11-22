# -*- coding: utf-8 -*-
"""The burned-in Arabic reader of the SNRT factory (tools/snrt/fabrica/lector_arab.py + 02_llegeix.py --lector-arab propi, #601).

No video and no weights are needed for most of this: a randomly initialised CRNN of the real architecture is written to a
temporary file to exercise loading, the cropping, the contract and the decoding; the stage-02 flow runs on a fake reader.
The CER figures (0.0074 on 100 hand-transcribed 1080p lines) need the real weights (TD_MODEL_ARAB) and are not asserted here, except by
the optional synthetic-line check at the bottom, which is skipped when the weights are absent.
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("scipy.ndimage")   # 02_llegeix.py importa scipy (eina de recerca, no del backend de Render)
from PIL import Image  # noqa: E402

FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import lector_arab as LA  # noqa: E402

SIGNES = list(" ابتثجحخدذرزسشصضطظعغفقكلمنهوي؟،")


@pytest.fixture()
def pes_aleatori(tmp_path, monkeypatch):
    torch.manual_seed(0)
    m = LA._classe_crnn()(len(SIGNES) + 1)
    p = tmp_path / "pes.pt"
    torch.save({"model": m.state_dict(), "signes": SIGNES, "alt": 64}, p)
    monkeypatch.setenv("TD_MODEL_ARAB", str(p))
    LA._model.clear()
    yield str(p)
    LA._model.clear()


def banda_amb_tinta(w=600, x0=200, x1=420):
    """Una banda 1450×64 de fons fosc amb una franja de píxels blancs entre vores fosques (com un text)."""
    a = np.full((64, 1450, 3), 40, np.uint8)
    for x in range(x0, x1, 8):
        a[14:50, x:x + 4] = 235
    return Image.fromarray(a)


def test_retall_ffmpeg_per_alcada_i_geometria():
    assert LA.retall_ffmpeg(1080) == "crop=1450:64:110:912"
    assert LA.retall_ffmpeg(720) == "crop=967:43:73:608"
    # geometria no estàndard (l'àrab a dalt, #601): la banda es desplaça 1,5 px de 1080p per cada px de 720p
    assert LA.retall_ffmpeg(1080, y0_720=600) == "crop=1450:64:110:894"
    # el retall no arriba al logotip de la dreta (x > 1560)
    assert LA.BANDA_X[1] == 1560 and 110 + 1450 == 1560


def test_a_banda_retalla_a_la_tinta_i_no_reescala():
    b = LA.a_banda(banda_amb_tinta())
    assert b.mode == "L" and b.height == 64
    assert 200 < b.width < 280            # 220 de tinta + 12 + 12 de marge, sense reescalar
    buida = LA.a_banda(Image.fromarray(np.full((64, 1450, 3), 30, np.uint8)))
    assert buida.size == (1450, 64)        # sense tinta no s'inventa cap retall


def test_a_banda_puja_un_retall_de_720p():
    petit = Image.fromarray(np.full((43, 967, 3), 30, np.uint8))
    assert LA.a_banda(petit).size == (1450, 64)


def test_llegeix_arab_contracte(pes_aleatori):
    r = LA.llegeix_arab(banda_amb_tinta())
    assert set(r) == {"arab", "conf", "conf_mitjana", "lector"}
    assert r["lector"] == LA.NOM == "crnn-v4"
    assert isinstance(r["arab"], str) and all(c in SIGNES for c in r["arab"])
    assert 0.0 <= r["conf"] <= r["conf_mitjana"] <= 1.0 or r["arab"] == ""
    assert r == LA.llegeix_arab(banda_amb_tinta())                      # determinista
    assert len(LA.llegeix_arabs([banda_amb_tinta(), banda_amb_tinta(x1=900)])) == 2   # amples diferents


def test_sense_pes_error_clar(tmp_path, monkeypatch):
    monkeypatch.setenv("TD_MODEL_ARAB", str(tmp_path / "no_hi_es.pt"))
    LA._model.clear()
    with pytest.raises(FileNotFoundError, match="TD_MODEL_ARAB"):
        LA.llegeix_arab(banda_amb_tinta())


def test_decideix():
    a = {"arab": "مرحبا بك", "conf": 0.95}
    b = {"arab": "مرحبا بك", "conf": 0.80}
    assert LA.decideix([a, b]) == ("مرحبا بك", 0.95, False, 2, 2)
    # dues lectures diferents: es queda la de més confiança i és dubtosa
    t, c, d, n, k = LA.decideix([a, {"arab": "مرحبا بكم", "conf": 0.70}])
    assert (t, d, n, k) == ("مرحبا بك", True, 2, 1)
    # una de buida: dubtosa
    assert LA.decideix([a, {"arab": "", "conf": 0.0}])[2:] == (True, 1, 1)
    # confiança baixa: dubtosa encara que només hi hagi una lectura
    assert LA.decideix([{"arab": "مرحبا بك", "conf": 0.55}])[2] is True
    # una sola lectura bona: no dubtosa
    assert LA.decideix([a])[2] is False
    # res: dubtosa i buida
    assert LA.decideix([{"arab": "", "conf": 0.0}]) == ("", 0.0, True, 0, 0)


def carrega_02():
    spec = importlib.util.spec_from_file_location("llegeix02", os.path.join(FABRICA, "02_llegeix.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_instants_del_tram():
    M = carrega_02()
    assert M.instants_del_tram([5]) == [5]
    assert M.instants_del_tram([5, 6]) == [6, 5]                 # mig = 6, un quart = 5
    assert M.instants_del_tram(list(range(10, 18))) == [14, 12]
    for t in ([3], [3, 4], [3, 4, 5], list(range(20, 29))):
        assert len(set(M.instants_del_tram(t))) == len(M.instants_del_tram(t)) and set(M.instants_del_tram(t)) <= set(t)


def test_ajunta_conserva_dubtos_i_pitjor_confiança():
    M = carrega_02()
    r1 = {"t_ini": 0, "t_fi": 3, "arab": "مرحبا بك يا صديقي", "arab_lectures": 2, "arab_dacord": 2, "arab_conf": 0.9, "arab_dubtos": False}
    r2 = {"t_ini": 3, "t_fi": 5, "arab": "مرحبا بك يا صديقي", "arab_lectures": 1, "arab_dacord": 1, "arab_conf": 0.4, "arab_dubtos": True}
    u = M.ajunta([r1, r2])
    assert len(u) == 1 and u[0]["arab_dubtos"] is True and u[0]["arab_conf"] == 0.4 and u[0]["t_fi"] == 5


def test_etapa_02_lector_propi_sense_visio(tmp_path, monkeypatch):
    """El flux de l'etapa amb un lector fals: cap crida de visió, lectures desades i represes, rèplica dubtosa quan els dos fotogrames discrepen."""
    M = carrega_02()
    lectures_fals = {10: ("مرحبا بك", 0.97), 12: ("مرحبا بك", 0.93),       # tram A: d'acord
                     20: ("كيف حالك اليوم", 0.55), 22: ("كيف حالك اليوم", 0.51),   # tram B: conf baixa
                     30: ("أنا بخير", 0.9), 32: ("انا بخبر", 0.9)}                  # tram C: discrepen
    crides = []

    class Fals:
        NOM = "crnn-v4"
        retall_ffmpeg = staticmethod(lambda alt, y0: "crop=1:1:0:0")
        carrega = staticmethod(lambda: None)
        decideix = staticmethod(LA.decideix)

        @staticmethod
        def llegeix_arab(im):
            t, c = im
            crides.append(t)
            return {"arab": t, "conf": c, "conf_mitjana": c, "lector": "crnn-v4"}
    monkeypatch.setitem(sys.modules, "lector_arab", Fals)
    monkeypatch.setattr(M, "fotograma_banda", lambda video, seg, alt, y0, lector: lectures_fals[seg])
    trams = [[9, 10, 11, 12, 13, 14, 15, 16][:8], [19, 20, 21, 22, 23], [29, 30, 31, 32, 33]]
    # instants dels trams amb els segons triats a mà: mig i un quart
    monkeypatch.setattr(M, "instants_del_tram", lambda t: {9: [10, 12], 19: [20, 22], 29: [30, 32]}[t[0]])
    carpeta = str(tmp_path)
    fora, c = M.llegeix_trams_propi(carpeta, trams, "v.mp4", 1080, 2, log=None)
    assert c["crides_visio"] == 0 and c["fitxes_visio"] == 0 and c["lector_arab"] == "crnn-v4"
    assert [(f["arab"], f["arab_dubtos"]) for f in fora] == [("مرحبا بك", False), ("كيف حالك اليوم", True), ("أنا بخير", True)]
    assert fora[0]["arab_lectures"] == 2 and fora[0]["arab_dacord"] == 2 and fora[2]["arab_dacord"] == 1
    desat = [json.loads(x) for x in open(os.path.join(carpeta, M.LECTURES_PROPI), encoding="utf-8")]
    assert sorted(x["segon"] for x in desat) == [10, 12, 20, 22, 30, 32] and all("conf" in x for x in desat)
    # reprendre no torna a llegir res
    n = len(crides)
    fora2, c2 = M.llegeix_trams_propi(carpeta, trams, "v.mp4", 1080, 2, log=None)
    assert len(crides) == n and c2["fotogrames_nous"] == 0 and [f["arab"] for f in fora2] == [f["arab"] for f in fora]


def _font_arab():
    for p in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return p
    return None


@pytest.mark.skipif(not os.path.exists(os.environ.get("TD_MODEL_ARAB", "")) or _font_arab() is None,
                    reason="cal TD_MODEL_ARAB (el .pt real, no és al repositori) i una font àrab del sistema")
def test_linia_sintetica_amb_el_pes_real():
    from PIL import ImageDraw, ImageFont, features
    if not features.check("raqm"):
        pytest.skip("PIL sense raqm: no es pot fer el shaping de l'àrab")
    LA._model.clear()
    f = ImageFont.truetype(_font_arab(), 36, layout_engine=ImageFont.Layout.RAQM)
    d = tot = 0
    for text in ("مرحبا بك يا صديقي", "كيف حالك اليوم", "هل تتذكر متى قلت ذلك؟"):
        im = Image.new("RGB", (1450, 64), (70, 60, 55))
        ImageDraw.Draw(im).text((900, 40), text, font=f, fill=(232, 228, 226), stroke_width=2, stroke_fill=(50, 45, 45), anchor="rs",
                                direction="rtl", language="ar")
        h = LA.llegeix_arab(im)["arab"]
        r, h = text.replace(" ", ""), h.replace(" ", "")
        ant = list(range(len(h) + 1))
        for i, ca in enumerate(r, 1):
            act = [i]
            for j, cb in enumerate(h, 1):
                act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
            ant = act
        d += ant[-1]
        tot += len(r)
    assert d / tot < 0.25, d / tot
