# -*- coding: utf-8 -*-
"""Classificador de glifs per plantilles (Tifinaghe-Ircam Unicode a l'escala de la franja: cos 28 px = 43 px nominals).

Cada glif segmentat (màscara de lletra + caixa) es compara amb cada plantilla col·locada a la mateixa y absoluta (±2 px) i x centrada (±2 px),
amb gruix de plantilla 0/1 px; puntuació = IoU. Les plantilles de lletra són a `tifinag_plantilles.npz` (34 signes de la font de l'IRCAM com a màscares
binàries; la font no és al repositori). Per refer-les: `python tifinag_plantilles.py --fes <Tifinaghe-Ircam_Unicode.ttf>`.

XIFRES. La font IRCAM no en té, i les del vídeo no són de cap font que tinguem: són una sans arrodonida d'uns 32 px d'alt que **no va a la mateixa alçada
sobre la línia** a tots els vídeos (a «Illy» baixen 2 px sota la base; a l'entrevista pugen 7 px sobre el cos). Per això es comparen per FORMA (alçada
normalitzada, sense y absoluta) contra glifs reals de la SNRT guardats a `tifinag_xifres.npz`: 8 i 0 de «80» (Illy, línia 283) i 2, 0, 2, 6 de «2026»
(entrevista, t=2687 s). Les xifres 1 3 4 5 7 9 no s'han vist mai al vídeo: hi ha Arial com a recurs (`real=False`) i **no estan verificades**.
"""
import os
import sys

import numpy as np
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
NPZ = os.path.join(AQUI, "tifinag_plantilles.npz")
LLETRES = list("ⴰⴱⴳⴷⴹⴻⴼⴽⵀⵃⵄⵅⵇⵉⵊⵍⵎⵏⵓⵔⵕⵖⵙⵚⵛⵜⵟⵡⵢⵣⵥⵯ") + [",", "?", ":", "."]
XIFRES = list("0123456789")
XIFRES_NPZ = os.path.join(AQUI, "tifinag_xifres.npz")
MIDA = 43
ALT_NORM = 36
GRUIXOS = (0, 1)
_cache = {}


def plantilles():
    """{signe: (màscara bool, dy)}; dy = fila superior de la plantilla respecte del capdamunt del cos (el de ⵏ)."""
    if "p" not in _cache:
        z = np.load(NPZ, allow_pickle=True)
        _cache["p"] = {str(c): (m.astype(bool), int(dy)) for c, m, dy in zip(z["signes"], z["mascares"], z["dy"]) if str(c) not in XIFRES}
    return _cache["p"]


def fes_npz(font_ircam, desti=NPZ):
    from PIL import Image, ImageDraw, ImageFont

    def mascara(font, ch, mida):
        im = Image.new("L", (mida * 3, mida * 3), 0)
        ImageDraw.Draw(im).text((mida, mida), ch, font=font, fill=255)
        a = np.asarray(im) > 110
        ys, xs = np.nonzero(a)
        return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1], int(ys.min()) - mida

    f = ImageFont.truetype(font_ircam, MIDA)
    brut = {ch: mascara(f, ch, MIDA) for ch in LLETRES}
    top_cos = brut["ⵏ"][1]
    sortida = {ch: (m, dy - top_cos) for ch, (m, dy) in brut.items()}
    signes = list(sortida)
    mascares = np.empty(len(signes), dtype=object)
    for i, ch in enumerate(signes):
        mascares[i] = sortida[ch][0]
    np.savez_compressed(desti, signes=np.array(signes), mascares=mascares, dy=np.array([sortida[c][1] for c in signes]))
    return desti


def _norm_alt(m):
    """Màscara retallada i escalada a ALT_NORM px d'alt (l'amplada segueix la proporció), centrada en un llenç de 40 px."""
    from PIL import Image
    ys, xs = np.nonzero(m)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w = max(3, int(round(m.shape[1] * ALT_NORM / m.shape[0])))
    a = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((w, ALT_NORM), Image.BILINEAR)) > 127
    out = np.zeros((ALT_NORM, 40), bool)
    x0 = (40 - min(w, 40)) // 2
    out[:, x0:x0 + min(w, 40)] = a[:, :40]
    return out


def xifres():
    if "x" not in _cache:
        z = np.load(XIFRES_NPZ, allow_pickle=True)
        _cache["x"] = [(str(d), _norm_alt(m if r else ndimage.binary_dilation(m, iterations=1)), bool(r))
                       for d, m, r in zip(z["digit"], z["mask"], z["real"])]
    return _cache["x"]


def puntua_xifres(mask):
    """[(IoU, xifra)] per forma (alçada normalitzada), amb desplaçaments ±2 px en x; la millor variant de cada xifra."""
    n = _norm_alt(mask)
    pts = {}
    for d, t, _ in xifres():
        best = 0.0
        for dx in (-2, -1, 0, 1, 2):
            tt = np.roll(t, dx, axis=1)
            u = (n | tt).sum()
            best = max(best, (n & tt).sum() / u if u else 0)
        pts[d] = max(pts.get(d, 0), best)
    return [(v, d) for d, v in pts.items()]


def _iou_posat(real, ry, temp, ty, gruix):
    """real, temp: màscares; ry, ty: y (relativa al cos) del seu capdamunt. Centra en x; prova ±2 en x i y."""
    t = ndimage.binary_dilation(temp, iterations=gruix) if gruix else temp
    th, tw = t.shape
    rh, rw = real.shape
    ty0 = ty - gruix
    y_lo = min(ry, ty0) - 3
    y_hi = max(ry + rh, ty0 + th) + 3
    cx = max(rw, tw) + 8
    A = np.zeros((y_hi - y_lo, cx), bool)
    xr = (cx - rw) // 2
    A[ry - y_lo:ry - y_lo + rh, xr:xr + rw] = real
    sa, st = A.sum(), t.sum()
    best = 0.0
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            y0 = ty0 - y_lo + dy
            x0 = (cx - tw) // 2 + dx
            if y0 < 0 or x0 < 0 or y0 + th > A.shape[0] or x0 + tw > cx:
                continue
            inter = (A[y0:y0 + th, x0:x0 + tw] & t).sum()
            u = sa + st - inter
            if u:
                best = max(best, inter / u)
    return float(best)


def classifica(mask, y_rel_top, gruix_real=1):
    """Llista [(IoU, signe)] ordenada de més a menys. mask: màscara del glif; y_rel_top: y del capdamunt relativa al cos.
    La màscara de «blanc entre vores» és ~1 px més prima que el traç real: es dilata `gruix_real` px.
    Una xifra fa ≥ 31 px d'alt: un glif més baix mai no és una xifra."""
    P = plantilles()
    if gruix_real:
        mask = ndimage.binary_dilation(mask, iterations=gruix_real)
        y_rel_top -= gruix_real
    punts = []
    if mask.shape[0] >= 30 + 2 * gruix_real:          # una xifra fa ≥ 31 px d'alt: un glif més baix mai no és una xifra
        punts.extend(puntua_xifres(mask))
    for ch, (m, dy) in P.items():
        punts.append((max(_iou_posat(mask, y_rel_top, m, dy, g) for g in GRUIXOS), ch))
    punts.sort(reverse=True)
    return punts


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fes":
        print("escrit", fes_npz(sys.argv[2]))
    else:
        print(__doc__)
