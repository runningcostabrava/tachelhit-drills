"""Quant s'infla el filtre si la ronda 2 sent el SNRT amb M1.

Dos grups de talls, tots dos de grau A sota M0 (CER d'esquelet <= 0,35), tots dos del SNRT:

  * **vistos**: els 1.849 que M1 va fer servir per entrenar-se (`inflacio/sortida`)
  * **no vistos**: els dels quatre capitols RETINGUTS, que M1 no ha tocat mai
    (`ronda/sortida/snrt_B_sortides.json`, prova `snrt-retingut`)

i per a cada grup la mateixa pregunta: passant de M0 a M1, quant baixa el CER d'esquelet contra
el subtitol, i quina part dels talls passa el filtre de 0,35.

    inflacio = (baixada als vistos) - (baixada als no vistos)

L'interval surt per remostreig de la DIFERENCIA, no de cada grup per separat.

El que aquesta mesura NO pot separar, i es diu al resultat: els retinguts son capitols sencers
diferents, i a la diferencia hi ha, a mes de la memoritzacio, el que separa uns capitols dels
altres. Per aixo la comparacio principal es fa nomes amb els capitols TACHELHIT de les dues
bandes (Akounad i Zahour contra els tachelhit del train), on les dues poblacions son mes
semblants; la de tot tambe es diu.

ESCRIT ABANS DE VEURE ELS NUMEROS -- que vol dir cada resultat:

  * interval de la diferencia que passa per zero  ->  no hi ha inflacio mesurable: adoptar M1 i
    tornar a sentir tot el SNRT no fa trampa, i la ronda 2 pot fer servir tot el material.
  * diferencia clarament positiva  ->  n'hi ha: la ronda 2 ha de triar el corpus nomes de talls
    que M1 no hagi vist, i el preu es el corpus que es perd (es compta aqui mateix).

    mira_la_inflacio.py
"""
import io
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
LLINDAR, VEGADES = .35, 2000
TACHELHIT_RETINGUTS = {"wckionryvrwatrvs", "jerkqzqplguvpzoh"}   #: Akounad i Zahour


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


varietat = {r["capitol"][:16]: r["varietat"]
            for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

#: --- els vistos ---
rows = {r["id"]: r for r in json.load(
    io.open(MAG / "inflacio" / "dades" / "rows.json", encoding="utf-8"))}
sent = {}
for quin in ("m0", "m1"):
    p = MAG / "inflacio" / "sortida" / f"sentit_{quin}.jsonl"
    if not p.exists():
        raise SystemExit(f"encara no hi ha {p} (recull la feina primer)")
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            sent.setdefault(x["id"], {})[quin] = (x.get("sentit") or "").strip()

vistos = []
for ident, d in sent.items():
    r = rows.get(ident)
    if not r or "m0" not in d or "m1" not in d:
        continue
    eu = esquelet(r["tifinag"])
    if not eu:
        continue
    vistos.append((r["slug"][:16], prop(eu, esquelet(d["m0"])), prop(eu, esquelet(d["m1"]))))

#: --- els no vistos: els retinguts ---
files = json.load(io.open(MAG / "ronda" / "sortida" / "snrt_B_sortides.json", encoding="utf-8"))
per = defaultdict(dict)
for x in files:
    if x.get("prova") != "snrt-retingut":
        continue
    clau = (x.get("video"), str(x.get("de")))
    quin = "m0" if (x.get("model") or "").startswith("abans") else "m1"
    per[clau][quin] = (x.get("dit") or "").strip()
    per[clau]["or"] = (x.get("or") or "").strip()
    per[clau]["cap"] = (x.get("video") or "")[:16]

no_vistos = []
for clau, d in per.items():
    if "m0" not in d or "m1" not in d:
        continue
    eu = esquelet(d["or"])
    if not eu:
        continue
    no_vistos.append((d["cap"], prop(eu, esquelet(d["m0"])), prop(eu, esquelet(d["m1"]))))


def mira(nom, v, nv):
    v = [x for x in v if x[1] <= LLINDAR]
    nv = [x for x in nv if x[1] <= LLINDAR]
    if len(v) < 30 or len(nv) < 30:
        print(f"\n{nom}: massa pocs talls ({len(v)} vistos, {len(nv)} no vistos)")
        return
    print(f"\n=== {nom}")
    print(f"{'grup':<12}{'talls':>7}{'CER M0':>9}{'CER M1':>9}{'baixa':>9}"
          f"{'passen 0,35 amb M1':>21}")
    res = {}
    for etiqueta, grup in (("vistos", v), ("no vistos", nv)):
        c0 = sum(x[1] for x in grup) / len(grup)
        c1 = sum(x[2] for x in grup) / len(grup)
        passen = sum(1 for x in grup if x[2] <= LLINDAR) / len(grup)
        print(f"{etiqueta:<12}{len(grup):7d}{c0:9.4f}{c1:9.4f}{c1-c0:+9.4f}{100*passen:20.1f}%")
        res[etiqueta] = (c0, c1, grup)
    dif = (res["vistos"][0] - res["vistos"][1]) - (res["no vistos"][0] - res["no vistos"][1])
    rnd = random.Random(20261120)
    reps = []
    for _ in range(VEGADES):
        a = [v[rnd.randrange(len(v))] for _ in v]
        b = [nv[rnd.randrange(len(nv))] for _ in nv]
        ba = sum(x[1] - x[2] for x in a) / len(a)
        bb = sum(x[1] - x[2] for x in b) / len(b)
        reps.append(ba - bb)
    reps.sort()
    baix, alt = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES)]
    diu = ("INFLACIO" if baix > 0 else
           "els vistos milloren MENYS" if alt < 0 else "no es pot dir (passa per zero)")
    print(f"\ninflacio = {dif:+.4f}   interval 95 % [{baix:+.4f}, {alt:+.4f}]   {diu}")
    return diu


print(f"{len(vistos)} talls vistos · {len(no_vistos)} talls retinguts (abans de filtrar)")
mira("tots els capitols", vistos, no_vistos)
mira("nomes tachelhit (les dues bandes)",
     [x for x in vistos if varietat.get(x[0]) == "tachelhit"],
     [x for x in no_vistos if x[0] in TACHELHIT_RETINGUTS])
#: El numerador son talls de **grau A** i el denominador que hi havia era el **cataleg
#: sencer** (14.426). Es llegia «el 13 % del material», quan de grau A nomes n'hi ha 2.190: el
#: preu comparable es el 84 %. Un numerador filtrat contra un denominador sense filtrar es la
#: mateixa trampa que feia dir que el record era del 99,7 %.
grau_a = sum(1 for l in io.open(MAG / "acord_triat.jsonl", encoding="utf-8") if l.strip()
             and (lambda c: c is not None and float(c) <= 0.35)(
                 json.loads(l).get("cer_esq", json.loads(l).get("cer"))))
cataleg = sum(1 for l in io.open(MAG / "acord_triat.jsonl", encoding="utf-8") if l.strip())
print("\nSi hi ha inflacio, el preu d'evitar-la es el corpus que M1 ja ha vist:")
print(f"   {len(vistos)} talls dels {grau_a} de GRAU A ({100*len(vistos)/max(1,grau_a):.0f} %)"
      f" -- no dels {cataleg} del cataleg sencer, que en faria nomes un"
      f" {100*len(vistos)/max(1,cataleg):.0f} %")
