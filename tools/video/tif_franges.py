"""Treu franges de subtitol tifinag d'un video, per fer-les llegir a una persona.

## Per que no serveix agafar fotogrames cada N segons

Un fotograma a l'atzar cau sovint **mentre el subtitol entra o surt**, o entre dos subtitols. La
persona perdria l'estona llegint mitges lletres.

El que funciona —i que ja ens va costar trobar— es triar per **quietud**: quan la imatge no
canvia respecte de l'anterior, el subtitol hi es sencer i aturat. I despres, d'entre els
moments quiets, quedar-se els que tenen **mes vora** a la franja de baix, que es on hi ha
lletra. Posicio, foscor i rellotge ja van fallar tots tres.

## Que en surt

Retalls de la franja inferior, ampliats, a punt perque una persona els llegeixi signe a signe.
No s'hi passa cap OCR a proposit: si la persona veu una proposta de maquina, la seguira sense
voler, i el que volem es justament una lectura que la maquina no hagi tocat.
"""
import io
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

S = os.path.dirname(os.path.abspath(__file__))
VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    S, "contes_feina", "wcUZI6__nk4", "wcUZI6__nk4.mp4")
ON = os.path.join(S, "franges_llegir")
QUANTES = int(sys.argv[2]) if len(sys.argv) > 2 else 30
#: La franja de sota on van els subtitols, en tant per u de l'alcada.
DE, A = 0.70, 0.99
#: Un fotograma cada tant per mirar; no cal mirar-los tots.
CADA = 0.5

os.makedirs(ON, exist_ok=True)
for f in os.listdir(ON):
    os.remove(os.path.join(ON, f))


def durada(cami):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", cami], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


dur = durada(VIDEO)
print("video: %s (%.0f s)" % (os.path.basename(VIDEO), dur))

#: Es treuen els fotogrames petits d'una tirada: mirar-los un per un amb ffmpeg es lentissim.
tmp = os.path.join(ON, "_mir")
os.makedirs(tmp, exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VIDEO, "-vf",
                "fps=%s,crop=iw:ih*%.2f:0:ih*%.2f,scale=320:-1" % (1 / CADA, A - DE, DE),
                os.path.join(tmp, "m%05d.png")], check=True)
mirats = sorted(os.listdir(tmp))
print("fotogrames mirats: %d" % len(mirats))


def vora(a):
    """Quanta vora vertical hi ha: la lletra en te molta, una paret llisa no."""
    d = np.abs(np.diff(a.astype(np.int16), axis=1))
    return float(d.mean())


anterior, candidats = None, []
for i, nom in enumerate(mirats):
    a = np.array(Image.open(os.path.join(tmp, nom)).convert("L"))
    canvi = 999.0 if anterior is None else float(np.abs(a.astype(np.int16)
                                                        - anterior.astype(np.int16)).mean())
    anterior = a
    candidats.append({"i": i, "segon": i * CADA, "canvi": canvi, "vora": vora(a)})

#: Quiets: els que canvien poc respecte del d'abans.
quiets = [c for c in candidats if c["canvi"] < 3.0]
print("moments quiets: %d de %d" % (len(quiets), len(candidats)))
#: I d'aquests, els que tenen mes lletra.
quiets.sort(key=lambda c: -c["vora"])

#: Separar-los pel rellotge NO n'hi ha prou: un subtitol s'esta deu segons a la pantalla i
#: sortien tres retalls identics. Es comparen per IMATGE, que es el que de debo distingeix un
#: subtitol d'un altre. (Les imatges petites ja son al disc: es tornen a llegir.)
def _petita(c):
    return np.array(Image.open(os.path.join(tmp, mirats[c["i"]])).convert("L"),
                    dtype=np.int16)


triats, vistes = [], []
for c in quiets:
    a = _petita(c)
    #: Prou diferent de totes les triades: si no, es el mateix subtitol.
    if any(float(np.abs(a - b).mean()) < 6.0 for b in vistes):
        continue
    triats.append(c)
    vistes.append(a)
    if len(triats) >= QUANTES:
        break
triats.sort(key=lambda c: c["segon"])
print("triats: %d" % len(triats))

fitxa = []
for n, c in enumerate(triats, 1):
    nom = "franja%02d.png" % n
    #: Ara sí, el retall a resolució sencera i ampliat: la persona l'ha de poder llegir.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % c["segon"], "-i", VIDEO,
                    "-frames:v", "1", "-vf",
                    "crop=iw:ih*%.2f:0:ih*%.2f,scale=iw*2:-1" % (A - DE, DE),
                    os.path.join(ON, nom)], check=True)
    if os.path.exists(os.path.join(ON, nom)):
        fitxa.append({"fitxer": nom, "segon": round(c["segon"], 2),
                      "video": os.path.splitext(os.path.basename(VIDEO))[0]})

for f in os.listdir(tmp):
    os.remove(os.path.join(tmp, f))
os.rmdir(tmp)

json.dump(fitxa, io.open(os.path.join(ON, "fitxa.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n%d franges a %s" % (len(fitxa), ON))
for x in fitxa[:5]:
    print("  %s  al segon %.1f" % (x["fitxer"], x["segon"]))
