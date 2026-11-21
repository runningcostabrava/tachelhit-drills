"""L'acord entre l'ull i l'orella als 26 capítols, i el magatzem de paraules que en surt.

L'ull: el tifinag que la fàbrica va llegir de la imatge (a les carpetes del visor).
L'orella: el que ha sentit el nostre transcriptor (sortida del quadern de Kaggle).
El significat: el català, que ve de l'àrab i no toca cap dels dos.

Són tres canals independents. Que l'ull i l'orella coincideixin en l'esquelet consonàntic d'una
frase sencera, sense saber res l'un de l'altre, és molt difícil per casualitat: per això serveix
de filtre sense necessitar cap veritat humana.

Surt:
  acord_26.jsonl        una línia per rèplica amb el grau
  ocurrencies_26.jsonl  una línia per PARAULA sentida, que és on es treballa

    acord_26.py <sortida_del_quadern/sentit.jsonl>
"""
import io
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

VISOR = Path(r"E:\tamazight\_visor")
MAG = Path(r"E:\tamazight\_magatzem")
SENTIT = Path(sys.argv[1]) if len(sys.argv) > 1 else MAG.parent / "_sentit" / "sortida_26" / "sentit.jsonl"
SEGUR = 0.85

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


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


if not SENTIT.exists():
    raise SystemExit(f"encara no hi ha {SENTIT}")
sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x
print(f"talls sentits: {len(sentit)}")

#: les línies de l'ull, per capítol
linies = {}
for carpeta in sorted(VISOR.iterdir()):
    p = carpeta / "subtitols.jsonl"
    if not p.exists() or carpeta.name.startswith("baba_ali") or carpeta.name == "tadfi_goughelt":
        continue   # el Baba Ali no té tifinag llegit de la imatge; el Goughelt ja té el seu
    for i, l in enumerate(io.open(p, encoding="utf-8")):
        if l.strip():
            x = json.loads(l)
            linies[f"{carpeta.name}:{x.get('k', i)}"] = x
print(f"línies amb lectura de l'ull: {len(linies)}")

# ---- per rèplica -----------------------------------------------------------
graus, per_cap = Counter(), defaultdict(Counter)
amb_tot = []
with io.open(MAG / "acord_26.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for ident, x in linies.items():
        cap = ident.split(":")[0]
        s = sentit.get(ident, {})
        ull, orella = (x.get("tifinag") or "").strip(), (s.get("sentit") or "").strip()
        eu, eo = esquelet(ull), esquelet(orella)
        if not eu or not eo:
            graus["sense"] += 1
            per_cap[cap]["sense"] += 1
            continue
        cer = lev(eu, eo) / max(len(eu), len(eo))
        g = "A" if cer <= .35 else ("B" if cer <= .6 else "C")
        graus[g] += 1
        per_cap[cap][g] += 1
        r = {"id": ident, "capitol": cap, "grau": g, "cer": round(cer, 3), "tifinag": ull,
             "sentit": orella, "catala": (x.get("catala") or "").strip() or None,
             "conf": s.get("conf"), "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi")}
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if g == "A" and r["catala"]:
            amb_tot.append(r)

n = sum(graus.values())
print(f"\nper rèplica (de {n}):")
for k in ("A", "B", "C", "sense"):
    print(f"   {k:6s} {graus[k]:6d}  {100*graus[k]/max(1,n):5.1f}%")
print(f"grau A amb significat: {len(amb_tot)}")

# ---- per paraula -----------------------------------------------------------
rep = Counter()
for x in sentit.values():
    for p in x.get("paraules", []):
        e = esquelet(p["p"])
        if len(e) >= 2:
            rep[e] += 1

gp = Counter()
with io.open(MAG / "ocurrencies_26.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for ident, x in linies.items():
        s = sentit.get(ident, {})
        ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
        ull_e = [esquelet(w) for w in ull]
        for p in s.get("paraules", []):
            e = esquelet(p["p"])
            millor, dist = None, 1.0
            for w, we in zip(ull, ull_e):
                d = prop(e, we)
                if d < dist:
                    millor, dist = w, d
            if p["c"] >= SEGUR:
                g = "A" if (millor is not None and dist <= .35) else "B"
            elif len(e) >= 2 and rep[e] >= 3:
                g = "C"
            else:
                g = "D"
            gp[g] += 1
            f.write(json.dumps({"id": ident, "capitol": ident.split(":")[0], "sentit": p["p"],
                                "esquelet": e, "conf": p["c"], "grau": g, "norma": millor,
                                "dist": round(dist, 3), "repeticions": rep[e],
                                "catala": (x.get("catala") or "").strip() or None,
                                "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi")},
                               ensure_ascii=False) + "\n")
np_ = sum(gp.values())
print(f"\nper paraula (de {np_}):")
for k in "ABCD":
    print(f"   {k}: {gp[k]:6d}  {100*gp[k]/max(1,np_):5.1f}%")
print(f"\nformes diferents: {len(rep)}")

print("\nels millors capítols per taxa d'acord:")
ordenats = sorted(per_cap.items(), key=lambda t: -(t[1]["A"] / max(1, sum(t[1].values()))))
for cap, c in ordenats[:6]:
    tot = sum(c.values())
    print(f"   {cap[:18]}… A {c['A']:4d} de {tot:4d}  ({100*c['A']/max(1,tot):4.1f}%)")
