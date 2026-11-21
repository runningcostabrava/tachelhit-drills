"""El text per al model de llengua del feix, **sense res que el test hagi de jutjar**.

L'H3 va fer el model de llengua amb 7.461 frases de la biblioteca i va donar WER 0,712 -> 0,640.
Ara en tenim mes: **10.878 repliques del SNRT** collides des d'aleshores. Pero afegir text a un
model de llengua que despres es mesura es la manera mes facil de mentir-se, i aqui hi ha dues
portes per on entra la trampa:

  1. **La biblioteca te particions.** Nomes `train` pot entrar: `test-dins`, `dev-dins`,
     `test-fora`, `dev-fora` i `fora-common-voice` son el que mesura.
  2. **Els capitols retinguts del SNRT.** Els quatre capitols de `snrt-retingut` son el test del
     cercle; si el model de llengua els llegeix, el test deixa de ser-ho. Es treuen llegint
     quins son de les propies sortides de la ronda, no d'una llista escrita a ma que es pot
     quedar vella.

I una decisio que **no** es meva i que deixo oberta amb dos fitxers: el subtitol del SNRT es una
**traduccio normalitzada per l'IRCAM**, no una transcripcio del que es diu. Posar-lo al model de
llengua pot arreglar les fronteres de paraula i alhora empenyer la sortida cap a una llengua que
ningu no parla. Per aixo es fan dos corpus i que els mesuri qui els mesuri:

    corpus_biblioteca.txt       nomes train de la biblioteca (com l'H3)
    corpus_biblioteca_snrt.txt  + les repliques del SNRT dels capitols NO retinguts

    corpus_pel_model_de_llengua.py
"""
import io
import json
import re
import unicodedata
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
BIBLIO = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
SORTIDES = MAG / "ronda/sortida/snrt_B_sortides.json"


def _taula_tifinag():
    t = io.open(MAG / "acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    j = t.index("}", i) + 1
    d = {}
    exec(t[i:j], {}, d)
    return d["TIF"]


TIF = _taula_tifinag()
#: a l'alfabet que el model sap escriure (com `exporta_unigrams.py`)
CANVI = {"c": "š", "x": "ḫ", "ɣ": "ġ", "ɛ": "ε", "ṛ": "r", "ʷ": "w"}
LLETRES = set("abdḍefgġhḥijklmnqrstṭuvwyzẓšεḫ ")


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
    #: tota frase amb una lletra que el model no sap escriure es llenca sencera
    return t if t and all(c in LLETRES for c in t) else ""


#: --- 1. la biblioteca, nomes train ---
biblio, fora_split = [], 0
for l in io.open(BIBLIO, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x.get("split") != "train":
        fora_split += 1
        continue
    #: la biblioteca te frases escrites en tifinag i altres en llati: les dues passen pel
    #: transliterador. Sense aixo se'n perdien 1.867 de 4.016, el 46 % del train.
    f = a_l_alfabet(del_tifinag(x.get("text")))
    if f:
        biblio.append(f)
print(f"biblioteca: {len(biblio)} frases · {fora_split} fora per no ser train")

#: --- 2. quins capitols reté el cercle, llegits de les sortides ---
retinguts = set()
for x in json.load(io.open(SORTIDES, encoding="utf-8")):
    if x.get("prova") == "snrt-retingut" and x.get("video"):
        retinguts.add(x["video"])
print(f"capítols retinguts del SNRT: {len(retinguts)} -> {sorted(retinguts)}")

#: --- 3. el SNRT, fora els retinguts ---
#:
#: De DUES fonts. `text_triat.jsonl` son els 25 capitols vells, els que ja han passat per tota
#: la canonada. Pero els episodis collits de nou **encara no hi son**: el seu `subtitols.jsonl`
#: te el tifinag i l'arab, i els falta la traduccio i l'orella. Per al model de llengua nomes
#: cal el tifinag, de manera que hi poden entrar ja, i son mes material que tot el vell junt.
import os                                                       # noqa: E402,PLC0415

TD_TV = Path(r"E:/tamazight/TD_TV")


def retingut(cap):
    return any(cap.startswith(r[:16]) or r.startswith(cap[:16]) for r in retinguts)


snrt, fora_ret, fora_alf, repetides = [], 0, 0, 0
vistes = set()
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if retingut(x.get("capitol") or ""):
        fora_ret += 1
        continue
    f = a_l_alfabet(del_tifinag(x.get("tifinag")))
    if f:
        snrt.append(f)
        vistes.add(f)
    else:
        fora_alf += 1
vells = len(snrt)

nous = 0
for d in sorted(os.listdir(TD_TV)) if TD_TV.exists() else []:
    p = TD_TV / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0 or retingut(d):
        if p.exists() and retingut(d):
            fora_ret += 1
        continue
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        y = json.loads(l)
        if y.get("credits"):          #: els credits del final no son llengua
            continue
        f = a_l_alfabet(del_tifinag(y.get("tifinag")))
        if not f:
            fora_alf += 1
        elif f in vistes:
            repetides += 1            #: el mateix episodi pot ser a les dues fonts
        else:
            snrt.append(f)
            vistes.add(f)
            nous += 1
print(f"SNRT: {len(snrt)} frases ({vells} del catàleg vell + {nous} dels episodis collits) · "
      f"{fora_ret} fora per capítol retingut · {repetides} repetides · "
      f"{fora_alf} fora per lletres que el model no escriu")

a = MAG / "corpus_biblioteca.txt"
b = MAG / "corpus_biblioteca_snrt.txt"
io.open(a, "w", encoding="utf-8", newline="\n").write("\n".join(biblio) + "\n")
io.open(b, "w", encoding="utf-8", newline="\n").write("\n".join(biblio + snrt) + "\n")
print(f"\nescrits:\n   {a.name}: {len(biblio)} frases, "
      f"{sum(len(f.split()) for f in biblio)} paraules")
print(f"   {b.name}: {len(biblio)+len(snrt)} frases, "
      f"{sum(len(f.split()) for f in biblio+snrt)} paraules")
vocab_a = {w for f in biblio for w in f.split()}
vocab_b = {w for f in biblio + snrt for w in f.split()}
print(f"\nformes diferents: {len(vocab_a)} -> {len(vocab_b)} "
      f"(+{100*(len(vocab_b)-len(vocab_a))/max(1,len(vocab_a)):.0f} %)")
