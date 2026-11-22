"""El desempat per topologia, ¿val? Mesurat en un capítol sencer, amb i sense.

Dues mesures, perquè una sola es pot moure per casualitat:

  1. la taxa d'acord amb el que sent el model (la vara de sempre);
  2. com escriu el lector la paraula `tskla`, que és on vam veure la fallada.

Si la taxa no puja, el desempat no val encara que arregli `tskla`: arreglar una paraula i
espatllar-ne tres no és una millora.
"""
import io
import json
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image

MAG = Path(r"E:\tamazight\_magatzem")
sys.path.insert(0, str(MAG))
FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import lector_tifinag as L        # noqa: E402
import tifinag_plantilles as PL   # noqa: E402
import desempat_topologic as DT   # noqa: E402

SLUG = sys.argv[1] if len(sys.argv) > 1 else "bueyrhjvjyaleocffcrxdtmeqfpfgqqwauwesbrw"
VIDEO = Path(r"E:\tamazight\_videos") / f"{SLUG}.mp4"
VISOR = Path(r"E:\tamazight\_visor") / SLUG / "subtitols.jsonl"
SENTIT = Path(r"E:\tamazight\_sentit\sortida_26\sentit.jsonl")
#: la franja NO és al mateix lloc a tots els capítols: 20 de 25 la tenen fora de l'estàndard,
#: amb set posicions diferents. Retallar sempre a y 870 escapçava els signes i la relectura
#: donava zero. La geometria de cada capítol la mesura la fàbrica i és a `geometries.json`.
GEO = json.load(io.open(MAG / "geometries.json", encoding="utf-8"))
_g = GEO.get(SLUG, {}).get("TIFINAG_720") or [580, 614]
Y0 = int(round(_g[0] * 1.5))
ALT = int(round((_g[1] - _g[0]) * 1.5))
print(f"franja del capítol: 720p {_g}  ->  1080p y={Y0} alt={ALT}"
      f"{'' if GEO.get(SLUG, {}).get('estandard') else '   (NO estàndard)'}")

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiou")


def esquelet(t):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c, LLATI.get(c, c))
        if c.isalpha() and c not in VOCALS:
            fora.append(c)
    return "".join(fora)


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()
files = [json.loads(l) for l in io.open(VISOR, encoding="utf-8") if l.strip()]
print(f"capítol {SLUG[:16]}…  {len(files)} rèpliques")

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(VIDEO),
                    "-vf", f"fps=1,crop=iw:{ALT}:0:{Y0}",
                    str(Path(tmp) / "%06d.png")], check=False)
    franges = sorted(Path(tmp).glob("*.png"))
    print(f"franges: {len(franges)}")
    imatges = {}
    for x in files:
        mig = int(round((float(x["t_ini"]) + float(x["t_fi"])) / 2))
        i = min(max(mig, 1), len(franges)) - 1
        imatges[x["k"]] = np.asarray(Image.open(franges[i]).convert("RGB"))
    mostra = [np.asarray(Image.open(f).convert("RGB"))
              for f in franges[::max(1, len(franges) // 40)][:40]]
    esc = L.estima_escala(mostra)

    def passada(nom):
        t0, llegit = time.time(), {}
        for x in files:
            try:
                llegit[x["k"]] = (L.llegeix_banda(imatges[x["k"]], esc).get("tifinag") or "").strip()
            except Exception:
                llegit[x["k"]] = ""
        a = b = c = sense = 0
        for k, ull in llegit.items():
            eu, eo = esquelet(ull), esquelet(sentit.get(f"{SLUG}:{k}", ""))
            if not eu or not eo:
                sense += 1
                continue
            cer = lev(eu, eo) / max(len(eu), len(eo))
            a += cer <= .35; b += .35 < cer <= .6; c += cer > .6
        tot = a + b + c + sense
        tskla = sum(1 for v in llegit.values() for w in v.split() if "ⴽⵍⴰ" in w and "ⵀ" in w)
        bo = sum(1 for v in llegit.values() for w in v.split() if "ⴽⵍⴰ" in w and "ⵙ" in w)
        print(f"{nom:<22} A {a:4d} ({100*a/max(1,tot):4.1f}%)  B {b:4d}  C {c:4d}  "
              f"sense {sense:3d}   tskla: {bo} bé / {tskla} amb ⵀ   [{time.time()-t0:.0f}s]")
        return a, tot

    a0, tot = passada("sense desempat")
    DT.posa_el_desempat()
    a1, _ = passada("amb desempat")
    print(f"\ndiferència: {100*(a1-a0)/max(1,tot):+.2f} punts de taxa d'acord ({a0} -> {a1})")
