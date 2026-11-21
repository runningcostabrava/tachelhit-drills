# -*- coding: utf-8 -*-
"""El lector de la línia de tifinag, darrere d'una sola funció: `llegeix_bandes(imatges) -> lectures`.

Avui és el **segmentador nou + classificador de plantilles** (`tifinag_segmenta.py` + `tifinag_plantilles.py`, #601): un píxel és de lletra si
és blanc i és entre dues vores fosques (el fons clar no ho és), els components es fusionen o es parteixen per geometria, es descarta el que no és
a la fila del cos ni a l'extensió centrada, i cada glif es classifica per IoU amb les plantilles de Tifinaghe-Ircam (i xifres). No cal cap model entrenat.

Mesurat (1080p): CER 0,0051 (7 errors de 1.370 caràcters) sobre les 52 línies de «Illy» transcrites a mà (el CRNN de línia donava 0,050 i el
lector per plantilles d'aslmdtv, 18 de 20 subtítols exactes a ull); 12 de 12 comes. A 720p simulat (baixant a 2/3 les línies de 1080p):
CER 0,0073; a 720p real encara no s'ha mesurat. Si es pot, el tifinag es llegeix sobre 1080p.

Contracte amb l'etapa 02 (§3.3 de l'especificació): per a cada banda torna
{"tifinag", "glifs", "n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"}, i el mòdul exposa NOM («plantilles-segmentador-v1») i `segmenta(a)`
(el rellotge del tifinag només necessita les caixes). La banda és el retall TIFINAG_720 (y 580–614 a 720p; 870–921 a 1080p).

**Confiança.** `conf` d'un glif és `min(1, IoU / K_CONF)`. Els llindars de la fàbrica (0,85 de §3.3 i de les portes de §5) són d'una altra escala
(correlació de les plantilles d'aslmdtv); K_CONF fa que «dubtós» segueixi voler dir el mateix sense tocar-los. No és una probabilitat.
"""
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import tifinag_plantilles as PL  # noqa: E402
import tifinag_segmenta as SEG  # noqa: E402

NOM = "plantilles-segmentador-v1"   # el valor de tifinag_lector a cada fila (§3.3)
LLINDAR = 0.85                      # com a §3.3: glif dubtós = conf sota 0,85
K_CONF = 0.75
LLINDAR_LOCAL = 0.66                # IoU sota el qual es prova el refinament local de la màscara
GAP_ESPAI = 10                      # px entre caixes (a l'escala de 1080p) per posar un espai: 4 dins el mot, 16 entre mots
GAP_DARRERE_W = 15                  # darrere ⵯ (dues marques fines: la caixa és més estreta que la cel·la)
GAP_DAVANT_INTERROGANT = 5          # el «?» va precedit d'espai (a les 52 línies de veritat, sempre)
GAP_ENTRE_XIFRES = 20               # dins d'un nombre («2026») no hi ha espai: les xifres van més separades que les lletres
Y_ORIGEN_720 = 580                  # y del retall TIFINAG_720 (crop=1280:34:0:580); a 1080p és 870


def _alt_video(a):
    return 720 if a.shape[1] <= 1400 else 1080


def _segmenta(a):
    a = np.asarray(a).astype(np.uint8)
    alt = _alt_video(a)
    return SEG.segmenta(a, y_origen=Y_ORIGEN_720 if alt == 720 else 870, alt_video=alt)


def segmenta(a):
    """Compatibilitat amb l'etapa 02 (rellotge del tifinag): (glifs, fila, H); glifs amb «caixa» (x0, y0, x1, y1); [] si no hi ha text."""
    r = _segmenta(a)
    if not r["glifs"]:
        return [], None, None
    return r["glifs"], [r["extensio"][0], r["cos"][0], r["extensio"][1], r["cos"][1]], 28.0


def _text(r, punts):
    """Del que ha vist el segmentador al text: un caràcter per glif i espais pels buits; la puntuació va enganxada al mot anterior."""
    text, glifs, ant_x1, ant_tipus, p = [], [], None, None, 0
    cos_bot = r["cos"][1]
    for g, pts in zip(r["glifs"], punts):
        x0, y0, x1, y1 = g["caixa"]
        iou, ch = pts[0]
        if g["tipus"] == "ⵯ":
            ch = "ⵯ"
        elif g["tipus"] == "coma" or (ch in (",", ".") and y1 - cos_bot >= 2):
            ch = ","                       # la coma baixa sota la base; el punt no
        llindar = GAP_ESPAI
        if ant_tipus == "ⵯ":
            llindar = GAP_DARRERE_W
        elif ch == "?":
            llindar = GAP_DAVANT_INTERROGANT
        elif ch.isdigit() and text and text[-1].isdigit():
            llindar = GAP_ENTRE_XIFRES
        if ant_x1 is not None and x0 - ant_x1 >= llindar and ch not in (",", ".", "ⵯ"):
            text.append(" ")
            p += 1
        text.append(ch)
        glifs.append({"caixa": [int(v) for v in g["caixa"]], "etiqueta": ch, "conf": round(min(1.0, iou / K_CONF), 3),
                      "iou": round(iou, 3), "paraula": p})
        ant_x1, ant_tipus = x1, g["tipus"]
    return "".join(text).strip(), glifs


def llegeix_banda(a):
    """Una banda RGB (array, 720p o 1080p) -> dict del contracte; amb text buit si no hi ha cap glif."""
    buit = {"tifinag": "", "glifs": [], "n_glifs": 0, "n_dubtosos": 0, "conf_mitjana": None, "conf_min": None}
    if a is None:
        return buit
    r = _segmenta(a)
    if not r["glifs"]:
        return buit
    SEG.unifica_grups(r, PL.classifica)     # un glif partit per un buit de columnes torna a ser un si la plantilla l'encaixa millor sencer
    SEG.resol_amples(r, PL.classifica)      # dues rodones tangents (ⴰ+ⵔ sobre fons clar): el tall el tria la plantilla
    if not r["glifs"]:
        return buit
    cos_top = r["cos"][0]
    punts = [PL.classifica(g["mask"], g["caixa"][1] - cos_top) for g in r["glifs"]]
    # Llindar LOCAL de fons: un glif de lletra amb IoU baix (< LLINDAR_LOCAL) es torna a binaritzar amb el blanc i el fosc d'allà mateix (el fons pot canviar
    # de fosc a clar a mig mot) i es queda la màscara nova si millora l'IoU en ≥ 0,05. Les xifres (≥ 30 px d'alt) es comparen per forma i no es refinen.
    for i, (g, p) in enumerate(zip(r["glifs"], punts)):
        if p[0][0] < LLINDAR_LOCAL and g["tipus"] == "cos" and (g["caixa"][3] - g["caixa"][1]) < 30:
            g2 = SEG.refina_local(r, g)
            if g2 is not None:
                p2 = PL.classifica(g2["mask"], g2["caixa"][1] - cos_top)
                if p2[0][0] >= p[0][0] + 0.05:
                    r["glifs"][i], punts[i] = g2, p2
    r["glifs"], punts = SEG.afegeix_marques_w(r, punts)   # el ⵯ (dues marques de 1-2 px) que la màscara fina perd darrere ⴳ/ⴽ
    text, glifs = _text(r, punts)
    confs = [g["conf"] for g in glifs]
    return {"tifinag": text, "glifs": glifs, "n_glifs": len(glifs), "n_dubtosos": sum(1 for c in confs if c < LLINDAR),
            "conf_mitjana": round(float(np.mean(confs)), 3), "conf_min": min(confs)}


def llegeix_bandes(imatges, log=print):
    """imatges: llista d'arrays RGB (una banda de tifinag per subtítol; None si no hi ha fotograma).
    Torna una llista paral·lela de {"tifinag", "glifs", "n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"}."""
    fora = [llegeix_banda(a) for a in imatges]
    c = [g["conf"] for x in fora for g in x["glifs"]]
    if c:
        log(f"  tifinag: {len(c)} glifs, {100 * (np.array(c) >= LLINDAR).mean():.1f} % >= {LLINDAR} (conf = IoU de plantilla / {K_CONF})")
    return fora
