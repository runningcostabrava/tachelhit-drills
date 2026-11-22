"""Quant català del corpus de grau A és utilitzable?

El corpus de grau A (2.190 rèpliques) és el que es veuria: so, tifinag, àrab i català. El català
va sortir de l'àrab amb la cascada de quota gratuïta del Qwen, i mirant l'índex em va aparèixer
una línia que deia «No parlis a l'ombra de la cagarada, Aguau», que no pot ser bona. Val més
saber quantes n'hi ha així que confiar que són poques.

No puc jutjar la traducció de l'àrab jo mateix, però sí comptar els trencaments OBJECTIUS, que
són els que fan mal de debò:

  - sense català;
  - amb lletres àrabs o tifinag a dins (no s'ha traduït);
  - repeticions d'una paraula tres vegades o més (el model s'ha encallat);
  - molt més llarga o molt més curta que l'àrab (ha inventat o ha deixat de traduir);
  - caràcters de control o seqüències de substitució.

El que no es pot comptar així queda dit com el que és: no mesurat.
"""
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
ARAB = re.compile(r"[\u0600-\u06ff]")
TIFINAG = re.compile(r"[\u2d30-\u2d7f]")

c = Counter()
mostres = {}
files = [json.loads(l) for l in io.open(MAG / "corpus_grau_a_triat.jsonl", encoding="utf-8")
         if l.strip()]
for r in files:
    cat = (r.get("catala") or "").strip()
    ar = (r.get("arab") or "").strip()
    mal = None
    if not cat:
        mal = "sense català"
    elif ARAB.search(cat) or TIFINAG.search(cat):
        mal = "porta lletres àrabs o tifinag"
    elif any(ord(ch) < 32 and ch not in "\t" for ch in cat) or "\ufffd" in cat:
        mal = "caràcters trencats"
    else:
        mots = [w.lower() for w in re.findall(r"\w+", cat) if len(w) > 2]
        rep = Counter(mots).most_common(1)
        if rep and rep[0][1] >= 3 and len(mots) >= 4:
            mal = f"paraula repetida {rep[0][1]} vegades"
        elif ar and len(cat) > 3.2 * len(ar):
            mal = "molt més llarga que l'àrab"
        elif ar and len(cat) < 0.35 * len(ar):
            mal = "molt més curta que l'àrab"
    if mal:
        c[mal] += 1
        mostres.setdefault(mal, []).append((cat[:70], ar[:40]))
    else:
        c["sense trencament objectiu"] += 1

n = len(files)
print(f"rèpliques de grau A amb significat: {n}\n")
for k, v in c.most_common():
    print(f"   {k:<34}{v:6d}  {100*v/n:5.1f}%")
print()
for k, ex in mostres.items():
    print(f"--- {k} ({len(ex)})")
    for cat, ar in ex[:3]:
        print(f"    «{cat}»")
        print(f"     àrab: {ar}")
print("\nel que això NO mesura: si la traducció diu el que diu l'àrab. Aixo demana algu que")
print("llegeixi arab, i no esta fet.")
