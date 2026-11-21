"""El ġ~ḫ es de la parla o es una confusio de la nostra orella?

Es el canvi mes gros de la taula de variacio (pes 25) i tambe el mes sospitos: la nostra
transliteracio porta ɣ->ġ i x->ḫ, que son dues fricatives veines, i una confusio sistematica de
l'adaptador `shi` el produiria igual que la produiria un convidat.

Es decideix amb una SEGONA ORELLA. Sobre els mateixos talls:

  - si el `kab` tambe sent ḫ alla on la pantalla escriu ⵖ amb la mateixa proporcio, el so diu
    ḫ i la variacio es de la parla;
  - si el `kab` hi sent ġ gairebe sempre, el ḫ era una confusio del `shi` i la parella ha de
    sortir de la taula.

Es compten nomes les paraules que CASEN (distancia <= 0,35), perque en les que no casen no se
sap de quina paraula parla cadascu. Es mira l'esquelet: si l'escrit porta ġ, que porta el sentit
al seu lloc.

    segona_orella_gh.py [carpeta_de_sortida]
"""
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_magatzem/prova_kab/sortida")
#: la parella a examinar: la lletra que la pantalla escriu i l'altra que l'orella hi posa
ESCRITA, ALTRA = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("ġ", "ḫ")


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


ull = {}
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        ull[x["id"]] = x.get("tifinag") or ""

fitxers = sorted(SORTIDA.glob("sentit_*.jsonl"))
if not fitxers:
    raise SystemExit(f"encara no hi ha sortida a {SORTIDA}")

for p in fitxers:
    lang = p.stem.split("_", 1)[1]
    c = Counter()
    exemples = []
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        paraules = [w["p"] for w in (x.get("paraules") or [])]
        escrites = [w for w in (ull.get(x["id"]) or "").split() if w.strip()]
        if not paraules or not escrites:
            continue
        for i, j in alinea(paraules, escrites):
            if j is None:
                continue
            eo, ee = esquelet(paraules[i]), esquelet(escrites[j])
            if not eo or not ee or prop(eo, ee) > .35:
                continue
            #: nomes les paraules on l'escrit porta la lletra que s'examina
            if ESCRITA not in ee:
                continue
            c["paraules amb la lletra"] += 1
            if ESCRITA in eo:
                c["l'orella hi diu " + ESCRITA] += 1
            elif ALTRA in eo:
                c["l'orella hi diu " + ALTRA] += 1
                if len(exemples) < 4:
                    exemples.append((escrites[j], paraules[i]))
            else:
                c["ni l'un ni l'altre"] += 1
    n = c["paraules amb la lletra"]
    print(f"\n=== orella `{lang}`: {n} paraules que casen i porten "
          f"{ESCRITA} a la pantalla")
    if not n:
        continue
    for k in ("l'orella hi diu " + ESCRITA, "l'orella hi diu " + ALTRA,
              "ni l'un ni l'altre"):
        print(f"   {k:<24}{c[k]:6d}  {100*c[k]/n:5.1f}%")
    if exemples:
        print(f"   exemples amb {ALTRA}: " + ", ".join(f"{a} -> {b}" for a, b in exemples))
