# -*- coding: utf-8 -*-
"""El lector de la línia d'àrab, darrere d'una sola funció: `llegeix_arab(franja) -> lectura` (#601, §6.3).

Avui és un CRNN+CTC propi (4,2 M paràmetres, CPU) entrenat amb línies sintètiques de 30 fonts i ajustat amb 659 línies reals de
«Illy» i de l'entrevista de Tadfi n Tskla; punt de control `lector_arab_final.pt` (17 MB: NO és al repositori). Cal `torch`
(només CPU; l'importa quan es llegeix, no en carregar el mòdul).

Mesurat (veritat feta pel peó que l'ha entrenat, no per en Pablo; 100 línies de 1080p, 2.447 caràcters, sense tashkil ni puntuació):
CER 0,0074 (84 línies exactes de 100). Només amb sintètic: 0,08. Els dos vídeos de la mesura són els de l'ajust fi (línies diferents),
amb la mateixa tipografia i sèrie: el CER sobre un capítol nou, o sobre un altre programa, és el que cal comprovar (vegeu
`tipografia/arab/INFORME_LECTOR.md`, a la carpeta de dades). Se'l tracta de CANDIDAT: no substitueix el model de visió.

**La franja.** És el retall de 1080p y 912–976 (alçada 64 px), x 110–1560 (1450 px de llarg; deixa fora el logotip de la dreta,
que Qwen llegeix com a subtítol), en color o gris, SENSE reescalar: les lletres han de tenir la mida del vídeo. Si el vídeo és
de 720p el retall es puja a 1450×64 (bicúbic; no està mesurat: el lector només ha vist 1080p). `retall_ffmpeg()` dona el
`crop=` d'un vídeo de qualsevol alçada i, per a una geometria no estàndard (`comu.ARAB_720`), el desplaça.

**Contracte.** `llegeix_arab(franja)` torna `{"arab", "conf", "conf_mitjana", "lector"}`: `arab` és el text en ordre lògic
(dreta a esquerra, com l'escrivim; amb vocals només si la imatge en té), `conf` és la probabilitat MÍNIMA dels símbols emesos i
`conf_mitjana` la mitjana. `conf` no és una probabilitat calibrada: sobre les 100 línies de veritat, «conf < 0,60» envia el 41 %
de les línies i recull el 88 % dels errors; «conf < 0,50» envia el 2 % i en recull el 5 %. `lector` és `NOM` (el valor d'`arab_lector`).

El pes es busca a `TD_MODEL_ARAB` (ruta), si no a `<TD_TV>/models/lector_arab_crnn_v4.pt`.
"""
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

NOM = "crnn-v4"                 # el valor d'arab_lector a cada fila (§3.3)
NOM_PES = "lector_arab_crnn_v4.pt"
LLINDAR_CONF = 0.60             # conf mínima per sota de la qual la rèplica és dubtosa
BANDA_X = (110, 1560)           # a 1080p: deixa fora el logotip de la dreta (x > 1560)
BANDA_Y0 = 912                  # a 1080p, per a la geometria per defecte (ARAB_720 = 612–656)
BANDA_H = 64
BANDA_W = BANDA_X[1] - BANDA_X[0]
ARAB_720_PER_DEFECTE = 612      # comu.ARAB_720[0] de la geometria per defecte; una altra geometria desplaça la banda
POOLS = ((2, 2), (2, 2), (2, 1), (8, 1))   # 64 -> 32 -> 16 -> 8 -> 1 en alçada; l'amplada /4

_model = {}


def ruta_pes():
    p = os.environ.get("TD_MODEL_ARAB")
    if p:
        return p
    import comu
    return os.path.join(comu.td_tv(), "models", NOM_PES)


def _classe_crnn():
    import torch.nn as nn

    class CRNN(nn.Module):
        def __init__(self, classes):
            super().__init__()

            def bloc(e, s, pool):
                return nn.Sequential(nn.Conv2d(e, s, 3, 1, 1), nn.BatchNorm2d(s), nn.ReLU(True), nn.MaxPool2d(pool))
            self.cnn = nn.Sequential(bloc(1, 64, POOLS[0]), bloc(64, 128, POOLS[1]), bloc(128, 256, POOLS[2]), bloc(256, 256, POOLS[3]),
                                     nn.Conv2d(256, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(True))
            self.rnn = nn.LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True, dropout=0.15)
            self.sortida = nn.Linear(512, classes)

        def forward(self, x):
            h = self.cnn(x).squeeze(2).permute(0, 2, 1)
            h, _ = self.rnn(h)
            return self.sortida(h)
    return CRNN


def carrega(ruta=None):
    """(model, signes). Es carrega un cop per procés."""
    import torch
    ruta = ruta or ruta_pes()
    if ruta not in _model:
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"no trobo el pes del lector d'àrab: {ruta} (TD_MODEL_ARAB o <TD_TV>/models/{NOM_PES})")
        ck = torch.load(ruta, map_location="cpu", weights_only=False)
        m = _classe_crnn()(len(ck["signes"]) + 1)
        m.load_state_dict(ck["model"])
        m.eval()
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        _model[ruta] = (m, ck["signes"])
    return _model[ruta]


def retall_ffmpeg(alt, y0_720=ARAB_720_PER_DEFECTE):
    """El `crop=W:H:X:Y` (píxels del vídeo de 16:9) de la banda d'àrab: la de 1080p escalada per alt/1080, i desplaçada si l'àrab no és a la
    línia de sempre (y0_720 = comu.ARAB_720[0])."""
    s = alt / 1080.0
    y = round((BANDA_Y0 + (y0_720 - ARAB_720_PER_DEFECTE) * 1.5) * s)
    return f"crop={round(BANDA_W * s)}:{round(BANDA_H * s)}:{round(BANDA_X[0] * s)}:{y}"


def a_banda(franja):
    """PIL/ndarray -> gris 64 px d'alçada (1450 de llarg si venia d'un vídeo que no és de 1080p), retallat a les columnes amb tinta."""
    im = franja if isinstance(franja, Image.Image) else Image.fromarray(np.asarray(franja).astype(np.uint8))
    im = im.convert("RGB")
    if im.height != BANDA_H:
        im = im.resize((BANDA_W, BANDA_H), Image.BICUBIC)
    a = np.asarray(im).astype(int)
    blanc = (a.min(axis=2) > 185).sum(axis=0).astype(float)
    k = np.convolve(blanc, np.ones(9) / 9, mode="same")
    cols = np.where(k >= 2.5)[0]
    if len(cols) >= 5:
        im = im.crop((max(0, cols[0] - 12), 0, min(im.width, cols[-1] + 12), im.height))
    return im.convert("L")


def llegeix_arab(franja, ruta_model=None):
    """Una franja d'àrab (vegeu el mòdul) -> {"arab", "conf", "conf_mitjana", "lector"}; text buit i conf 0 si no hi ha res."""
    import torch
    m, signes = carrega(ruta_model)
    x = torch.from_numpy(np.asarray(a_banda(franja), dtype=np.float32) / 255.0)[None, None]
    with torch.no_grad():
        p = m(x)[0].softmax(-1)
    mx, fila = p.max(-1)
    ant, s, ps = -1, [], []
    for k, q in zip(fila.numpy(), mx.numpy()):
        if k != ant and k != 0:
            s.append(signes[k - 1])
            ps.append(float(q))
        ant = k
    # el CRNN treu l'etiqueta en ordre visual (esquerra -> dreta): es gira a ordre lògic
    return {"arab": "".join(s)[::-1], "conf": min(ps) if ps else 0.0, "conf_mitjana": sum(ps) / len(ps) if ps else 0.0, "lector": NOM}


def llegeix_arabs(franges, ruta_model=None):
    return [llegeix_arab(f, ruta_model) for f in franges]


def decideix(lectures, llindar=LLINDAR_CONF, curta=2):
    """De les lectures de fotogrames del mateix tram (cada una amb «arab» normalitzat i «conf»), la lectura que es queda i si és dubtosa.
    Dubtosa si: dues lectures no vuides diferents, alguna lectura buida, la triada és més curta que `curta`, o la seva `conf` és sota `llindar`.
    Torna (text, conf, dubtos, n_lectures_no_buides, n_d_acord)."""
    bones = [x for x in lectures if x["arab"]]
    if not bones:
        return "", 0.0, True, 0, 0
    millor = max(bones, key=lambda x: x["conf"])
    d_acord = sum(1 for x in bones if x["arab"] == millor["arab"])
    dubtos = (len({x["arab"] for x in bones}) > 1 or len(bones) < len(lectures)
              or len(millor["arab"]) < curta or millor["conf"] < llindar)
    return millor["arab"], millor["conf"], bool(dubtos), len(bones), d_acord
