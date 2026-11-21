"""Desar sencers els episodis tarifit de produccio, abans de treure'ls.

En Pablo: «treu tarifit del visor i de la app». Del visor ja esta fet. De l'app son **11
episodis** de Tadfi n Tskla, classificats tarifit (`varietats.json`, feta amb el presentador
dient d'on es cada convidat i confirmada per les marques fonetiques).

Regla de sempre: **res no s'esborra de produccio sense tenir-ho escrit en un fitxer primer**.
Aqui es baixa tot el que en te produccio -- cada linia amb el seu temps, el tifinag, l'arab i
el catala -- i es desa. Despres ja es pot esborrar, i si algun dia es vol recuperar, hi es.

No esborra res: nomes desa.

    desa_el_tarifit_de_produccio.py
"""
import io
import json
import time
import urllib.request
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
API = "https://tachelhit-drills-api.onrender.com"
FORA = MAG / "copia_tarifit_produccio"


def demana(cami, intents=4):
    for i in range(intents):
        try:
            with urllib.request.urlopen(API + cami, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == intents - 1:
                print(f"   {cami}: {type(e).__name__}: {e}")
            time.sleep(4)
    return None


v = json.load(io.open(MAG / "varietat_produccio.json", encoding="utf-8"))
rif = [s for s, x in v.items() if x.get("varietat") == "tarifit"]
print(f"{len(rif)} episodis tarifit a producció\n")

FORA.mkdir(parents=True, exist_ok=True)
total = 0
index = []
for i, s in enumerate(rif, 1):
    d = demana(f"/snrt-privat/{s}")
    if d is None:
        print(f"   {i:2d}. {s[:16]} NO S'HA POGUT BAIXAR — no es pot esborrar")
        index.append({"slug": s, "desat": False})
        continue
    linies = d.get("linies") or d.get("repliques") or []
    io.open(FORA / f"{s}.json", "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1))
    total += len(linies)
    index.append({"slug": s, "titol": d.get("titol"), "linies": len(linies), "desat": True})
    print(f"   {i:2d}. {s[:16]} {str(d.get('titol'))[:34]:<36}{len(linies):5d} línies", flush=True)

json.dump(index, io.open(FORA / "_index.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
fets = sum(1 for x in index if x["desat"])
print(f"\n{fets} de {len(rif)} desats · {total} línies · a {FORA}")
if fets < len(rif):
    print("ATENCIÓ: no s'han desat tots. No s'ha d'esborrar res fins que hi siguin.")
