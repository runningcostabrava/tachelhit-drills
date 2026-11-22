"""El corpus per afinar el traductor tifinag -> arab, partit per CAPITOLS.

En Pablo: «si el model es capac de traduir perfectament del tifinag a l'arab, despres la
traduccio de l'arab al catala es trivial». Te rao i les dades hi son: cada replica porta el
tifinag i l'arab **cremats al mateix fotograma**, de manera que l'alineacio es exacta i no
costa res.

**Es parteix per capitols, no per linies.** Dues linies del mateix capitol comparteixen tema,
convidat i vocabulari; partir per linies posaria el mateix convidat als dos costats i el
resultat sortiria millor del que es. Es el mateix error que vam trobar a la regla del cercle.

Portes (les de la fabrica): no credits, tifinag amb confianca >= 0,85 i <= 2 glifs dubtosos,
les dues linies presents. I es treuen els **duplicats exactes** de tifinag: a les entrevistes
es repeteixen formules («gracies», «si us plau») i inflarien el test.

Surten tres fitxers jsonl amb {zgh, ar, capitol} per a Kaggle.

    corpus_tifinag_arab.py [capitols_de_test] [capitols_de_dev]
"""
import io
import json
import os
import random
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
FORA = Path(r"E:/tamazight/_magatzem/zgh_ar")
N_TEST = int(sys.argv[1]) if len(sys.argv) > 1 else 4
N_DEV = int(sys.argv[2]) if len(sys.argv) > 2 else 2


def net(t):
    return unicodedata.normalize("NFC", (t or "").strip())



#: --- FORA EL RIF -------------------------------------------------------------------------
#: En Pablo: «no volem coses en tarifit perque es una altra llengua». El classificador pel
#: lexic deia «tachelhit» als 27 capitols, pero no es de fiar: el lexic diferencial te 117
#: marques tachelhit contra 39 tarifit, i el subtitol esta normalitzat per l'IRCAM, que es on
#: les marques dialectals s'esborren.
#:
#: El senyal bo son els **toponims a l'arab**, que no passen per cap d'aquests dos filtres:
#: `-SyzF2LtAEs` diu Tafersit 26 vegades, `hiKMeMfsIxw` diu Rif 30, `XSQcExn0e08` 27. I els
#: dos senyals es confirmen: els cinc capitols amb menys puntuacio tachelhit son cinc dels sis
#: del Rif.
#:
#: Sense aixo, el dev era **100 % tarifit** i el test el 53 %.
import json as _json
_don = _json.load(io.open(r"E:/tamazight/_magatzem/don_son_els_nous.json", encoding="utf-8"))
RIF = {k for k, v in _don.items() if v.get("diu") == "rif"}
print(f"fora {len(RIF)} capitols del Rif: {sorted(RIF)}")

per_cap = defaultdict(list)
fora_porta = defaultdict(int)
for d in sorted(os.listdir(ARREL)):
    p = ARREL / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0 or d in RIF:
        continue
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        zgh, ar = net(x.get("tifinag")), net(x.get("arab"))
        if x.get("credits"):
            fora_porta["crèdits"] += 1
        elif not zgh or not ar:
            fora_porta["falta una banda"] += 1
        elif (x.get("tifinag_conf") or 0) < 0.85:
            fora_porta["confiança < 0,85"] += 1
        elif (x.get("tifinag_dubtosos") or 0) > 2:
            fora_porta["glifs dubtosos > 2"] += 1
        elif len(zgh.split()) < 2 or len(ar.split()) < 2:
            fora_porta["massa curta"] += 1
        else:
            per_cap[d].append({"zgh": zgh, "ar": ar, "capitol": d})

print(f"{sum(len(v) for v in per_cap.values())} parelles de {len(per_cap)} capítols")
for k, v in sorted(fora_porta.items(), key=lambda kv: -kv[1]):
    print(f"   fora per {k}: {v}")

#: els capitols de test i dev: els mitjans, no els mes grans ni els mes petits, perque el test
#: no sigui ni el cas facil ni el raro
ordre = sorted(per_cap, key=lambda d: len(per_cap[d]))
mitjans = ordre[len(ordre) // 4: 3 * len(ordre) // 4]
rnd = random.Random(20261121)
rnd.shuffle(mitjans)
test = set(mitjans[:N_TEST])
dev = set(mitjans[N_TEST:N_TEST + N_DEV])
train = [d for d in per_cap if d not in test and d not in dev]

#: fora els duplicats exactes de tifinag, i cap text del test pot ser al train
vist = set()
parts = {}
for nom, caps in (("test", test), ("dev", dev), ("train", train)):
    files, repes = [], 0
    for d in caps:
        for x in per_cap[d]:
            k = x["zgh"].lower()
            if k in vist:
                repes += 1
                continue
            vist.add(k)
            files.append(x)
    parts[nom] = files
    print(f"{nom}: {len(files)} parelles de {len(caps)} capítols ({repes} duplicats fora)")

FORA.mkdir(parents=True, exist_ok=True)
for nom, files in parts.items():
    with io.open(FORA / f"{nom}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for x in files:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

#: comprovacio que no s'ha colat res: cap text del test al train
t = {x["zgh"].lower() for x in parts["test"]}
r = {x["zgh"].lower() for x in parts["train"]}
print(f"\ntextos del test que també són al train: {len(t & r)}")
print(f"capítols: test {sorted(test)}")
print(f"           dev {sorted(dev)}")
print(f"\nescrit a {FORA}")
