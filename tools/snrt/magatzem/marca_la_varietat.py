"""Marcar de quina varietat es cada episodi, amb l'evidencia al costat.

El principi de varietat del projecte diu que una frase ha de dir d'on es, i fins ara aquestes
15.365 no ho deien. Ara es pot: dels 25 episodis de Tadfi n Tskla, uns son del Sus (el pais del
tachelhit), uns de l'Atles central i uns del Rif, i aixo es llegeix de tres senyals
INDEPENDENTS:

  1. **el presentador**, que diu d'on es el convidat (ve de l'arab, no toca el nostre OCR ni la
     nostra orella): la part de mencions de lloc de cada zona;
  2. **l'acord ull-orella**, que es desploma quan la varietat no es tachelhit (22,7 % al Sus
     contra 1,7 % al Rif);
  3. **dues marques fonetiques** al so mateix: k->š i l->r, que son del tarifit.

La marca no s'inventa: es posa la zona que el presentador fa dominar, i es desen els tres
senyals perque qui ho llegeixi pugui discutir-ho. Quan els tres no van junts, es diu.

Surt `varietats.tsv` i `varietats.json`.
"""
import io
import json
import glob
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

MAG = r"E:/tamazight/_magatzem"
LLOCS = {
    "sus": ["sous", "souss", "sus", "agadir", "taroudant", "tiznit", "tafraout", "chtouka",
            "ait baha", "inezgane", "massa", "ifni", "guelmim", "tata", "anti-atles",
            "anti atles", "ouarzazate", "taliouine", "igherm", "biougra", "essaouira",
            "imintanout", "chichaoua"],
    "atles": ["azilal", "beni mellal", "khenifra", "midelt", "ait merghad", "ait mrabet",
              "ait ayach", "ait hadiddou", "imilchil", "errachidia", "atles central",
              "khemisset", "ait seghrouchen", "boumalne", "tinghir", "zaida", "ait izdeg",
              "ait yafelman"],
    "rif": ["rif", "nador", "al hoceima", "alhucemas", "driouch", "berkane", "oujda", "taza",
            "temsamane", "ait waryaghel", "aït waryaghel", "guercif", "figuig", "jerada",
            "tarifit", "rifeny", "rifenya", "ait said", "beni snassen", "snassen", "bouarfa"],
}


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

acord = defaultdict(lambda: [0, 0])
for l in io.open(f"{MAG}/acord_triat.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        acord[r["capitol"]][1] += 1
        acord[r["capitol"]][0] += r["grau"] == "A"

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

dades = defaultdict(lambda: {"llocs": defaultdict(int), "k": 0, "š": 0, "l": 0, "r": 0,
                             "linies": 0})
for l in io.open(f"{MAG}/text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    d = dades[x["capitol"]]
    d["linies"] += 1
    t = ((x.get("catala") or "") + " " + (x.get("arab") or "")).lower()
    for zona, noms in LLOCS.items():
        for nom in noms:
            if re.search(r"\b" + re.escape(nom) + r"\b", t):
                d["llocs"][zona] += 1
    s = sentit.get(x["id"], {})
    paraules = [w["p"] for w in (s.get("paraules") or [])]
    escrites = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if not paraules or not escrites:
        continue
    for i, j in alinea(paraules, escrites):
        if j is None:
            continue
        eo, ee = esquelet(paraules[i]), esquelet(escrites[j])
        if not eo or not ee or prop(eo, ee) > .35:
            continue
        if "k" in ee:
            d["k" if "k" in eo else ("š" if "š" in eo else "k")] += 1
        if "l" in ee:
            d["l" if "l" in eo else ("r" if "r" in eo else "l")] += 1

fora = []
for cap, d in dades.items():
    a, n = acord[cap]
    tot = sum(d["llocs"].values())
    zona = max(d["llocs"], key=d["llocs"].get) if tot >= 4 else None
    part = d["llocs"][zona] / tot if zona else 0
    nk, nl = d["k"] + d["š"], d["l"] + d["r"]
    #: la zona que mes mencions té NO n'hi ha prou: un convidat del Sus que parli de música del
    #: Rif en produeix (Said Ou Boulman, 5 mencions del Rif contra 4 del Sus, i és l'episodi amb
    #: més acord de tots). Es demana majoria clara I que l'acord no ho contradigui; quan es
    #: contradiuen, es diu «en dubte» en comptes de triar.
    ac = a / max(1, n)
    nom = {"sus": "tachelhit", "atles": "amazic de l'Atles central", "rif": "tarifit"}
    if zona and part >= .6 and not (zona == "rif" and ac >= .10) \
            and not (zona == "sus" and ac < .05):
        varietat, com = nom[zona], "el presentador, amb majoria clara"
    elif ac >= .15:
        varietat, com = "tachelhit", "l'acord alt (el presentador no és concloent)"
    elif ac < .05:
        varietat, com = "tarifit", "l'acord molt baix (el presentador no és concloent)"
    else:
        varietat, com = "en dubte", "els senyals no van junts"
    fora.append({
        "capitol": cap, "titol": titols.get(cap, cap), "linies": d["linies"],
        "varietat": varietat, "com_s_ha_decidit": com,
        "zona": zona, "part_de_la_zona": round(part, 2),
        "mencions": dict(d["llocs"]), "acord": round(ac, 4),
        "k_a_s": round(d["š"] / nk, 3) if nk >= 5 else None,
        "l_a_r": round(d["r"] / nl, 3) if nl >= 10 else None,
    })
fora.sort(key=lambda r: (r["varietat"], -r["acord"]))

json.dump(fora, io.open(f"{MAG}/varietats.json", "w", encoding="utf-8"), ensure_ascii=False,
          indent=1)
with io.open(f"{MAG}/varietats.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("capitol\ttitol\tvarietat\tpart_zona\tacord\tk_a_s\tl_a_r\tlinies\n")
    for r in fora:
        f.write(f"{r['capitol']}\t{r['titol']}\t{r['varietat']}\t{r['part_de_la_zona']}\t"
                f"{r['acord']}\t{r['k_a_s']}\t{r['l_a_r']}\t{r['linies']}\n")

print(f"{'varietat':<26}{'episodis':>9}{'linies':>9}{'acord mitja':>13}")
per_var = defaultdict(lambda: [0, 0, 0.0])
for r in fora:
    v = per_var[r["varietat"]]
    v[0] += 1
    v[1] += r["linies"]
    v[2] += r["acord"] * r["linies"]
for v, (n, li, ac) in sorted(per_var.items(), key=lambda kv: -kv[1][1]):
    print(f"{v:<26}{n:9d}{li:9d}{100*ac/max(1,li):12.1f}%")

print(f"\n{'titol':<26}{'varietat':<26}{'acord':>7}{'k→š':>6}{'l→r':>6}")
for r in fora:
    print(f"{r['titol'][:24]:<26}{r['varietat']:<26}{100*r['acord']:6.1f}%"
          f"{(100*r['k_a_s'] if r['k_a_s'] is not None else -1):5.0f}%"
          f"{(100*r['l_a_r'] if r['l_a_r'] is not None else -1):5.0f}%")
print(f"\ndesat a {MAG}/varietats.tsv i varietats.json")
