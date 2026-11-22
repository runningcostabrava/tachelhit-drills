"""La inflacio, amb els dos grups mesurats EXACTAMENT igual.

La primera mesura comparava dos grups processats per dos nuclis diferents: el de la ronda passa
tot el text per `rica()` (NFC, minuscules, tifinag->llati ric, fora la resta) i el meu desava el
text cru. Les baixades de dins de cada grup si que eren comparables -- el mateix tractament per a
M0 i per a M1 --, pero els NIVELLS no, i l'aparellament es feia justament amb els nivells.

Aqui es copia `rica()` del nucli (tal com es a `tools/lm/kaggle/transcriptor_snrt.py` del commit
c2044c4) i s'aplica al grup dels vistos, que es el que venia cru. El grup de control ja hi havia
passat.

Despres, dues mesures:

  1. **sense aparellar**: la baixada mitjana de cada grup.
  2. **aparellada pel CER de M0**, que treu que els dos grups parteixin de punts diferents
     (0,2219 contra 0,2019) -- cosa que sola ja pot fer que millorin diferent.

I una tercera cosa que es mira perque explica les altres dues: **la baixada segons el CER de
partida**. Si als vistos la millora creix amb el CER de M0 i als no vistos es plana, aixo es la
firma de la memoritzacio: on el model estava mes lluny de l'etiqueta, l'entrenament l'hi ha
acostat mes.
"""
import io
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
VEGADES = 4000
TACH_RETINGUTS = {"wckionryvrwatrvs", "jerkqzqplguvpzoh"}

#: --- copiat del nucli, perque el control ja hi ha passat i el altre grup hi ha de passar igual
TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
           "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
           "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ",
           "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
             "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiouəā")


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


def esq(t):
    return "".join(c for c in rica(t) if c.isalpha() and c not in VOCALS)


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


def cer(ull, dit):
    a, b = esq(ull), esq(dit)
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


var = {r["capitol"][:16]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

#: vistos (text cru del meu nucli: hi passa `rica` ara)
rows = {r["id"]: r for r in json.load(
    io.open(MAG / "inflacio" / "dades" / "rows.json", encoding="utf-8"))}
sent = {}
for quin in ("m0", "m1"):
    for l in io.open(MAG / "inflacio" / "sortida" / f"sentit_{quin}.jsonl", encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            sent.setdefault(x["id"], {})[quin] = (x.get("sentit") or "").strip()
vistos = []
for ident, d in sent.items():
    r = rows.get(ident)
    if not r or "m0" not in d or "m1" not in d or var.get(r["slug"][:16]) != "tachelhit":
        continue
    if not esq(r["tifinag"]):
        continue
    c0 = cer(r["tifinag"], d["m0"])
    if c0 <= .35:
        vistos.append((c0, cer(r["tifinag"], d["m1"])))

#: no vistos (ja venien passats per `rica` al nucli de la ronda: tornar-hi no els canvia)
per = defaultdict(dict)
for x in json.load(io.open(MAG / "ronda" / "sortida" / "snrt_B_sortides.json", encoding="utf-8")):
    if x.get("prova") != "snrt-retingut":
        continue
    k = (x.get("video"), str(x.get("de")))
    per[k]["m0" if (x.get("model") or "").startswith("abans") else "m1"] = (x.get("dit") or "")
    per[k]["or"] = (x.get("or") or "")
    per[k]["cap"] = (x.get("video") or "")[:16]
no_vistos = []
for k, d in per.items():
    if "m0" not in d or "m1" not in d or d["cap"] not in TACH_RETINGUTS or not esq(d["or"]):
        continue
    c0 = cer(d["or"], d["m0"])
    if c0 <= .35:
        no_vistos.append((c0, cer(d["or"], d["m1"])))

print(f"capitols tachelhit · {len(vistos)} vistos · {len(no_vistos)} no vistos "
      f"(tots de grau A sota M0, i tots mesurats amb el MATEIX `rica`)\n")


def baixada(g):
    return sum(a - b for a, b in g) / max(1, len(g))


print(f"{'grup':<12}{'talls':>7}{'CER M0':>9}{'CER M1':>9}{'baixa':>9}")
for nom, g in (("vistos", vistos), ("no vistos", no_vistos)):
    print(f"{nom:<12}{len(g):7d}{sum(a for a, _ in g)/len(g):9.4f}"
          f"{sum(b for _, b in g)/len(g):9.4f}{-baixada(g):+9.4f}")
print(f"\nsense aparellar: inflacio = {baixada(vistos) - baixada(no_vistos):+.4f}")

#: --- aparellat pel CER de partida ---
#: L'ordre importa i em va enganyar: ordenant `vistos` per (CER_M0, CER_M1), quan uns quants
#: comparteixen el CER de partida -- i en comparteixen molts, perque son fraccions de paraules
#: curtes-- el primer de la llista es el que MES ha millorat. Agafant sempre el primer em triava
#: els millors jo mateix i sortia una inflacio de +0,0989 que no existeix. Es desfa a l'atzar.
rnd_par = random.Random(7)
ordre = list(range(len(vistos)))
rnd_par.shuffle(ordre)
usat = [False] * len(vistos)
parelles = []
for c0, c1 in no_vistos:
    millor, dif = None, 9.9
    for j in ordre:
        if usat[j]:
            continue
        d = abs(vistos[j][0] - c0)
        if d < dif:
            millor, dif = j, d
    if millor is not None and dif <= .03:
        usat[millor] = True
        parelles.append(((c0, c1), vistos[millor]))
print(f"\n{len(parelles)} parelles (tolerancia 0,03)")
if parelles:
    print(f"CER M0 de partida: no vistos {sum(p[0][0] for p in parelles)/len(parelles):.4f} · "
          f"vistos {sum(p[1][0] for p in parelles)/len(parelles):.4f}")
    bn = sum(p[0][0] - p[0][1] for p in parelles) / len(parelles)
    bv = sum(p[1][0] - p[1][1] for p in parelles) / len(parelles)
    print(f"baixada: no vistos {-bn:+.4f} · vistos {-bv:+.4f}")
    rnd = random.Random(20261120)
    reps = sorted(
        (lambda m: sum(x[1][0] - x[1][1] for x in m) / len(m)
         - sum(x[0][0] - x[0][1] for x in m) / len(m))(
            [parelles[rnd.randrange(len(parelles))] for _ in parelles])
        for _ in range(VEGADES))
    lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES)]
    print(f"\ninflacio aparellada = {bv - bn:+.4f}   interval 95 % [{lo:+.4f}, {hi:+.4f}]   "
          + ("INFLACIO" if lo > 0 else "al reves" if hi < 0 else "no es pot dir"))

#: --- la firma: la baixada segons el CER de partida ---
print(f"\n{'CER de M0':>12}{'vistos':>20}{'no vistos':>20}")
for lo_, hi_ in ((0, .05), (.05, .10), (.10, .15), (.15, .20), (.20, .25), (.25, .30), (.30, .36)):
    a = [x for x in vistos if lo_ <= x[0] < hi_]
    b = [x for x in no_vistos if lo_ <= x[0] < hi_]
    fa = f"{-baixada(a):+.4f} (n={len(a)})" if len(a) >= 10 else f"(n={len(a)})"
    fb = f"{-baixada(b):+.4f} (n={len(b)})" if len(b) >= 10 else f"(n={len(b)})"
    print(f"{lo_:5.2f}-{hi_:<6.2f}{fa:>20}{fb:>20}")
