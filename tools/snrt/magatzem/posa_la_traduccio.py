"""Posar al capitol la traduccio feta a ma, sense tocar res mes.

El catala va al camp `catala`, amb `catala_estat` que diu d'on surt. No es toca cap altre
camp: ni el tifinag, ni l'arab, ni els temps. El text dels parlants es d'ells.

    posa_la_traduccio.py <capitol>
"""
import io
import json
import shutil
import sys
import time
from pathlib import Path

cap = sys.argv[1] if len(sys.argv) > 1 else "JwF_qqtT8J0"
MAG = Path(r"E:/tamazight/_magatzem")
SUB = Path(r"E:/tamazight/TD_TV") / cap / "subtitols.jsonl"

t = json.load(io.open(MAG / f"traduccio_{cap}.json", encoding="utf-8"))
ca = t["linies"]
print(f"{len(ca)} línies traduïdes")

L = [json.loads(l) for l in io.open(SUB, encoding="utf-8") if l.strip()]
print(f"{len(L)} línies al capítol")
if len(L) != len(ca):
    print("NO CASEN: no toco res")
    raise SystemExit(1)

shutil.copy2(SUB, str(SUB) + ".abans-" + time.strftime("%Y%m%d-%H%M"))

posats = 0
for i, x in enumerate(L):
    nou = (ca.get(str(i)) or "").strip()
    if not nou:
        continue
    x["catala"] = nou
    x["catala_estat"] = "traduit_a_ma_de_l_arab"
    posats += 1

with io.open(SUB, "w", encoding="utf-8", newline="\n") as f:
    for x in L:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")

print(f"{posats} línies amb català · còpia de l'anterior al costat")
