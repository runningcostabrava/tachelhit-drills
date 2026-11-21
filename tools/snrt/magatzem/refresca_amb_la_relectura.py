"""Fa servir la relectura d'avui en lloc del text desat, i torna a comptar.

El `tifinag` de `subtitols.jsonl` el va llegir un lector més vell. Rellegint les mateixes
franges amb el d'ara, la taxa d'acord amb el que sent el model puja de 10,7 % a 17,1 % sense
tocar res més. Això actualitza:

  - `acord.jsonl`      (graus per rèplica)
  - `ocurrencies.jsonl` (graus per paraula, que és on es treballa)
  - el fitxer del visor, perquè el tifinag que es veu a la pantalla sigui el bo

No toca `subtitols.jsonl`, que és la sortida de la fàbrica i no és meva per reescriure: la
relectura viu al magatzem amb la data i el que la va fer.
"""
import io
import json
import unicodedata
from collections import Counter
from pathlib import Path

RELLEGIT = Path(r"E:\tamazight\_magatzem\rellegit.json")
SENTIT = Path(r"E:\tamazight\_sentit\sortida\sentit.jsonl")
CAP = Path(r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay\tadfi_goughelt")
VISOR = Path(r"E:\tamazight\_visor\tadfi_goughelt\subtitols.jsonl")
AC = Path(r"E:\tamazight\_magatzem\acord.jsonl")
OC = Path(r"E:\tamazight\_magatzem\ocurrencies.jsonl")
MODEL = "mms-1b-all+shi+adaptador_inici (19-11-2026)"
LECTOR = "lector_tifinag lector-tawnza (19-11-2026)"
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


nou = json.load(io.open(RELLEGIT, encoding="utf-8"))["llegit_amb"]
sentit = {x["id"]: x for x in (json.loads(l) for l in io.open(SENTIT, encoding="utf-8") if l.strip())}
subs = [json.loads(l) for l in io.open(CAP / "subtitols.jsonl", encoding="utf-8") if l.strip()]

# ---- per rèplica ----------------------------------------------------------
graus, acord = Counter(), []
for i, x in enumerate(subs):
    k = x.get("k", i)
    ull = (nou.get(str(k)) or "").strip()
    s = sentit.get(x["id"], {})
    orella = (s.get("sentit") or "").strip()
    eu, eo = esquelet(ull), esquelet(orella)
    if not eu or not eo:
        graus["sense"] += 1
        g, cer = None, None
    else:
        cer = lev(eu, eo) / max(len(eu), len(eo))
        g = "A" if cer <= .35 else ("B" if cer <= .6 else "C")
        graus[g] += 1
    acord.append({"id": x["id"], "k": k, "grau": g, "cer": None if cer is None else round(cer, 3),
                  "tifinag": ull or None, "sentit": orella or None,
                  "catala_de_arab": (x.get("catala_de_arab") or "").strip() or None,
                  "conf": s.get("conf"), "so": x.get("tall"),
                  "de": x.get("tall_de"), "a": x.get("tall_a"),
                  "lector": LECTOR, "model": MODEL})
with io.open(AC, "w", encoding="utf-8", newline="\n") as f:
    for r in acord:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"per rèplica: A {graus['A']} ({100*graus['A']/len(subs):.1f}%)  B {graus['B']}  "
      f"C {graus['C']}  sense {graus['sense']}")

# ---- per paraula ----------------------------------------------------------
rep = Counter()
for x in sentit.values():
    for p in x.get("paraules", []):
        e = esquelet(p["p"])
        if len(e) >= 2:
            rep[e] += 1

files = []
for i, x in enumerate(subs):
    k = x.get("k", i)
    ull = [w for w in (nou.get(str(k)) or "").split() if w.strip()]
    ull_e = [esquelet(w) for w in ull]
    s = sentit.get(x["id"], {})
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
        files.append({"capitol": "tadfi_goughelt", "id": x["id"], "sentit": p["p"], "esquelet": e,
                      "conf": p["c"], "grau": g, "norma": millor, "dist": round(dist, 3),
                      "repeticions": rep[e], "so": x.get("tall"), "de": x.get("tall_de"),
                      "a": x.get("tall_a"),
                      "catala_de_arab": (x.get("catala_de_arab") or "").strip() or None,
                      "model": MODEL, "lector": LECTOR})
with io.open(OC, "w", encoding="utf-8", newline="\n") as f:
    for r in files:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
gp = Counter(r["grau"] for r in files)
print(f"per paraula: " + "  ".join(f"{k} {gp[k]} ({100*gp[k]/len(files):.1f}%)" for k in "ABCD"))

# ---- el visor -------------------------------------------------------------
visor = [json.loads(l) for l in io.open(VISOR, encoding="utf-8") if l.strip()]
if len(visor) != len(subs):
    raise SystemExit("el visor i la font no casen: no el toco")
for v, x, in zip(visor, subs):
    v["tifinag"] = (nou.get(str(x.get("k"))) or "").strip() or None
with io.open(VISOR, "w", encoding="utf-8", newline="\n") as f:
    for v in visor:
        f.write(json.dumps(v, ensure_ascii=False) + "\n")
print(f"visor actualitzat amb la relectura: {sum(1 for v in visor if v['tifinag'])} línies amb tifinag")
