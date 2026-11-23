"""L'arab reduit al que el fa «la mateixa frase», per tancar fuites entre entrenament i test.

**Per que es un modul.** El fan servir `corpus_veu_arab_combinat.py` i
`corpus_veu_arab_amb_baba.py`, i ha de ser la mateixa funcio als dos: si cada un en porta una
copia, se separen i una frase del test pot tornar a entrar a l'entrenament amb una altra
grafia. Abans `corpus_veu_arab_amb_baba.py` la importava de l'altre guio, i importar-lo
l'executava sencer (el 23-11 va refer els manifests de la primera tirada; van sortir identics
perque no hi ha atzar, pero no ha de passar).
"""
import re
import unicodedata


def norma(t):
    """Sense vocals ni tatweel, totes les alef iguals, ى=ي i ة=ه, i sense puntuacio."""
    t = unicodedata.normalize("NFKC", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("ـ", "")
    t = re.sub("[أإآٱ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"[^؀-ۿ\s]", " ", t)
    t = re.sub(r"[،؛؟۔]", " ", t)
    return " ".join(t.split())
