"""L'OCR de tifinag, aqui, sobre imatges de debo. I la seva confianca.

## Per que calia aixo

El model dona CER 0,0104 sobre text fabricat que no havia vist mai. Sobre el primer fotograma
de debo va dir `ⵓ ⵏ` quan la persona hi llegia `ⵉⴼⴼⵖ ⴷ ⵓⵢⵔⴰⴷ, ⵢⵉⵏⵉ ⴰⵙ:`. La culpa no era del
model: li vaig donar la franja sencera, amb DUES linies de text, esclafada a 48 pixels. Esta
entrenat amb UNA linia.

## La confianca, i per que val tant

El CTC dona, a cada passa, la probabilitat del simbol que tria. La mitjana d'aquestes
probabilitats diu com de segur esta el model. Aixo serveix per a una cosa que no sabiem fer:
**trobar on es el text sense saber-ho d'abans**. En comptes de deduir la franja del subtitol
mirant els pixels —ho he provat de tres maneres i cap no distingeix el subtitol del dibuix en
una pel·licula animada—, es prova de llegir moltes franges i es queden les que es llegeixen amb
seguretat. Es mes honest: no s'endevina on hi ha lletra, es comprova.
"""
import os

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

S = os.path.dirname(os.path.abspath(__file__))
PES = os.path.join(S, "k_ocr_out", "ocr_tifinag.pt")
ALT = 48
MAX_AMPLE = 1600


class CRNN(nn.Module):
    """La mateixa xarxa del quadern, caracter per caracter: si canvia, els pesos no hi entren."""

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
    a = np.array(im.resize((w, ALT), Image.BILINEAR), dtype=np.float32) / 255.0
    return torch.from_numpy(a).unsqueeze(0).unsqueeze(0)


def llegeix(im):
    """Torna (text, confianca). La confianca es la probabilitat mitjana de les passes que
    aporten lletra: les passes buides no compten, perque una imatge sense text en te moltes i
    totes molt segures, i inflarien el numero."""
    with torch.no_grad():
        logits = MODEL(_prepara(im))[0]
    prob = logits.softmax(-1)
    millors = prob.argmax(-1)
    valors = prob.max(-1).values
    ant, lletres, segures = -1, [], []
    for k, (idx, v) in enumerate(zip(millors.tolist(), valors.tolist())):
        if idx != ant and idx != 0:
            lletres.append(A_SIGNE.get(idx, ""))
            segures.append(v)
        ant = idx
    return "".join(lletres), (float(np.mean(segures)) if segures else 0.0)


def vores_per_fila(a):
    d = np.abs(np.diff(a.astype(np.int16), axis=1))
    return d.mean(axis=1)


def talla_linies(im, minim_alt=10):
    """Parteix una imatge en blocs de files amb lletra. Cada bloc es una linia candidata."""
    a = np.array(im.convert("L"))
    v = vores_per_fila(a)
    if v.max() <= 0:
        return []
    llindar = max(3.0, v.max() * 0.22)
    marca = v >= llindar
    blocs, dins, inici = [], False, 0
    for k, m in enumerate(marca):
        if m and not dins:
            dins, inici = True, k
        elif not m and dins:
            dins = False
            if k - inici >= minim_alt:
                blocs.append((inici, k))
    if dins and len(marca) - inici >= minim_alt:
        blocs.append((inici, len(marca)))
    return [im.crop((0, max(0, p - 4), im.width, min(a.shape[0], q + 4))) for p, q in blocs]


def retalla_marges(im, marge=6):
    """Treu el blanc dels costats: una linia amb mig fotograma buit a cada banda es llegeix
    pitjor, perque el model l'ha vista sempre amb el text ocupant l'amplada."""
    a = np.array(im.convert("L"))
    d = np.abs(np.diff(a.astype(np.int16), axis=0)).mean(axis=0)
    if d.max() <= 0:
        return im
    cols = np.where(d >= max(2.0, d.max() * 0.14))[0]
    if len(cols) < 4:
        return im
    return im.crop((max(0, cols.min() - marge), 0, min(im.width, cols.max() + marge), im.height))


def linies_y(im, minim_alt=10):
    """La y de dalt de cada linia de talla_linies (mateix tall, mateix ordre)."""
    a = np.array(im.convert("L"))
    v = vores_per_fila(a)
    if v.max() <= 0:
        return []
    marca = v >= max(3.0, v.max() * 0.22)
    ys, dins, inici = [], False, 0
    for k, m in enumerate(list(marca) + [False]):
        if m and not dins:
            dins, inici = True, k
        elif not m and dins:
            dins = False
            if k - inici >= minim_alt:
                ys.append(max(0, inici - 4))
    return ys


def marge_esquerre(im, marge=6):
    """Quants px treu retalla_marges per l'esquerra."""
    a = np.array(im.convert("L"))
    d = np.abs(np.diff(a.astype(np.int16), axis=0)).mean(axis=0)
    if d.max() <= 0:
        return 0
    cols = np.where(d >= max(2.0, d.max() * 0.14))[0]
    if len(cols) < 4:
        return 0
    return max(0, cols.min() - marge)
