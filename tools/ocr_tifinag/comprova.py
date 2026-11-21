"""comprova.py — tria 5 files a l'atzar (llavor 1114), en desa el retall en color del fotograma
original a 4× (fulls/comprova_N.png) i imprimeix la transcripció, per comparar-les a ull lletra
per lletra. Ús: python -X utf8 comprova.py [llavor] [n]"""
import json, os, random, sys, warnings
warnings.filterwarnings("ignore")
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
llavor = int(sys.argv[1]) if len(sys.argv) > 1 else 1114
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
vid = sys.argv[3] if len(sys.argv) > 3 else ""   # id del vídeo: transcripcio_<vid>.json, fot_<vid>/
T = json.load(open(os.path.join(AQUI, f"transcripcio_{vid}.json" if vid else "transcripcio.json"), encoding="utf-8"))
FOT = os.path.join(AQUI, f"fot_{vid}" if vid else "fot")
random.seed(llavor)
tria = sorted(random.sample(range(len(T)), n))
font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
fulls = []
for k, i in enumerate(tria):
    r = T[i]
    x0, y0, x1, y1 = r["caixa"]
    im = Image.open(os.path.join(FOT, r["fotograma"])).convert("RGB").crop((x0 - 3, y0 - 3, x1 + 3, y1 + 3))
    ESC = 4
    im = im.resize((im.width * ESC, im.height * ESC), Image.NEAREST)
    AMPLE = 700
    tires = [im.crop((x, 0, min(im.width, x + AMPLE), im.height)) for x in range(0, im.width, AMPLE)]
    full = Image.new("RGB", (AMPLE, sum(t.height + 6 for t in tires) + 20), (40, 40, 40))
    d = ImageDraw.Draw(full)
    d.text((2, 2), f"fila {i}: pàgina {r['pagina']} fila {r['fila']} {r['fotograma']} {r['de']}-{r['a']} s", font=font, fill="yellow")
    y = 20
    for t in tires:
        full.paste(t, (0, y)); y += t.height + 6
    nom = os.path.join(AQUI, "fulls", f"comprova_{vid + "_" if vid else ""}{k}.png")
    full.save(nom)
    fulls.append(full)
    print(f"[{k}] fila {i} (pàg {r['pagina']} fila {r['fila']}, {r['fotograma']}, {r['n_glifs']} glifs) -> {nom}")
    print(f"     {r['tifinag']}")
    print(f"     {r['llati']}")

# un sol full amb totes les files, per revisar-les d'un cop
tot = Image.new("RGB", (max(f.width for f in fulls), sum(f.height + 8 for f in fulls)), (90, 90, 90))
y = 0
for f in fulls:
    tot.paste(f, (0, y)); y += f.height + 8
tot.save(os.path.join(AQUI, "fulls", f"comprova_{vid or 'v1'}_tot.png"))
