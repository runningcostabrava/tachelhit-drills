# -*- coding: utf-8 -*-
"""Classificador de glifs per plantilles (Tifinaghe-Ircam Unicode a l'escala de la franja: cos 28 px = 43 px nominals).

Cada glif segmentat (màscara de lletra + caixa) es compara amb cada plantilla col·locada a la mateixa y absoluta (±2 px) i x centrada (±2 px),
amb gruix de plantilla 0/1 px; puntuació = IoU. Les plantilles són a `tifinag_plantilles.npz` (34 signes de la font de l'IRCAM + les 10 xifres,
com a màscares binàries; la font no és al repositori). Per refer-les: `python tifinag_plantilles.py --fes <Tifinaghe-Ircam_Unicode.ttf> <arial.ttf>`.

Les xifres del vídeo no són de la font IRCAM (no en té): són una sans arrodonida d'uns 33 px d'alt (mesurat a «80» de la línia 283 d'«Illy»:
8 = 22×33, 0 = 23×33, capdamunt 4 px per sobre del cos). Es fabriquen amb Arial a 33 px; només 8 i 0 s'han pogut comprovar amb glifs reals.
"""
import os
import sys

import numpy as np
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
NPZ = os.path.join(AQUI, "tifinag_plantilles.npz")
LLETRES = list("ⴰⴱⴳⴷⴹⴻⴼⴽⵀⵃⵄⵅⵇⵉⵊⵍⵎⵏⵓⵔⵕⵖⵙⵚⵛⵜⵟⵡⵢⵣⵥⵯ") + [",", "?", ":", "."]
XIFRES = list("0123456789")
MIDA = 43
ALT_XIFRA = 33
GRUIXOS = (0, 1)
_cache = {}


def plantilles():
    """{signe: (màscara bool, dy)}; dy = fila superior de la plantilla respecte del capdamunt del cos (el de ⵏ)."""
    if "p" not in _cache:
        z = np.load(NPZ, allow_pickle=True)
        _cache["p"] = {str(c): (m.astype(bool), int(dy)) for c, m, dy in zip(z["signes"], z["mascares"], z["dy"])}
    return _cache["p"]


def fes_npz(font_ircam, font_xifres, desti=NPZ):
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
    for mida in range(30, 60):
        b = ImageFont.truetype(font_xifres, mida).getbbox("8")
        if b[3] - b[1] >= ALT_XIFRA:
            break
    fx = ImageFont.truetype(font_xifres, mida)
    for ch in XIFRES:
        sortida[ch] = (mascara(fx, ch, mida)[0], -4)
    signes = list(sortida)
    mascares = np.empty(len(signes), dtype=object)
    for i, ch in enumerate(signes):
        mascares[i] = sortida[ch][0]
    np.savez_compressed(desti, signes=np.array(signes), mascares=mascares, dy=np.array([sortida[c][1] for c in signes]))
    return desti


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
    for ch, (m, dy) in P.items():
        if ch in XIFRES and mask.shape[0] < 31 + 2 * gruix_real:
            continue
        punts.append((max(_iou_posat(mask, y_rel_top, m, dy, g) for g in GRUIXOS), ch))
    punts.sort(reverse=True)
    return punts


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--fes":
        print("escrit", fes_npz(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__)
