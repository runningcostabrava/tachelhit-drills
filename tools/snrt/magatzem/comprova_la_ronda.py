"""Comprovar la ronda ABANS que entreni dues hores.

Quatre coses que, si estan malament, fan perdre la nit i donen un numero que sembla bo:

  1. cada fila ha de tenir el seu so, i el so ha de sonar (no silenci, no buit);
  2. cap capitol retingut pot ser al train ni al dev: si hi es, el test ja no mesura res;
  3. cap frase del train pot ser al test (la fuita per text la tanca el nucli, pero val mes
     saber quanta n'hi ha abans);
  4. les etiquetes han de ser text amazic de debo, no restes de l'OCR.
"""
import io
import json
import wave
from collections import Counter
from pathlib import Path

import numpy as np

D = Path(r"E:/tamazight/_magatzem/ronda/dades")
RETINGUTS = ("jerkqzqplguvpzoh", "wckionryvrwatrvs", "hmssyuzoyqzywbaj", "oeeljuwkqlqtebzr")

files = json.load(io.open(D / "rows.json", encoding="utf-8"))
print(f"files: {len(files)}")
c = Counter(r["split"] for r in files)
print("  " + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))

# 1. el so
falten, muts, durades = 0, 0, []
for r in files:
    p = D / r["fitxer"]
    if not p.exists():
        falten += 1
        continue
    try:
        with wave.open(str(p)) as w:
            n, sr = w.getnframes(), w.getframerate()
            a = np.frombuffer(w.readframes(min(n, sr * 20)), dtype=np.int16)
    except Exception:
        muts += 1
        continue
    durades.append(n / sr)
    if a.size < sr // 10 or float(np.sqrt((a.astype(np.float32) / 32768) ** 2).mean()) < .002:
        muts += 1
print(f"\n1. so: falten {falten} · muts o il·legibles {muts} · "
      f"durada mitjana {np.mean(durades):.1f} s · la mes llarga {max(durades):.1f} s")

# 2. els retinguts
mal = [r for r in files if r["split"] != "test" and r["slug"][:16] in RETINGUTS]
mal2 = [r for r in files if r["split"] == "test" and r["slug"][:16] not in RETINGUTS]
print(f"2. retinguts: {len(mal)} files d'un capitol retingut fora del test · "
      f"{len(mal2)} files de test que no son d'un capitol retingut")

# 3. la fuita per text
def neta(t):
    return " ".join((t or "").split()).strip()


train = {neta(r["tifinag"]) for r in files if r["split"] == "train"}
test = {neta(r["tifinag"]) for r in files if r["split"] == "test"}
comuns = {t for t in (train & test) if len(t) > 6}
print(f"3. fuita: {len(comuns)} frases de mes de 6 caracters son al train i al test")
for t in list(comuns)[:5]:
    print(f"     {t[:60]}")

# 4. les etiquetes
TIF = range(0x2D30, 0x2D80)
dolentes = [r for r in files
            if sum(1 for ch in r["tifinag"] if ord(ch) in TIF) < 4]
print(f"4. etiquetes: {len(dolentes)} amb menys de 4 lletres tifinag")
llargs = [len(r["tifinag"].split()) for r in files]
print(f"   paraules per etiqueta: mitjana {np.mean(llargs):.1f} · la mes llarga {max(llargs)}")
print(f"\n{'TOT BE' if not (falten or muts or mal or mal2 or dolentes) else 'MIRA-T HO'}")
