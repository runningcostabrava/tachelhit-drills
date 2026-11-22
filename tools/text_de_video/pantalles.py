"""Treure les TAULES d'un vídeo de gramàtica, una per pantalla (#313).

El canal d'Ait ouarab Lhoucine explica la gramàtica amb taules escrites a la pantalla en quatre
escriptures —tifinag, llatí, francès i àrab— i amb la seva veu a sobre. El text viu **a la
imatge**: aquests vídeos no porten subtítols i la descripció només té el títol.

Per què no l'OCR: el nostre Space d'OCR llegeix llatí i àrab de subtítols enganxats a baix, i
aquí el text és una taula sencera a tota la pantalla; i el tifinag, els OCR de fora amb prou
feines el saben llegir. El que sí que surt bé és **mirar-s'ho**: aquest guió prepara les
pantalles i qui les llegeix és el model, que llegeix les quatre escriptures.

Què fa, doncs:

1. baixa el vídeo a una mida petita (no es desa res més que a la carpeta de treball);
2. en treu una imatge cada pocs segons;
3. **es queda una sola imatge per pantalla**: compara cada imatge amb l'anterior i, mentre no
   canviï prou, és la mateixa taula. Una taula que està vint segons a la pantalla dona una
   imatge, no quatre.

El que en surt és una carpeta de pantalles numerades amb el seu segon, a punt per llegir-les i
escriure-les a mà en una proposta —que és el que farà una persona (o jo) després, i que entrarà
com a suggeriment, mai com a text d'un parlant.

Ús:  python treu_taules.py <id del vídeo> [--cada 4] [--canvi 6.0]
"""
from __future__ import annotations

import subprocess
import os
import sys
from pathlib import Path

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)


def baixa(vid: str, cap_a: Path) -> Path:
    """El vídeo, petit: per llegir una taula no cal alta definició."""
    fitxer = cap_a / f"{vid}.mp4"
    if fitxer.exists():
        return fitxer
    # Nomes la imatge: la veu no es llegeix, i el vídeo sol pesa la meitat. A 720p, que es el
    # que el canal puja i el minim per llegir una taula de quatre escriptures.
    subprocess.run([
        sys.executable, "-m", "yt_dlp",
        "-f", "bv*[height<=720][protocol^=http]/bv*[height<=720]/b[height<=720]/b",
        # Sense client «android» el YouTube diu que vídeos ben vius «no estan disponibles»
        # (ho tenim escrit: `ytdlp-player-client-false-unavailable`).
        "--extractor-args", "youtube:player_client=android,web",
        "--no-playlist", "-o", str(fitxer),
        f"https://www.youtube.com/watch?v={vid}",
    ], check=True)
    return fitxer


def pantalles(video: Path, cap_a: Path, cada: int) -> list[Path]:
    """Una imatge cada `cada` segons, totes a la mateixa mida."""
    cap_a.mkdir(parents=True, exist_ok=True)
    for vell in cap_a.glob("*.jpg"):
        vell.unlink()
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps=1/{cada},scale=1024:-1", "-q:v", "3",
        str(cap_a / "f_%04d.jpg"),
    ], check=True)
    return sorted(cap_a.glob("f_*.jpg"))


def _petita(f):
    from PIL import Image
    return Image.open(f).convert("L").resize((160, 90))


def canvia_prou(a, b) -> float:
    """Quant es diferencien dues pantalles, de 0 a 100.

    Es mira en petit i en gris: el que interessa es si **la taula ha canviat**, no si el cursor
    s'ha mogut un pel."""
    from PIL import ImageChops, ImageStat
    ia = a if hasattr(a, "size") else _petita(a)
    ib = b if hasattr(b, "size") else _petita(b)
    return ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0] / 2.55


def tria_les_bones(totes, cada, llindar, quiet=1.2):
    """Una pantalla per tanda: l'ULTIMA que estigui QUIETA.

    Dues trampes que aquest video ensenya de seguida:

    · la pantalla **es va omplint** fila a fila mentre ell parla, de manera que la primera imatge
      d'una taula sovint es la taula buida: val la del final;
    · entre pantalla i pantalla hi ha una **animacio de passar full**, i just el fotograma del
      final de la tanda cau enmig del full doblegat, amb mitja taula tapada.

    Per aixo es mira, a mes del canvi gran que separa tandes, si cada imatge esta quieta respecte
    de la d'abans; de cada tanda es guarda l'ultima quieta, que es la taula sencera i plana."""
    petites = [_petita(f) for f in totes]
    diff = [0.0] + [canvia_prou(petites[i - 1], petites[i]) for i in range(1, len(petites))]

    tandes, actual = [], []
    for i in range(len(totes)):
        if diff[i] >= llindar and actual:
            tandes.append(actual)
            actual = []
        actual.append(i)
    if actual:
        tandes.append(actual)

    fora = []
    for t in tandes:
        quietes = [i for i in t if diff[i] < quiet]
        fora.append(quietes[-1] if quietes else t[-1])
    return fora


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    vid = args[0]
    cada = int(args[args.index("--cada") + 1]) if "--cada" in args else 3
    llindar = float(args[args.index("--canvi") + 1]) if "--canvi" in args else 5.0

    feina = ON / vid
    feina.mkdir(parents=True, exist_ok=True)
    video = baixa(vid, feina)
    totes = pantalles(video, feina / "totes", cada)
    print("imatges: %d (una cada %ds)" % (len(totes), cada))

    tria = feina / "pantalles"
    tria.mkdir(exist_ok=True)
    for vell in tria.glob("*.jpg"):
        vell.unlink()

    bones = tria_les_bones(totes, cada, llindar)
    print("pantalles diferents: %d" % len(bones))
    for n, i in enumerate(bones, 1):
        segon = i * cada
        desti = tria / ("p_%03d_%02d-%02d.jpg" % (n, segon // 60, segon % 60))
        desti.write_bytes(totes[i].read_bytes())
        print("  ", desti.name)


if __name__ == "__main__":
    main()
