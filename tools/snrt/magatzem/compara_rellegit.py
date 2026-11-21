"""La relectura, ¿puja la taxa d'acord? Un capítol, abans i després, abans de gastar-hi hores.

Es compara el text que va deixar la fàbrica (`plantilles-segmentador-v1`) amb el que llegeix el
lector d'avui sobre les mateixes imatges, i es mesura cadascun contra el MATEIX so sentit. Si no
puja, la relectura no val i s'ha de dir; rellegir 25 capítols són unes tres hores i no es gasten
per intuïció.
"""
import io
import json
import sys
import unicodedata
from pathlib import Path

MAG = Path(r"E:\tamazight\_magatzem")
VISOR = Path(r"E:\tamazight\_visor")
SENTIT = Path(r"E:\tamazight\_sentit\sortida_26\sentit.jsonl")

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


def compta(slug, textos):
    """A/B/C comptats contra el so, amb el text que se li doni."""
    g = {"A": 0, "B": 0, "C": 0, "sense": 0}
    for k, ull in textos.items():
        orella = sentit.get(f"{slug}:{k}", "")
        eu, eo = esquelet(ull), esquelet(orella)
        if not eu or not eo:
            g["sense"] += 1
            continue
        cer = lev(eu, eo) / max(len(eu), len(eo))
        g["A" if cer <= .35 else ("B" if cer <= .6 else "C")] += 1
    return g


slugs = sys.argv[1:] or [p.stem for p in sorted((MAG / "rellegit_26").glob("*.json"))]
print(f"{'capítol':<18}{'abans':>22}{'després':>22}")
tot_a = tot_d = tot_n = 0
for slug in slugs:
    nou = json.load(io.open(MAG / "rellegit_26" / f"{slug}.json", encoding="utf-8"))["llegit"]
    vell = {}
    for l in io.open(VISOR / slug / "subtitols.jsonl", encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            vell[str(x["k"])] = (x.get("tifinag") or "").strip()
    a, d = compta(slug, vell), compta(slug, nou)
    n = sum(a.values())
    tot_a += a["A"]; tot_d += d["A"]; tot_n += n
    print(f"{slug[:16]:<18}{a['A']:6d} ({100*a['A']/n:4.1f}%)      "
          f"{d['A']:6d} ({100*d['A']/n:4.1f}%)   {100*(d['A']-a['A'])/n:+5.1f} punts")

if tot_n:
    print(f"\ntotal: {tot_a} -> {tot_d} de {tot_n}   "
          f"({100*tot_a/tot_n:.1f}% -> {100*tot_d/tot_n:.1f}%, {100*(tot_d-tot_a)/tot_n:+.1f} punts)")
