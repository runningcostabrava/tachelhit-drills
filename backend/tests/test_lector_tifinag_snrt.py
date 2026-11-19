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
    P = dict(PL.plantilles())
    z = np.load(PL.XIFRES_NPZ, allow_pickle=True)
    for d, m, real in zip(z["digit"], z["mask"], z["real"]):     # real SNRT digits (8, 0 from «Illy»; 2, 0, 6 from the interview), 4 px above the body
        if real and str(d) not in P:
            P[str(d)] = (m.astype(bool), -4)
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
    """Digits are not in the IRCAM font and sit at different heights in different videos: they are matched by shape against real SNRT glyphs.
    In-sample by construction (the templates come from these very glyphs): it guards the plumbing, not the generalisation. 1 3 4 5 7 9 are unverified."""
    out = LT.llegeix_bandes([draw_band("ⵜⵎⵉ 2026 ⵙ")], log=lambda s: None)[0]
    assert "2026" in out["tifinag"]          # one number, no spaces inside


def test_segmenta_compat_for_the_clock():
    glifs, fila, H = LT.segmenta(draw_band(LINES[0]))
    assert len(glifs) == len(LINES[0].replace(" ", "")) and all("caixa" in g for g in glifs)
    assert fila[0] < 964 < fila[2] and H == 28.0


# --- el desempat per topologia (#699) ---------------------------------------------------------

def test_les_lletres_cercle_tenen_firma_topologica_propia():
    """Sis lletres son la mateixa anella amb una marca diferent a dins i l'IoU no les separa.

    Mesurat sobre les plantilles d'aquest repositori: ⵔ/ⵙ se solapen 0,83 i ⵔ/ⵕ 0,88, o sigui
    que la forma global no decideix; a `tskla` el lector triava ⵀ sobre ⵙ per 0,03. El desempat
    es recolza en una propietat que s'ha de mantenir: comptant trossos de tinta i forats,
    aquestes quatre lletres tenen firma UNICA. Si algu canvia les plantilles i la perd, el
    desempat deixa de funcionar en silenci, i per aixo es prova aqui.
    """
    taula = PL.topologia_plantilles()
    assert taula["ⵙ"] == (2, 1, "")          # anella + punt: dos trossos, un forat
    assert taula["ⵀ"] == (1, 2, "costat")    # barra vertical: dos forats, un al costat de l'altre
    assert taula["ⴱ"] == (1, 2, "apilats")   # barra horitzontal: un forat sobre l'altre
    assert taula["ⵛ"] == (1, 2, "petits")    # dos punts minusculs
    for ch in ("ⵙ", "ⵀ", "ⴱ", "ⵛ"):
        altres = [c for c, t in taula.items() if t == taula[ch] and c != ch]
        assert altres == [], f"{ch} ja no te firma propia: la comparteix amb {altres}"


def test_el_desempat_no_toca_res_quan_el_primer_guanya_de_molt():
    """Si la forma global ho te clar, la topologia no s'hi ha de ficar."""
    mask = np.zeros((20, 20), bool)
    mask[5:15, 5:15] = True
    punts = [(0.90, "ⵔ"), (0.40, "ⵙ"), (0.30, "ⵀ")]
    assert PL.desempata(mask, punts) == punts


def test_el_desempat_posa_davant_el_que_casa_amb_la_topologia():
    """Amb dos candidats empatats, mana el que te la mateixa topologia que el glif.

    El glif es una anella amb un punt al mig: la firma de la ⵙ. Encara que la nota de la ⵀ
    vagi primera per tres mil·lesimes, el desempat ha de posar la ⵙ davant.
    """
    anella, punt = PL.plantilles()["ⵙ"][0], None
    assert PL.topologia(anella) == (2, 1, "")
    punts = [(0.461, "ⵀ"), (0.458, "ⵙ"), (0.40, "ⵔ")]
    sortida = PL.desempata(anella, punts)
    assert sortida[0][1] == "ⵙ", sortida[:2]
    #: i no es perd cap candidat pel cami
    assert sorted(s for _, s in sortida) == sorted(s for _, s in punts)
