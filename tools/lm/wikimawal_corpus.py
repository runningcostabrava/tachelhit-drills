# -*- coding: utf-8 -*-
"""El text amazic del Viccionari zgh (definicions i exemples, CC BY-SA) com a corpus per al model
de llengua del lector: en llatí (transliterador nostre) i en l'alfabet del model MMS `shi`, una
frase per línia, afegit al corpus de la biblioteca. És la primera font de text LLIURE en amazic
estàndard que tenim; cap frase dels vídeos de prova no hi és per construcció.

ÚS: wikimawal_corpus.py <wikimawal.json> <sortida.txt>
"""
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import transliteration as T   # noqa: E402

CAP_AL_MODEL = (("c", "š"), ("x", "ḫ"), ("ɣ", "ġ"), ("ɛ", "ε"), ("ṛ", "r"), ("ʷ", "w"), ("°", "w"), ("ǝ", "e"))
ALFABET = set("abcdefghijklmnopqrstuvwyz") | set("šḫġεḍḥṣṭẓž")


def llati(tif):
    try:
        return (T.to_forms(tif) or {}).get("clean_latin") or ""
    except Exception:
        return ""


def al_model(s):
    s = s.lower()
    for a, b in CAP_AL_MODEL:
        s = s.replace(a, b)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\d+", " ", s)
    return " ".join(s.split())


if __name__ == "__main__":
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    frases, vist, fora = 0, set(), []
    for e in d["entrades"]:
        textos = list(e.get("definicions") or [])
        for t in textos:
            for frase in re.split(r"[.!?؟]\s*", t):
                frase = frase.strip()
                if not re.search(r"[ⴰ-⵿]", frase) or len(frase.split()) < 2:
                    continue
                lat = al_model(llati(frase))
                if not lat or any(ch not in ALFABET and ch != " " for ch in lat) or lat in vist:
                    continue
                vist.add(lat)
                fora.append(lat)
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write("\n".join(fora) + "\n")
    print(f"{len(fora)} frases · {sum(len(f.split()) for f in fora)} tokens → {sys.argv[2]}")
    print("  ex:", fora[:3])
