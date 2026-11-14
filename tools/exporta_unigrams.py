# -*- coding: utf-8 -*-
"""La llista de paraules que el descodificador del Space ha de preferir, en l'alfabet del model.

Per a `/transcribe_mms_lm` (#601, H3): el feix es decanta cap a cadenes que SÓN paraules. Les
paraules surten del lèxic que ja tenim —diccionari d'Oulhaj, IRCAM, formes conjugades, DGLAI— i
de les dues taules escrites a mà de `morfologia.py` (partícules i formes gramaticals), que són
justament les que el diccionari no té o té malament.

L'alfabet importa, i ja ens ha mossegat: el lèxic escriu `c`, `x`, `ɣ`, `ɛ`, `ṛ`; el model
escriu `š`, `ḫ`, `ġ`, `ε` i no té `ṛ`. Una paraula en l'alfabet equivocat no la trobaria mai
cap feix. Es converteix tot a l'alfabet del model i es llencen les formes amb lletres que el
model no pot escriure.

ÚS:  exporta_unigrams.py <sortida unigrams_shi.txt>
"""
import io
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.environ.setdefault("LEXICON_WARMUP", "0")

#: del lèxic a l'alfabet `shi` del MMS (mms_shi.py: «ɣ is ġ and ɛ is ε; ṛ is not in it»)
CAP_AL_MODEL = (("c", "š"), ("x", "ḫ"), ("ɣ", "ġ"), ("ɛ", "ε"), ("ṛ", "r"), ("ʷ", "w"))
#: el que el model sap escriure: lletres llatines bàsiques i aquestes
ALFABET = set("abcdefghijklmnopqrstuvwyz") | set("šḫġεḍḥṣṭẓž")


def al_model(forma: str) -> str:
    f = forma.lower().strip()
    for a, b in CAP_AL_MODEL:
        f = f.replace(a, b)
    return f


def val(f: str) -> bool:
    return 2 <= len(f) <= 24 and all(ch in ALFABET for ch in f)


def main(sortida: str) -> int:
    import lexicon
    import morfologia
    lexicon.load()
    formes = set()
    for nom in dir(lexicon):
        o = getattr(lexicon, nom)
        if isinstance(o, dict) and len(o) > 5000:
            for k in o:
                if isinstance(k, str):
                    formes.add(k)
    formes.update(morfologia.PARTICULES)
    formes.update(morfologia.FORMES_GRAMATICALS)
    fora = set()
    for f in formes:
        for tros in re.split(r"[\s\-]+", f):
            m = al_model(tros)
            if val(m):
                fora.add(m)
    with io.open(sortida, "w", encoding="utf-8") as g:
        for f in sorted(fora):
            g.write(f + "\n")
    print(f"{len(formes)} formes del lèxic i de les taules → {len(fora)} unigrams en l'alfabet "
          f"del model → {sortida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
