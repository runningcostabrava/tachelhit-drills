# -*- coding: utf-8 -*-
"""Quina de les dues línies de subtítol és el tifinag i quina l'àrab, pel TIPUS DE CARÀCTER i no per la posició (#601).

A la sèrie d'«Illy» i a l'entrevista el tifinag va a dalt i l'àrab a sota, però en una sèrie històrica de Tamazight TV l'ordre és invertit. L'etapa 02 ho
resolia amb constants (comu.TIFINAG_720 / ARAB_720). Aquí es miren uns quants fotogrames del vídeo:

1. Es troben les files de text a la part baixa del fotograma: un píxel és de lletra si és blanc i és entre dues vores fosques (la mateixa prova que el segmentador
   de tifinag); les files amb tinta es converteixen en trams, i es queden els dos trams amb més tinta, de mida de subtítol i centrats.
2. Cada tram es puntua com a tifinag amb dues proves independents: (a) la tinta que cau en components AMPLES (> 1,4 × l'alçada del tram): l'àrab cursiu
   s'enganxa en paraules llargues, el tifinag són glifs aïllats de cos uniforme (≤ 1,2 × el cos); (b) la confiança del lector de plantilles de tifinag
   sobre el tram (un tram d'àrab dona glifs poc o gens encaixats).
3. En cada fotograma, el tram més tifinag és el tifinag si guanya per un marge; el capítol decideix per majoria. Si no hi ha prou fotogrames informatius o
   la majoria és fluixa, es llança `OrdreIndecis`: l'etapa 02 s'atura amb un error clar en lloc d'endevinar.

Tot es fa a l'escala de 1080p (els fotogrames de 720p es pugen ×1,5, com fa el segmentador).
"""
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import lector_tifinag as LT  # noqa: E402
import tifinag_segmenta as SEG  # noqa: E402

AMPLE_RELATIU = 1.4        # un component més ample que això × l'alçada del tram és una paraula enganxada (àrab)
MARGE_FOTOGRAMA = 0.15     # diferència mínima entre les puntuacions dels dos trams perquè el fotograma voti
MIN_FOTOGRAMES = 4         # fotogrames informatius mínims per decidir
MAJORIA = 0.7              # fracció mínima de vots per al mateix ordre
COS_1080 = 28              # alçada del cos del tifinag a 1080p (vegeu tifinag_segmenta)
COS_PERFIL = 0.35          # el cos és el tram de files amb ≥ 35 % de la tinta de la fila més carregada (les comes, el ⵯ i els punts queden fora)
COS_BIAS = 1               # sobre els fotogrames de l'entrevista (cos nominal 884) el perfil dona 883: la correcció que ho fa coincidir


class OrdreIndecis(RuntimeError):
    """No es pot saber quina línia és tifinag i quina àrab (pocs fotogrames amb dues línies, o vots partits)."""


def _a_1080(rgb):
    """Fotograma (RGB uint8) a l'escala de 1080p; torna (rgb, factor) amb factor = alçada_1080 / alçada_original per tornar les y a l'original."""
    if rgb.shape[1] <= 1400:
        im = Image.fromarray(rgb)
        return np.asarray(im.resize((int(round(im.width * 1.5)), int(round(im.height * 1.5))), Image.LANCZOS)), 1.5
    return rgb, 1.0


def trams_de_text(rgb1080, y_ini=0):
    """Els trams de files amb text de subtítol d'un fotograma (o d'un retall) a escala 1080p.
    Torna [(y0, y1, tinta, mascara_del_tram)] amb y relatives a rgb1080, els dos de més tinta que hi caben a ordre de dalt a baix."""
    mask, _, _ = SEG.mascara_lletra(rgb1080)
    w = mask.shape[1]
    prof = mask.sum(axis=1)
    actives = prof >= 4
    trams, ini = [], None
    for y, v in enumerate(actives):
        if v and ini is None:
            ini = y
        elif not v and ini is not None:
            if y + 2 < len(actives) and actives[y + 1:y + 3].any():   # es toleren 2 files buides dins un tram (les comes i els punts)
                continue
            trams.append((ini, y)); ini = None
    if ini is not None:
        trams.append((ini, len(actives)))
    sortida = []
    for a, b in trams:
        if not (16 <= b - a <= 56):
            continue
        sub = mask[a:b]
        cols = np.nonzero(sub.sum(axis=0))[0]
        if len(cols) == 0 or cols.max() - cols.min() < 150:
            continue
        if abs((cols.min() + cols.max()) / 2 - w / 2) > 0.18 * w:
            continue                                                  # el subtítol és centrat
        sortida.append((a + y_ini, b + y_ini, int(sub.sum()), sub))
    sortida.sort(key=lambda t: -t[2])
    return sorted(sortida[:2], key=lambda t: t[0])


def cos_del_tram(sub):
    """(top, bot) de les files del cos dins un tram: les que tenen ≥ COS_PERFIL de la tinta de la fila més carregada. Per al tifinag és el cos de 26–29 px
    (sense comes ni marques); es fa servir per saber a quina y real és el cos, que és el que el lector del tifinag necessita."""
    prof = sub.sum(axis=1).astype(float)
    ys = np.nonzero(prof >= COS_PERFIL * prof.max())[0]
    return int(ys.min()), int(ys.max()) + 1


def forma_ample(sub):
    """Fracció de la tinta en components amples: ≈ 0 per al tifinag (glifs aïllats), alta per a l'àrab cursiu."""
    lab, n = ndimage.label(sub, structure=np.ones((3, 3)))
    if n == 0:
        return 0.0
    H = sub.shape[0]
    arees = ndimage.sum(sub, lab, index=np.arange(1, n + 1))
    sls = ndimage.find_objects(lab)
    ample = np.array([(s[1].stop - s[1].start) > AMPLE_RELATIU * H for s in sls])
    return float(arees[ample].sum() / max(1.0, arees.sum()))


def puntua_tifinag(rgb1080, tram):
    """Puntuació 0–1 de «aquest tram és tifinag»: mitjana de (1 − tinta en components amples) i la confiança del lector de plantilles."""
    y0, y1, _, sub = tram
    fa = forma_ample(sub)
    # El lector espera la banda de 51 files que comença 14 files per sobre del cos (vegeu tifinag_segmenta). Si el tram fos tifinag, el seu cos començaria a y0.
    top = y0 - 14
    if top < 0 or top + 51 > rgb1080.shape[0]:
        return 0.5 * (1 - fa), fa, 0.0, 0
    r = LT.llegeix_banda(rgb1080[top:top + 51])
    conf = min(1.0, r["conf_mitjana"] or 0.0) if r["n_glifs"] >= 3 else 0.0
    return 0.5 * (1 - fa) + 0.5 * conf, fa, conf, r["n_glifs"]


def ordre_del_fotograma(rgb):
    """Un fotograma (RGB, tot el fotograma o només la part baixa). Torna None si no hi ha dues línies; si no un dict amb l'ordre, el marge i els trams."""
    f, factor = _a_1080(np.asarray(rgb))
    trams = trams_de_text(f)
    if len(trams) != 2:
        return None
    p = [puntua_tifinag(f, t) for t in trams]
    marge = abs(p[0][0] - p[1][0])
    return {"ordre": "normal" if p[0][0] > p[1][0] else "invertit", "marge": marge,
            "puntuacions": [round(x[0], 3) for x in p], "trams_1080": [(t[0], t[1]) for t in trams], "factor": factor,
            "cos_1080": [tuple(t[0] + c for c in cos_del_tram(t[3])) for t in trams]}


def decideix(resultats):
    """Els resultats de `ordre_del_fotograma` d'un capítol (None inclosos) -> 'normal' | 'invertit'; OrdreIndecis si no es pot."""
    bons = [r for r in resultats if r is not None and r["marge"] >= MARGE_FOTOGRAMA]
    if len(bons) < MIN_FOTOGRAMES:
        raise OrdreIndecis(f"no puc saber quina línia és tifinag i quina àrab: només {len(bons)} fotogrames de {len(resultats)} amb dues línies "
                           f"ben diferenciades (en calen {MIN_FOTOGRAMES})")
    n_normal = sum(1 for r in bons if r["ordre"] == "normal")
    f = max(n_normal, len(bons) - n_normal) / len(bons)
    if f < MAJORIA:
        raise OrdreIndecis(f"no puc saber quina línia és tifinag i quina àrab: {n_normal} fotogrames diuen «tifinag a dalt» i {len(bons) - n_normal} «a sota»")
    return "normal" if n_normal > len(bons) - n_normal else "invertit"


def geometria(resultats, ordre, alt=None):
    """La posició REAL (escala 1080p) del cos del tifinag i de la línia d'àrab, medianes dels fotogrames que han votat l'ordre decidit:
    {"cos_tifinag_1080": (top, bot) amb la correcció COS_BIAS, "arab_1080": (y0, y1) del tram d'àrab, "alt_cos_1080": alçada del cos}."""
    bons = [r for r in resultats if r is not None and r["ordre"] == ordre and r["marge"] >= MARGE_FOTOGRAMA]
    i_tif, i_ara = (0, 1) if ordre == "normal" else (1, 0)
    cos = np.median([r["cos_1080"][i_tif] for r in bons], axis=0)
    ara = np.median([r["trams_1080"][i_ara] for r in bons], axis=0)
    return {"cos_tifinag_1080": (float(cos[0]) + COS_BIAS, float(cos[1]) + COS_BIAS), "arab_1080": (float(ara[0]), float(ara[1])),
            "alt_cos_1080": float(cos[1] - cos[0]), "fotogrames_votants": len(bons)}


def ordre_del_video(video, ample, alt, durada, log=print, n=12, part_baixa=0.55):
    """Mira `n` fotogrames repartits del vídeo (la part baixa, des del `part_baixa` de l'alçada) i torna {"ordre", "geometria", "fotogrames"}.
    Llança OrdreIndecis si no pot decidir."""
    resultats = []
    for k in range(1, n + 1):
        t = durada * k / (n + 1)
        out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True).stdout
        if not out:
            continue
        a = np.asarray(Image.open(io.BytesIO(out)).convert("RGB"))
        y0 = int(a.shape[0] * part_baixa)
        r = ordre_del_fotograma(a[y0:])
        if r is not None:
            r["trams_1080"] = [(t0 + y0 * r["factor"], t1 + y0 * r["factor"]) for t0, t1 in r["trams_1080"]]
            r["cos_1080"] = [(t0 + y0 * r["factor"], t1 + y0 * r["factor"]) for t0, t1 in r["cos_1080"]]
        resultats.append(r)
    ordre = decideix(resultats)
    log(f"ordre de les línies: {ordre} ({sum(1 for r in resultats if r is not None)} fotogrames amb dues línies de {len(resultats)})")
    return {"ordre": ordre, "geometria": geometria(resultats, ordre, alt), "fotogrames": len(resultats)}
