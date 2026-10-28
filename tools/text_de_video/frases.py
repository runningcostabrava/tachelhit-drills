"""Treure les FRASES d'un conte amb els subtítols cremats a la imatge (#291).

Els contes d'en Rajae Marzouki i de la Hafida Benkahia porten, en una franja negra a baix, dues
línies alhora: **la frase en tifinag i la seva traducció a l'àrab**. I a sobre hi ha la veu de qui
el narra dient aquella mateixa frase. És a dir: text, significat i so, tots tres alineats. Això és
exactament la forma d'una frase de la biblioteca —menys el permís, que no el dona cap guió.

El que aquest guió fa, i el que deixa expressament per a una persona:

· **Fa**: troba quan canvia la franja de baix (i només la franja: el dibuix de sobre es mou tota
  l'estona i no vol dir res), li posa començament i final, en retalla la imatge i en talla el
  tros de veu que li correspon.
· **No fa**: llegir. El tifinag d'aquests vídeos no el sap llegir cap OCR nostre —l'EasyOCR del
  Space va per al llatí i l'àrab—, i una lectura dolenta entraria com a text de qui parla, que és
  el que mai no s'ha de tocar. Les imatges surten preparades perquè les llegeixi algú (o jo), i
  el que en surti va a `*_suggested` fins que una persona ho confirmi.

També mira com de QUIETA està la franja: quan una frase es pinta de cop i s'està tres segons, el
fotograma bo és qualsevol dels del mig; el que no val és el de la transició.

Ús:  python treu_subtitols.py <id> [--cada 1] [--caixa esq,dalt,dret,baix] [--canvi 4]
Surt: <id>/frases/f_###.png (la franja, al doble) · <id>/frases/f_###.m4a (la veu)
      <id>/frases.json  (número, del segon X al Y, fitxers)
"""
from __future__ import annotations

import json
import subprocess
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)
#: Sota d'això, la franja és negre pla: ningú no hi diu res.
TINTA_MINIMA = 6.0
#: Una frase més curta que això és una transició, no una frase.
DURADA_MINIMA = 1.0


def veu(vid: str, feina: Path) -> Path:
    """La veu sencera del vídeo, a part: el que es talla després surt d'aquí."""
    fitxer = feina / f"{vid}.m4a"
    if fitxer.exists():
        return fitxer
    subprocess.run([
        sys.executable, "-m", "yt_dlp", "-f", "ba[ext=m4a]/ba/b",
        "--extractor-args", "youtube:player_client=android,web",
        "--no-playlist", "-o", str(fitxer),
        f"https://www.youtube.com/watch?v={vid}",
    ], check=True)
    return fitxer


def _caixa(mida, c):
    """On és la caixa del text dins del fotograma, en tant per u (esq, dalt, dret, baix).

    Dues trampes seguides, que valen per a tots aquests contes:

    · no és «el tros de baix»: el conte va emmarcat i la franja del text seu dins del rectangle,
      amb negre per sota;
    · i no és tota l'amplada: la caixa negra és **només al mig**, i a banda i banda hi continua
      el dibuix, que es mou sempre. Mirant la franja sencera, cada segon semblava una frase nova.

    Per això es mesura només la caixa, i cada vídeo porta la seva a `VIDEOS`."""
    w, h = mida
    return (int(w * c[0]), int(h * c[1]), int(w * c[2]), int(h * c[3]))


#: On seu el text a cada vídeo, en tant per u (esquerra, dalt, dreta, baix).
#:
#: Això està escrit a mà, mirant un fotograma de cada vídeo, i no endevinat. Val la pena dir per
#: què: el detector automàtic de més avall endevina bé un vídeo i es menja el fotograma sencer al
#: següent, perquè cada canal posa el text on vol —caixa negra a baix, dues ratlles damunt del
#: dibuix, un plafó a la dreta— i no hi ha cap senyal que valgui per a tots. Mirar-ne un
#: fotograma costa un cop d'ull i no falla; afinar el detector a cegues costa una tarda i falla.
#: Per a un vídeo que no hi sigui, el detector proposa una caixa i aleshores **s'ha de mirar**.
CAIXES = {
    # Rajae Marzouki (Figuig): caixa negra a baix, tifinag a dalt i àrab a sota.
    "ce3s668AaSw": [0.34, 0.855, 0.70, 1.0],
    "6jN4ob9u4eQ": [0.20, 0.800, 0.80, 0.97],
    # Rajae Marzouki: sense caixa, dues ratlles damunt del dibuix (llatí en cursiva + tifinag).
    "issyx0SahJc": [0.15, 0.520, 0.85, 0.82],
    "13v1ggb7LJM": [0.14, 0.400, 0.87, 0.79],
    # Hafida Benkahia: un plafó negre a la dreta amb tot un tros de conte en tifinag.
    "WMb3hNiuYLM": [0.42, 0.030, 1.00, 0.97],
    "wcUZI6__nk4": [0.15, 0.780, 0.85, 0.96],
}


def _blanc(f: Path):
    """La lletra sola: el blanc viu del fotograma, sense el dibuix de sota.

    A tots aquests contes el text va en blanc, sigui damunt d'una caixa negra, d'un bosc o d'un
    dibuix. El que NO canvia d'un canal a l'altre és això: la lletra és el més blanc que hi ha.
    Buscar una caixa negra només va servir per a un dels sis."""
    im = Image.open(f).convert("L")
    return im.point(lambda v: 255 if v > 195 else 0), im.size


def caixa_automatica(imgs) -> list:
    """Trobar sol ON és el text, mirant unes quantes pantalles del vídeo.

    De trenta pantalles escampades se'n pren només el blanc de la lletra i es compta quanta n'hi
    ha a cada fila i a cada columna. Les files on gairebé sempre hi ha lletra són el text; el
    dibuix, que es mou, no es repeteix mai al mateix lloc. La caixa és el tros que queda, amb un
    dit de marge.

    Si no hi surt res prou constant, torna None: val més dir que aquí no s'ha trobat text que
    posar-se a tallar «frases» d'un tros de cel.
    """
    mostra = imgs[:: max(1, len(imgs) // 30)][:30]
    if not mostra:
        return None
    masks = [_blanc(f) for f in mostra]
    w, h = masks[0][1]
    n = len(masks)

    files = [0] * h
    cols = [0] * w
    for m, _ in masks:
        px = m.load()
        for y in range(0, h, 2):
            fila = 0
            for x in range(0, w, 4):
                if px[x, y]:
                    fila += 1
                    cols[x] += 1
            if fila >= 3:          # tres taques blanques en una fila ja és una ratlla de lletra
                files[y] += 1

    te_text = [y for y in range(0, h, 2) if files[y] >= n * 0.30]
    if len(te_text) < 6:
        return None
    dalt, baix = min(te_text), max(te_text) + 2
    mitjana = (sum(cols) / max(1, len([c for c in cols if c])))
    amb = [x for x in range(0, w, 4) if cols[x] >= mitjana * 0.25]
    if len(amb) < 6:
        return None
    esq, dret = min(amb), max(amb) + 4

    alt = (baix - dalt) / h
    marge_v = max(6, int((baix - dalt) * 0.12))
    marge_h = max(10, int((dret - esq) * 0.03))
    return [round(max(0, esq - marge_h) / w, 4), round(max(0, dalt - marge_v) / h, 4),
            round(min(w, dret + marge_h) / w, 4), round(min(h, baix + marge_v) / h, 4), round(alt, 3)]


def _franja(f: Path, c):
    """La caixa del text, en gris petit i també com a màscara de lletra.

    Torna (gris, lletra): el gris serveix per dir si això ÉS una caixa de subtítol, i la
    màscara —només el blanc viu de la lletra— per dir si el text ha CANVIAT. Comparant el gris
    sencer, el dibuix que s'escola per les vores movia el resultat tota l'estona."""
    im = Image.open(f).convert("L").crop(_caixa(Image.open(f).size, c)).resize((320, 60))
    return im, im.point(lambda v: 255 if v > 170 else 0)


def hi_ha_res(gris) -> bool:
    """Si en aquesta caixa hi ha res de res: només rebutja una pantalla plana.

    Abans aquí hi havia una prova més fina —«fons negre amb lletra blanca»—, i servia per a un
    sol dels sis contes. Els altres posen el text damunt d'un bosc o d'un dibuix groc, i la prova
    els deixava fora sencers: zero frases d'un conte que en té trenta.

    Qui separa les frases, doncs, és el CANVI del text, no el seu color; i el que decideix què és
    bo és qui ho mira després. Tallar de més costa unes quantes imatges de sobres; tallar de menys
    perd frases d'algú que les ha dites, i això no es recupera."""
    return ImageStat.Stat(gris).stddev[0] >= 3.0


def talla(vid: str, cada: int, c, llindar: float) -> list[dict]:
    feina = ON / vid
    imgs = sorted((feina / "totes").glob("f_*.jpg"))
    if not imgs:
        sys.exit("primer cal treure els fotogrames amb treu_taules.py")

    parts = [_franja(f, c) for f in imgs]
    hi_ha = [hi_ha_res(g) for g, _ in parts]
    canvi = [99.0] + [ImageStat.Stat(ImageChops.difference(parts[i - 1][1], parts[i][1])).mean[0]
                      for i in range(1, len(parts))]

    frases, actual = [], None
    for i in range(len(imgs)):
        tanca = actual is not None and (not hi_ha[i] or canvi[i] >= llindar)
        if tanca:
            actual["fi"] = i * cada
            frases.append(actual)
            actual = None
        if hi_ha[i] and actual is None:
            actual = {"inici": i * cada, "i": i}
        elif actual is not None and canvi[i] < canvi[actual["i"]]:
            # El fotograma MÉS QUIET de la frase: la lletra ja hi és tota i encara no s'esborra.
            actual["i"] = i
    if actual:
        actual["fi"] = len(imgs) * cada
        frases.append(actual)

    return [f for f in frases if f["fi"] - f["inici"] >= DURADA_MINIMA]


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    vid = args[0]
    cada = int(args[args.index("--cada") + 1]) if "--cada" in args else 1
    imgs0 = sorted((ON / vid / "totes").glob("f_*.jpg"))
    if "--caixa" in args:
        c = [float(x) for x in args[args.index("--caixa") + 1].split(",")]
    elif vid in CAIXES:
        c = CAIXES[vid]
    else:
        c = caixa_automatica(imgs0)
        if c is not None:
            c = c[:4]
        if c is None:
            print("%s: aqui no hi ha cap caixa de subtitols" % vid)
            return
    print("caixa:", c)
    llindar = float(args[args.index("--canvi") + 1]) if "--canvi" in args else 4.0

    feina = ON / vid
    frases = talla(vid, cada, c, llindar)
    so = veu(vid, feina)
    fora = feina / "frases"
    fora.mkdir(exist_ok=True)
    for vell in fora.iterdir():
        vell.unlink()

    imgs = sorted((feina / "totes").glob("f_*.jpg"))
    taula = []
    for n, fr in enumerate(frases, 1):
        im = Image.open(imgs[fr["i"]])
        # Per llegir-la es guarda MÉS AMUNT i més ampla del que s'ha mesurat. El que es mesura
        # és la part de la caixa que hi és sempre —a aquests contes, la línia de l'àrab—, i just
        # a sobre hi ha la línia amaziga, que és la que de debò volem llegir.
        tros = im.crop(_caixa(im.size, [max(0.0, c[0] - .02), max(0.0, c[1] - .01),
                                        min(1.0, c[2] + .02), min(1.0, c[3] + .01)]))
        tros = tros.resize((tros.width * 2, tros.height * 2), Image.LANCZOS)
        png = fora / ("f_%03d.png" % n)
        tros.save(png)
        m4a = fora / ("f_%03d.m4a" % n)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-ss", str(fr["inici"]), "-to", str(fr["fi"]),
                        "-i", str(so), "-c", "copy", str(m4a)], check=False)
        taula.append({"n": n, "inici": fr["inici"], "fi": fr["fi"],
                      "imatge": png.name, "veu": m4a.name})
    (feina / "frases.json").write_text(
        json.dumps({"video": vid, "frases": taula}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("%s: %d frases" % (vid, len(taula)))
    for t in taula:
        print("  %3d  %4ds-%4ds  %s" % (t["n"], t["inici"], t["fi"], t["imatge"]))


if __name__ == "__main__":
    main()
