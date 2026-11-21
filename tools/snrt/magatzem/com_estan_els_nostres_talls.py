"""Quant silenci i quanta veu tallada hi ha als talls que alimentaran la via 3.

El diagnostic d'alineacio forcada del 18-11 deia que el **62 %** dels talls tenen l'inici
desplacat mes de mig segon, i que retallant-los on el model sent la veu el CER baixa **0,0789**.
Pero aixo era sobre 589 talls de **capitols antics**.

Els nostres son uns altres i alimenten la via 3 (veu -> arab), on el tall ES l'entrada del
model: si porta silenci o mig tros de la frase veina, el model ho aprèn.

Aqui no cal el model acustic: amb el **nivell del so** ja es veu on comenca i acaba la veu.
Es mesura, per cada tall:
  * quant silenci hi ha al davant i al darrere (es podria retallar);
  * si el so **toca els extrems** amb nivell alt, que vol dir que la frase esta **tallada**
    pel mig -- aixo es el greu, perque el que falta no es pot recuperar.

    com_estan_els_nostres_talls.py [quants]
"""
import io
import json
import random
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

CORPUS = Path(r"E:/tamazight/_magatzem/veu_ar")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
LLINDAR_DB = -34.0        #: per sota d'aixo es considera silenci
FINESTRA = 0.02           #: 20 ms


def perfil(cami):
    d, sr = sf.read(cami, dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    n = max(1, int(sr * FINESTRA))
    trossos = [d[i:i + n] for i in range(0, len(d), n)]
    db = np.array([20 * np.log10(max(1e-7, float(np.sqrt(np.mean(t ** 2))))) for t in trossos])
    veu = db > LLINDAR_DB
    if not veu.any():
        return None
    ini = int(np.argmax(veu)) * FINESTRA
    fi = (len(veu) - int(np.argmax(veu[::-1]))) * FINESTRA
    return {"durada": len(d) / sr, "silenci_davant": ini,
            "silenci_darrere": max(0.0, len(d) / sr - fi),
            "comenca_fort": bool(veu[:3].any()), "acaba_fort": bool(veu[-3:].any())}


files = [json.loads(l) for l in io.open(CORPUS / "train.jsonl", encoding="utf-8") if l.strip()]
random.Random(20261121).shuffle(files)
files = files[:N]
print(f"{len(files)} talls mirats de {CORPUS.name}\n")

res = []
for x in files:
    p = CORPUS / "so" / x["so"]
    if p.exists():
        r = perfil(p)
        if r:
            res.append(r)

dav = sorted(r["silenci_davant"] for r in res)
dar = sorted(r["silenci_darrere"] for r in res)
tallats = sum(1 for r in res if r["comenca_fort"] or r["acaba_fort"])
print(f"SILENCI que es podria retallar (segons):")
print(f"   davant:  mediana {dav[len(dav)//2]:.2f} · mitjana {sum(dav)/len(dav):.2f} · "
      f">0,3 s: {sum(1 for x in dav if x > .3)} ({100*sum(1 for x in dav if x>.3)/len(dav):.0f} %)")
print(f"   darrere: mediana {dar[len(dar)//2]:.2f} · mitjana {sum(dar)/len(dar):.2f} · "
      f">0,3 s: {sum(1 for x in dar if x > .3)} ({100*sum(1 for x in dar if x>.3)/len(dar):.0f} %)")
sob = sum(dav) + sum(dar)
tot = sum(r["durada"] for r in res)
print(f"\n   del total, {100*sob/tot:.0f} % és silenci als extrems "
      f"({sob/60:.0f} min de cada {tot/60:.0f})")
print(f"\nTALLS QUE COMENCEN O ACABEN AMB VEU ALTA (la frase pot estar tallada pel mig):")
print(f"   {tallats} de {len(res)} ({100*tallats/len(res):.0f} %)")
print("\nEl silenci es pot treure sol. El que està tallat pel mig no: el que falta no hi és.")
