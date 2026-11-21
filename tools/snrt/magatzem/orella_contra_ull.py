"""Quines línies tenen l'orella i l'ull d'acord. És el filtre que falta.

Principi d'en Pablo (19-11-2026): **la traducció es fa des de l'àrab i l'aprenentatge es fa des
del tifinag.** L'àrab dona el significat de cada rèplica sense haver de fiar-se de l'OCR amaziga;
el tifinag és la llengua que volem que el model aprengui a sentir i a traduir.

D'això en surt una comprovació que abans no es podia fer: per a cada rèplica tenim DUES lectures
independents de la mateixa frase amaziga —el que el lector ha vist a la pantalla (`tifinag`) i el
que el transcriptor ha sentit al so (`sentit`)— i cap de les dues no sap què ha dit l'altra. Quan
coincideixen, és molt difícil que totes dues s'equivoquin igual: aquella línia té text amazic de
fiar, so, i significat (del català de l'àrab). Les quatre coses alhora.

Es comparen per ESQUELET CONSONÀNTIC: les vocals i l'ortografia són justament on l'estàndard i el
dialecte difereixen, i comptar-les com a error barrejaria dos problemes diferents.

No escriu res al visor ni a producció: deixa `acord.jsonl` al magatzem.
"""
import io
import json
import re
import unicodedata
from pathlib import Path

ORIG = Path(r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay\tadfi_goughelt\subtitols.jsonl")
SENTIT = Path(r"E:\tamazight\_sentit\sortida\sentit.jsonl")
DESTI = Path(r"E:\tamazight\_magatzem\acord.jsonl")

#: mateixa taula que el nucli del cercle (`cercle_observa_snrt.py`), per no inventar-ne una altra
TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiou")


def esquelet(t):
    """Només les consonants, en un sol alfabet. Les vocals cauen: són on l'estàndard i la parla
    es diferencien més, i aquí es vol saber si parlen de la mateixa paraula."""
    t = unicodedata.normalize("NFC", t or "").lower()
    fora = []
    for c in t:
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


sentit = {x["id"]: x for x in (json.loads(l) for l in io.open(SENTIT, encoding="utf-8") if l.strip())}
files = [json.loads(l) for l in io.open(ORIG, encoding="utf-8") if l.strip()]

graus = {"A (orella i ull d'acord)": 0, "B (es toquen)": 0, "C (no s'assemblen)": 0,
         "sense les dues lectures": 0}
sortida = []
for x in files:
    s = sentit.get(x["id"], {})
    ull, orella = (x.get("tifinag") or "").strip(), (s.get("sentit") or "").strip()
    cat = (x.get("catala_de_arab") or "").strip()
    if not ull or not orella:
        graus["sense les dues lectures"] += 1
        continue
    eu, eo = esquelet(ull), esquelet(orella)
    if not eu or not eo:
        graus["sense les dues lectures"] += 1
        continue
    cer = lev(eu, eo) / max(len(eu), len(eo))
    grau = "A" if cer <= 0.35 else ("B" if cer <= 0.6 else "C")
    graus[{"A": "A (orella i ull d'acord)", "B": "B (es toquen)",
           "C": "C (no s'assemblen)"}[grau]] += 1
    sortida.append({"id": x["id"], "grau": grau, "cer": round(cer, 3), "tifinag": ull,
                    "sentit": orella, "catala_de_arab": cat or None,
                    "conf": s.get("conf"), "tall": x.get("tall"),
                    "de": x.get("tall_de"), "a": x.get("tall_a")})

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for r in sortida:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"rèpliques: {len(files)}")
for k, n in graus.items():
    print(f"   {k:28s} {n:5d}  {100*n/len(files):5.1f}%")
amb_cat = sum(1 for r in sortida if r["grau"] == "A" and r["catala_de_arab"])
print(f"\ngrau A amb significat (català de l'àrab) i so: {amb_cat}")
print(f"desat a {DESTI}")
print("\nmostra del grau A (ull / orella / significat):")
for r in [r for r in sortida if r["grau"] == "A"][:6]:
    print(f"   ull   : {r['tifinag'][:46]}")
    print(f"   orella: {r['sentit'][:46]}   (cer {r['cer']})")
    print(f"   vol dir: {(r['catala_de_arab'] or '—')[:60]}")
