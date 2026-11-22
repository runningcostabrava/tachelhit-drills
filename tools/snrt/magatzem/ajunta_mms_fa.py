"""Ajuntar els fitxers dels tres fluxos del MMS_FA en un de sol.

Cada flux escriu el seu fitxer a proposit: dos processos escrivint al mateix fitxer es van
barrejar a mig buffer el 23-11 i van deixar una linia trencada. Aqui es tornen a ajuntar, saltant
les linies que no siguin JSON i quedant-se una sola entrada per tall.

    python ajunta_mms_fa.py
"""
import glob
import io
import json
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
DESTI = MAG / "alineacio_mms_fa_tot.jsonl"

vist, males, caps = {}, 0, {}
for p in sorted(glob.glob(str(MAG / "alineacio_mms_fa_tot_*de*.jsonl"))):
    n = 0
    for l in io.open(p, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except ValueError:
            males += 1
            continue
        vist[r["so"]] = r
        caps[r["capitol"]] = caps.get(r["capitol"], 0) + 1
        n += 1
    print(f"   {Path(p).name}: {n}")

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for k in sorted(vist):
        f.write(json.dumps(vist[k], ensure_ascii=False) + "\n")

print(f"\n{len(vist)} talls · {len(caps)} capítols · {males} línies trencades saltades")
print(f"-> {DESTI}")
