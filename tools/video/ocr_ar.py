"""L'OCR d'arab, aqui, sobre franges de video de debo.

Igual que `ocr_tif.py`, amb dues diferencies que venen de l'arab:

  · **la linia s'emmiralla** abans d'entrar al model, perque es va entrenar amb la imatge en
    mirall per fer coincidir l'ordre visual (dreta a esquerra) amb l'ordre del text;
  · les vocals curtes no hi son: el text d'entrenament les tenia tretes.

El numero que en surt contra les 904 lectures del Qwen es «coincidencia amb el Qwen», no CER:
el Qwen no es text d'or.
"""
import os
import re

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

S = os.path.dirname(os.path.abspath(__file__))
PES = os.path.join(S, "k_ocr_ar_out", "ocr_arab.pt")
ALT = 48
MAX_AMPLE = 1600
TASHKIL = re.compile(r"[ً-ْـٰ]")


class CRNN(nn.Module):
    def __init__(self, classes):
        super().__init__()

        def bloc(e, s, pool):
            return nn.Sequential(nn.Conv2d(e, s, 3, 1, 1), nn.BatchNorm2d(s),
                                 nn.ReLU(True), nn.MaxPool2d(pool))

        self.cnn = nn.Sequential(
            bloc(1, 64, (2, 2)), bloc(64, 128, (2, 2)),
            bloc(128, 256, (2, 1)), bloc(256, 256, (2, 1)),
            nn.Conv2d(256, 256, (3, 1)), nn.BatchNorm2d(256), nn.ReLU(True),
        )
        self.rnn = nn.LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True,
                           dropout=0.1)
        self.sortida = nn.Linear(512, classes)

    def forward(self, x):
        h = self.cnn(x).squeeze(2).permute(0, 2, 1)
        h, _ = self.rnn(h)
        return self.sortida(h)


_estat = torch.load(PES, map_location="cpu")
SIGNES = _estat["signes"]
A_SIGNE = {i + 1: c for i, c in enumerate(SIGNES)}
MODEL = CRNN(len(SIGNES) + 1)
MODEL.load_state_dict(_estat["model"])
MODEL.eval()


def _prepara(im):
    im = im.convert("L")
    w = max(16, min(MAX_AMPLE, int(im.width * ALT / im.height)))
    im = im.resize((w, ALT), Image.BILINEAR).transpose(Image.FLIP_LEFT_RIGHT)
    a = np.array(im, dtype=np.float32) / 255.0
    return torch.from_numpy(a).unsqueeze(0).unsqueeze(0)


def llegeix(im):
    """Torna (text, confianca): la mitjana de probabilitat de les passes amb lletra."""
    with torch.no_grad():
        logits = MODEL(_prepara(im))[0]
    prob = logits.softmax(-1)
    millors = prob.argmax(-1)
    valors = prob.max(-1).values
    ant, lletres, segures = -1, [], []
    for idx, v in zip(millors.tolist(), valors.tolist()):
        if idx != ant and idx != 0:
            lletres.append(A_SIGNE.get(idx, ""))
            segures.append(v)
        ant = idx
    return "".join(lletres), (float(np.mean(segures)) if segures else 0.0)


def vores_per_fila(a):
    d = np.abs(np.diff(a.astype(np.int16), axis=1))
    return d.mean(axis=1)


def talla_linies(im, minim_alt=10):
    a = np.array(im.convert("L"))
    v = vores_per_fila(a)
    if v.max() <= 0:
        return []
    llindar = max(3.0, v.max() * 0.22)
    marca = v >= llindar
    blocs, dins, inici = [], False, 0
    for k, m in enumerate(list(marca) + [False]):
        if m and not dins:
            dins, inici = True, k
        elif not m and dins:
            dins = False
            if k - inici >= minim_alt:
                blocs.append((inici, k))
    return [im.crop((0, max(0, p - 4), im.width, min(a.shape[0], q + 4))) for p, q in blocs]


def retalla_marges(im, marge=6):
    a = np.array(im.convert("L"))
    d = np.abs(np.diff(a.astype(np.int16), axis=0)).mean(axis=0)
    if d.max() <= 0:
        return im
    cols = np.where(d >= max(2.0, d.max() * 0.14))[0]
    if len(cols) < 4:
        return im
    return im.crop((max(0, cols.min() - marge), 0, min(im.width, cols.max() + marge), im.height))


def net(t):
    """La mateixa neteja a les dues bandes: sense vocals curtes, un sol espai."""
    return re.sub(r"\s+", " ", TASHKIL.sub("", t or "")).strip()
