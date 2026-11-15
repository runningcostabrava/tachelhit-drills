# -*- coding: utf-8 -*-
"""El que el professor explica als vídeos en dàrija (sortida de `mina_transcrits.py`), contra el
nostre lèxic. Per a cada ítem amb forma llatina: què en diu `glossa()`, i si el significat que
dóna el professor (català, posat pel model a partir de l'àrab del transcrit) casa amb la nostra
glossa per arrel de paraula. Tres caixes: coincideix / contradiu / no la tenim. Els ítems sense
forma llatina es llisten a part, per freqüència de la forma àrab, perquè són els que caldria
resoldre a mà o amb el transliterador.

ÚS: mina_vs_lexic.py <mina_transcrits.jsonl> <sortida.md>
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
import lexicon       # noqa: E402
import morfologia    # noqa: E402

STOP = set("de la el les els uns unes que és són amb per al del dels en i o no sí d l s".split())
#: el professor parla (traduït) en català i el lèxic en francès/anglès: sinònims per arrel
CA_SIN = {"aigua": ["eau", "water"], "muntanya": ["montagne", "mountain"], "petit": ["small", "little"],
          "un": ["a", "an", "une", "one"], "una": ["a", "an", "une", "one"], "nen": ["garçon", "boy", "kid"],
          "jo": ["moi", "me"], "tu": ["toi", "you"], "dos": ["deux", "two"], "tres": ["trois", "three"],
          "voler": ["vouloir", "want"], "vols": ["vouloir", "want"], "vol": ["vouloir", "want"],
          "benvingut": ["bienvenue", "welcome", "salut", "hello"], "hola": ["salut", "hello", "hi"],
          "poesia": ["poésie", "poetry", "poème"], "arada": ["charrue", "plough", "plow"],
          "llaurador": ["laboureur", "farmer", "ploughman"], "genoll": ["genou", "knee"],
          "pàgina": ["page"], "força": ["force", "strength"], "veure": ["voir", "see"],
          "parlar": ["parler", "speak", "talk"], "parlo": ["parler", "speak"], "llengua": ["langue", "language"],
          "casa": ["maison", "house"], "home": ["homme", "man"], "dona": ["femme", "woman"],
          "mare": ["mère", "mother"], "pare": ["père", "father"], "fill": ["fils", "son"],
          "gran": ["grand", "big", "large"], "cap": ["tête", "head"], "mà": ["main", "hand"],
          "menjar": ["manger", "eat"], "beure": ["boire", "drink"], "pa": ["pain", "bread"],
          "llet": ["lait", "milk"], "carn": ["viande", "meat"], "sal": ["sel", "salt"], "foc": ["feu", "fire"],
          "sol": ["soleil", "sun"], "lluna": ["lune", "moon"], "nit": ["nuit", "night"], "dia": ["jour", "day"],
          "any": ["an", "année", "year"], "terra": ["terre", "land", "earth"], "cel": ["ciel", "sky"],
          "paraula": ["mot", "parole", "word"], "nom": ["nom", "noun", "name"], "verb": ["verbe", "verb"],
          "anar": ["aller", "go"], "venir": ["venir", "come"], "saber": ["savoir", "know"], "no": ["non", "not", "ne"],
          "article": ["article"], "indefinit": ["indéfini", "indefinite"], "plural": ["pluriel", "plural"]}


def arrel(w):
    return re.sub(r"(ment|ció|cions|es|s|ar|er|ir|at|ada|ats|ades)$", "", w.lower())[:5]


def mots(s):
    fora = []
    for w in re.findall(r"[a-zà-ÿ·]+", (s or "").lower()):
        if w in CA_SIN:
            fora.extend(CA_SIN[w])
        if len(w) > 2 and w not in STOP:
            fora.append(w)
    return fora


if __name__ == "__main__":
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    per_forma = collections.defaultdict(list)
    sense = collections.Counter()
    n_items = n_videos = 0
    for l in io.open(sys.argv[1], encoding="utf-8"):
        d = json.loads(l)
        n_videos += 1
        for it in d.get("items") or []:
            n_items += 1
            lat = re.sub(r"[^a-zɣɛḍṭẓṣṛḥʷ' -]", "", (it.get("amazic_llati") or "").lower()).strip()
            if lat and " " not in lat and len(lat) >= 2:
                per_forma[lat].append((d["video"], it))
            else:
                sense[it.get("amazic_ar") or "?"] += 1
    files = []
    for lat, its in per_forma.items():
        g = morfologia.glossa(lat, sig, ev, en)
        seus = set()
        for _, it in its:
            seus.update(mots(it.get("significat_ca")))
        nostres = set(mots(g[0])) if g else set()
        for r in lexicon.lookup(lat) or []:
            for dd in r.get("dictionary") or []:
                for e in (dd.get("english") or []) + [dd.get("french") or ""]:
                    nostres.update(mots(e))
        if not g and not nostres:
            caixa = "no la tenim"
        elif any(a == b or (len(a) > 3 and len(b) > 3 and arrel(a) == arrel(b)) for a in seus for b in nostres):
            caixa = "coincideix"
        else:
            caixa = "contradiu"
        files.append((caixa, len(its), lat, its[0][1].get("significat_ca", "")[:60], (g[0][:60] + f" [{g[1]}]") if g else "—",
                      its[0][0], its[0][1].get("mena", "")))
    ordre = {"contradiu": 0, "no la tenim": 1, "coincideix": 2}
    files.sort(key=lambda x: (ordre[x[0]], -x[1]))
    c = collections.Counter(x[0] for x in files)
    with io.open(sys.argv[2], "w", encoding="utf-8") as g:
        g.write(f"# El que el professor explica en dàrija, contra el nostre lèxic\n\n{n_videos} vídeos minats · {n_items} ítems · "
                f"{len(per_forma)} formes llatines diferents · {sum(sense.values())} ítems sense forma llatina\n\n"
                f"Caixes: {dict(c)}\n\n| caixa | cops | forma | el professor (ca) | nosaltres | vídeo | mena |\n|---|---|---|---|---|---|---|\n")
        for x in files:
            g.write("| " + " | ".join(str(v).replace("|", "/") for v in x) + " |\n")
        g.write("\n## Ítems sense forma llatina (forma àrab del transcrit, cops)\n\n")
        for k, v in sense.most_common(60):
            g.write(f"- {k} ×{v}\n")
    print(f"{n_videos} vídeos · {n_items} ítems · {len(per_forma)} formes · {dict(c)} · sense llatí {sum(sense.values())}")
    for x in files[:30]:
        print(f"  {x[0]:12} ×{x[1]:<3} {x[2]:14} {x[3][:34]:34} | {x[4][:44]}")
