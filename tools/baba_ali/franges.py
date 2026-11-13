"""Treu del vídeo una franja de subtítol per segon, i mesura ON és la franja.

El camí per posar un episodi nou a la biblioteca comença aquí: aquestes franges són el que el
Qwen llegeix a Kaggle (`tools/notebooks/llegeix_episodi_arab.py`), i d'allà en surten les línies
amb el seu segon.

## Per què la franja es MESURA i no s'hereta

`canvis.py` fa servir `crop=1280:120:0:572`, que surt de les pujades dels episodis 7 i 9. La
pujada «1-2» no hi casa de cap manera: porta **barres negres** (la imatge va de la fila 52 a la
648 de 720) i el subtítol cau a baix de tot de la IMATGE, cap a la fila 630, no a baix del
fotograma. Amb la franja heretada, buscant-hi subtítols en sortien 25 en 22 minuts; l'episodi 2
en té 210.

I hi ha un parany a sobre: a dalt del fotograma hi ha una banda blanca al **100 %** dels
fotogrames. No és cap subtítol, és el rètol SUBSCRIBE que va afegir qui va pujar el vídeo. Qui
busqui «on hi ha més blanc» el trobarà a ell. Per això el mesurador ensenya el perfil sencer
perquè es miri amb els ulls, i la tria es desa al costat de les imatges.

## Per què una per segon i no una per subtítol

Perquè decidir on comença i on acaba un subtítol comptant píxels **no funciona** — està provat
tres vegades i escrit a `tools/notebooks/llegir_imatges_qwen.py`. Un fotograma per segon, i els
que diguin el mateix s'ajunten després, quan ja se sap què diuen.

## Ús

    python franges.py mira  video.mp4                      # on és la franja
    python franges.py treu  video.mp4 --de 35 --fins 1341 \\
                            --franja 1920:150:0:845 --a ep1_kaggle
"""
import argparse
import json
import os
import subprocess

import numpy as np

ALT, AMPLE = 720, 1280     #: el perfil es mesura sempre aquí, sigui quina sigui la font
LLINDAR = 200              #: el text del subtítol és gairebé blanc; l'escena, rarament


def _ffmpeg(args):
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error"] + args,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("ffmpeg: " + p.stderr.decode("utf-8", "replace")[-500:])
    return p.stdout


def mira(video, de, fins, quantes):
    """El perfil de blanc per alçada, perquè es miri amb els ulls."""
    pas = (fins - de) / quantes
    crua = _ffmpeg(["-ss", str(de), "-to", str(fins), "-i", video,
                    "-vf", f"scale={AMPLE}:{ALT},format=gray,fps=1/{pas:.4f}",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    f = np.frombuffer(crua, dtype=np.uint8)
    n = len(f) // (ALT * AMPLE)
    f = f[:n * ALT * AMPLE].reshape(n, ALT, AMPLE)
    print(f"{n} fotogrames de mostra, de {de:.0f} a {fins:.0f} s")

    blanc = f > LLINDAR
    sovint = (blanc.sum(axis=2) > 20).mean(axis=0)
    per_fila = blanc.sum(axis=2).mean(axis=0)

    mitjana = f.mean(axis=(0, 2))
    imatge = np.where(mitjana > 6)[0]
    if len(imatge):
        print(f"imatge de debò: files {imatge[0]}–{imatge[-1]} "
              f"(barres negres: {imatge[0]} a dalt, {ALT - 1 - imatge[-1]} a baix)")

    print(f"\n{'files':>11} {'blanc/fot.':>11} {'% fot. amb blanc':>17}")
    for y in range(0, ALT, 10):
        s = sovint[y:y + 10].mean() * 100
        print(f"{y:>4}-{y+9:<6} {per_fila[y:y+10].mean():>11.1f} {s:>16.0f}%  "
              + "#" * int(min(60, s / 100 * 60)))
    print("\nLa franja és la banda, a BAIX DE LA IMATGE, on el blanc surt sovint però no sempre.")
    print("Una banda que surt al 100 % dels fotogrames és un rètol fix, no un subtítol.")
    if len(imatge):
        y = max(0, imatge[-1] - 60)
        print(f"\nproposta (els 80 últims de la imatge):  --franja "
              f"{int(AMPLE*1.5)}:{int(80*1.5)}:0:{int(y*1.5)}   (en 1920x1080)")


def treu(video, de, fins, franja, a):
    """Una franja per segon, en gris, a `a/arab/`, amb el rellotge al costat."""
    arab = os.path.join(a, "arab")
    os.makedirs(arab, exist_ok=True)
    print(f"traient una franja per segon, de {de} a {fins}…")
    _ffmpeg(["-ss", str(de), "-to", str(fins), "-i", video,
             "-vf", f"crop={franja},format=gray,fps=1", "-y", os.path.join(arab, "%05d.png")])
    quantes = len([f for f in os.listdir(arab) if f.endswith(".png")])
    #: El fitxer 00001 és el segon `de`, i d'allà endavant un per segon. Es desa perquè qui
    #: llegeixi les imatges no ho hagi de deduir, que és d'on surten els errors d'índex.
    json.dump({"segons": {f"{i:05d}.png": int(de) + i - 1 for i in range(1, quantes + 1)},
               "de_segon": int(de), "fins_segon": int(fins), "franja": franja,
               "video": os.path.basename(video)},
              open(os.path.join(a, "temps.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{quantes} franges a {arab}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("que", choices=["mira", "treu"])
    p.add_argument("video")
    p.add_argument("--de", type=float, default=0)
    p.add_argument("--fins", type=float, default=600)
    p.add_argument("--mostres", type=int, default=240)
    p.add_argument("--franja", default="1920:150:0:845", help="amplada:alçada:x:y, en 1920x1080")
    p.add_argument("--a", default="franges", help="on es desen (hi farà arab/ i temps.json)")
    o = p.parse_args()
    if o.que == "mira":
        mira(o.video, o.de, o.fins, o.mostres)
    else:
        treu(o.video, o.de, o.fins, o.franja, o.a)
