"""Treure de la ronda el que no hi ha de ser, abans d'entrenar.

Dues coses que la comprovacio ha trobat:

  - talls de fins a 19,5 s. El nucli es posa un limit de 14 s per a les altres fonts
    (`SEGONS_MAXIM`) i amb lots de 4 un tall llarg pot deixar la GPU sense memoria a mig
    entrenament, que es la pitjor manera de perdre dues hores.
  - 30 etiquetes amb menys de quatre lletres tifinag (`ⵏ`, `ⴳ`): no ensenyen res i afegeixen
    soroll al CTC.

Es treuen les files, no els fitxers: el dataset es torna a pujar amb el `rows.json` net i els
wav que sobren hi queden sense fer nosa (no els mira ningu). I es diu quantes se'n van.
"""
import io
import json
import wave
from collections import Counter
from pathlib import Path

D = Path(r"E:/tamazight/_magatzem/ronda/dades")
MAX_SEGONS = 14.0
MIN_TIFINAG = 4
TIF = range(0x2D30, 0x2D80)

files = json.load(io.open(D / "rows.json", encoding="utf-8"))
fora = Counter()
netes = []
for r in files:
    n_tif = sum(1 for ch in r["tifinag"] if ord(ch) in TIF)
    if n_tif < MIN_TIFINAG:
        fora[f"{r['split']}: etiqueta curta"] += 1
        continue
    p = D / r["fitxer"]
    try:
        with wave.open(str(p)) as w:
            segons = w.getnframes() / w.getframerate()
    except Exception:
        fora[f"{r['split']}: so il·legible"] += 1
        continue
    if segons > MAX_SEGONS:
        fora[f"{r['split']}: mes de {MAX_SEGONS:.0f} s"] += 1
        continue
    netes.append(r)

json.dump(netes, io.open(D / "rows.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"de {len(files)} files en queden {len(netes)}")
for k, v in sorted(fora.items()):
    print(f"   fora  {k}: {v}")
c = Counter(r["split"] for r in netes)
print("  " + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))
