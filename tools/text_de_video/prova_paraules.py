"""Escriure unes paraules en tifinag amb el NOSTRE transliterador, ben grosses, per comparar-les
amb el que es veu a la pantalla del video. Aixi la lectura no depen de recordar la carta."""
import os
import sys
from pathlib import Path

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from transliteration import to_forms

mots = sys.argv[1:] or ["izm", "ixf", "ifri", "izf", "ixm"]
tif = ImageFont.truetype(r"C:\Windows\Fonts\ebrima.ttf", 86)
lla = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 40)
im = Image.new("RGB", (900, 120 * len(mots) + 20), "white")
d = ImageDraw.Draw(im)
for i, m in enumerate(mots):
    y = 10 + i * 120
    d.text((20, y + 10), to_forms(m)["tifinagh"], font=tif, fill="black")
    d.text((520, y + 32), "= " + m, font=lla, fill="#b00")
f = ON / "prova_paraules.png"
im.save(f); print(f)
