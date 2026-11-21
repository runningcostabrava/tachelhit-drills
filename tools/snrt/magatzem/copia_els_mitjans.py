"""Una copia local dels 21.036 mitjans abans d'esborrar el Cloudinary.

La migracio del #577 els va passar a R2 amb la mateixa ruta i esta verificada (16 de 16 d'una
mostra a l'atzar baixen be), i la biblioteca ja no apunta enlloc a Cloudinary. Pero **no hi ha
cap copia local**: esborrant el Cloudinary, R2 queda com a copia unica, i una copia unica no es
una copia.

Aixo baixa cada fitxer del CSV de la migracio a `E:/tamazight/_mitjans_copia/<ruta>`. Es
reprenible (salta el que ja hi es i te mida) i no toca res de cap servidor: nomes llegeix.

    copia_els_mitjans.py [quants]
"""
import csv
import io
import os
import sys
import time
import urllib.request
from pathlib import Path

CSV = Path(r"C:/Users/josep/app2/tachelhit-drills/backend/reescriptura_a_r2.csv")
DESTI = Path(r"E:/tamazight/_mitjans_copia")
BASE = "https://tachelhit-drills-api.onrender.com"
QUANTS = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9

files = list(csv.DictReader(io.open(CSV, encoding="utf-8", newline="")))
#: el mateix fitxer pot sortir a mes d'una fila (audio i tts del mateix drill, per exemple)
rutes = []
vistes = set()
for r in files:
    p = (r.get("despres") or "").strip()
    if p.startswith("/mitjans/") and p not in vistes:
        vistes.add(p)
        rutes.append(p)
print(f"{len(rutes)} fitxers diferents a copiar", flush=True)

fets = saltats = errors = 0
t0 = time.time()
for i, ruta in enumerate(rutes[:QUANTS], 1):
    desti = DESTI / ruta[len("/mitjans/"):]
    if desti.exists() and desti.stat().st_size > 200:
        saltats += 1
        continue
    desti.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(BASE + ruta, timeout=120) as r:
            dades = r.read()
        if len(dades) < 200:
            raise ValueError(f"massa petit ({len(dades)} bytes)")
        desti.write_bytes(dades)
        fets += 1
    except Exception as e:
        errors += 1
        if errors <= 10:
            print(f"   falla {ruta}: {type(e).__name__} {str(e)[:60]}", flush=True)
    if i % 250 == 0:
        print(f"{i}/{len(rutes)} · {fets} copiats · {saltats} ja hi eren · {errors} errors "
              f"· {time.time()-t0:.0f} s", flush=True)

print(f"\nFET: {fets} copiats · {saltats} ja hi eren · {errors} errors · "
      f"{time.time()-t0:.0f} s", flush=True)
mida = sum(f.stat().st_size for f in DESTI.rglob("*") if f.is_file())
print(f"la copia ocupa {mida/1e9:.2f} GB a {DESTI}")
