# -*- coding: utf-8 -*-
"""El text amazic de la biblioteca, una frase per línia, en l'alfabet del model MMS `shi`,
per entrenar-hi el model de llengua de l'H3.

Font: /corpus/export de producció (12.202 drills, 7.461 amb text_tachelhit). El text d'un
parlant és sagrat i aquí només es LLEGEIX. El tifinag passa pel transliterador del backend
(`to_forms` → clean_latin), el llatí es porta a l'alfabet del model com fa exporta_unigrams.py
(c→š, x→ḫ, ɣ→ġ, ɛ→ε, ṛ→r, ʷ→w), i es llença tota frase amb lletres que el model no sap escriure.

Cap frase dels 8 vídeos de prova (subtítols humans de Tamazight For All) no hi entra: es
comprova pel source_url.

ÚS:  fes_corpus_lm.py <corpus_export.json> <corpus_shi.txt>
"""
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import transliteration as T          # noqa: E402

PROVA = {"4Y4FcUHUeU4", "8DfuBnaijUg", "9TdhtZkmUTo", "TJFWJ5FKQg8", "lDbAAcdoVgQ",
         "o21uxEQoczE", "oFVo66DStDc", "tR-hRjd9O-k", "X7_kAT8_J64"}
CAP_AL_MODEL = (("c", "š"), ("x", "ḫ"), ("ɣ", "ġ"), ("ɛ", "ε"), ("ṛ", "r"), ("ʷ", "w"), ("°", "w"))
ALFABET = set("abcdefghijklmnopqrstuvwyz") | set("šḫġεḍḥṣṭẓž")
TIF = re.compile(r"[\u2d30-\u2d7f]")


def al_model(s):
    s = s.lower()
    for a, b in CAP_AL_MODEL:
        s = s.replace(a, b)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\d+", " ", s)
    return " ".join(s.split())


#: Alguns drills porten català al camp amazic («Necesito que vinguis ara mateix»). Una frase
#: cau si més de la meitat dels seus mots són de la llista catalana del corpus i cap no és del
#: lèxic amazic.
CATALA = set(l.strip().lower() for l in io.open(
    os.path.join(ARREL, "backend", "data", "catala_mots.txt"), encoding="utf-8") if l.strip())


def sembla_catala(t, lexic):
    mots = t.split()
    cat = sum(1 for m in mots if m in CATALA and m not in lexic)
    return mots and cat * 2 > len(mots)


if __name__ == "__main__":
    lexic = set(l.strip() for l in io.open(sys.argv[3], encoding="utf-8") if l.strip()) if len(sys.argv) > 3 else set()
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    rows = d if isinstance(d, list) else (d.get("drills") or d.get("rows") or list(d.values())[0])
    vistes, fora, llençades, de_prova = set(), [], 0, 0
    for r in rows:
        if any(v in (r.get("source_url") or "") + (r.get("video_url") or "") for v in PROVA):
            de_prova += 1
            continue
        t = (r.get("text_tachelhit") or "").strip()
        if not t:
            continue
        if TIF.search(t):
            lat = (r.get("text_tachelhit_latin") or "").strip()
            if not lat:
                try:
                    lat = (T.to_forms(t) or {}).get("clean_latin") or ""
                except Exception:
                    lat = ""
            t = lat
        t = al_model(t)
        if not t or any(ch not in ALFABET and ch != " " for ch in t) or sembla_catala(t, lexic):
            llençades += 1
            continue
        if t in vistes:
            continue
        vistes.add(t)
        fora.append(t)
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write("\n".join(fora) + "\n")
    print(f"{len(fora)} frases úniques · {sum(len(f.split()) for f in fora)} tokens · "
          f"llençades {llençades} · de la prova {de_prova}")
