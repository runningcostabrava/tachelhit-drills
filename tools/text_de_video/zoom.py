"""Un tros petit d'una pantalla, ben gros: per mirar signes que s'assemblen."""
import os
import sys
from pathlib import Path

#: On van els vídeos baixats i els retalls. No és dins del repositori a posta: són fitxers
#: grossos i de ningú —el vídeo és de qui l'ha fet— i aquí només hi ha l'eina que els mira.
ON = Path(os.environ.get("TEXT_DE_VIDEO_DIR", Path.cwd() / "feina"))
ON.mkdir(parents=True, exist_ok=True)
from PIL import Image
vid, segon = sys.argv[1], int(sys.argv[2])
esq, dalt, dret, baix = [float(x) for x in sys.argv[3].split(",")]
veus = int(sys.argv[4]) if len(sys.argv) > 4 else 4
im = Image.open(ON / vid / "gran" / ("s_%05d.png" % segon))
w, h = im.size
t = im.crop((int(w*esq), int(h*dalt), int(w*dret), int(h*baix)))
t = t.resize((t.width*veus, t.height*veus), Image.LANCZOS)
f = ON / vid / "gran" / ("zoom_%05d.png" % segon)
t.save(f); print(f, t.size)
