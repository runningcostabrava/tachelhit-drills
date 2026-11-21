"""El lexic diferencial, fet amb el SNRT, sap dir d'on es una frase de la BIBLIOTECA?

Anit vaig separar els 25 capitols de Tadfi n Tskla en tres llengues, i la prova mes forta va ser
un lexic diferencial: les formes que surten molt mes als episodis tachelhit que als rifenys, i a
l'inreves. Validat deixant-ne un fora, encertava 20 de 22 episodis.

Pero el lexic surt del SNRT, es jutja amb episodis del SNRT, i el sent la MATEIXA orella. Aixo
es un cercle: pot estar mesurant una manya del model i no una propietat de la llengua.

Aqui se'n surt. El manifest de la biblioteca (`manifest_v3.jsonl`, 6.628 gravacions) porta text
escrit per PERSONES i una etiqueta de varietat que no ha sortit mai de cap mesura meva: ve de qui
va recollir cada frase. Si el lexic del SNRT sap separar aquestes etiquetes, es que parla de la
llengua; si no, parlava del model.

PREDICCIO, escrita abans de mesurar-ho:
  `shi` (tachelhit) ha de treure molta mes densitat de formes tachelhit que rifenyes. El `tzm`
  (Atles central) ha de quedar entremig i tirant cap al tachelhit, com van quedar els tres
  episodis de l'Atles. A la biblioteca no hi ha rifeny, i per tant NO espero cap grup que tiri
  cap al rifeny: si n'hi surt cap, el lexic no mesura el que dic.

Avis sobre el que aixo NO prova: el lexic es va fer amb paraules SENTIDES (ortografia del model)
i aqui s'aplica a text ESCRIT per persones. Les formes que no casin per ortografia no compten a
favor ni en contra: es per aixo que es diu quantes formes del lexic s'han trobat.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MANIFEST = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
MIN_TOTAL, MIN_EPISODIS = 12, 3

#: --- el lexic, fet nomes amb el SNRT (mateix codi que `de_quina_varietat_es_baba_ali.py`) ---
var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

per_ep = defaultdict(lambda: defaultdict(int))
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x["capitol"] not in var:
        continue
    for p in (sentit.get(x["id"], {}).get("paraules") or []):
        if p.get("c", 0) >= .85 and len(esquelet(p["p"])) >= 3:
            #: per ESQUELET i no per forma: la biblioteca escriu el tachelhit en tifinag i el
            #: lexic surt de l'orella, que escriu en llati. Comparant formes senceres surt un
            #: zero absolut (0 de 9.278 paraules), que no vol dir res mes que dos alfabets.
            per_ep[x["capitol"]][esquelet(p["p"])] += 1

c = defaultdict(lambda: defaultdict(int))
eps = defaultdict(lambda: defaultdict(set))
tot = defaultdict(int)
for cap, formes in per_ep.items():
    v = var.get(cap)
    if v not in ("tachelhit", "tarifit"):
        continue
    for forma, n in formes.items():
        c[forma][v] += n
        eps[forma][v].add(cap)
        tot[v] += n
sh, rf = set(), set()
for forma, d in c.items():
    if d["tachelhit"] + d["tarifit"] < MIN_TOTAL:
        continue
    pm_sh = 1000 * d["tachelhit"] / max(1, tot["tachelhit"])
    pm_rf = 1000 * d["tarifit"] / max(1, tot["tarifit"])
    if pm_sh > pm_rf and len(eps[forma]["tachelhit"]) >= MIN_EPISODIS:
        sh.add(forma)
    elif pm_rf > pm_sh and len(eps[forma]["tarifit"]) >= MIN_EPISODIS:
        rf.add(forma)
print(f"lexic del SNRT: {len(sh)} esquelets del tachelhit · {len(rf)} del tarifit\n")

#: --- la biblioteca, que no hi ha participat gens ---
grups = defaultdict(lambda: defaultdict(int))
etiquetes = defaultdict(lambda: defaultdict(int))
for l in io.open(MANIFEST, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    v = (x.get("variety") or "(sense)").strip()
    for w in (x.get("text") or "").lower().split():
        w = esquelet(w.strip(".,;:!?«»\"'()[]"))
        if len(w) >= 3:
            grups[v][w] += 1
    for t in str(x.get("tag") or "").split(","):
        t = t.strip()
        if t:
            etiquetes[t][v] += 1

print(f"{'varietat':<12}{'paraules':>10}{'del lexic':>11}{'sh/1000':>9}{'rf/1000':>9}{'diu':>12}")
for v, formes in sorted(grups.items(), key=lambda kv: -sum(kv[1].values())):
    n = sum(formes.values())
    if n < 300:
        continue
    n_sh = sum(k for f, k in formes.items() if f in sh)
    n_rf = sum(k for f, k in formes.items() if f in rf)
    diu = ("tachelhit" if n_sh > 1.6 * n_rf else
           "tarifit" if n_rf > 1.6 * n_sh else "al mig")
    print(f"{v:<12}{n:10d}{n_sh + n_rf:11d}{1000*n_sh/n:9.1f}{1000*n_rf/n:9.1f}{diu:>12}")

print("\nper comparar, els episodis del SNRT (d'on surt el lexic):")
print("   tachelhit      89-192/1000 de sh · 16-38 de rf")
print("   Atles central  61-106/1000 de sh · 28-37 de rf")
print("   tarifit         8-60/1000 de sh · 42-75 de rf")
