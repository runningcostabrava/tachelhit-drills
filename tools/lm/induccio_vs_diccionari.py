# -*- coding: utf-8 -*-
"""Els candidats induïts del corpus paral·lel, contra el que el diccionari i la taula a mà diuen.

Tres caixes, i cadascuna mana una acció diferent:
  confirmat     el candidat anglès (o un sinònim de l'arrel) és entre les glosses del lèxic
                → la glossa queda avalada per un parlant (el subtitulador), sense cap persona nostra
  nou           el lèxic no té el token (ni per morfologia) → lèxic del camp que faltava; candidat
                a la taula a mà, amb el número al costat
  contradiu     el lèxic té el token i cap glossa no s'assembla al candidat → un dels dos és fals

ÚS: induccio_vs_diccionari.py <induccio.md> <sortida.md>
"""
import io
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.chdir(os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import lexicon        # noqa: E402
import morfologia     # noqa: E402

#: traduccions català→anglès de les glosses de la taula a mà més corrents, per poder comparar
CAT_EN = {"vaixell": "ship", "casa": "house", "riu": "river", "lloc": "place", "paraula": "word",
          "llengua": "language", "tot": "all", "però": "but", "perquè": "because", "on": "where",
          "jo": "i", "tu": "you", "ell": "he", "sol": "sun", "clau": "key", "home": "man",
          "homes": "men", "país": "country", "terra": "land", "capità": "captain", "mar": "sea",
          "nit": "night", "dia": "day", "aigua": "water", "pare": "father", "mare": "mother",
          "fill": "son", "filla": "daughter", "només": "only", "de sobte": "suddenly",
          "anar": "go", "trobar": "find", "sortir": "out", "dir": "say", "saber": "know",
          "hi ha": "there", "rei": "king", "ciutat": "city", "damunt": "above"}


#: el lèxic parla francès (IRCAM, conjugacions) i la inducció anglès: sinònims per arrel
FR_EN = {"chef": "chief", "roi": "king", "monarque": "king", "envoy": "messenger", "savoir": "know",
         "connaître": "know", "rester": "stay", "demeurer": "remain", "asseoir": "sit",
         "mourir": "die", "mort": "dead", "lever": "stand", "regarder": "look", "ville": "city",
         "village": "village", "maison": "house", "homme": "man", "femme": "woman", "enfant": "child",
         "fils": "son", "fille": "daughter", "père": "father", "mère": "mother", "frère": "brother",
         "sœur": "sister", "mer": "sea", "eau": "water", "nuit": "night", "jour": "day", "soleil": "sun",
         "terre": "land", "pays": "country", "chemin": "road", "porte": "door", "parole": "word",
         "dire": "say", "voir": "see", "aller": "go", "venir": "come", "donner": "give", "prendre": "take",
         "trouver": "find", "manger": "eat", "boire": "drink", "dormir": "sleep", "entendre": "hear",
         "écouter": "listen", "parler": "speak", "pleurer": "cry", "rire": "laugh", "peur": "fear",
         "tête": "head", "main": "hand", "cœur": "heart", "œil": "eye", "yeux": "eyes", "bateau": "ship",
         "cheval": "horse", "chien": "dog", "oiseau": "bird", "vautour": "vulture", "argent": "money",
         "clé": "key", "tout": "all", "grand": "big", "petit": "small", "vieux": "old", "seul": "alone"}


#: irregulars anglesos que la poda de sufixos no veu
EN_BASE = {"went": "go", "gone": "go", "stood": "stand", "sat": "sit", "dead": "die", "died": "die",
           "said": "say", "saw": "see", "found": "find", "took": "take", "gave": "give", "came": "come",
           "men": "man", "women": "woman", "children": "child", "eyes": "eye", "everything": "all",
           "everyone": "all", "dark": "darkness", "obscurité": "darkness", "debout": "stand",
           "obscur": "darkness"}


def arrel(w):
    w = FR_EN.get(w.lower(), w.lower())
    w = EN_BASE.get(w, w)
    return re.sub(r"(ies|es|s|ed|ing|ly)$", "", w)[:5]


def glosses_en(tok, sig, ev, en):
    """Totes les paraules angleses (i les catalanes de la taula, traduïdes) que el lèxic dóna."""
    fora = set()
    for r in lexicon.lookup(tok) or []:
        for d in r.get("dictionary") or []:
            for e in (d.get("english") or []) + [d.get("french") or ""]:
                fora.update(re.findall(r"[a-zà-ÿ]+", e.lower()))
        for c in r.get("conjugation") or []:
            fora.update(re.findall(r"[a-zà-ÿ]+", (c.get("french") or "").lower()))
        for c in r.get("ircam") or []:
            fora.update(re.findall(r"[a-zà-ÿ]+", (c.get("french") or "").lower()))
    g = morfologia.glossa(tok, sig, ev, en)
    if g:
        fora.update(re.findall(r"[a-zà-ÿ]+", g[0].lower()))
        for cat, eng in CAT_EN.items():
            if cat in g[0].lower():
                fora.add(eng)
    return fora, bool(g)


if __name__ == "__main__":
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    files = []
    for l in io.open(sys.argv[1], encoding="utf-8"):
        m = re.match(r"\| (\d+) \| `([^`]+)` \| (.*) \|$", l.strip())
        if not m:
            continue
        n, tok, cands = int(m.group(1)), m.group(2), m.group(3)
        cand = [(c, float(d)) for c, d in re.findall(r"\*\*([^*]+)\*\* \(([\d.]+),", cands)]
        gl, te_glossa = glosses_en(tok, sig, ev, en)
        caixa = "nou" if not gl else "contradiu"
        for c, d in cand:
            if c in gl or any(arrel(c) == arrel(x) for x in gl if len(x) > 3):
                caixa = "confirmat"
                break
        #: un candidat que és el mateix token (o quasi) escrit a l'anglès és un NOM PROPI que el
        #: subtitulador deixa tal qual: `isġi` → «Isghi». El diccionari que el tradueix («vautour»)
        #: no s'equivoca de paraula, s'equivoca de categoria: un nom no es glossa.
        tok_pla = re.sub(r"[^a-z]", "", tok.lower().replace("ġ", "gh").replace("ḫ", "kh").replace("š", "sh"))
        if caixa != "confirmat" and any(re.sub(r"[^a-z]", "", c.lower()).rstrip("s") == tok_pla for c, d in cand):
            caixa = "nom propi"
        #: partícules, pronoms i còpules de la taula a mà coapareixen amb tot: el que diguin
        #: d'elles no és una glossa, és soroll, i es marca a part
        elif caixa == "contradiu" and te_glossa and (morfologia.glossa(tok, sig, ev, en) or ("", ""))[1] in (
                "partícula", "forma gramatical", "preposició amb pronom"):
            caixa = "funció"
        files.append((caixa, n, tok, cand, sorted(gl)[:6]))
    ordre = {"contradiu": 0, "nou": 1, "nom propi": 2, "confirmat": 3, "funció": 4}
    files.sort(key=lambda x: (ordre[x[0]], -x[1]))
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write("# Candidats induïts contra el lèxic\n\n| caixa | rètols | token | candidats (Dice) | el lèxic diu |\n|---|---|---|---|---|\n")
        for caixa, n, tok, cand, gl in files:
            g.write(f"| **{caixa}** | {n} | `{tok}` | " + ", ".join(f"{c} ({d:.2f})" for c, d in cand) +
                    f" | {', '.join(gl) if gl else '—'} |\n")
    import collections
    print(collections.Counter(x[0] for x in files))
    for caixa, n, tok, cand, gl in files[:30]:
        print(f"  {caixa:10} {n:4} {tok:14} {cand[0][0]:14} | lèxic: {', '.join(gl)[:60]}")
