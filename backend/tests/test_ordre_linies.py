# -*- coding: utf-8 -*-
"""Which of the two subtitle lines is Tifinagh and which is Arabic, by the kind of character and not by position
(tools/snrt/fabrica/ordre_linies.py, #601). A historical Tamazight TV series has the Arabic on top.

Synthetic frames of both layouts: the Tifinagh line is drawn from the shipped glyph templates, the Arabic line is a stand-in
(joined sine-wave words with tall stems and dots, white with a dark border: what matters is that the words are long connected
components, like cursive). The real-frame check (150 «Illy» frames, normal and with the lines swapped) lives in the PR text.
"""
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


def tifinag_mask(text, top):
    P = PL.plantilles()
    parts, width = [], 0
    for ch in text:
        if ch == " ":
            width += 12
            continue
        m, dy = P[ch]
        parts.append((width, m, dy)); width += m.shape[1] + 4
    x0 = 964 - width // 2
    white = np.zeros((H, W), bool)
    for dx, m, dy in parts:
        y = top + dy
        white[y:y + m.shape[0], x0 + dx:x0 + dx + m.shape[1]] |= m
    return white


def arab_mask(top, seed=0):
    """Joined words: a wavy baseline 4 px thick, with an alef-like stem and dots; 41 px tall, centred at x=964, like the real Arabic line."""
    rng = np.random.default_rng(seed)
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    x = 964 - 480
    while x < 964 + 460:
        n = int(rng.integers(90, 190))
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


def frame(tif_top, arab_top, seed=0):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 3), np.float32) + np.array((110, 90, 85), np.float32) + rng.normal(0, 6, (H, W, 1))
    white = tifinag_mask(TIF, tif_top) | arab_mask(arab_top, seed)
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


def test_chapter_decision_and_geometry():
    for fabrica, esperat in ((normal_frame, "normal"), (inverted_frame, "invertit")):
        rs = [OL.ordre_del_fotograma(fabrica(s)[800:1040]) for s in range(6)]
        assert OL.decideix(rs) == esperat
    rs = [OL.ordre_del_fotograma(inverted_frame(s)[800:1040]) for s in range(6)]
    g = OL.geometria(rs, "invertit", 1080)
    # the Tifinagh body starts at 940 (1080p) = 626.7 (720p); the Arabic line starts at 884 = 589.3
    assert abs(g["tifinag_720"][0] + 800 * 2 / 3 - 626.7) < 4 and abs(g["arab_720"][0] + 800 * 2 / 3 - 589.3) < 4


def test_inverted_geometry_for_the_factory(monkeypatch):
    g = comu.geometria_de_linies((626.7, 645), (589.3, 616))
    assert g["TIFINAG_720"] == (619 - 0, 653)     # 8 px above the body, 34 px tall
    assert g["BANDA_720"][0] <= g["ARAB_720"][0] and g["BANDA_720"][1] >= g["TIFINAG_720"][1]
    monkeypatch.setattr(comu, "BANDA_720", comu.BANDA_720); monkeypatch.setattr(comu, "TIFINAG_720", comu.TIFINAG_720)
    monkeypatch.setattr(comu, "ARAB_720", comu.ARAB_720)
    comu.aplica_geometria(g)
    assert comu.TIFINAG_720 == g["TIFINAG_720"]


def test_default_geometry_is_what_the_stage_always_used():
    """For the standard layout the derived crops reproduce the constants of §4 (tifinag 588 -> 580-614)."""
    g = comu.geometria_de_linies((588, 610), (615, 652))
    assert g["TIFINAG_720"] == (580, 614) and g["ARAB_720"] == (612, 656)


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
