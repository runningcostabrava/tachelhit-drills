"""Quines formes son la MATEIXA paraula dita de maneres diferents.

Fa una estona vaig provar d'aparellar variants per semblanca de lletres (distancia d'un canvi
sobre l'esquelet) i va sortir que `nns` es variant d'`insi` («erico») i `tizi` d'`adz`. En
paraules de tres consonants, una distancia d'un canvi aparella qualsevol cosa amb qualsevol
cosa: es el mateix artefacte de les frases curtes del test-fora.

La manera bona es **per evidencia**, i es la mateixa idea que va obrir tot el projecte: dues
formes son variants si **s'alineen repetidament amb la MATEIXA paraula escrita**. No ho decideix
una semblanca, ho decideix que l'ull hi hagi posat el mateix signe moltes vegades.

Es demana, per a cada parella:

  * que totes dues s'alinein amb la mateixa `norma` almenys TRES vegades;
  * i que l'alineament sigui bo (CER d'esquelet <= 0,5): si l'ull i l'orella no s'assemblen gens,
    l'aparellament no vol dir res.

De cada parella es diu **qui la diu**: les boques i les varietats de cada forma. Aixo es el que
converteix una taula de variants en un mapa de com es diu una cosa segons d'on ets.

Surt `taula_variants.tsv`.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MIN_COPS, MAX_DIST = 3, .5

var_cap = {r["capitol"][:16]: r["varietat"]
           for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

#: norma escrita -> forma sentida -> {cops, capitols, varietats}
per_norma = defaultdict(lambda: defaultdict(lambda: {"cops": 0, "caps": set(), "vars": set()}))
for l in io.open(MAG / "ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    norma, forma, dist = x.get("norma"), (x.get("sentit") or "").strip(), x.get("dist")
    if not norma or not forma or dist is None or float(dist) > MAX_DIST:
        continue
    if len(esquelet(forma)) < 2:
        continue
    d = per_norma[norma][forma]
    d["cops"] += 1
    d["caps"].add((x.get("capitol") or "")[:16])
    d["vars"].add(var_cap.get((x.get("capitol") or "")[:16], "?"))

def prop(a, b):
    """Distancia relativa entre dos esquelets: 0 = iguals, 1 = res en comu."""
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


grups = []
for norma, formes in per_norma.items():
    bones = {f: d for f, d in formes.items() if d["cops"] >= MIN_COPS}
    if len(bones) >= 2:
        grups.append((norma, bones))
grups.sort(key=lambda g: -sum(d["cops"] for d in g[1].values()))
print(f"{len(per_norma)} paraules escrites · {len(grups)} amb dues formes o més\n")

print(f"{'escrit':<16}{'formes que hi diem (cops · boques · varietats)'}")
for norma, bones in grups[:18]:
    trossos = []
    for f, d in sorted(bones.items(), key=lambda kv: -kv[1]["cops"]):
        vs = ",".join(sorted(v[:3] for v in d["vars"] if v != "?"))
        trossos.append(f"{f} ({d['cops']}·{len(d['caps'])}·{vs})")
    print(f"{norma:<16}{'   '.join(trossos)[:98]}")

camps = ["escrit", "forma", "cops", "capitols", "varietats", "altres_formes"]
with io.open(MAG / "taula_variants.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("\t".join(camps) + "\n")
    for norma, bones in grups:
        noms = sorted(bones, key=lambda x: -bones[x]["cops"])
        for forma in noms:
            d = bones[forma]
            #: La germanor NO es transitiva. El filtre de dalt demana que cada forma sigui a
            #: MAX_DIST **de la norma escrita**, pero dues formes que hi son totes dues poden
            #: estar lluny entre elles: a la taula hi havia `yan`~`ns` i `igan`~`ns` a distancia
            #: 1,0, i `nns`~`nk` a 0,67 -- que es la parella `nnk`/`nns` de l'avis de la
            #: capcalera. Una germana ho es si s'assembla a AQUESTA forma, no a la norma.
            germanes = [x for x in noms
                        if x != forma and prop(esquelet(forma), esquelet(x)) <= MAX_DIST]
            if not germanes:
                continue        #: sola al seu grup: no es cap variant de res
            f.write("\t".join([norma, forma, str(d["cops"]), str(len(d["caps"])),
                               ",".join(sorted(v for v in d["vars"] if v != "?")),
                               ",".join(germanes)]) + "\n")
print(f"\nescrit taula_variants.tsv ({sum(len(b) for _, b in grups)} files)")
print("\nAixò no diu quina forma és «correcta»: diu qui diu cada una. Decidir-ho no és nostre.")
