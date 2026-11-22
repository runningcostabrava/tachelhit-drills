"""Cada episodi del visor te el seu video a la carpeta, amb el nom que el visor busca?

El visor demana `<slug>.mp4` a la carpeta que tu triis (`videoDesat.ts`). Si el fitxer existeix
pero es diu d'una altra manera -- i molts es diuen amb l'identificador de 40 lletres de la forja,
com `epvzzvfisvghiegujguzzhbbrgcxmhwoqmohvojb.mp4` -- el visor no el troba i ensenya negre sense
dir per que.

Aixo mira, per a cada un dels 39 episodis: si hi es amb el nom bo, si hi es amb un altre nom (i
quin), o si no hi es enlloc. No mou res: nomes diu que hi ha.

Per casar un fitxer amb un episodi sense fiar-se del nom es mira la DURADA: el visor sap quants
segons dura cada episodi, i un video d'una hora no es confon amb un altre si les durades casen
a menys de cinc segons.

    on_son_els_videos.py            -> l'inventari
    on_son_els_videos.py arregla    -> fa un enllac dur <slug>.mp4 per als que casen per durada
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

CARPETA = Path(os.environ.get("VIDEOS", r"E:/tamazight/_videos"))
BUSCA = [CARPETA, Path(r"E:/tamazight/_episodis"), Path(r"E:/tamazight/TD_TV"),
         Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/tamazight_tv/replay")]
EXT = (".mp4", ".mkv", ".webm", ".mov", ".m4v")
API = "https://tachelhit-drills-api.onrender.com"
MARGE = 5.0        #: segons de diferencia que encara es consideren el mateix video


def durada(cami):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(cami)], capture_output=True, text=True)
        return float((r.stdout or "0").strip())
    except Exception:
        return 0.0


import urllib.request  # noqa: E402

with urllib.request.urlopen(API + "/snrt-privat/", timeout=90) as r:
    eps = json.load(r)["episodis"]
print(f"{len(eps)} episodis al visor\n", flush=True)

#: tots els videos que tenim, amb la seva durada (es calcula un cop)
tots = []
for d in BUSCA:
    if not d.exists():
        continue
    for p in d.rglob("*"):
        if p.suffix.lower() in EXT and p.is_file():
            tots.append(p)
print(f"{len(tots)} fitxers de video trobats; mirant-ne la durada…", flush=True)
dur = {p: durada(p) for p in tots}

be, altre_nom, falten = [], [], []
for e in eps:
    slug, d = e["slug"], e.get("durada")
    bo = CARPETA / (slug + ".mp4")
    if bo.exists():
        be.append(slug)
        continue
    #: amb un altre nom? primer pel nom (algun porta el slug a dins), despres per durada
    cands = [p for p in tots if p.stem == slug]
    if not cands and d:
        cands = [p for p in tots if abs(dur.get(p, 0) - float(d)) <= MARGE]
    if cands:
        altre_nom.append((slug, cands[0], e.get("titol", "")[:34]))
    else:
        falten.append((slug, d, e.get("titol", "")[:34]))

print(f"\n{len(be)} amb el nom bo a {CARPETA}")
print(f"{len(altre_nom)} hi son amb UN ALTRE NOM:")
for slug, p, t in altre_nom:
    print(f"   {slug:<22} -> {p.name[:46]}   ({t})")
print(f"{len(falten)} NO hi son enlloc:")
for slug, d, t in falten:
    print(f"   {slug:<22} {('%.0f min' % (d/60)) if d else '?':>8}   ({t})")

if len(sys.argv) > 1 and sys.argv[1] == "arregla" and altre_nom:
    print("\nfent els enllaços…")
    fets = copiats = 0
    for slug, p, _ in altre_nom:
        desti = CARPETA / (slug + p.suffix.lower())
        if desti.exists():
            continue
        try:
            os.link(p, desti)       #: mateix volum: no ocupa res i el fitxer original no es toca
            fets += 1
        except OSError:
            import shutil
            shutil.copy2(p, desti)  #: un altre volum: cal copiar
            copiats += 1
    print(f"{fets} enllaços + {copiats} còpies a {CARPETA}")
