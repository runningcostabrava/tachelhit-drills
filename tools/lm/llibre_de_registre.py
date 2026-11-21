# -*- coding: utf-8 -*-
"""El llibre de registre del canal: per a cada una de les 566 peces, què té (subtítols humans i
en quines llengües, transcrit automàtic i quina llengua s'hi parla) i què n'hem tret (escoltada
pel nostre lector, minada en dàrija, parells amb subtítol humà, veritat humana en amazic).
En Pablo (15-11): «you should check one by one every video to see if transcripts and translations
are available». Això és la comprovació, escrita, peça per peça.

ÚS: llibre_de_registre.py <cataleg_unic.jsonl> <sortida.md> --escoltats <dir> --escoltats_lm <dir>
     --transcripcions <dir> --mina <jsonl> [<jsonl>…] --veritat <dir amb *.la*.vtt>
"""
import collections
import glob
import io
import json
import os
import sys


def arg(nom, molts=False):
    a = sys.argv
    if nom not in a:
        return [] if molts else None
    i = a.index(nom) + 1
    if not molts:
        return a[i]
    fora = []
    while i < len(a) and not a[i].startswith("--"):
        fora.append(a[i])
        i += 1
    return fora


if __name__ == "__main__":
    cataleg, fora = sys.argv[1], sys.argv[2]
    ids_de = lambda d: set(os.path.basename(f).split(".")[0] for f in glob.glob(os.path.join(d, "*.json"))) if d else set()
    escoltats, escoltats_lm, transcr = ids_de(arg("--escoltats")), ids_de(arg("--escoltats_lm")), ids_de(arg("--transcripcions"))
    minats = {}
    for f in arg("--mina", True):
        for l in io.open(f, encoding="utf-8"):
            d = json.loads(l)
            #: 0 ítems també és «minada»: el professor no hi explicava res (opinió, història)
            minats[d["video"]] = len(d.get("items") or []) or "0"
    veritat = set(os.path.basename(f).split(".")[0] for f in glob.glob(os.path.join(arg("--veritat") or "", "*.la*.vtt")))
    peces = [json.loads(l) for l in io.open(cataleg, encoding="utf-8")]
    ordre = {"classe": 0, "conte": 1, "cançó": 2, "directe": 3, "opinió/altres": 4}
    peces.sort(key=lambda d: (ordre.get(d["mena"], 9), d.get("llengua", ""), -(d.get("durada") or 0)))
    c = collections.Counter()
    linies = [f"# Llibre de registre del canal Tamazight For All — {len(peces)} peces (15-11-2026)\n",
              "Columnes: subtítols humans (llengües), llengua parlada estimada (pel transcrit automàtic), i què n'hem tret: "
              "**E** escoltada pel nostre lector (greedy), **L** escoltada amb el lector amb lèxic, **T** transcrita per al corpus paral·lel, "
              "**M** minada (n ítems d'explicacions en dàrija), **V** veritat humana en amazic (pista llatina/tifinag).\n",
              "| id | mena | llengua | durada | subtítols humans | auto (mots/min) | E | L | T | M | V | títol |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in peces:
        vid = d["id"]
        marques = {"E": vid in escoltats, "L": vid in escoltats_lm, "T": vid in transcr, "M": minats.get(vid, 0), "V": vid in veritat}
        for k, v in marques.items():
            if v:
                c[k] += 1
        hum = ", ".join(d.get("humans_text") or []) or "—"
        if d.get("humans_text"):
            c["humans"] += 1
        dur = d.get("durada") or 0
        linies.append(f"| `{vid}` | {d['mena']} | {d['llengua']} | {dur//60}:{dur%60:02d} | {hum} | {d.get('wpm_auto', '')} | "
                      f"{'✓' if marques['E'] else ''} | {'✓' if marques['L'] else ''} | {'✓' if marques['T'] else ''} | "
                      f"{marques['M'] or ''} | {'✓' if marques['V'] else ''} | {(d.get('titol') or '')[:60].replace('|', '/')} |")
    resum = (f"\n**Recompte:** {c['humans']} amb subtítols humans · {c['E']} escoltades (greedy) · {c['L']} amb lèxic · "
             f"{c['T']} transcrites per al corpus paral·lel · {c['M']} minades · {c['V']} amb veritat humana en amazic.\n")
    linies.insert(3, resum)
    io.open(fora, "w", encoding="utf-8").write("\n".join(linies) + "\n")
    print(resum.strip())
