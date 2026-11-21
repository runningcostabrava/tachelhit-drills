"""El text desat del TAWNZA, ¿també és d'un lector vell?

Al capítol del Tadfi, rellegir les mateixes franges amb el lector d'avui va pujar la taxa
d'acord de 10,7 % a 17,1 % sense dades noves: el text guardat l'havia escrit un lector més vell.
Aquí es mira si passa el mateix amb les dues carpetes del TAWNZA.

Límit, dit abans de començar: **aquí no hi ha so**, o sigui que no hi ha orella amb qui contrastar
i no es pot dir si el text nou és MILLOR. Només es pot dir si és DIFERENT. Si ho és molt, vol dir
que el desat és vell i s'hauria de refer; si no, que ja estava al dia. Canvi no vol dir millora, i
no ho diré pas.

No escriu res: només compara i informa.
"""
import io
import json
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import lector_tifinag as L  # noqa: E402

BASE = Path(r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\tipografia\tawnza_fase2")
DESTI = Path(r"E:\tamazight\_magatzem\rellegit_tawnza.json")


def esquelet(t):
    return "".join(c for c in unicodedata.normalize("NFC", t or "") if "\u2d30" <= c <= "\u2d7f")


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


sortida = {}
for v in ("tawnza_in_j2", "tawnza_SLy6"):
    carpeta = BASE / v
    franges = sorted((carpeta / "tif").glob("*.png"))
    vells = [json.loads(l) for l in io.open(carpeta / "subtitols.jsonl", encoding="utf-8") if l.strip()]
    per_k = {x.get("k", i): x for i, x in enumerate(vells)}
    print(f"\n{v}: {len(franges)} franges, {len(vells)} línies desades")

    #: l'escala es treu de les imatges mateixes, com fa la fàbrica
    mostra = [np.asarray(Image.open(f).convert("RGB")) for f in franges[::max(1, len(franges) // 40)][:40]]
    esc = L.estima_escala(mostra)
    print(f"   escala: {esc}")

    t0, igual, canviat, buits_nous, buits_vells = time.time(), 0, 0, 0, 0
    dif, exemples = [], []
    for i, f in enumerate(franges):
        k = int(f.stem)
        try:
            nou = (L.llegeix_banda(np.asarray(Image.open(f).convert("RGB")), esc).get("tifinag") or "").strip()
        except Exception:
            nou = ""
        vell = ((per_k.get(k) or {}).get("tifinag") or "").strip()
        en, ev = esquelet(nou), esquelet(vell)
        if not en:
            buits_nous += 1
        if not ev:
            buits_vells += 1
        if en == ev:
            igual += 1
        else:
            canviat += 1
            if en and ev:
                dif.append(lev(en, ev) / max(len(en), len(ev)))
                if len(exemples) < 4 and lev(en, ev) / max(len(en), len(ev)) > .3:
                    exemples.append((k, vell, nou))
        if (i + 1) % 300 == 0:
            print(f"   {i+1}/{len(franges)}  {time.time()-t0:.0f}s", flush=True)

    n = len(franges)
    print(f"   iguals: {igual} ({100*igual/n:.0f}%)   canviats: {canviat} ({100*canviat/n:.0f}%)")
    print(f"   buits: {buits_vells} abans -> {buits_nous} ara")
    if dif:
        dif.sort()
        print(f"   quan canvia, quant: mediana {dif[len(dif)//2]:.2f} de distància")
    for k, vell, nou in exemples:
        print(f"      [{k}] abans: {vell[:46]}")
        print(f"           ara  : {nou[:46]}")
    sortida[v] = {"franges": n, "iguals": igual, "canviats": canviat,
                  "buits_vells": buits_vells, "buits_nous": buits_nous}

json.dump(sortida, io.open(DESTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\ndesat a {DESTI}")
print("AVÍS: sense so no es pot dir que el text nou sigui millor, només que és diferent.")
