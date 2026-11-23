"""L'arab del TutlAit, es traduccio o es amazic escrit amb lletres arabs?

**Per que importa.** La via 3 (veu amazic -> arab escrit) nomes aprofita els parells on l'arab
diu el **significat**. Si l'arab es la **transliteracio** del que sona -- `أزول` per «azul» --,
aquell parell ensenya al model justament el vici que li volem treure: el Whisper sense afinar ja
fa aixo, i per aixo el seu punt de partida es chrF 0,1003.

El TutlAit es va recollir de dues maneres (segons el seu article): gent llegint en amazic una
frase arab, que dona una parella de traduccio, i gent escrivint amb lletres arabs el que sentia,
que no en dona. Abans d'ajuntar-lo amb el corpus de la SNRT cal saber quants n'hi ha de cada.

**Com es distingeix sense model.** Una frase arab de debo porta **paraules funcionals** arabs
--l'article, les preposicions, els demostratius, els relatius-- que una transliteracio de
l'amazic no pot portar, perque l'amazic no les te. Es compta la proporcio de frases que en
porten alguna.

**Amb un control, que si no no vol dir res.** El mateix calcul sobre l'arab dels subtitols de la
SNRT, que sabem que es arab escrit per persones, i sobre el tifinag transliterat a lletres
arabs si n'hi ha. El numero sol no diu res; el que diu alguna cosa es la distancia al control.

No toca res: llegeix i compta.

    python quin_arab_es_el_del_tutlait.py
"""
import io
import json
import re
import statistics as st
from pathlib import Path

TUT = Path(r"E:/tamazight/_paquets/tutlait/metadades.jsonl")
SNRT = Path(r"E:/tamazight/talls_ecs")

#: paraules funcionals de l'arab. Cap no es amazic, i l'amazic no te article definit ni
#: aquestes preposicions: si hi son, algu ha escrit arab.
FUNCIO = ["في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي",
          "لا", "ما", "أن", "إن", "كان", "قد", "كل", "بعد", "قبل", "عند", "لكن",
          "أو", "ثم", "حتى", "كما", "هل", "لم", "لن", "هو", "هي", "نحن", "انت"]
ART = re.compile(r"(^|\s)ال\S")        #: l'article definit enganxat a una paraula
ARAB = re.compile(r"[\u0600-\u06ff]")


def mira(t):
    t = (t or "").strip()
    if not t:
        return None
    mots = t.split()
    nf = sum(1 for m in mots if m.strip("،.؟!«»\"'") in FUNCIO)
    return {"mots": len(mots), "funcio": nf, "article": bool(ART.search(t)),
            "te_arab": bool(ARAB.search(t))}


def conta(nom, textos):
    v = [x for x in (mira(t) for t in textos) if x and x["te_arab"]]
    if not v:
        print(f"   {nom}: cap text arab")
        return
    amb = sum(1 for x in v if x["funcio"] or x["article"])
    print(f"   {nom:<34}{len(v):>7}{st.median(x['mots'] for x in v):>8.0f}"
          f"{100*amb/len(v):>13.0f} %{100*sum(1 for x in v if x['article'])/len(v):>12.0f} %")


print("L'arab del TutlAit contra l'arab de la SNRT\n")
print(f"   {'font':<34}{'frases':>7}{'mots':>8}{'amb funcional':>15}{'amb article':>14}")

#: TutlAit
camps, textos = {}, []
for l in io.open(TUT, encoding="utf-8"):
    if not l.strip():
        continue
    d = json.loads(l)
    for k in d:
        camps[k] = camps.get(k, 0) + 1
    for k in ("arabic", "text_arabic", "arab", "transcription", "text", "sentence"):
        if d.get(k):
            textos.append(d[k])
            break
conta("TutlAit", textos)

#: SNRT, el control: arab escrit per persones a la pantalla
snrt = []
for p in sorted(SNRT.glob("*/subtitols.jsonl"))[:6]:
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            if d.get("arab"):
                snrt.append(d["arab"])
conta("SNRT (control: arab de persones)", snrt)

print(f"\n   camps del TutlAit: {', '.join(sorted(camps))}")
print("\n   a prop del control = traduccio · molt per sota = transliteracio")
