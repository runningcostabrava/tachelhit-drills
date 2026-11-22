"""Posa el text triat al visor, canviant NOMES el tifinag i sense perdre cap altre camp.

Per que cal: a dotze capitols la relectura de 1080p guanya la lectura de la fabrica, i a quatre
d'ells per molt (de 0,0 % a 16-30 % d'acord amb l'orella, i comprovat contra l'arab linia a
linia). El visor encara mostra el text vell, que en aquells quatre es `,` i `?ⵯ`.

Dues precaucions, les dues apreses a cops:

1. **L'endpoint substitueix l'episodi SENCER** (`/snrt-privat/{slug}/importa`). Per aixo aqui es
   LLEGEIX l'episodi primer, es canvia nomes el camp `tifinag` de cada linia i es torna a
   enviar tot el que ja hi havia: catala, catala_estat, arab, sentit, temps i titol. Enviar
   nomes el tifinag esborraria la resta.
2. **Un capitol cada vegada i es comprova.** El 29-10 una carrega massiva va deixar sense
   memoria un treballador de Render i `/health` seguia dient 200, aixi que no es reiniciava sol.

De manera que per defecte NO escriu: diu que canviaria. Cal `--escriu` per fer-ho.

    posa_el_text_triat_al_visor.py            # nomes diu que canviaria
    posa_el_text_triat_al_visor.py --escriu   # ho fa, capitol per capitol
"""
import io
import json
import os
import sys
from pathlib import Path

import requests

MAG = Path(r"E:/tamazight/_magatzem")
API = os.environ.get("API_BASE", "https://tachelhit-drills.onrender.com")
ESCRIU = "--escriu" in sys.argv

#: el testimoni d'administrador: de .env.prod, mai escrit en cap sortida
TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not TOKEN:
    for cami in (r"C:\Users\josep\app2\tachelhit-drills\backend\.env.prod",
                 r"C:\Users\josep\app2\tachelhit-drills\backend\.env"):
        p = Path(cami)
        if not p.exists():
            continue
        for l in io.open(p, encoding="utf-8", errors="replace"):
            l = l.strip()
            if l.startswith(("ADMIN_TOKEN", "USER_TOKEN")) and "=" in l:
                TOKEN = l.split("=", 1)[1].strip().strip('"').strip("'")
                break
        if TOKEN:
            break
if not TOKEN:
    raise SystemExit("falta el testimoni d'administrador (ADMIN_TOKEN a l'entorn o a .env.prod)")
CAP = {"X-User-Token": TOKEN}

#: el text triat, per capitol i linia
triat = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x.get("d_on") == "relectura":
        triat.setdefault(x["capitol"], {})[str(x["id"].split(":")[1])] = x.get("tifinag") or ""
print(f"capitols on la relectura guanya: {len(triat)}")

for slug, nous in sorted(triat.items()):
    r = requests.get(f"{API}/snrt-privat/{slug}", headers=CAP, timeout=60)
    if r.status_code != 200:
        print(f"{slug[:16]}: no el puc llegir ({r.status_code})")
        continue
    ep = r.json()
    linies = ep.get("linies") or ep.get("cues") or []
    if not linies:
        print(f"{slug[:16]}: sense linies al visor")
        continue
    canvis = 0
    for l in linies:
        nou = nous.get(str(l.get("k")))
        if nou is not None and (l.get("tifinag") or "") != nou:
            l["tifinag"] = nou
            canvis += 1
    print(f"{slug[:16]}: {canvis} linies canviarien de {len(linies)}")
    if not ESCRIU or not canvis:
        continue
    dades = {"titol": ep.get("titol") or slug, "url_pagina": ep.get("url_pagina"),
             "video_youtube": ep.get("video_youtube"), "durada": ep.get("durada"),
             "linies": linies}
    p = requests.post(f"{API}/snrt-privat/{slug}/importa", headers=CAP, json=dades, timeout=300)
    print(f"   escrit: {p.status_code} {p.text[:120]}")
    #: es torna a llegir per comprovar que hi ha el que toca, no es confia en el 200
    c = requests.get(f"{API}/snrt-privat/{slug}", headers=CAP, timeout=60)
    if c.status_code == 200:
        ara = {str(x.get("k")): (x.get("tifinag") or "") for x in (c.json().get("linies") or [])}
        be = sum(1 for k, v in nous.items() if ara.get(k) == v)
        print(f"   comprovat: {be} de {len(nous)} linies hi son tal com toca")
