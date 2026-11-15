# -*- coding: utf-8 -*-
"""El Viccionari zgh (lliure) contra el nostre lèxic, en dues proves:

1. GLOSSES: per a cada entrada amb forma llatina i traducció (en/fr/ar), què en diu `glossa()`:
   coincideix (alguna paraula de la traducció casa amb la nostra glossa, per arrel), a revisar
   (tenim glossa i cap casa) o nova (el lèxic no la té: candidata LLIURE a entrar, amb atribució).
2. MORFOLOGIA: per a les entrades amb estat d'annexió (244), si la nostra regla `_sense_annexio`
   recupera la forma lliure a partir de l'annexada (ⵓⵔⴳⴰⵣ → ⴰⵔⴳⴰⵣ), i si el plural que dóna el
   Viccionari és al lèxic. És la primera mesura de la regla d'annexió contra dades que no són
   nostres.

ÚS: wikimawal_vs_lexic.py <wikimawal.json> <sortida.md>
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
import lexicon             # noqa: E402
import morfologia          # noqa: E402
import transliteration as T   # noqa: E402

CAT_EN_FR = {"llengua": ["language", "langue"], "paraula": ["word", "mot"], "casa": ["house", "maison"],
             "aigua": ["water", "eau"], "home": ["man", "homme"], "dona": ["woman", "femme"], "rei": ["king", "roi"],
             "cap": ["head", "tête", "chief", "chef"], "mà": ["hand", "main"], "ull": ["eye", "oeil", "œil"],
             "nit": ["night", "nuit"], "dia": ["day", "jour"], "sol": ["sun", "soleil"], "terra": ["land", "earth", "terre"],
             "foc": ["fire", "feu"], "pa": ["bread", "pain"], "llet": ["milk", "lait"], "gos": ["dog", "chien"],
             "riu": ["river", "rivière"], "muntanya": ["mountain", "montagne"], "país": ["country", "pays"],
             "mare": ["mother", "mère"], "pare": ["father", "père"], "germà": ["brother", "frère"], "fill": ["son", "fils"],
             "anar": ["go", "aller"], "venir": ["come", "venir"], "veure": ["see", "voir"], "saber": ["know", "savoir"],
             "dir": ["say", "dire"], "menjar": ["eat", "manger"], "beure": ["drink", "boire"], "morir": ["die", "mourir"],
             "petit": ["small", "petit"], "gran": ["big", "grand"], "tot": ["all", "tout"], "però": ["but", "mais"],
             "perquè": ["because", "parce"], "on": ["where", "où"], "qui": ["who", "qui"], "què": ["what", "quoi"]}


def arrel(w):
    return re.sub(r"(ies|es|s|ed|ing|ly|ment|e)$", "", w.lower())[:5]


def mots(s):
    fora = []
    for w in re.findall(r"[a-zà-ÿœ]+", (s or "").lower()):
        fora.append(w)
        fora.extend(CAT_EN_FR.get(w, []))
    return [w for w in fora if len(w) > 2]


def llati(tif):
    try:
        return (T.to_forms(tif) or {}).get("clean_latin") or ""
    except Exception:
        return ""


if __name__ == "__main__":
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    caixes = collections.Counter()
    files = []
    for e in d["entrades"]:
        lat = re.sub(r"[^a-zɣɛḍṭẓṣṛḥʷ ]", "", e["llati"].lower()).strip()
        tr = e.get("traduccions") or {}
        if not lat or " " in lat or not (tr.get("en") or tr.get("fr")):
            continue
        g = morfologia.glossa(lat, sig, ev, en)
        nostres = set(mots(g[0])) if g else set()
        for r in lexicon.lookup(lat) or []:
            for dd in r.get("dictionary") or []:
                for x in (dd.get("english") or []) + [dd.get("french") or ""]:
                    nostres.update(mots(x))
            for c in r.get("ircam") or []:
                nostres.update(mots(c.get("french") or ""))
        seus = set(mots(" ".join(tr.get("en", []) + tr.get("fr", []))))
        if not g and not nostres:
            caixa = "nova (lliure)"
        elif any(arrel(a) == arrel(b) for a in seus for b in nostres if len(a) > 2 and len(b) > 2):
            caixa = "coincideix"
        else:
            caixa = "a revisar"
        caixes[caixa] += 1
        files.append((caixa, lat, e["tifinag"], ", ".join((tr.get("en") or [])[:2] + (tr.get("fr") or [])[:2])[:50],
                      (g[0][:50] + f" [{g[1]}]") if g else "—", e.get("categoria") or ""))
    #: morfologia: annexió i plural
    morf = collections.Counter()
    exemples = []
    for e in d["entrades"]:
        m = e.get("morfologia") or {}
        lliure, annex, plural = e["tifinag"], m.get("ⴰⴷⴷⴰⴷ ⴰⵎⴰⵔⵓⵣ"), m.get("ⴰⵎⴰⴳⵓⵜ")
        if annex and annex != lliure:
            morf["parelles_annexio"] += 1
            la, ll = llati(annex).lower(), llati(lliure).lower()
            recuperades = {x.lower() for x in morfologia._sense_annexio(la)}
            if ll in recuperades:
                morf["regla_recupera"] += 1
            else:
                if len(exemples) < 12:
                    exemples.append(f"{la} → {ll} (regla: {', '.join(sorted(recuperades)) or '—'})")
        if plural and plural != lliure:
            morf["plurals"] += 1
            lp = llati(plural).lower()
            if lexicon.lookup(lp) and any((r.get("dictionary") or r.get("ircam")) for r in lexicon.lookup(lp)):
                morf["plural_al_lexic"] += 1
    ordre = {"a revisar": 0, "nova (lliure)": 1, "coincideix": 2}
    files.sort(key=lambda x: ordre[x[0]])
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write(f"# ⵡⵉⴽⵉⵎⴰⵡⴰⵍ (Viccionari zgh, CC BY-SA) contra el nostre lèxic\n\n{len(files)} entrades amb traducció en/fr · caixes: {dict(caixes)}\n\n")
        g.write(f"**Morfologia:** {morf['parelles_annexio']} parelles lliure↔annexió; la nostra regla recupera la forma lliure en "
                f"{morf['regla_recupera']} ({100*morf['regla_recupera']/max(1,morf['parelles_annexio']):.0f} %). "
                f"{morf['plurals']} plurals; {morf['plural_al_lexic']} són al lèxic.\n\nExemples on la regla falla: " + "; ".join(exemples) + "\n\n")
        g.write("| caixa | llatí | tifinag | Viccionari (en/fr) | nosaltres | categoria |\n|---|---|---|---|---|---|\n")
        for x in files:
            g.write("| " + " | ".join(str(v).replace("|", "/") for v in x) + " |\n")
    print(len(files), "entrades ·", dict(caixes), "· annexió:", dict(morf))
    for x in [f for f in files if f[0] == "a revisar"][:15]:
        print(f"  {x[1]:14} {x[3][:30]:30} | {x[4][:45]}")
