# -*- coding: utf-8 -*-
"""El lèxic que l'autor del canal publica al seu web (tamazightforall.com), contra el nostre.

Font forta: és l'autor mateix qui dóna el terme en tifinag amb la seva traducció a l'anglès, el
castellà i l'àrab (termes lingüístics), o la llista de mots de funció, pronoms i preposicions, o
les taules dels cursos (tifinag + llatí + traducció). És l'«autoglossa» del 15-11 però escrita.

Per a cada forma: el llatí (de la taula si n'hi ha, o transliterant el tifinag amb el nostre
transliterador), el que el nostre `glossa()` en diu, i la caixa:
  coincideix   alguna paraula de la traducció de l'autor és a la nostra glossa (anglès/àrab/castellà)
  contradiu    tenim glossa i cap paraula no hi casa
  no la tenim  glossa() no en diu res
ÚS: web_vs_lexic.py <dades.json> <sortida.md>
"""
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import lexicon            # noqa: E402
import morfologia         # noqa: E402
import transliteration as T   # noqa: E402

CAT_EN = {"llengua": "language", "paraula": "word", "nom": "noun", "verb": "verb", "arrel": "root",
          "frase": "sentence", "lletra": "letter", "so": "sound", "traducció": "translation",
          "lèxic": "lexicon", "diccionari": "dictionary", "jo": "i", "tu": "you", "ell": "he",
          "ella": "she", "nosaltres": "we", "vosaltres": "you", "ells": "they", "i": "and",
          "de": "of", "a": "to", "en": "in", "amb": "with", "sobre": "on", "sota": "under",
          "no": "not", "què": "what", "qui": "who", "on": "where", "quan": "when", "com": "how",
          "però": "but", "perquè": "because", "si": "if", "o": "or", "tot": "all", "molt": "very",
          "aquí": "here", "allà": "there", "ara": "now", "també": "also", "només": "only",
          "mare": "mother", "pare": "father", "germà": "brother", "germana": "sister", "casa": "house",
          "aigua": "water", "pa": "bread", "sol": "sun", "nit": "night", "dia": "day"}
TASHKIL = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")


def llati(tif):
    try:
        return (T.to_forms(tif) or {}).get("clean_latin") or ""
    except Exception:
        return ""


def arrel(w):
    return re.sub(r"(ies|es|s|ed|ing|ly|ción|ción|os|as)$", "", w.lower())[:5]


def mots(s):
    return [w for w in re.findall(r"[a-zà-ÿ]+", (s or "").lower()) if len(w) > 2]


def arabitza(w):
    w = TASHKIL.sub("", w)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        w = w.replace(a, b)
    for p in ("وال", "بال", "ال", "و", "ب", "ل"):
        if w.startswith(p) and len(w) - len(p) >= 3:
            w = w[len(p):]
            break
    return w


def glosses_nostres(forma, sig, ev, en):
    """(text de la glossa, com, paraules en/fr/ca, paraules àrabs)"""
    g = morfologia.glossa(forma, sig, ev, en)
    paraules, arabs = set(), set()
    if g:
        paraules.update(mots(g[0]))
        for c, e in CAT_EN.items():
            if re.search(r"\b" + re.escape(c) + r"\b", g[0].lower()):
                paraules.add(e)
    for r in lexicon.lookup(forma) or []:
        for d in r.get("dictionary") or []:
            for e in (d.get("english") or []) + [d.get("french") or ""]:
                paraules.update(mots(e))
        for c in (r.get("ircam") or []) + (r.get("conjugation") or []):
            paraules.update(mots(c.get("french") or ""))
            arabs.update(arabitza(x) for x in re.findall(r"[\u0600-\u06ff]+", c.get("arabic") or ""))
    return g, paraules, arabs


def caixa(autor_en, autor_es, autor_ar, g, paraules, arabs):
    if not (autor_en or autor_es or autor_ar):
        return "sense traducció de l'autor" if (g or paraules) else "no la tenim"
    if not g and not paraules:
        return "no la tenim"
    seus = set(mots(autor_en)) | set(mots(autor_es))
    if any(arrel(a) == arrel(p) for a in seus for p in paraules if len(p) > 2):
        return "coincideix"
    seus_ar = {arabitza(x) for x in re.findall(r"[\u0600-\u06ff]+", autor_ar or "")}
    if any(a[:3] == p[:3] for a in seus_ar for p in arabs if len(a) >= 3 and len(p) >= 3):
        return "coincideix"
    return "contradiu"


if __name__ == "__main__":
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    files = []
    for t in d.get("linguisticTerms", []):
        tif = t.get("amazigh") or ""
        files.append(("terme lingüístic", tif, llati(tif), t.get("english", ""), t.get("spanish", ""), t.get("arabic", "")))
    for nom, llista in (("mot de funció", d.get("amazighLexicon", [])), ("preposició", d.get("prepositions", [])),
                        ("pronom", d.get("pronouns", []))):
        for x in llista:
            tif = x if isinstance(x, str) else (x.get("amazigh") or x.get("tifinagh") or x.get("text") or "")
            tr = "" if isinstance(x, str) else " ".join(str(v) for k, v in x.items() if k not in ("amazigh", "tifinagh", "text"))
            files.append((nom, tif, llati(tif), tr, "", tr))
    for taula in d.get("__taules_amb_tifinag", []):
        cap = taula[0]
        for f in taula[1:]:
            tifs = [c for c in f if re.search(r"[\u2d30-\u2d7f]", c)]
            lats = [c for c in f if re.fullmatch(r"[A-Za-zɣɛḍṭẓṣṛḥčğ'’\- !?.,]+", c or "") and not re.search(r"[\u2d30-\u2d7f\u0600-\u06ff]", c)]
            trads = [c for c in f if re.search(r"[\u0600-\u06ff]", c) and not re.search(r"[\u2d30-\u2d7f]", c)]
            if tifs and len(tifs[0].split()) <= 2:        # vocabulari: una o dues paraules
                files.append(("curs (vocabulari)", tifs[0], (lats[0] if lats else llati(tifs[0])).strip(" !?.,").lower(),
                              "", "", " ".join(trads)))
    vist, fora = set(), []
    for mena, tif, lat, a_en, a_es, a_ar in files:
        lat = re.sub(r"[^a-zɣɛḍṭẓṣṛḥ ]", "", lat.lower()).strip()
        if not lat or lat in vist:
            continue
        vist.add(lat)
        forma = lat.split()[0] if " " in lat else lat
        g, paraules, arabs = glosses_nostres(forma, sig, ev, en)
        fora.append((caixa(a_en, a_es, a_ar, g, paraules, arabs), mena, tif, lat, a_en or a_es, a_ar, (g[0][:60] + f" [{g[1]}]") if g else "—"))
    ordre = {"contradiu": 0, "no la tenim": 1, "coincideix": 2, "sense traducció de l'autor": 3}
    fora.sort(key=lambda x: (ordre[x[0]], x[1]))
    import collections
    print(collections.Counter(x[0] for x in fora))
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write("# El lèxic del web de l'autor contra el nostre (15-11-2026)\n\n")
        g.write("| caixa | mena | tifinag | llatí | l'autor diu (en/es) | l'autor diu (ar) | nosaltres diem |\n|---|---|---|---|---|---|---|\n")
        for x in fora:
            g.write("| " + " | ".join(str(c).replace("|", "/") for c in x) + " |\n")
    for x in fora[:40]:
        print(f"  {x[0]:12} {x[1]:18} {x[3]:16} {x[4][:22]:22} | {x[6][:50]}")
