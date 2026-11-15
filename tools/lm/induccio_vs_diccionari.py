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
          "fill": "son", "filla": "daughter", "només": "only", "de sobte": "suddenly"}


def arrel(w):
    return re.sub(r"(ies|es|s|ed|ing|ly)$", "", w.lower())[:5]


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
        files.append((caixa, n, tok, cand, sorted(gl)[:6]))
    ordre = {"contradiu": 0, "nou": 1, "confirmat": 2}
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
