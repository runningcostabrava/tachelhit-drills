"""Llegir el tifinag cremat SIGNE A SIGNE, agrupant les formes iguals (#439).

Fins ara la sortida per a aquests vídeos era llegir-los a ull amb `carta_de_lletres.py` al
costat. Provat de debò damunt del conte del lleó i el ratolí —`wcUZI6__nk4`, de la Hafida
Benkahia, 2:23, 25 frases—, això **no dona una lectura que es pugui signar**, per dues raons que
val la pena deixar escrites:

· El vídeo **només existeix a 360p** (ho diu `yt-dlp -F`), i a aquesta mida els parells que
  s'assemblen es confonen: la barra sola (`ⵏ`) i les dues barres juntes (`ⵍ`), el cercle amb
  punt (`ⵙ`) i el cercle sol (`ⵔ`), l'anella petita (`ⴰ`) i els dos puntets (`ⵓ`).
· I cada frase és una ocasió nova d'equivocar-se. Vint-i-cinc frases són vint-i-cinc ocasions,
  i l'error no es nota enlloc: surt a l'app com el text de qui parla.

El que aquest guió fa és canviar on es pren la decisió. El vídeo fa servir **sempre la mateixa
lletra**: si es retalla cada signe i s'agrupen els que tenen la mateixa forma, els signes
diferents són trenta i escaig i s'identifiquen **una vegada**. A partir d'aquí la frase surt
sola, i un dubte queda localitzat **en un signe** —i en les poques frases que el porten— en
comptes d'escampar-se per tot el conte.

Això no fa certa la lectura; fa que es pugui comprovar. El que en surti segueix anant a
`*_suggested` i el confirma una persona: el text de qui parla és sagrat.

## Com es fa servir

```bash
export TEXT_DE_VIDEO_DIR=~/feina-video
python tools/text_de_video/frases.py <id> --cada 1     # primer, els talls i els fotogrames
python tools/text_de_video/signes.py <id>              # retalla els signes i agrupa les formes
#   -> <id>/signes/grups.png   un representant de cada forma, numerat: això és el que es mira
#   -> <id>/signes/formes.json les formes desades
#   -> <id>/signes/linies.json cada frase, en números de forma
# s'escriu a ma <id>/signes/lletres.json  {"a": [1, 60], "n": [2], ...}
python tools/text_de_video/signes.py <id> --text       # i surt el text
```

**Les formes es desen a posta.** Sense desar-les, els números de grup depenen de l'ordre en què
es troben, i una segona passada —amb un filtre tocat, o amb un fotograma més— els canvia tots:
la taula de lletres que ha fet una persona queda invalidada sense que res ho digui. Amb
`formes.json`, una passada nova reconeix les formes velles i només numera les noves.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageDraw

#: On van els vídeos i els retalls. El mateix que les altres eines de la carpeta.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))

#: Els llindars de foscor que es proven a cada fotograma. **No n'hi ha cap de bo per a tots**:
#: aquests contes canvien de fons a cada escena, i al conte del lleó hi ha un verd que ja és més
#: fosc que la tinta d'una altra escena. Amb un llindar fix de 90, el fons i les lletres es
#: fonien en una sola taca i de frases que es veuen perfectament en sortien sis signes (frase
#: 27) o dos (frase 30). Triant-lo a cada fotograma, els mateixos 25 fotogrames passen de 527
#: signes de mida de lletra a 874.
LLINDARS = (25, 35, 45, 60, 75, 90, 110)
#: Tots els signes es porten a aquesta mida per poder-los comparar.
MIDA = 24
#: Dues formes són la mateixa a partir d'aquí. Més amunt, la mateixa lletra es parteix en dos
#: grups per una mica de compressió; més avall, la `ⵏ` i la `ⵍ` cauen al mateix sac.
SEMBLA = 0.95
#: Una frase més curta que això és una transició i no es mira.
DURADA_MINIMA = 2


def trossos(mask: np.ndarray) -> List[List[int]]:
    """Els trossos negres enganxats, amb les seves caixes. Sense scipy: una passada amb pila."""
    h, w = mask.shape
    vist = np.zeros_like(mask, dtype=bool)
    out: List[List[int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or vist[y, x]:
                continue
            pila = [(y, x)]
            vist[y, x] = True
            x0 = x1 = x
            y0 = y1 = y
            n = 0
            while pila:
                cy, cx = pila.pop()
                n += 1
                x0, x1 = min(x0, cx), max(x1, cx)
                y0, y1 = min(y0, cy), max(y1, cy)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not vist[ny, nx]:
                            vist[ny, nx] = True
                            pila.append((ny, nx))
            out.append([x0, y0, x1, y1, n])
    return out


def ajunta_punts(caixes: List[List[int]], alt: int) -> List[List[int]]:
    """Dos puntets l'un damunt de l'altre són UNA lletra: la `ⵓ` (i la schwa).

    Això no és un detall. Sense ajuntar-los, cada puntet és un tros massa petit, el filtre de
    mida se'ls menja tots dos i la paraula perd una vocal sense que res ho digui: `uɣrda`
    (ratolí) sortia `ɣrda`."""
    caixes = sorted(caixes, key=lambda c: (c[0], c[1]))
    fet = [False] * len(caixes)
    out: List[List[int]] = []
    for i, c in enumerate(caixes):
        if fet[i]:
            continue
        if _petit(c, alt):
            for j in range(i + 1, len(caixes)):
                d = caixes[j]
                if fet[j] or not _petit(d, alt):
                    continue
                solapen = min(c[2], d[2]) - max(c[0], d[0]) > -2
                a_prop = abs(d[1] - c[1]) < alt * 1.3
                if solapen and a_prop:
                    out.append([min(c[0], d[0]), min(c[1], d[1]),
                                max(c[2], d[2]), max(c[3], d[3]), c[4] + d[4]])
                    fet[i] = fet[j] = True
                    break
        if not fet[i]:
            out.append(c)
            fet[i] = True
    return out


def _petit(c: List[int], alt: int) -> bool:
    return (c[3] - c[1]) < alt * 0.55 and (c[2] - c[0]) < alt * 0.55


def alt_de_lletra(caixes: List[List[int]]) -> int:
    """L'alçada que fa una lletra en aquest fotograma: la mediana de les caixes que en poden ser.

    El filtre de mida d'aquí és el que falta a la versió ingènua. Sense ell, una taca del dibuix
    —un tronc, una ombra— entra a la mediana, l'alçada surt el doble del que toca i després
    tota lletra de debò es queda per sota del mínim: a la frase 27 del conte del lleó, que es
    veu perfectament, en sortien **zero** signes."""
    alts = sorted(c[3] - c[1] for c in caixes
                  if c[4] >= 15 and 6 <= (c[3] - c[1]) <= 40 and (c[2] - c[0]) <= 40)
    return alts[len(alts) // 2] if alts else 12


def sembla_lletra(c: List[int]) -> bool:
    """Una caixa que podria ser una lletra d'aquests vídeos, per mida i prou."""
    return c[4] >= 8 and 6 <= (c[3] - c[1]) <= 40 and 3 <= (c[2] - c[0]) <= 40


def tinta(gris: np.ndarray) -> np.ndarray:
    """La tinta d'aquest fotograma, amb el llindar que en treu més lletres.

    Es tria mirant el resultat i no el fotograma: de tots els llindars, el bo és el que deixa
    més trossos de **mida de lletra**. Això es defensa sol contra el que passa de debò —un fons
    més fosc que la tinta d'una altra escena— sense haver d'endevinar res per endavant."""
    millor, quants = LLINDARS[0], -1
    for t in LLINDARS:
        n = sum(1 for c in trossos(gris < t) if sembla_lletra(c))
        if n > quants:
            millor, quants = t, n
    return gris < millor


def normalitza(tros: np.ndarray) -> np.ndarray:
    """Un signe, portat a una mida fixa i a llargada 1, per poder-lo comparar amb els altres."""
    im = Image.fromarray((tros * 255).astype("uint8")).resize((MIDA, MIDA), Image.BILINEAR)
    v = np.asarray(im, dtype=float) / 255.0
    return v / (np.linalg.norm(v) + 1e-6)


def text_de_linies(linies: List[dict], lletres: Dict[str, List[int]]) -> List[dict]:
    """De números de forma a text, dient quants signes han quedat sense identificar.

    Un signe que ningú no ha dit quin és surt com a punt volat, i la frase que en porti cap
    **no es dona per llegida**. Val més una casella buida que una lectura inventada."""
    de_forma: Dict[int, str] = {}
    for lletra, ids in lletres.items():
        if lletra.startswith("_"):
            continue
        for i in ids:
            de_forma[i] = lletra
    fora = []
    for f in linies:
        parts, dubtes = [], 0
        for fila in f.get("linies", []):
            out = []
            for g in fila:
                if g == -1:
                    out.append(" ")
                elif g in de_forma:
                    out.append(de_forma[g])
                else:
                    out.append("·")
                    dubtes += 1
            if out:
                parts.append("".join(out).strip())
        text = " ".join(p for p in parts if p)
        fora.append({**{k: v for k, v in f.items() if k != "linies"},
                     "text": text, "dubtes": dubtes, "llegida": bool(text) and dubtes == 0})
    return fora


class Formes:
    """Les formes trobades, i com reconèixer-ne una de nova.

    Es desen perquè els números no canviïn d'una passada a l'altra: si canviessin, la taula de
    lletres que ha escrit una persona passaria a dir una altra cosa sense avisar."""

    def __init__(self, desades: Optional[dict] = None):
        self.centres: List[np.ndarray] = []
        self.vistes: List[int] = []
        self.mostra: List[Optional[np.ndarray]] = []
        if desades:
            for g in desades.get("formes", []):
                self.centres.append(np.asarray(g["centre"], dtype=float).reshape(MIDA, MIDA))
                self.vistes.append(int(g.get("vistes", 0)))
                self.mostra.append(None)

    def quina(self, v: np.ndarray) -> int:
        millor, dist = -1, -1.0
        for i, c in enumerate(self.centres):
            s = float(np.dot(v.ravel(), c.ravel()))
            if s > dist:
                dist, millor = s, i
        if millor >= 0 and dist > SEMBLA:
            n = self.vistes[millor] + 1
            nou = (self.centres[millor] * self.vistes[millor] + v) / n
            self.centres[millor] = nou / (np.linalg.norm(nou) + 1e-6)
            self.vistes[millor] = n
            return millor
        self.centres.append(v)
        self.vistes.append(1)
        self.mostra.append(None)
        return len(self.centres) - 1

    def desa(self, fitxer: Path) -> None:
        fitxer.write_text(json.dumps({
            "_llegeix-me": "Les formes trobades. No les toquis a mà: el que s'escriu a mà és "
                           "lletres.json, que diu quin número és quina lletra.",
            "formes": [{"id": i, "vistes": self.vistes[i], "centre": self.centres[i].ravel().round(4).tolist()}
                       for i in range(len(self.centres))],
        }, ensure_ascii=False), encoding="utf-8")


def signes_de_frase(fotograma: Path, formes: Formes) -> List[List[int]]:
    """Els signes d'un fotograma, per files i d'esquerra a dreta, en números de forma.

    Un -1 vol dir un espai entre paraules."""
    im = Image.open(fotograma).convert("L")
    w, h = im.size
    mask = tinta(np.asarray(im.crop((0, int(h * 0.50), w, int(h * 0.99)))))
    caixes = [c for c in trossos(mask) if c[4] >= 4]
    if not caixes:
        return []
    alt = alt_de_lletra(caixes)
    caixes = [c for c in ajunta_punts(caixes, alt)
              if c[4] >= 8 and alt * 0.35 <= (c[3] - c[1]) <= alt * 2.0 and (c[2] - c[0]) <= alt * 2.0]
    files: List[List[List[int]]] = []
    for c in sorted(caixes, key=lambda c: c[1]):
        for fila in files:
            centre = sum((x[1] + x[3]) / 2 for x in fila) / len(fila)
            if abs((c[1] + c[3]) / 2 - centre) < alt * 0.6:
                fila.append(c)
                break
        else:
            files.append([c])
    files = sorted((sorted(f, key=lambda c: c[0]) for f in files), key=lambda f: min(c[1] for c in f))
    fora = []
    for fila in files:
        if len(fila) < 3:
            continue
        seq, anterior = [], None
        for c in fila:
            if anterior is not None and c[0] - anterior > alt * 0.75:
                seq.append(-1)
            seq.append(formes.quina(normalitza(mask[c[1]:c[3] + 1, c[0]:c[2] + 1])))
            anterior = c[2]
        fora.append(seq)
    return fora


def full_de_formes(formes: Formes, mostres: Dict[int, np.ndarray], fitxer: Path) -> None:
    """El full que mira una persona: un representant de cada forma, gros i numerat."""
    ordre = sorted(range(len(formes.centres)), key=lambda i: -formes.vistes[i])
    col, cel = 8, 120
    files = (len(ordre) + col - 1) // col
    full = Image.new("RGB", (col * cel, max(1, files) * cel), (255, 255, 255))
    dib = ImageDraw.Draw(full)
    for pos, i in enumerate(ordre):
        cx, cy = (pos % col) * cel, (pos // col) * cel
        dib.rectangle([cx, cy, cx + cel - 2, cy + cel - 2], outline=(205, 205, 205))
        dib.text((cx + 5, cy + 5), "#%d x%d" % (i, formes.vistes[i]), fill=(190, 0, 0))
        tros = mostres.get(i)
        if tros is None:
            continue
        glif = Image.fromarray(((1 - tros) * 255).astype("uint8")).convert("RGB")
        esc = min((cel - 40) / glif.width, (cel - 40) / glif.height)
        glif = glif.resize((max(1, int(glif.width * esc)), max(1, int(glif.height * esc))), Image.LANCZOS)
        full.paste(glif, (cx + (cel - glif.width) // 2, cy + 26 + (cel - 40 - glif.height) // 2))
    full.save(fitxer)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    vid = args[0]
    feina = ON / vid
    fora = feina / "signes"
    fora.mkdir(parents=True, exist_ok=True)

    if "--text" in args:
        linies = json.loads((fora / "linies.json").read_text(encoding="utf-8"))
        mapa = fora / "lletres.json"
        if not mapa.exists():
            print("falta %s: digues quin número és quina lletra mirant grups.png" % mapa)
            return
        fet = text_de_linies(linies, json.loads(mapa.read_text(encoding="utf-8")))
        for f in fet:
            print("%3d  %4ds-%4ds  dubtes=%-3d %s" % (f["frase"], f["inici"], f["fi"], f["dubtes"], f["text"]))
        print("\nfrases llegides senceres, sense cap dubte: %d de %d"
              % (sum(1 for f in fet if f["llegida"]), len(fet)))
        (fora / "text.json").write_text(json.dumps(fet, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    desades = fora / "formes.json"
    formes = Formes(json.loads(desades.read_text(encoding="utf-8")) if desades.exists() else None)
    sabudes = len(formes.centres)
    talls = json.loads((feina / "frases.json").read_text(encoding="utf-8"))
    linies, mostres = [], {}
    for f in talls["frases"]:
        if f["fi"] - f["inici"] < DURADA_MINIMA:
            continue
        mig = (f["inici"] + f["fi"]) // 2
        fotograma = feina / "totes" / ("f_%04d.jpg" % (mig + 1))
        if not fotograma.exists():
            print("falta %s: passa-hi abans pantalles.py" % fotograma)
            return
        abans = len(formes.centres)
        fila = signes_de_frase(fotograma, formes)
        linies.append({"frase": f["n"], "inici": f["inici"], "fi": f["fi"], "segon": mig, "linies": fila})
        for nova in range(abans, len(formes.centres)):
            mostres.setdefault(nova, None)
    # una mostra per forma, per poder-les mirar
    for f in linies:
        mig = f["segon"]
        im = Image.open(feina / "totes" / ("f_%04d.jpg" % (mig + 1))).convert("L")
        w, h = im.size
        mask = tinta(np.asarray(im.crop((0, int(h * 0.50), w, int(h * 0.99)))))
        caixes = [c for c in trossos(mask) if c[4] >= 4]
        if not caixes:
            continue
        alt = alt_de_lletra(caixes)
        for c in ajunta_punts(caixes, alt):
            if not (c[4] >= 8 and alt * 0.35 <= (c[3] - c[1]) <= alt * 2.0 and (c[2] - c[0]) <= alt * 2.0):
                continue
            tros = mask[c[1]:c[3] + 1, c[0]:c[2] + 1]
            v = normalitza(tros)
            for i, centre in enumerate(formes.centres):
                if float(np.dot(v.ravel(), centre.ravel())) > SEMBLA and mostres.get(i) is None:
                    mostres[i] = tros
                    break

    (fora / "linies.json").write_text(json.dumps(linies, ensure_ascii=False), encoding="utf-8")
    formes.desa(desades)
    full_de_formes(formes, mostres, fora / "grups.png")
    print("frases: %d · signes: %d · formes: %d (%d ja sabudes)"
          % (len(linies), sum(formes.vistes), len(formes.centres), sabudes))
    print("mira %s i escriu %s" % (fora / "grups.png", fora / "lletres.json"))


if __name__ == "__main__":
    main()
