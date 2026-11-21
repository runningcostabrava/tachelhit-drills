"""Baixar de Cloudinary els 32.306 fitxers que la migracio a R2 **no** va moure.

Aixo es la feina que va evitar un desastre. L'inventari previ a l'esborrat (20-11-2026) va
ensenyar que a Cloudinary hi ha 53.265 fitxers i que la migracio del #577 nomes en va moure
20.959. Els altres **32.306 no son a R2**, i entre ells hi ha 3.557 de `tachelhit/audio` (veus
reals) i 411 de `tachelhit/cd_metode` (el CD del Metode).

La copia que ja corria baixa de `/mitjans/` (R2) i per tant **no els estava salvant**: nomes
copiava els que ja estaven duplicats. Aquesta els baixa de la seva adreca de Cloudinary, que es
a l'inventari.

Reprenible: salta el que ja hi es amb mida. No esborra ni toca res de cap servidor.

    salva_els_no_migrats.py
"""
import csv
import io
import json
import time
import urllib.request
from pathlib import Path

AQUI = Path(r"E:/tamazight/_magatzem")
DESTI = Path(r"E:/tamazight/_cloudinary_no_migrat")
CSV = Path(r"C:/Users/josep/app2/tachelhit-drills/backend/reescriptura_a_r2.csv")

mig = set()
for r in csv.DictReader(io.open(CSV, encoding="utf-8", newline="")):
    p = (r["despres"] or "").strip()
    if p.startswith("/mitjans/"):
        mig.add(p[len("/mitjans/"):])

pendents = []
for l in io.open(AQUI / "cloudinary_inventari.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    pid, f = x["public_id"], (x.get("format") or "")
    if {pid, pid + "." + f} & mig:
        continue
    pendents.append(x)

#: primer el que no es pot refer: veus reals i el CD; el TTS sintetic, l'ultim
def prioritat(x):
    p = x["public_id"]
    if p.startswith("tachelhit/cd_metode"):
        return 0
    if p.startswith("tachelhit/audio"):
        return 1
    if p.startswith("tachelhit/tts"):
        return 9
    return 5


pendents.sort(key=prioritat)
print(f"{len(pendents)} fitxers no migrats per salvar "
      f"({sum(1 for x in pendents if prioritat(x) <= 1)} son veus reals o el CD)", flush=True)

fets = saltats = errors = 0
t0 = time.time()
for i, x in enumerate(pendents, 1):
    pid, f = x["public_id"], (x.get("format") or "bin")
    desti = DESTI / (pid + "." + f)
    if desti.exists() and desti.stat().st_size > 100:
        saltats += 1
        continue
    desti.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(x["url"], timeout=120) as r:
            dades = r.read()
        if len(dades) < 100:
            raise ValueError(f"massa petit ({len(dades)})")
        desti.write_bytes(dades)
        fets += 1
    except Exception as e:
        errors += 1
        if errors <= 10:
            print(f"   falla {pid}: {type(e).__name__} {str(e)[:60]}", flush=True)
    if i % 500 == 0:
        print(f"{i}/{len(pendents)} · {fets} salvats · {saltats} ja hi eren · {errors} errors "
              f"· {time.time()-t0:.0f} s", flush=True)

print(f"\nFET: {fets} salvats · {saltats} ja hi eren · {errors} errors "
      f"· {time.time()-t0:.0f} s", flush=True)
mida = sum(p.stat().st_size for p in DESTI.rglob("*") if p.is_file())
print(f"ocupen {mida/1e9:.2f} GB a {DESTI}")
