# -*- coding: utf-8 -*-
"""Obre la clau després del judici a cegues i treu el número: abans (greedy + taules del 14-11)
contra després (feix amb lèxic + taules del 15-11), sobre la mateixa mostra de 40.

Per columna: tokens, caselles plenes (segons el jutge), caselles falses, % de falses sobre plenes,
caselles bones (plenes − falses) per tros, frases bo / a mitges / fals / cap, temes bons.
I l'acord del jutge amb ell mateix sobre els 16 duplicats plantats (mateixa `caselles_falses` i
mateixa `frase`): si és baix, la resta no val gaire.

ÚS: ab40_resultat.py <carpeta ab40> [sortida.md]
"""
import collections
import io
import json
import os
import sys

if __name__ == "__main__":
    c = sys.argv[1]
    full = {x["id"]: x for x in json.load(io.open(os.path.join(c, "ab40_full.json"), encoding="utf-8"))}
    clau = {x["id"]: x for x in json.load(io.open(os.path.join(c, "ab40_clau.json"), encoding="utf-8"))}
    jud = {x["id"]: x for x in json.load(io.open(os.path.join(c, "ab40_judici.json"), encoding="utf-8"))}
    falten = [i for i in full if i not in jud]
    #: acord del jutge amb ell mateix: duplicat ↔ original (dup_de és l'índex intern; es troba per contingut)
    per_contingut = collections.defaultdict(list)
    for i, f in full.items():
        per_contingut[(f["am"], tuple(f["interlineal"]), f["frase"])].append(i)
    parelles = [ids for ids in per_contingut.values() if len(ids) >= 2]
    acord_c = sum(1 for ids in parelles if len({jud[i]["caselles_falses"] for i in ids if i in jud}) == 1)
    acord_f = sum(1 for ids in parelles if len({jud[i]["frase"] for i in ids if i in jud}) == 1)
    res = {}
    vist = set()
    for i, k in clau.items():
        if i not in jud or k.get("dup_de") is not None:
            continue
        key = (k["n"], k["col"])
        if key in vist:
            continue
        vist.add(key)
        r = res.setdefault(k["col"], collections.Counter())
        j = jud[i]
        r["trossos"] += 1
        r["tokens"] += len(full[i]["am"].split())
        r["plenes"] += int(j.get("caselles_plenes") or 0)
        r["falses"] += int(j.get("caselles_falses") or 0)
        r["frase_" + str(j.get("frase") or "cap")] += 1
        if j.get("tema_ok") is True:
            r["tema_ok"] += 1
        elif j.get("tema_ok") is False:
            r["tema_fals"] += 1
    linies = ["| | abans (greedy, taules 14-11) | després (feix+lèxic, taules 15-11) |", "|---|---|---|"]
    def v(col, k):
        return res.get(col, {}).get(k, 0)
    for nom, k in (("trossos", "trossos"), ("tokens de l'ASR", "tokens"), ("caselles plenes", "plenes"),
                   ("caselles falses", "falses")):
        linies.append(f"| {nom} | {v('vell', k)} | {v('nou', k)} |")
    for col in ("vell", "nou"):
        res[col]["pct_falses"] = round(100 * v(col, "falses") / max(1, v(col, "plenes")), 1)
        res[col]["bones"] = v(col, "plenes") - v(col, "falses")
    linies.append(f"| % falses sobre plenes | {res['vell']['pct_falses']} % | {res['nou']['pct_falses']} % |")
    linies.append(f"| caselles bones (plenes − falses) | {res['vell']['bones']} | {res['nou']['bones']} |")
    linies.append(f"| frases: bo / a mitges / fals / cap | {v('vell','frase_bo')} / {v('vell','frase_a mitges')} / {v('vell','frase_fals')} / {v('vell','frase_cap')} | "
                  f"{v('nou','frase_bo')} / {v('nou','frase_a mitges')} / {v('nou','frase_fals')} / {v('nou','frase_cap')} |")
    linies.append(f"| temes bons / falsos | {v('vell','tema_ok')} / {v('vell','tema_fals')} | {v('nou','tema_ok')} / {v('nou','tema_fals')} |")
    linies.append(f"\nAcord del jutge amb ell mateix ({len(parelles)} duplicats): caselles falses {acord_c}/{len(parelles)}, frase {acord_f}/{len(parelles)}. Fitxes sense judici: {len(falten)}.")
    out = "\n".join(linies)
    print(out)
    if len(sys.argv) > 2:
        io.open(sys.argv[2], "w", encoding="utf-8").write(out + "\n")
