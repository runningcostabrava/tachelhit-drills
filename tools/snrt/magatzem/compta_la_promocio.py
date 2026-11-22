"""Quants talls promou M1? (i per tant: te material la ronda 2?)

El corpus de la ronda 2 ha de sortir nomes d'allo que M1 no ha vist, i no queda cap tall no vist
per sota del llindar fora dels capitols retinguts. O sigui que tot ha de sortir de **promocio**:
talls que avui son per sobre de 0,35 i que amb M1 hi baixen.

Es compta sobre els 3.164 candidats (no vistos, fora dels retinguts, CER de M0 <= 0,60), amb les
dues mesures fetes pel MATEIX nucli i passades pel mateix `rica()`, que es la precaucio que la
primera mesura de la inflacio no tenia.

PREDICCIO, escrita abans: la millora de M1 als talls que no ha vist era d'uns 0,015, o sigui que
nomes creuarien els que avui son entre 0,35 i 0,365. Espero unes desenes. Si es aixi, el SNRT
s'ha esgotat a aquest llindar.

Tambe es diu quantes hores serien i de quina varietat, que es el que decideix si val la pena.
"""
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
LLINDAR = .35

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
rows = {r["id"]: r for r in json.load(
    io.open(MAG / "ronda2" / "dades" / "rows.json", encoding="utf-8"))}
#: durada i catala, del catalegue
extra = {}
for l in io.open(MAG / "acord_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        extra[x["id"]] = x

sent = {}
for quin in ("m0", "m1"):
    p = MAG / "ronda2" / "sortida" / f"sentit_{quin}.jsonl"
    if not p.exists():
        raise SystemExit(f"encara no hi ha {p}")
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            sent.setdefault(x["id"], {})[quin] = (x.get("sentit") or "").strip()

trams = ((.35, .40), (.40, .45), (.45, .50), (.50, .55), (.55, .61))
n = Counter()
promoguts = []
for ident, d in sent.items():
    r = rows.get(ident)
    if not r or "m0" not in d or "m1" not in d or not esq(r["tifinag"]):
        continue
    c0, c1 = cer(r["tifinag"], d["m0"]), cer(r["tifinag"], d["m1"])
    for lo, hi in trams:
        if lo <= c0 < hi:
            n[(lo, "n")] += 1
            n[(lo, "baixa")] += c0 - c1
            if c1 <= LLINDAR:
                n[(lo, "creuen")] += 1
                promoguts.append((ident, r, c0, c1))

print(f"{sum(n[(lo, 'n')] for lo, _ in trams)} candidats mesurats\n")
print(f"{'CER sota M0':>14}{'talls':>8}{'baixada':>10}{'creuen 0,35':>14}{'%':>7}")
for lo, hi in trams:
    k = n[(lo, "n")]
    if not k:
        continue
    print(f"{lo:6.2f}-{hi:<7.2f}{k:8d}{-n[(lo, 'baixa')]/k:+10.4f}{n[(lo, 'creuen')]:14d}"
          f"{100*n[(lo, 'creuen')]/k:7.1f}")

print(f"\nPROMOGUTS: {len(promoguts)} talls")
if promoguts:
    seg = per_var = 0
    hores = defaultdict(float)
    amb_catala = 0
    for ident, r, c0, c1 in promoguts:
        x = extra.get(ident, {})
        if x.get("t_ini") is not None and x.get("t_fi") is not None:
            d = float(x["t_fi"]) - float(x["t_ini"])
            seg += d
            hores[var.get(r["slug"][:16], "?")] += d
        if (x.get("catala") or "").strip():
            amb_catala += 1
    print(f"   {seg/3600:.2f} hores · {amb_catala} amb significat en català")
    for v, s in sorted(hores.items(), key=lambda kv: -kv[1]):
        print(f"   {v:<28}{s/3600:.2f} h")
    with io.open(MAG / "corpus_ronda2.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for ident, r, c0, c1 in promoguts:
            x = extra.get(ident, {})
            f.write(json.dumps({"id": ident, "capitol": r["slug"], "tifinag": r["tifinag"],
                                "sentit_m1": sent[ident]["m1"], "cer_m0": round(c0, 4),
                                "cer_m1": round(c1, 4), "catala": x.get("catala"),
                                "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi")},
                               ensure_ascii=False) + "\n")
    print("   escrit corpus_ronda2.jsonl")
print("\nPer comparar: el train de la ronda 1 eren 1.678 talls del SNRT (1,1 h) + 1.421 de Zouhir.")
