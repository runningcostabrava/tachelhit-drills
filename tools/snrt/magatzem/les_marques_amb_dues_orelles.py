"""La l -> r del rifeny: es a la parla o es cosa del nostre adaptador?

Anit vaig dir que dues marques fonetiques separen les varietats: k -> s i l -> r, aquesta ultima
molt mes alta als episodis rifenys (12,9 % contra 1 %). Pero aquelles dues xifres les va treure
la NOSTRA orella (MMS + adaptador shi), comparant amb el subtitol. Si l'adaptador shi, davant
d'un so que no coneix, tendis a escriure `r`, la marca seria nostra i no de la llengua.

Aqui es mira sense cap alineament i sense el subtitol, que son les dues fonts de soroll:
**dins de cada orella**, quina proporcio de `r` hi ha sobre el total de `l` + `r` a cada episodi.
Comparar una orella amb ella mateixa entre episodis es valid encara que les dues orelles
escriguin diferent.

Les dues orelles:
  * `shi` = la nostra (MMS-1b-all + adaptador shi + el nostre afinat)
  * `rif` = un model entrenat en rifeny, **altra base i altra ortografia**

PREDICCIO: si la marca es de la parla, les DUES orelles han de treure mes `r` als episodis
rifenys que als tachelhit. Si nomes ho fa la nostra, la marca era nostra i he de desdir-me de la
§13 del DESXIFRAT.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
var = {r["capitol"][:16]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}


def compta(fitxers, nom):
    """r/(l+r) i s/(k+s) per episodi, dins d'una sola orella."""
    per = defaultdict(lambda: defaultdict(int))
    for cami in fitxers:
        for l in io.open(cami, encoding="utf-8"):
            if not l.strip():
                continue
            x = json.loads(l)
            cap = x["id"].split(":")[0][:16]
            t = (x.get("sentit") or "").lower()
            for c in t:
                if c in "lrkšc":
                    per[cap][c] += 1
    files = []
    for cap, c in per.items():
        v = var.get(cap)
        if v not in ("tachelhit", "tarifit", "amazic de l'Atles central"):
            continue
        lr, ks = c["l"] + c["r"], c["k"] + c["š"] + c["c"]
        if lr < 100:
            continue
        files.append((v, cap, lr, 100 * c["r"] / lr, ks,
                      100 * (c["š"] + c["c"]) / ks if ks else float("nan")))
    files.sort()
    print(f"\n=== orella «{nom}»  ({len(files)} episodis amb prou lletres)")
    print(f"{'varietat':<26}{'capitol':<18}{'l+r':>7}{'r %':>8}{'k+š':>7}{'š %':>8}")
    for v, cap, lr, pr, ks, ps in files:
        print(f"{v:<26}{cap:<18}{lr:7d}{pr:8.1f}{ks:7d}{ps:8.1f}")
    for v in ("tachelhit", "amazic de l'Atles central", "tarifit"):
        d = [f for f in files if f[0] == v]
        if not d:
            continue
        lr = sum(f[2] for f in d)
        r = sum(f[2] * f[3] / 100 for f in d)
        ks = sum(f[4] for f in d)
        s = sum(f[4] * f[5] / 100 for f in d if f[5] == f[5])
        print(f"   {v:<26} r = {100*r/lr:5.1f} %   š = {100*s/max(1,ks):5.1f} %"
              f"   ({len(d)} episodis)")


compta([r"E:/tamazight/_sentit/sortida_26/sentit.jsonl"], "shi (la nostra)")
compta([MAG / "prova_rif" / "sortida" / "sentit_rif.jsonl",
        MAG / "prova_dolents" / "sortida" / "sentit_rif.jsonl"], "rif (altra base)")
print("\nSi les dues orelles van en el mateix sentit, la marca es de la parla.")
