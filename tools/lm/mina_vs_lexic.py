# -*- coding: utf-8 -*-
"""El que el professor explica als vídeos en dàrija (sortida de `mina_transcrits.py`), contra el
nostre lèxic. Per a cada ítem amb forma llatina: què en diu `glossa()`, i si el significat que
dóna el professor (català, posat pel model a partir de l'àrab del transcrit) casa amb la nostra
glossa per arrel de paraula. Tres caixes: coincideix / contradiu / no la tenim. Els ítems sense
forma llatina es llisten a part, per freqüència de la forma àrab, perquè són els que caldria
resoldre a mà o amb el transliterador.

L'APARELLADOR CURT I EL JUTGE. El nostre lèxic no és en català: les glosses són en anglès (Oulhaj),
francès (IRCAM: conjugacions i DGLAI) i en/fr/ar (ⵡⵉⴽⵉⵎⴰⵡⴰⵍ); només les partícules de
`morfologia._TAULA` i el `LEXIC_VALIDAT` són en català. L'aparellador de sota compara paraules
catalanes del professor amb aquestes glosses amb una taula de sinònims de 80 mots (`CA_SIN`): tot
el que no hi és surt «contradiu» encara que digui el mateix (`imi` «boca» ↔ «bouche»). El 17-11,
de 283 «contradiu» sobre els ítems confirmats, la majoria eren això. Amb `--jutge`, cada
«contradiu» de l'aparellador va a DeepSeek (t = 0), que el classifica:
  a  mateix sentit; la diferència és només la llengua de la nostra glossa
  b  mateix sentit dit diferent (sinònim, plural, article, més general o més concret)
  c  contradicció real de significat
  d  l'ítem del professor és dolent (no és un significat, és un fragment, barreja mots)
i la caixa final és «coincideix (a)», «coincideix (b)», «contradiu» (c) o «ítem dolent» (d). Els
veredictes es desen a <sortida>.jutge.jsonl (clau = forma) i es reaprofiten.

ÚS: mina_vs_lexic.py <mina_transcrits.jsonl> <sortida.md> [--jutge] [--fils N]
Claus per a --jutge: `DEEPSEEK_ENV` (un .env amb DEEPSEEK_API_KEY), si no és al .env del backend.
"""
import collections
import io
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

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

JUTGE_SYS = """Ets un lingüista de l'amazic (taixelhit i tamazight del Marroc). Comparem dues glosses d'una mateixa
forma amaziga:
  · la del PROFESSOR: el que un professor marroquí diu a classe que vol dir (en català, traduït per una
    màquina del dàrija del transcrit automàtic; també tens l'àrab original i la frase on ho diu)
  · la NOSTRA: el que en diu el nostre lèxic (glosses en anglès del diccionari d'Oulhaj, en francès de
    l'IRCAM, o en català si és una partícula o lèxic validat; entre claudàtors, com s'hi ha arribat:
    [diccionari], [verb] = forma conjugada d'un verb, [annexió], [plural], [partícula], [lèxic validat])
Classifica la parella amb UNA lletra:
  a = el mateix sentit; l'única diferència és que la nostra glossa és en anglès, francès o una altra
      llengua que no és el català
  b = el mateix sentit dit diferent (sinònim, plural o singular, amb article, més general o més concret,
      la mateixa funció gramatical dita amb altres paraules)
  c = contradicció real: la forma vol dir una cosa per al professor i una altra per al lèxic (també quan
      el lèxic l'ha llegida com a forma d'un verb o d'un nom que no té res a veure)
  d = l'ítem del professor és dolent i no es pot comparar: no és un significat sinó una descripció
      buida («forma usada en…», «conjugació de…» sense dir què vol dir), un fragment, o barreja mots
Si dubtes entre a i b, tria a quan la nostra glossa no és en català. Respon una sola línia: la lletra,
un espai i un motiu en català de 15 paraules com a molt."""

CAIXA_DEL_JUTGE = {"a": "coincideix (a: altra llengua)", "b": "coincideix (b: dit diferent)", "c": "contradiu", "d": "ítem dolent"}


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


def jutja(lat, its, nostre, cache, pany):
    """DeepSeek classifica un «contradiu» de l'aparellador: a/b/c/d i motiu. Reaprofita la cache."""
    if lat in cache:
        return cache[lat]
    import requests
    key = os.environ["DEEPSEEK_API_KEY"].strip()
    prof = []
    for _, it in its[:3]:
        prof.append(f"- català: {it.get('significat_ca')} · àrab: {it.get('significat_ar')} · frase: {(it.get('on') or '')[:160]}")
    q = (f"FORMA: {lat}\n\nEL PROFESSOR DIU:\n" + "\n".join(prof) + f"\n\nLA NOSTRA GLOSSA:\n{nostre}\n\n"
         "La teva resposta (a / b / c / d, i el motiu):")
    body = {"model": "deepseek-chat", "messages": [{"role": "system", "content": JUTGE_SYS}, {"role": "user", "content": q}],
            "max_tokens": 120, "temperature": 0}
    dit, err, fitxes = "", "", (0, 0)
    for intent in range(4):
        try:
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers={"Authorization": "Bearer " + key},
                              json=body, timeout=90)
            if r.status_code == 200:
                d = r.json()
                dit = (d["choices"][0]["message"].get("content") or "").strip()
                u = d.get("usage") or {}
                fitxes = (u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
                break
            err = f"{r.status_code} {r.text[:100]}"
            if r.status_code in (429, 500, 502, 503):
                time.sleep(5 + 10 * intent)
                continue
            break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(3 + 5 * intent)
    m = re.match(r"\s*\(?([abcd])\)?[\s.:,;)-]", dit.lower() + " ")
    v = {"forma": lat, "classe": m.group(1) if m else ("error" if err else "altre"), "dit": dit, "error": err or None,
         "in": fitxes[0], "out": fitxes[1]}
    with pany:
        cache[lat] = v
    return v


if __name__ == "__main__":
    args = sys.argv[1:]
    jutge = "--jutge" in args
    fils = 3
    if "--fils" in args:
        fils = int(args[args.index("--fils") + 1])
        del args[args.index("--fils"):args.index("--fils") + 2]
    args = [a for a in args if a != "--jutge"]
    if jutge:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ARREL, "backend", ".env"), override=True)
        if os.environ.get("DEEPSEEK_ENV"):
            load_dotenv(os.environ["DEEPSEEK_ENV"], override=False)
    lexicon.load()
    sig, ev, en = morfologia.amb_lexicon(lexicon)
    per_forma = collections.defaultdict(list)
    sense = collections.Counter()
    n_items = n_videos = 0
    for l in io.open(args[0], encoding="utf-8"):
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
        files.append([caixa, len(its), lat, its[0][1].get("significat_ca", "")[:60], (g[0][:60] + f" [{g[1]}]") if g else "—",
                      its[0][0], its[0][1].get("mena", ""), ""])
    c_curt = collections.Counter(x[0] for x in files)
    fitxes = [0, 0]
    if jutge:
        cami_cache = re.sub(r"\.md$", "", args[1]) + ".jutge.jsonl"
        cache = {}
        if os.path.exists(cami_cache):
            for l in io.open(cami_cache, encoding="utf-8"):
                if l.strip():
                    v = json.loads(l)
                    if v.get("classe") in CAIXA_DEL_JUTGE:
                        cache[v["forma"]] = v
        pany = threading.Lock()
        pend = [x for x in files if x[0] == "contradiu"]
        print(f"jutge: {len(pend)} «contradiu» de l'aparellador, {sum(1 for x in pend if x[2] in cache)} ja jutjats", flush=True)
        with ThreadPoolExecutor(max_workers=fils) as ex:
            def una(x):
                g = morfologia.glossa(x[2], sig, ev, en)
                nostre = (g[0] + f" [{g[1]}]") if g else ""
                extra = []
                for r in lexicon.lookup(x[2]) or []:
                    for dd in r.get("dictionary") or []:
                        extra += (dd.get("english") or [])[:4] + ([dd.get("french")] if dd.get("french") else [])
                if extra:
                    nostre += " · diccionari: " + ", ".join(dict.fromkeys(e for e in extra if e))[:200]
                v = jutja(x[2], per_forma[x[2]], nostre, cache, pany)
                with pany:
                    fitxes[0] += v.get("in", 0); fitxes[1] += v.get("out", 0)
                return v
            list(ex.map(una, pend))
        with io.open(cami_cache, "w", encoding="utf-8") as g:
            for v in cache.values():
                g.write(json.dumps(v, ensure_ascii=False) + "\n")
        for x in files:
            if x[0] == "contradiu":
                v = cache.get(x[2])
                if v and v["classe"] in CAIXA_DEL_JUTGE:
                    x[0] = CAIXA_DEL_JUTGE[v["classe"]]
                    x[7] = v["dit"][2:].strip(" .:-") if len(v["dit"]) > 2 else ""
                else:
                    x[0] = "contradiu (sense jutge)"
    ordre = {"contradiu": 0, "contradiu (sense jutge)": 0, "ítem dolent": 1, "no la tenim": 2,
             "coincideix (b: dit diferent)": 3, "coincideix (a: altra llengua)": 4, "coincideix": 5}
    files.sort(key=lambda x: (ordre[x[0]], -x[1]))
    c = collections.Counter(x[0] for x in files)
    with io.open(args[1], "w", encoding="utf-8") as g:
        g.write(f"# El que el professor explica en dàrija, contra el nostre lèxic\n\n{n_videos} vídeos minats · {n_items} ítems · "
                f"{len(per_forma)} formes llatines diferents · {sum(sense.values())} ítems sense forma llatina\n\n"
                f"Caixes de l'aparellador curt: {dict(c_curt)}\n\n")
        if jutge:
            g.write(f"Caixes amb el jutge (DeepSeek, t = 0) sobre els «contradiu» de l'aparellador: {dict(c)} · "
                    f"fitxes {fitxes[0]} dins / {fitxes[1]} fora\n\n")
        g.write("| caixa | cops | forma | el professor (ca) | nosaltres | vídeo | mena | el jutge |\n|---|---|---|---|---|---|---|---|\n")
        for x in files:
            g.write("| " + " | ".join(str(v).replace("|", "/") for v in x) + " |\n")
        g.write("\n## Ítems sense forma llatina (forma àrab del transcrit, cops)\n\n")
        for k, v in sense.most_common(60):
            g.write(f"- {k} ×{v}\n")
    print(f"{n_videos} vídeos · {n_items} ítems · {len(per_forma)} formes · {dict(c)} · sense llatí {sum(sense.values())}")
    for x in files[:30]:
        print(f"  {x[0]:30} ×{x[1]:<3} {x[2]:14} {x[3][:34]:34} | {x[4][:44]} | {x[7][:50]}")
