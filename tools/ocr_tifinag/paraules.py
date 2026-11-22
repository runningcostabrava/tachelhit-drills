"""paraules.py — mostra paraules senceres a 6× en color (del fotograma) amb el número de grup
sota cada glif. Ús:
  python -X utf8 paraules.py --grup 31 [--max 6] [--out fitxer.png]
  python -X utf8 paraules.py 65:1:2 283:0:4 ...      (tram:fila:paraula)"""
import json, os, sys, warnings
warnings.filterwarnings("ignore")
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(AQUI, "glifs.json"), encoding="utf-8"))
L = {s["id"]: s for s in json.load(open(os.path.join(AQUI, "linies.json"), encoding="utf-8"))}
etiq = {}
p = os.path.join(AQUI, "etiquetes.json")
if os.path.exists(p):
    etiq = {int(k[1:]): v.get("glif", "?") for k, v in json.load(open(p, encoding="utf-8")).items() if k.startswith("g") and isinstance(v, dict)}
args = sys.argv[1:]
MAX, OUT, grups, claus = 6, None, [], []
i = 0
while i < len(args):
    a = args[i]
    if a == "--grup":
        grups.append(int(args[i + 1])); i += 2
    elif a == "--max":
        MAX = int(args[i + 1]); i += 2
    elif a == "--out":
        OUT = args[i + 1]; i += 2
    elif a == "--text":
        textos = globals().setdefault("TEXTOS", []); textos.append(args[i + 1]); i += 2
    else:
        t, f, pz = map(int, a.split(":")); claus.append((t, f, pz)); i += 1
par = {}
for g in G:
    par.setdefault((g["linia"], g["fila"], g["paraula"]), []).append(g)
for txt in globals().get("TEXTOS", []):
    n = 0
    for k, gs in par.items():
        lab = "".join(etiq.get(g["grup"], "?") for g in sorted(gs, key=lambda g: g["posicio"])).replace("MARCA", "·")
        if txt in lab and k not in claus and n < MAX:
            claus.append(k); n += 1
if grups:
    for k, gs in par.items():
        if any(g["grup"] in grups for g in gs) and k not in claus:
            claus.append(k)
    claus = claus[:MAX * max(1, len(grups))]
ESC = 6
font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)
ims = []
for (t, f, pz) in claus:
    gs = par[(t, f, pz)]
    x0 = min(g["caixa_fotograma"][0] for g in gs) - 3; x1 = max(g["caixa_fotograma"][2] for g in gs) + 3
    y0 = min(g["caixa_fotograma"][1] for g in gs) - 3; y1 = max(g["caixa_fotograma"][3] for g in gs) + 3
    im = Image.open(os.path.join(AQUI, "fot", L[t]["fotograma"])).convert("RGB").crop((x0, y0, x1, y1))
    im = im.resize((im.width * ESC, im.height * ESC), Image.NEAREST)
    tela = Image.new("RGB", (im.width + 160, im.height + 18), (40, 40, 40))
    tela.paste(im, (160, 0))
    d = ImageDraw.Draw(tela)
    d.text((2, 2), f"t{t} f{f} p{pz}", font=font, fill="yellow")
    for g in gs:
        gx = 160 + (g["caixa_fotograma"][0] - x0) * ESC
        lab = f"{g['grup']}" + (f" {etiq.get(g['grup'], '')}" if etiq else "")
        d.text((gx, im.height + 2), lab, font=font, fill="cyan")
    ims.append(tela)
if not ims:
    print("res"); sys.exit()
W = max(i.width for i in ims); H = sum(i.height + 4 for i in ims)
full = Image.new("RGB", (W, H), (20, 20, 20)); y = 0
for im in ims:
    full.paste(im, (0, y)); y += im.height + 4
nom = OUT or os.path.join(AQUI, "fulls", "paraules_" + ("g" + "_".join(map(str, grups)) if grups else "sel") + ".png")
full.save(nom)
print(nom, full.size, len(ims), "paraules")
