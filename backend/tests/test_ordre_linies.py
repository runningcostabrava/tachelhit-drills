# -*- coding: utf-8 -*-
"""Which of the two subtitle lines is Tifinagh and which is Arabic, by the kind of character and not by position
(tools/snrt/fabrica/ordre_linies.py, #601). A historical Tamazight TV series has the Arabic on top.

Synthetic frames of both layouts: the Tifinagh line is drawn from the shipped glyph templates, the Arabic line is a stand-in
(joined sine-wave words with tall stems and dots, white with a dark border: what matters is that the words are long connected
components, like cursive). The real-frame check (150 «Illy» frames, normal and with the lines swapped) lives in the PR text.
"""
import io
import os
import sys

import numpy as np
import pytest

ndimage = pytest.importorskip("scipy.ndimage")     # scipy is not in Render's requirements.txt: skip instead of breaking CI
from PIL import Image, ImageDraw  # noqa: E402

FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import comu  # noqa: E402
import ordre_linies as OL  # noqa: E402
import tifinag_plantilles as PL  # noqa: E402

W, H = 1920, 1080
TIF = "ⵓⵟⵟⵓⵏ ⵉⴳⴳⵓⵜ ⵎⵉⵏⵣⵉ ⴰⵙⵏⴼⴰⵕ ⵉⵎⵇⵓⵔ ⴰⵡⴷ ⵏⵜⵜⴰ"


def tifinag_mask(text, top, x0=None):
    """The glyphs of `text` from the shipped templates, with their body on row `top`; centred at x=964 unless `x0` says where to start."""
    P = PL.plantilles()
    parts, width = [], 0
    for ch in text:
        if ch == " ":
            width += 12
            continue
        m, dy = P[ch]
        parts.append((width, m, dy)); width += m.shape[1] + 4
    x0 = 964 - width // 2 if x0 is None else x0
    white = np.zeros((H, W), bool)
    for dx, m, dy in parts:
        y = top + dy
        white[y:y + m.shape[0], x0 + dx:x0 + dx + m.shape[1]] |= m
    return white


def arab_mask(top, seed=0, xa=964 - 480, xb=964 + 460, mot=(90, 190)):
    """Joined words: a wavy baseline 4 px thick, with an alef-like stem and dots; 41 px tall, from `xa` to `xb` (by default centred at x=964, like the real Arabic line)."""
    rng = np.random.default_rng(seed)
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    x = xa
    while x < xb:
        n = int(rng.integers(*mot))
        pts = [(x + i, top + 24 + 5 * np.sin(i / 7.0 + rng.uniform(0, 1))) for i in range(0, n, 2)]
        d.line(pts, fill=255, width=4)
        for _ in range(int(rng.integers(1, 4))):
            sx = x + int(rng.integers(8, n - 8))
            d.line([(sx, top + 24), (sx, top + 2)], fill=255, width=4)           # tall stem
        for _ in range(int(rng.integers(1, 3))):
            dx = x + int(rng.integers(10, n - 10)); dy = top + int(rng.choice([6, 38]))
            d.ellipse([dx - 3, dy - 3, dx + 3, dy + 3], fill=255)                # dots
        x += n + 22
    return np.asarray(im) > 0


LOGO_X0, LOGO_X1 = 1686, 1812      # the channel's logo, measured on the Tamazight TV frames: always these columns, 1080p
LOGO_TIF = "ⵜⴰⴷⴼ"                  # the logo is a stacked block of Tifinagh over Arabic (ⵜⴰⴷⴼⵉ ⵏ ⵜⵙⴽⵍⴰ / تاصفي ن تسكلا)


def logo_mask(tif_top, arab_top, seed=0):
    """The channel's logo in the right-hand corner, at the height of the subtitle lines: a Tifinagh word over an Arabic one.
    The glyphs are at subtitle size (the templates are not scaled), which makes it the most confusable corner possible."""
    return (tifinag_mask(LOGO_TIF, tif_top, x0=LOGO_X0)
            | arab_mask(arab_top, seed + 7, xa=LOGO_X0, xb=LOGO_X1, mot=(30, 55)))


def frame(tif_top, arab_top, seed=0, logo=False, subtitol=True):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 3), np.float32) + np.array((110, 90, 85), np.float32) + rng.normal(0, 6, (H, W, 1))
    white = np.zeros((H, W), bool)
    if subtitol:
        white |= tifinag_mask(TIF, tif_top) | arab_mask(arab_top, seed)
    if logo:
        white |= logo_mask(884, 924, seed)          # the logo does not move with the subtitle: it is always at the same rows
    ring = ndimage.binary_dilation(white, iterations=2)
    img[ring] = (60, 55, 55)
    img[white] = (225, 221, 218)
    img = ndimage.gaussian_filter(img, sigma=(0.5, 0.5, 0))
    return np.clip(img, 0, 255).astype(np.uint8)


def normal_frame(seed=0):      # tifinag body 884-910, Arabic 924-964: «Illy» and the interview
    return frame(884, 924, seed)


def inverted_frame(seed=0):    # Arabic on top (884-925), Tifinagh below (body 940-966)
    return frame(940, 884, seed)


def test_one_frame_each_layout():
    n = OL.ordre_del_fotograma(normal_frame()[800:1040])
    i = OL.ordre_del_fotograma(inverted_frame()[800:1040])
    assert n["ordre"] == "normal" and n["marge"] >= OL.MARGE_FOTOGRAMA
    assert i["ordre"] == "invertit" and i["marge"] >= OL.MARGE_FOTOGRAMA


def _rs(fabrica, n=6, y0=800):
    out = []
    for sd in range(n):
        r = OL.ordre_del_fotograma(fabrica(sd)[y0:1040])
        r["trams_1080"] = [(t0 + y0, t1 + y0) for t0, t1 in r["trams_1080"]]
        r["cos_1080"] = [(t0 + y0, t1 + y0) for t0, t1 in r["cos_1080"]]
        out.append(r)
    return out


def test_chapter_decision():
    for fabrica, esperat in ((normal_frame, "normal"), (inverted_frame, "invertit")):
        assert OL.decideix(_rs(fabrica)) == esperat


def test_standard_chapter_keeps_the_constants():
    """The standard layout (body at 884) must give back EXACTLY the constants the stage always used: same crops, same band."""
    rs = _rs(normal_frame)
    g = OL.geometria(rs, "normal")
    assert abs(g["cos_tifinag_1080"][0] - 884) <= 1
    G = comu.geometria_de_linies(g["cos_tifinag_1080"], g["arab_1080"])
    assert G["estandard"] is True
    assert (G["BANDA_720"], G["TIFINAG_720"], G["ARAB_720"]) == ((576, 660), (580, 614), (612, 656))


def shifted_frame(seed=0):     # same order, whole block 9 px higher (a real chapter, «caxy…»): body at 875, Arabic at 915
    return frame(875, 915, seed)


def test_shifted_chapter_gets_its_own_geometry_and_reads_well():
    """A chapter whose lines sit 9 px higher than the standard: the standard crop (870-921) cuts the Tifinagh so the reader keeps nothing;
    the crop derived from the measured geometry reads the line."""
    import lector_tifinag as LT
    rs = _rs(shifted_frame)
    assert OL.decideix(rs) == "normal"
    g = OL.geometria(rs, "normal")
    assert abs(g["cos_tifinag_1080"][0] - 875) <= 1.5
    G = comu.geometria_de_linies(g["cos_tifinag_1080"], g["arab_1080"])
    assert G["estandard"] is False and G["TIFINAG_720"][0] < 580
    f = shifted_frame()
    estandard = LT.llegeix_banda(f[870:921])
    dinamica = LT.llegeix_banda(f[round(G["TIFINAG_720"][0] * 1.5):round(G["TIFINAG_720"][1] * 1.5)])
    assert dinamica["tifinag"] == TIF
    assert estandard["tifinag"] != TIF
    assert G["BANDA_720"][0] == min(G["TIFINAG_720"][0], G["ARAB_720"][0]) - 4      # the band covers both lines


def test_inverted_chapter_geometry():
    g = OL.geometria(_rs(inverted_frame), "invertit")
    G = comu.geometria_de_linies(g["cos_tifinag_1080"], g["arab_1080"])
    assert G["estandard"] is False
    assert abs(g["cos_tifinag_1080"][0] - 940) <= 1.5 and abs(g["arab_1080"][0] - 884) <= 4      # Arabic above, Tifinagh below
    assert G["TIFINAG_720"][0] > G["ARAB_720"][0]


def test_geometry_json_roundtrip(tmp_path, monkeypatch):
    for k in ("BANDA_720", "TIFINAG_720", "ARAB_720"):
        monkeypatch.setattr(comu, k, getattr(comu, k))
    G = comu.geometria_de_linies((876.0, 905.0), (932.0, 972.0))
    comu.desa_geometria(str(tmp_path), dict(G, ordre="normal"))
    comu.aplica_geometria({"BANDA_720": (576, 660), "TIFINAG_720": (580, 614), "ARAB_720": (612, 656)})
    assert comu.carrega_geometria(str(tmp_path)) is True
    assert comu.TIFINAG_720 == tuple(G["TIFINAG_720"])


def test_stage_02_regenerates_bands_cut_with_another_geometry(tmp_path, monkeypatch):
    """Bands extracted with the old standard geometry (no marker) are thrown away, with the arab readings derived from them, when the chapter has another geometry."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("llegeix02", os.path.join(FABRICA, "02_llegeix.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    fr = tmp_path / "franges"; fr.mkdir()
    for i in range(1, 6):
        (fr / f"{i:05d}.png").write_bytes(b"x")
    (tmp_path / "lectures.jsonl").write_text("{}")
    monkeypatch.setattr(comu, "BANDA_720", (561, 660))
    chamades = []
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: chamades.append(a))
    m.treu_franges("v.mp4", str(tmp_path), 1280, 720, 5.0, io.StringIO())
    assert chamades and not (tmp_path / "lectures.jsonl").exists() and not (fr / "00001.png").exists()
    assert (fr / "_banda.json").exists()
    # with the standard geometry the existing bands are kept
    fr2 = tmp_path / "b" / "franges"; fr2.mkdir(parents=True)
    for i in range(1, 6):
        (fr2 / f"{i:05d}.png").write_bytes(b"x")
    monkeypatch.setattr(comu, "BANDA_720", (576, 660)); chamades.clear()
    assert m.treu_franges("v.mp4", str(tmp_path / "b"), 1280, 720, 5.0, io.StringIO()) == 5 and not chamades


def test_the_logo_alone_does_not_vote():
    """#721: half of a «nkkni-didk» episode runs with no subtitle, and then the only text in the band is the channel's logo —
    a stacked Tifinagh-over-Arabic block in the corner. There is nothing to decide, so the frame must not vote."""
    assert OL.ordre_del_fotograma(frame(884, 924, logo=True, subtitol=False)[800:1040]) is None


def test_the_logo_does_not_touch_the_vote_of_a_frame_with_a_subtitle():
    """#721: the logo sits at the same rows as the two subtitle lines, so its ink joined their runs and poisoned both scores.
    The same frame with and without the logo must vote the same, with the same lines and the same margin."""
    for fabrica, esperat in ((normal_frame, "normal"), (inverted_frame, "invertit")):
        tops = (884, 924) if esperat == "normal" else (940, 884)
        net = OL.ordre_del_fotograma(fabrica()[800:1040])
        amb = OL.ordre_del_fotograma(frame(*tops, logo=True)[800:1040])
        assert net["ordre"] == esperat
        assert amb["ordre"] == esperat and amb["marge"] >= OL.MARGE_FOTOGRAMA
        assert amb["trams_1080"] == net["trams_1080"] and amb["cos_1080"] == net["cos_1080"]
        assert abs(amb["marge"] - net["marge"]) < 0.05


def test_an_episode_half_without_subtitle_still_decides():
    """#721: six frames with a subtitle and six with only the logo. The six mute ones must add nothing, and the chapter decides
    on the six that say something — which is what the 70 % majority is for."""
    rs = [OL.ordre_del_fotograma(frame(884, 924, sd, logo=True)[800:1040]) for sd in range(6)]
    rs += [OL.ordre_del_fotograma(frame(884, 924, sd, logo=True, subtitol=False)[800:1040]) for sd in range(6)]
    assert OL.decideix(rs) == "normal"


def test_stops_with_a_clear_error_when_it_cannot_decide():
    # only one line (no subtitle with two lines): nothing informative
    solo = normal_frame()[800:1040].copy()
    solo[110:170] = 110
    rs = [OL.ordre_del_fotograma(solo) for _ in range(8)]
    with pytest.raises(OL.OrdreIndecis, match="no puc saber"):
        OL.decideix(rs)
    # a split vote: half the frames say one thing, half the other
    mixt = [OL.ordre_del_fotograma(normal_frame(s)[800:1040]) for s in range(4)] + [OL.ordre_del_fotograma(inverted_frame(s)[800:1040]) for s in range(4)]
    with pytest.raises(OL.OrdreIndecis):
        OL.decideix(mixt)
