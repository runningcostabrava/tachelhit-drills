# -*- coding: utf-8 -*-
"""El lector de la línia de tifinag, darrere d'una sola funció: `llegeix_bandes(imatges) -> lectures`.

Avui és el lector per plantilles d'aslmdtv (`tools/ocr_tifinag/glifs.py` + `plantilles.npz`): segmenta els
glifs del text blanc amb vora fosca, els classifica per correlació amb les plantilles i fa una segona
passada amb les plantilles adaptades al vídeo (per això la funció rep TOTES les bandes alhora, no una).
Mesurat a «Illy» cap. 1 (1080p): 88 % dels glifs per sobre de 0,85, 18 de 20 subtítols exactes a ull.
A 720p (lletra de 20 px) ⵎ↔ⴹ es confonen: si es pot, el tifinag es llegeix sobre el vídeo de 1080p.

Quan el peó de tipografia tingui el lector entrenat amb el sintètic, es canvia aquest mòdul i prou:
l'etapa 02 només sap que li torna, per a cada banda, {"tifinag", "glifs", "conf_mitjana", "n_dubtosos"}.
"""
import os
import re
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
OCR = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "ocr_tifinag")
sys.path.insert(0, OCR)
import glifs as G  # noqa: E402

PLANTILLES = os.path.join(OCR, "plantilles.npz")
NOM = "plantilles-aslmdtv"   # el valor de tifinag_lector a cada fila (§3.3)
LLINDAR_1A = 0.80
LLINDAR = 0.85
COMPOSTOS = {'"ⵍ': "ⵍ", '"ⵎ': "ⵎ", '"ⵓ': "ⵓ"}   # les cometes compostes d'aslmdtv no hi són als subtítols


def tres_nivells(a):
    """Blanc pur = nucli; blanc antialiasat cap a la vora fosca = halo. Es demana que a 3 px del blanc hi hagi
    píxels foscos: així una paret clara no és lletra."""
    mn, mx = a.min(axis=2), a.max(axis=2)
    nucli = (mn > 185) & ((mx - mn) < 45)
    halo = (mn > 120) & ((mx - mn) < 70)
    fosc = mx < 110
    prop_fosc = ndimage.binary_dilation(fosc, structure=np.ones((3, 3)), iterations=3)
    lab, n = ndimage.label(nucli, structure=np.ones((3, 3)))
    if n:
        te_vora = ndimage.sum(prop_fosc, lab, index=np.arange(1, n + 1)) > 0
        nucli = nucli & np.isin(lab, np.nonzero(te_vora)[0] + 1)
    halo = halo & ndimage.binary_dilation(nucli, structure=np.ones((3, 3)))
    return np.where(nucli, 255, np.where(halo, 110, 0)).astype(np.uint8), nucli


def fila_de_text(nucli, min_px=3):
    """La fila: el tram vertical més poblat de nucli (tolerant 1 fila buida), i el seu abast en x."""
    prof = nucli.sum(axis=1)
    files = prof >= min_px
    if not files.any():
        return None
    trams, ini = [], None
    for y, v in enumerate(files):
        if v and ini is None:
            ini = y
        elif not v and ini is not None:
            if y + 1 < len(files) and files[y + 1]:
                continue
            trams.append((ini, y)); ini = None
    if ini is not None:
        trams.append((ini, len(files)))
    y0, y1 = max(trams, key=lambda t: prof[t[0]:t[1]].sum())
    if y1 - y0 < 8:
        return None
    cols = np.nonzero(nucli[y0:y1].sum(axis=0) > 0)[0]
    return [int(cols.min()), int(y0), int(cols.max()) + 1, int(y1)]


def segmenta(a):
    """Els glifs d'una banda RGB (array int), ordenats i amb número de paraula; [] si no hi ha text."""
    niv, nucli = tres_nivells(a)
    fila = fila_de_text(nucli)
    if fila is None:
        return [], None, None
    gs = G.segmenta_fila(niv, fila, [0, 0])
    gs = [g for g in gs if g["caixa"][1] < fila[3] - 2 and g["caixa"][3] > fila[1] + 2]
    if not gs:
        return [], fila, None
    alcades = [g["caixa"][3] - g["caixa"][1] for g in gs]
    H = float(np.percentile(alcades, 85))
    if H < 8:
        return [], fila, H
    gs.sort(key=lambda g: g["caixa"][0])
    buits = [b["caixa"][0] - a_["caixa"][2] for a_, b in zip(gs, gs[1:])]
    buit_tipic = float(np.median([b for b in buits if b >= 0])) if buits else 4.0
    llindar_espai = max(1.5 * buit_tipic, buit_tipic + 3)
    paraula = 0
    for i, g in enumerate(gs):
        if i > 0 and g["caixa"][0] - gs[i - 1]["caixa"][2] > llindar_espai:
            paraula += 1
        g["paraula"] = paraula
        g["h_rel"] = round((g["caixa"][3] - g["caixa"][1]) / H, 3)
        g["tela"] = G.normalitza(g["mask"], H)
    return gs, fila, H


def carrega_plantilles():
    z = np.load(PLANTILLES, allow_pickle=True)
    etq = [str(e) for e in z["etiquetes"]]
    usar = [i for i, e in enumerate(etq) if e != "(meitat)"]
    return [etq[i] for i in usar], np.stack([G.vector(z["imatges"][i]) for i in usar])


def text_de(gs, fila):
    """De les etiquetes al text: cometa/coma pel senyal petit segons l'alçada, ⵯ darrere ⴳ/ⴽ, el «:» és la ⵓ
    (dos anellets que a 30 px surten com dos punts), i una ⵯ sola com a paraula és una brillantor."""
    paraules = []
    for g in gs:
        e = COMPOSTOS.get(g["etiqueta"], g["etiqueta"])
        if e == "MARCA":
            rel = (g["caixa"][1] - fila[1]) / max(1, fila[3] - fila[1])
            e = '"' if rel < 0.35 else ","
            if paraules and paraules[-1][0] == g["paraula"] and paraules[-1][1][-1:] in ("ⴳ", "ⴽ", "ⵯ"):
                e = "" if paraules[-1][1].endswith("ⵯ") else "ⵯ"
        elif e == ":":
            e = "ⵓ"
        if paraules and paraules[-1][0] == g["paraula"]:
            paraules[-1][1] += e; paraules[-1][2] = max(paraules[-1][2], g["conf"])
        else:
            paraules.append([g["paraula"], e, g["conf"]])
    # una «paraula» on cap glif passa de 0,6 és el logotip del programa o una taca (l'entrevista «Tadfi n Tskla»
    # porta un llibre dibuixat a la dreta de la línia, que sortia com a ⵄⵄ a cada subtítol)
    # i una coma o cometa enmig d'una paraula és un tros de lletra trencada (a 720p passa sovint), no puntuació
    text = " ".join(re.sub(r'[,"](?=.)', "", p) for _, p, c in paraules if p and p not in ("ⵯ", "ⵯⵯ") and c >= 0.6).strip()
    # cap espai abans de , . ! (el signe surt com a «paraula» pròpia); el «?» sí que porta espai als subtítols de la SNRT
    return re.sub(r" +([,.!])", lambda m: m.group(1), text)


def llegeix_bandes(imatges, log=print):
    """imatges: llista d'arrays RGB (una banda de tifinag per subtítol; None si no hi ha fotograma).
    Torna una llista paral·lela de {"tifinag", "glifs", "n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"}."""
    etiquetes, P = carrega_plantilles()
    per_banda = []
    tot, teles = [], []
    for i, a in enumerate(imatges):
        if a is None:
            per_banda.append(([], None)); continue
        gs, fila, H = segmenta(np.asarray(a).astype(int))
        per_banda.append((gs, fila))
        for g in gs:
            tot.append((i, g)); teles.append(g.pop("tela"))
    buides = [{"tifinag": "", "glifs": [], "n_glifs": 0, "n_dubtosos": 0, "conf_mitjana": None, "conf_min": None}
              for _ in imatges]
    if not teles:
        return buides
    V = np.stack([G.vector(t) for t in teles])
    S1 = V @ P.T
    m1, c1 = S1.argmax(axis=1), S1.max(axis=1)
    P2 = P.copy()
    T2 = np.stack(teles)
    adaptades = 0
    for j in range(len(etiquetes)):
        sel = np.nonzero((m1 == j) & (c1 >= LLINDAR_1A))[0]
        if len(sel) >= 3:
            P2[j] = G.vector(T2[sel].mean(axis=0)); adaptades += 1
    S = V @ P2.T
    millor, conf = S.argmax(axis=1), S.max(axis=1)
    log(f"  tifinag: {len(teles)} glifs, {adaptades} plantilles adaptades, {100 * (conf >= LLINDAR).mean():.1f} % >= {LLINDAR}")
    for (i, g), m, c in zip(tot, millor, conf):
        g["etiqueta"] = etiquetes[m]; g["conf"] = round(float(c), 3)
    fora = []
    for (gs, fila), buit in zip(per_banda, buides):
        if not gs:
            fora.append(buit); continue
        confs = [g["conf"] for g in gs]
        fora.append({"tifinag": text_de(gs, fila), "n_glifs": len(gs), "n_dubtosos": sum(1 for c in confs if c < LLINDAR),
                     "conf_mitjana": round(float(np.mean(confs)), 3), "conf_min": min(confs),
                     "glifs": [{"caixa": g["caixa"], "etiqueta": g["etiqueta"], "conf": g["conf"], "paraula": g["paraula"]} for g in gs]})
    return fora
