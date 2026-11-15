# -*- coding: utf-8 -*-
"""Induir glosses a partir del corpus paral·lel sorollós (ASR amazic ↔ subtítol humà anglès).

Mètode: per a cada token amazic prou freqüent, quins mots anglesos de contingut surten al mateix
rètol més del que l'atzar faria (Dice sobre rètols: 2·c(a,e) / (c(a) + c(e))). És el mateix
raonament que va confirmar `turft` = «ship» a mà, fet per a tots els tokens alhora. El que surt
NO és una glossa: és un candidat amb un número, que es compara amb el diccionari:
  · coincideix amb el diccionari → la glossa queda confirmada per un parlant (el subtitulador);
  · el diccionari no té el token → candidat nou (el lèxic del camp que faltava);
  · contradiu el diccionari → un dels dos és fals; a mirar.
Els subtítols humans tradueixen el sentit, no paraula per paraula, i l'ASR talla malament: el
senyal és feble i cal freqüència. Per això el mínim de rètols per token és 4.

ÚS: induccio.py <parells.jsonl> <sortida.md> [mínim de rètols=4]
"""
import collections
import io
import json
import re
import sys

STOP_EN = set("""the a an and or of to in on at for with from by is are was were be been being am i you he she it
we they me him her us them my your his its our their this that these those there here not no yes do does did
have has had will would can could shall should may might must as if then than so but what which who whom whose
when where why how all any some one two very just also too only even still about into out up down over under
again more most such own same other s t ll re ve d m don didn doesn isn aren wasn weren won can't let go get got
going come came said say says tell told like know knew think thought want wanted take took give gave make made
see saw look looked find found put keep let oh ah hey well now back off away ever never always""".split())


def mots(t):
    return [w for w in re.findall(r"[a-z']+", t.lower()) if len(w) > 2 and w not in STOP_EN]


if __name__ == "__main__":
    parells = [json.loads(l) for l in io.open(sys.argv[1], encoding="utf-8") if l.strip()]
    minim = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    c_am, c_en, c_junts = collections.Counter(), collections.Counter(), collections.Counter()
    for p in parells:
        if not p.get("en"):
            continue
        am = set(w.lower() for w in p["asr"].split() if len(w) >= 3)
        en = set(mots(p["en"]))
        c_am.update(am)
        c_en.update(en)
        for a in am:
            for e in en:
                c_junts[(a, e)] += 1
    files = []
    for a, na in c_am.items():
        if na < minim:
            continue
        cands = []
        for (x, e), nj in c_junts.items():
            if x != a or nj < 2:
                continue
            dice = 2 * nj / (na + c_en[e])
            cands.append((dice, nj, e))
        cands.sort(reverse=True)
        if cands and cands[0][0] >= 0.25:
            files.append((na, a, cands[:3]))
    files.sort(key=lambda x: -x[0])
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write(f"# Glosses induïdes del corpus paral·lel ({len(parells)} rètols, mínim {minim} rètols per token)\n\n")
        g.write("Candidats, no glosses: Dice ≥ 0,25 entre el token de l'ASR i un mot anglès del mateix rètol.\n\n")
        g.write("| rètols | token ASR | candidats anglesos (Dice, rètols junts) |\n|---|---|---|\n")
        for na, a, cands in files:
            g.write(f"| {na} | `{a}` | " + "; ".join(f"**{e}** ({d:.2f}, {nj})" for d, nj, e in cands) + " |\n")
    print(f"{len(files)} tokens amb candidat → {sys.argv[2]}")
    for na, a, cands in files[:25]:
        print(f"  {na:4} {a:14} " + "; ".join(f"{e} ({d:.2f},{nj})" for d, nj, e in cands))
