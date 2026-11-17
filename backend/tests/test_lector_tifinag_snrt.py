# -*- coding: utf-8 -*-
"""The burned-in Tifinagh reader of the SNRT factory (tools/snrt/fabrica/lector_tifinag.py, #601).

No video or frame is needed: lines are drawn from the shipped glyph templates (white body, dark 2 px border, textured
background, centred at x=964 like the real subtitles) and read back. This exercises the segmenter (border test, merge of
stacked pieces, width limit, extent filter) and the template classifier together. The real-frame figure (CER 0.0051 on
52 hand-transcribed lines) is reproduced by tools/snrt/fabrica/prova_lector_tifinag.py when the frames are at hand.
"""
import os
import sys

import numpy as np
import pytest

# scipy no és a requirements.txt de Render (el lector de la fàbrica és una eina de recerca, no del backend): sense
# scipy aquestes proves se salten en comptes de trencar la CI.
ndimage = pytest.importorskip("scipy.ndimage")

FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import lector_tifinag as LT  # noqa: E402
import tifinag_plantilles as PL  # noqa: E402

BAND_H, BAND_W, BODY_TOP = 51, 1920, 14      # the 1080p band is rows 870..921; the body starts at row 884 = 14 in the band


def draw_band(text, bg=(120, 90, 80), seed=0):
    """A 1080p Tifinagh band: glyph templates with 4 px between letters, 16 px between words, centred at x=964."""
    P = PL.plantilles()
    rng = np.random.default_rng(seed)
    base = np.zeros((BAND_H, BAND_W, 3), np.float32) + np.array(bg, np.float32)
    base += rng.normal(0, 6, (BAND_H, BAND_W, 1))
    parts, width = [], 0
    for ch in text:
        if ch == " ":
            width += 16 - 4
            continue
        m, dy = P[ch]
        parts.append((width, m, dy)); width += m.shape[1] + 4
    x0 = 964 - width // 2
    white = np.zeros((BAND_H, BAND_W), bool)
    for dx, m, dy in parts:
        y = BODY_TOP + dy
        white[y:y + m.shape[0], x0 + dx:x0 + dx + m.shape[1]] |= m
    ring = ndimage.binary_dilation(white, iterations=2)
    img = base.copy()
    img[ring] = (60, 55, 55)
    img[white] = (225, 221, 218)
    img = ndimage.gaussian_filter(img, sigma=(0.5, 0.5, 0))
    return np.clip(img, 0, 255).astype(np.uint8)


LINES = [
    "ⵓⵟⵟⵓⵏ ⵉⴳⴳⵓⵜ ⵎⵉⵏⵣⵉ ⴰⵙⵏⴼⴰⵕ ⵉⵎⵇⵓⵔ ⴰⵡⴷ ⵏⵜⵜⴰ",
    "ⵢⴰⵀ, ⴰⵡⵙ ⵉⵢⵉ ⵉⵎⵉⴽ",
    "ⵎⴰⵏⵉ ⵏⴰⴱⵉⵍ ⵎⵏⵛⴽ ⴰⵢⴷ ⵓⵔ ⵜ ⵥⵕⵉⵖ ?",
    "ⴰⴷ ⵢⵉⵍⵉ ⵓⴼⵓⵍⴽⵉ, ⵖⴰⵙ ⵙⵓⵏⴼⵓ",
]


@pytest.mark.parametrize("text", LINES)
def test_reads_a_drawn_line_exactly(text):
    out = LT.llegeix_bandes([draw_band(text)], log=lambda s: None)[0]
    assert out["tifinag"] == text
    assert out["n_glifs"] == len([c for c in text if c != " "])


def test_contract_keys_and_name():
    out = LT.llegeix_bandes([draw_band(LINES[1]), None], log=lambda s: None)
    assert LT.NOM == "plantilles-segmentador-v1"
    for k in ("tifinag", "glifs", "n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"):
        assert k in out[0] and k in out[1]
    assert out[1] == {"tifinag": "", "glifs": [], "n_glifs": 0, "n_dubtosos": 0, "conf_mitjana": None, "conf_min": None}
    assert all(set(g) >= {"caixa", "etiqueta", "conf", "paraula"} for g in out[0]["glifs"])
    assert 0 < out[0]["conf_mitjana"] <= 1


def test_empty_band_has_no_text():
    flat = np.full((BAND_H, BAND_W, 3), 90, np.uint8)
    assert LT.llegeix_bandes([flat], log=lambda s: None)[0]["n_glifs"] == 0
    assert LT.segmenta(flat) == ([], None, None)


def test_light_background_reflection_is_not_text():
    """A bright patch with no dark border (a wall, a reflection) must not be read as letters next to a real line."""
    band = draw_band(LINES[1])
    band[10:45, 1500:1700] = 235
    out = LT.llegeix_bandes([band], log=lambda s: None)[0]
    assert out["tifinag"] == LINES[1]


def test_digits_are_read_as_digits():
    """Digits are not in the IRCAM font; they come from sans-serif templates 33 px tall (illy01_0283 reads « ... 80 ... »)."""
    out = LT.llegeix_bandes([draw_band("ⵜⵎⵉ 80 ⵙ")], log=lambda s: None)[0]
    assert "80" in out["tifinag"].replace(" ", "")


def test_segmenta_compat_for_the_clock():
    glifs, fila, H = LT.segmenta(draw_band(LINES[0]))
    assert len(glifs) == len(LINES[0].replace(" ", "")) and all("caixa" in g for g in glifs)
    assert fila[0] < 964 < fila[2] and H == 28.0
