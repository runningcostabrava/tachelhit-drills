# -*- coding: utf-8 -*-
"""El que amazic.cat diu de cada forma (lemes catalans on surt) contra el que diem nosaltres.
Com que amazic.cat parla CATALÀ, la comparació és directa: coincideix si alguna paraula del lema
(o del seu context) comparteix arrel amb la nostra glossa catalana; «no hi és» si el diccionari no
té la forma; «a revisar» si la té i cap paraula no casa (sovint perquè la nostra glossa és en
francès/anglès del diccionari general: aleshores és una glossa en català que ens falta).

ÚS: amazic_cat_vs_lexic.py <consultes.jsonl> <sortida.md>
"""
import collections
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import lexicon      # noqa: E402
import morfologia   # noqa: E402

STOP = set("de la el les els un una uns unes que és són amb per a al del dels en i o no sí d l s esser ésser".split())
FR_CA = {"eau": "aigua", "maison": "casa", "montagne": "muntanya", "homme": "home", "femme": "dona", "langue": "llengua",
         "mot": "paraula", "parole": "paraula", "terre": "terra", "pays": "país", "feu": "foc", "soleil": "sol", "nuit": "nit",
         "jour": "dia", "mer": "mar", "chien": "gos", "cheval": "cavall", "pain": "pa", "lait": "llet", "main": "mà",
         "tête": "cap", "oeil": "ull", "ship": "vaixell", "boat": "vaixell", "house": "casa", "water": "aigua",
         "mountain": "muntanya", "man": "home", "woman": "dona", "language": "llengua", "word": "paraula", "land": "terra",
         "country": "país", "fire": "foc", "sun": "sol", "night": "nit", "day": "dia", "sea": "mar", "dog": "gos",
         "horse": "cavall", "bread": "pa", "milk": "llet", "hand": "mà", "head": "cap", "eye": "ull", "king": "rei",
         "roi": "rei", "chef": "cap", "chief": "cap", "river": "riu", "rivière": "riu", "key": "clau", "clé": "clau",
         "goods": "béns", "biens": "béns", "die": "morir", "dead": "mort", "mourir": "morir", "go": "anar", "aller": "anar",
         "find": "trobar", "trouver": "trobar", "know": "saber", "savoir": "saber", "say": "dir", "dire": "dir",
         "see": "veure", "voir": "veure", "come": "venir", "venir": "venir", "eat": "menjar", "manger": "menjar",
         "small": "petit", "petit": "petit", "big": "gran", "grand": "gran", "all": "tot", "tout": "tot", "only": "només",
         "but": "però", "mais": "però", "because": "perquè", "where": "on", "who": "qui", "what": "què", "after": "després",
         "beyond": "més enllà", "above": "damunt", "under": "sota", "sous": "sota", "with": "amb", "avec": "amb"}


def arrel(w):
    return re.sub(r"(ment|ció|cions|es|s|ar|er|ir|at|ada|ats|ades|a)$", "", w.lower())[:5]


def mots(s):
    fora = []
    for w in re.findall(r"[a-zà-ÿ·]+", (s or "").lower()):
        if w in FR_CA:
            fora.append(FR_CA[w])
        if len(w) > 2 and w not in STOP:
            fora.append(w)
    return fora


if __name__ == "__main__":
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    files = []
    for l in io.open(sys.argv[1], encoding="utf-8"):
        d = json.loads(l)
        forma = d["forma"]
        lemes = d.get("lemes") or []
        g = morfologia.glossa(forma, sig, ev, en)
        nostres = set(mots(g[0])) if g else set()
        for r in lexicon.lookup(forma) or []:
            for dd in r.get("dictionary") or []:
                for e in (dd.get("english") or []) + [dd.get("french") or ""]:
                    nostres.update(mots(e))
        seus = set()
        for x in lemes:
            seus.update(mots(x["lema"].replace("-", " ")))
        if not lemes:
            caixa = "no hi és"
        elif any(arrel(a) == arrel(b) for a in seus for b in nostres if len(a) > 2 and len(b) > 2):
            caixa = "coincideix"
        elif not nostres:
            caixa = "nova (només amazic.cat)"
        else:
            caixa = "a revisar"
        files.append((caixa, forma, ", ".join(sorted({x["lema"] for x in lemes}))[:70], (g[0][:55] + f" [{g[1]}]") if g else "—",
                      (lemes[0]["context"][:90] if lemes else "")))
    ordre = {"a revisar": 0, "nova (només amazic.cat)": 1, "coincideix": 2, "no hi és": 3}
    files.sort(key=lambda x: ordre[x[0]])
    c = collections.Counter(x[0] for x in files)
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write(f"# amazic.cat contra el nostre lèxic ({len(files)} formes)\n\nCaixes: {dict(c)}\n\n")
        g.write("| caixa | forma | lemes d'amazic.cat | nosaltres | context |\n|---|---|---|---|---|\n")
        for x in files:
            g.write("| " + " | ".join(str(v).replace("|", "/") for v in x) + " |\n")
    print(dict(c))
    for x in files[:25]:
        print(f"  {x[0]:24} {x[1]:14} {x[2][:40]:40} | {x[3][:40]}")
