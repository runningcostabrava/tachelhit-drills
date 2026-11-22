"""La carta de les lletres: cada signe tifinag amb la seva lletra llatina al costat.

No es per a l'app: es perque qui llegeix les pantalles del video pugui dir quin signe es quin
sense anar de memoria. Les parelles surten del NOSTRE transliterador (`transliteration._TIFINAGH`),
que es el que mana a tot el projecte, i es dibuixen amb l'Ebrima, la lletra de Windows que te
tifinag.
"""
import os
import sys
from pathlib import Path

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from transliteration import _TIFINAGH  # noqa: E402

parelles = [(lla, tif) for lla, tif in _TIFINAGH.items() if len(tif) == 1]
cols, fila_h, col_w = 6, 120, 230
files = (len(parelles) + cols - 1) // cols
im = Image.new("RGB", (cols * col_w + 20, files * fila_h + 20), "white")
d = ImageDraw.Draw(im)
tif_f = ImageFont.truetype(r"C:\Windows\Fonts\ebrima.ttf", 64)
lla_f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 34)
for i, (lla, tif) in enumerate(parelles):
    x, y = 10 + (i % cols) * col_w, 10 + (i // cols) * fila_h
    d.rectangle([x, y, x + col_w - 6, y + fila_h - 6], outline="#ccc")
    d.text((x + 16, y + 18), tif, font=tif_f, fill="black")
    d.text((x + 110, y + 34), "= " + lla, font=lla_f, fill="#b00")
f = ON / "carta_tifinag.png"
im.save(f)
print(f, len(parelles), "lletres")
