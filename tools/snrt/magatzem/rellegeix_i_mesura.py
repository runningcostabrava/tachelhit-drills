"""Torna a llegir les franges d'un capítol i mesura la TAXA D'ACORD amb el que sent el model.

La taxa d'acord és el % de rèpliques on el text llegit de la imatge i el text sentit del so
coincideixen en l'esquelet consonàntic (CER <= 0,35). Val com a mesura perquè les dues lectures
són independents —una mira, l'altra escolta— i cap no sap què diu l'altra: coincidir per
casualitat en una frase sencera és molt difícil. I, sobretot, **no cal veritat humana**, que
d'aquest capítol no n'hi ha.

Es llegeix dues vegades: amb `SEG.unifica_veins` (l'arreglo de la ⵓ partida en dues ⵏ) i sense,
per saber si l'arreglo val sobre dades de debò i no només sobre les 143 peces etiquetades.

No escriu res a producció ni al visor.
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
import lector_tifinag as L      # noqa: E402
import tifinag_segmenta as SEG  # noqa: E402

CAP = Path(r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay\tadfi_goughelt")
SENTIT = Path(r"E:\tamazight\_sentit\sortida\sentit.jsonl")
DESTI = Path(r"E:\tamazight\_magatzem\rellegit.json")

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiou")


def esquelet(t):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c, LLATI.get(c, c))
        if c.isalpha() and c not in VOCALS:
            fora.append(c)
    return "".join(fora)


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


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()
subs = [json.loads(l) for l in io.open(CAP / "subtitols.jsonl", encoding="utf-8") if l.strip()]
#: la franja `tif_1080/NNNN.png` i la rèplica `k` són el mateix número; es comprova, perquè
#: casar per posició entre dues llistes és com es fan els desplaçaments d'una línia
per_k = {x.get("k", i): x for i, x in enumerate(subs)}

franges = sorted((CAP / "tif_1080").glob("*.png"))
print(f"franges: {len(franges)}   rèpliques: {len(subs)}   amb so sentit: {len(sentit)}")

ESC = None   #: `estima_escala` la treu de les imatges mateixes; es fa un cop i es reaprofita
mostra = [np.asarray(Image.open(f).convert("RGB")) for f in franges[::max(1, len(franges) // 40)][:40]]
ESC = L.estima_escala(mostra)
print("escala estimada:", ESC)


def passada(nom, amb_arreglo):
    hi_era = SEG.unifica_veins
    if not amb_arreglo:
        SEG.unifica_veins = lambda r, *a, **k: r
    t0, llegit = time.time(), {}
    for i, f in enumerate(franges):
        k = int(f.stem)
        try:
            r = L.llegeix_banda(np.asarray(Image.open(f).convert("RGB")), ESC)
            llegit[k] = (r.get("tifinag") or "").strip()
        except Exception:
            llegit[k] = ""
        if (i + 1) % 300 == 0:
            print(f"   {nom}: {i+1}/{len(franges)}  {time.time()-t0:.0f}s", flush=True)
    SEG.unifica_veins = hi_era

    graus = {"A": 0, "B": 0, "C": 0, "sense": 0}
    for k, ull in llegit.items():
        x = per_k.get(k)
        orella = sentit.get((x or {}).get("id"), "")
        eu, eo = esquelet(ull), esquelet(orella)
        if not eu or not eo:
            graus["sense"] += 1
            continue
        cer = lev(eu, eo) / max(len(eu), len(eo))
        graus["A" if cer <= .35 else ("B" if cer <= .6 else "C")] += 1
    n = len(llegit)
    print(f"{nom:28s} A {graus['A']:4d} ({100*graus['A']/n:4.1f}%)   B {graus['B']:4d}   "
          f"C {graus['C']:4d}   sense {graus['sense']:4d}   [{time.time()-t0:.0f}s]")
    return llegit, graus


amb, g_amb = passada("amb l'arreglo de la ⵓ", True)
sense, g_sense = passada("sense l'arreglo", False)

print(f"\ndiferència de la taxa d'acord: {100*(g_amb['A']-g_sense['A'])/len(amb):+.2f} punts")
json.dump({"amb": g_amb, "sense": g_sense,
           "llegit_amb": {str(k): v for k, v in amb.items()}},
          io.open(DESTI, "w", encoding="utf-8"), ensure_ascii=False)
print("desat a", DESTI)
