"""Compara l'orella rifenya amb la de tachelhit, episodi a episodi.

La predicció escrita abans de mesurar-la: si els deu convidats que no entenem son del Rif,
aquesta orella n'ha de treure MES acord que el `shi` (que hi fa 0-2 %), i als dos controls de
tachelhit n'ha de treure MENYS (el `shi` hi fa 32-40 %).

Dues lectures de la `č`, i es diuen les dues perque triar-ne una seria decidir la prova:

  - **estricta**: la `č` es una consonant propia, de manera que una forma palatalitzada NO casa
    amb la `k` del subtitol estandard;
  - **indulgent**: `č` -> `k`, que val tant com dir «ha reconegut la paraula encara que el
    parlant la palatalitzi». Afavoreix el rifeny, i per aixo va a part.

    mira_el_rifeny.py [carpeta_de_sortida]
"""
import io
import json
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_magatzem/prova_adaptadors/sortida")

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(r"E:/tamazight/_magatzem/varietats.json", encoding="utf-8"))}
titols = {r["capitol"]: r["titol"]
          for r in json.load(io.open(r"E:/tamazight/_magatzem/varietats.json",
                                     encoding="utf-8"))}

ull = {}
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        ull[x["id"]] = x.get("tifinag") or ""


def taxa(a, b):
    return lev(a, b) / max(len(a), len(b)) if a and b else 1.0


def mesura(p, indulgent):
    """Acord per episodi del fitxer `p`."""
    per = {}
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        dit = (x.get("sentit") or "").strip()
        eo = esquelet(dit)
        if indulgent:
            eo = eo.replace("č", "k")
        ee = esquelet(ull.get(x["id"], ""))
        if not eo or not ee:
            continue
        cap = x["id"].split(":")[0]
        c = per.setdefault(cap, [0, 0])
        c[1] += 1
        c[0] += taxa(eo, ee) <= .35
    return per


fitxers = {p.stem.split("_", 1)[1]: p for p in SORTIDA.glob("sentit_*.jsonl")}
if "rif" not in fitxers:
    raise SystemExit(f"encara no hi ha sentit_rif.jsonl a {SORTIDA}")

shi = mesura(fitxers["shi"], False) if "shi" in fitxers else {}
rif_e = mesura(fitxers["rif"], False)
rif_i = mesura(fitxers["rif"], True)

print(f"{'episodi':<24}{'varietat':<12}{'shi':>7}{'rif':>7}{'rif indulgent':>15}{'talls':>7}")
grups = {}
for cap in sorted(rif_e, key=lambda c: (var.get(c, "z"), titols.get(c, c))):
    v = var.get(cap, "?")
    a_s = 100 * shi.get(cap, [0, 1])[0] / max(1, shi.get(cap, [0, 1])[1]) if shi else float("nan")
    a_e = 100 * rif_e[cap][0] / max(1, rif_e[cap][1])
    a_i = 100 * rif_i[cap][0] / max(1, rif_i[cap][1])
    print(f"{titols.get(cap, cap)[:22]:<24}{v[:10]:<12}{a_s:6.1f}%{a_e:6.1f}%{a_i:14.1f}%"
          f"{rif_e[cap][1]:7d}")
    g = grups.setdefault(v, [0, 0, 0, 0])
    g[0] += shi.get(cap, [0, 0])[0]
    g[1] += rif_e[cap][0]
    g[2] += rif_i[cap][0]
    g[3] += rif_e[cap][1]

print(f"\n{'varietat':<24}{'shi':>7}{'rif':>7}{'rif indulgent':>15}{'talls':>7}")
for v, g in sorted(grups.items()):
    print(f"{v[:22]:<24}{100*g[0]/max(1,g[3]):6.1f}%{100*g[1]/max(1,g[3]):6.1f}%"
          f"{100*g[2]/max(1,g[3]):14.1f}%{g[3]:7d}")

sh = grups.get("tachelhit")
rf = grups.get("tarifit")
if sh and rf:
    print("\nla predicció era: el rifeny MILLOR que el shi al tarifit, i PITJOR al tachelhit")
    print(f"   al tarifit:   shi {100*rf[0]/max(1,rf[3]):.1f}% · rif {100*rf[1]/max(1,rf[3]):.1f}%"
          f"  ->  {'COMPLEIX' if rf[1] > rf[0] else 'NO compleix'}")
    print(f"   al tachelhit: shi {100*sh[0]/max(1,sh[3]):.1f}% · rif {100*sh[1]/max(1,sh[3]):.1f}%"
          f"  ->  {'COMPLEIX' if sh[1] < sh[0] else 'NO compleix'}")
