"""Una tira de frases en una sola imatge, numerades, per poder-les llegir de cop.

Mirar-les d'una en una costa un viatge per frase; aixi en van vuit o deu en una.
Us:  python tira.py <id> <de> <fins>
"""
import os
import sys
from pathlib import Path

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)
from PIL import Image, ImageDraw, ImageFont

vid, de, fins = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
fora = ON / vid / "frases"
imgs = [fora / ("f_%03d.png" % n) for n in range(de, fins + 1)]
imgs = [p for p in imgs if p.exists()]
f = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 26)
trossos = []
for p in imgs:
    im = Image.open(p).convert("RGB")
    nou = Image.new("RGB", (im.width + 90, im.height), "white")
    nou.paste(im, (90, 0))
    d = ImageDraw.Draw(nou)
    d.text((8, im.height // 2 - 14), p.stem.split("_")[1], font=f, fill="black")
    trossos.append(nou)
w = max(t.width for t in trossos)
h = sum(t.height + 8 for t in trossos)
tira = Image.new("RGB", (w, h), "white")
y = 0
for t in trossos:
    tira.paste(t, (0, y)); y += t.height + 8
d = ON / vid / ("tira_%03d_%03d.png" % (de, fins))
tira.save(d)
print(d, tira.size)
