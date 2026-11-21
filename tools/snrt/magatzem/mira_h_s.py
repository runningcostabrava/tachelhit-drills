"""Per què el lector escriu ⵀ on hi ha ⵙ. Arqueologia d'un sol signe.

La taula estàndard ↔ dialecte va treure `thkla ↔ tskla` 10 vegades en 6 capítols: l'ull llegeix
ⵀ on l'orella sent una s, i *tskla* (literatura) és la paraula del títol del programa. Repartit
per vuit capítols i el 10 % de les vegades, o sigui que no és d'un vídeo: és del lector.

Això no s'aclareix mirant-s'ho: cal demanar al classificador de plantilles què en pensa. Per a
cada signe que ha llegit ⵀ dins d'una paraula que acaba en -ⴽⵍⴰ, es mira quina nota treu contra
la plantilla de ⵀ i quina contra la de ⵙ. Si les dues notes són gairebé iguals, és un empat que
el lector perd per poc i es pot desempatar; si la de ⵙ és molt pitjor, el signe de la pantalla
no s'assembla a una ⵙ i el problema és un altre.

No canvia res: només mesura i deixa una imatge per mirar.
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import lector_tifinag as L      # noqa: E402
import tifinag_plantilles as PL  # noqa: E402

VIDEO = Path(r"E:\tamazight\_videos\bueyrhjvjyaleocffcrxdtmeqfpfgqqwauwesbrw.mp4")
SORTIDA = Path(r"C:\Users\josep\AppData\Local\Temp\claude\b9bc3d8a9f758b87"
               r"\104dfaed-6dfd-4f67-bac4-fece7f991424\scratchpad")
SEGONS = [220, 1613, 1633]

import subprocess  # noqa: E402

trossos = []
for t in SEGONS:
    p = SORTIDA / f"hs_{t}.png"
    if not p.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(VIDEO),
                        "-frames:v", "1", "-vf", "crop=iw:60:0:866", "-y", str(p)], check=False)
    if p.exists():
        trossos.append((t, np.asarray(Image.open(p).convert("RGB"))))

print(f"franges: {len(trossos)}")
mostres = []
for t, a in trossos:
    res = L.analitza_banda(a, None)
    if res is None:
        print(f"  {t}s: el lector no hi veu cap línia")
        continue
    r, punts = res
    cos_top = r["cos"][0]
    text = "".join(p[0][1] if p else "?" for p in punts)
    print(f"  {t}s: {text[:60]}")
    for g, p in zip(r["glifs"], punts):
        if not p or p[0][1] != "ⵀ":
            continue
        #: què diu la plantilla de cada signe per a aquesta mateixa màscara
        notes = PL.classifica(g["mask"], g["caixa"][1] - cos_top)
        d = {s: v for v, s in notes[:8]}
        h = d.get("ⵀ", 0.0)
        s_ = next((v for v, s in notes if s == "ⵙ"), 0.0)
        print(f"      un ⵀ a x={g['caixa'][0]:4d}: ⵀ {h:.3f}   ⵙ {s_:.3f}   "
              f"diferència {h - s_:+.3f}   (2n: {notes[1][1]} {notes[1][0]:.3f})")
        mostres.append((g, t))

#: una imatge amb els signes trobats, ampliats, per mirar-los de debò
if mostres:
    amp = sum(g["mask"].shape[1] for g, _ in mostres) + 10 * len(mostres)
    alt = max(g["mask"].shape[0] for g, _ in mostres)
    out = Image.new("L", (amp, alt), 0)
    x = 0
    for g, _ in mostres:
        m = Image.fromarray((g["mask"] * 255).astype(np.uint8))
        out.paste(m, (x, 0))
        x += m.width + 10
    out = out.resize((out.width * 6, out.height * 6), Image.NEAREST)
    out.save(SORTIDA / "signes_h.png")
    print(f"\nsignes desats a {SORTIDA / 'signes_h.png'}  ({len(mostres)})")

#: i les plantilles, per comparar-les amb els signes de debús
try:
    import numpy as _np
    z = _np.load(PL.NPZ, allow_pickle=True)
    signes = list(z["signes"])
    masc = z["mascares"]
    tria = [s for s in ("ⵀ", "ⵙ") if s in signes]
    ims = []
    for s in tria:
        m = masc[signes.index(s)]
        ims.append(Image.fromarray((_np.asarray(m) * 255).astype(_np.uint8)))
    if ims:
        amp = sum(i.width for i in ims) + 12 * len(ims)
        alt = max(i.height for i in ims)
        out = Image.new("L", (amp, alt), 0)
        x = 0
        for i in ims:
            out.paste(i, (x, 0)); x += i.width + 12
        out = out.resize((out.width * 6, out.height * 6), Image.NEAREST)
        out.save(SORTIDA / "plantilles_h_s.png")
        print(f"plantilles de {' i '.join(tria)} a {SORTIDA / 'plantilles_h_s.png'}")
except Exception as e:
    print("no s'han pogut treure les plantilles:", type(e).__name__, e)
