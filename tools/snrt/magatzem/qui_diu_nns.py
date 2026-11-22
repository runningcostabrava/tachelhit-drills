"""El k~š es un tret del convidat o un vici del model?

A l'index, la paraula escrita ⵏⵏⴽ («teu») es sent `nnš` 20 vegades i `nnk` 11. Si aixo fos un
vici del model, les dues formes es repartirien per igual entre els convidats. Si es un tret de
la parla, cada convidat dira la seva i les formes es CONCENTRARAN per episodi -- i llavors el
numero no nomes diu que la variacio existeix: diu **qui parla com**, que es el que volem saber.

Es mira, per episodi, quantes vegades l'orella diu cada forma a les paraules que casen amb un
escrit que porta `k`. Nomes compten les paraules que casen, perque en les altres no se sap de
quina paraula parla cadascu.
"""
import io
import json
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

per_cap = defaultdict(lambda: {"k": 0, "š": 0})
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    s = sentit.get(x["id"], {})
    paraules = [w["p"] for w in (s.get("paraules") or [])]
    escrites = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if not paraules or not escrites:
        continue
    for i, j in alinea(paraules, escrites):
        if j is None:
            continue
        eo, ee = esquelet(paraules[i]), esquelet(escrites[j])
        if not eo or not ee or "k" not in ee or prop(eo, ee) > .35:
            continue
        if "k" in eo:
            per_cap[x["capitol"]]["k"] += 1
        elif "š" in eo:
            per_cap[x["capitol"]]["š"] += 1

files = [(c["š"] / max(1, c["k"] + c["š"]), cap, c) for cap, c in per_cap.items()
         if c["k"] + c["š"] >= 5]
files.sort(reverse=True)
print(f"{'convidat':<26}{'diu k':>7}{'diu š':>7}{'% š':>7}")
for _, cap, c in files:
    n = c["k"] + c["š"]
    print(f"{titols.get(cap, cap)[:24]:<26}{c['k']:7d}{c['š']:7d}{100*c['š']/n:6.0f}%")
tk = sum(c["k"] for _, _, c in files)
ts = sum(c["š"] for _, _, c in files)
print(f"\nen conjunt: k {tk} · š {ts} · {100*ts/max(1,tk+ts):.0f}% de š")
if files:
    print(f"el que mes en diu: {100*files[0][0]:.0f}% · el que menys: {100*files[-1][0]:.0f}%")
    print("si fos un vici del model, tots els episodis donarien la mateixa proporcio")
