"""Quin dels models de llengua es millor, mesurat sense model acustic.

Afegir text a un model de llengua el fa mes gran, no necessariament millor: el subtitol del SNRT
es una **traduccio normalitzada per l'IRCAM**, i pot empenyer la sortida cap a una llengua que
ningu no parla. Aixo es pot decidir **abans** de gastar GPU, amb la **perplexitat** sobre text
que cap dels dos models no ha vist.

El text de prova son els **quatre capitols retinguts**, que estan fora dels dos corpus per
construccio (`corpus_pel_model_de_llengua.py` els treu). Perplexitat baixa = el model troba
normal el que hi diu.

I es mira tambe la **cobertura**: quantes paraules del text retingut son al vocabulari. Un model
que no coneix les paraules no les pot proposar al feix, per bona que sigui la seva perplexitat
sobre les que si que coneix.

    quin_model_de_llengua_val.py
"""
import io
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/arpa/tools/lm")
import arpa_lm                                   # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SORTIDES = MAG / "ronda/sortida/snrt_B_sortides.json"
CANVI = {"c": "š", "x": "ḫ", "ɣ": "ġ", "ɛ": "ε", "ṛ": "r", "ʷ": "w"}
LLETRES = set("abdḍefgġhḥijklmnqrstṭuvwyzẓšεḫ ")


def _taula():
    t = io.open(MAG / "acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    d = {}
    exec(t[i:t.index("}", i) + 1], {}, d)
    return d["TIF"]


TIF = _taula()


def del_tifinag(t):
    fora = []
    for c in (t or ""):
        if c in TIF:
            fora.append(TIF[c])
        elif unicodedata.name(c, "").startswith("TIFINAGH"):
            fora.append("")
        else:
            fora.append(c)
    return "".join(fora)


def a_l_alfabet(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = "".join(CANVI.get(c, c) for c in t)
    t = re.sub(r"\s+", " ", t).strip()
    return t if t and all(c in LLETRES for c in t) else ""


#: el text retingut: la veritat de l'ull als quatre capitols que el cercle reté
retingut = []
for x in json.load(io.open(SORTIDES, encoding="utf-8")):
    if x.get("prova") != "snrt-retingut" or (x.get("model") or "").startswith("abans"):
        continue
    f = a_l_alfabet(x.get("or"))
    if f:
        retingut.append(f)
print(f"{len(retingut)} frases retingudes · "
      f"{sum(len(f.split()) for f in retingut)} paraules\n")

print(f"{'model':<26}{'unigr.':>8}{'bigr.':>8}{'perplexitat':>13}{'cobertura':>11}")
for nom in ("corpus_biblioteca", "corpus_biblioteca_snrt"):
    cami = MAG / "arpa" / nom / "corpus_bi.arpa"
    if not cami.exists():
        continue
    m = arpa_lm.Model(str(cami))
    logp = n = coneguts = total = 0.0
    for f in retingut:
        mots = f.split()
        if not mots:
            continue
        logp += m.score(f, bos=True, eos=True)
        n += len(mots) + 1                 #: + el final de frase
        total += len(mots)
        coneguts += sum(1 for w in mots if w in m)
    pp = 10 ** (-logp / max(1, n))
    print(f"{nom:<26}{len(m):>8}{len(m._bi):>8}{pp:>13.1f}{100*coneguts/max(1,total):>10.1f}%")

print("\nPerplexitat baixa = el model troba normal el que diu el text que no ha vist.")
print("La cobertura és el sostre: una paraula que no és al vocabulari no la pot proposar.")
