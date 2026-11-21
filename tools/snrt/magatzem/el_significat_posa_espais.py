"""La idea d'en Pablo serveix per als espais? Mesurat.

El cami invers (`el_cami_invers.py`) troba, dins d'una cadena enganxada, les formes que el
significat de l'arab fa esperar: 433 formes, 318 confirmades per l'ull (73 %).

La pregunta d'ara es una altra: **si hi partim per alla, la frase s'assembla mes al que diu
l'ull?** Trobar una paraula i posar-hi be els espais no es el mateix: el tros de davant i el de
darrere poden quedar fets un nyap.

Es mesura aparellat, replica a replica, contra el tifinag transliterat -- que es **l'altre
testimoni**, el que no ha sentit res -- i amb interval remostrejant **capitols**, que es la
unitat que es va mostrejar.

    el_significat_posa_espais.py
"""
import io
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")


def _taula_tifinag():
    t = io.open(r"E:/tamazight/_magatzem/acord_26.py", encoding="utf-8").read()
    i = t.index("TIF = {")
    j = t.index("}", i) + 1
    d = {}
    exec(t[i:j], {}, d)
    return d["TIF"]


TIF = _taula_tifinag()
from tria_el_millor_text import esquelet      # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
BIBLIO = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
WIKI = Path(r"C:/Users/josep/Veus-tachelhit/_escoltats/wikimawal/wikimawal.json")
MIN_CADENA, MIN_COPS, MIN_DICE = 11, 2, 0.22
VEGADES = 2000

BUIDES = set("""el la els les un una uns unes de del dels d a al als en amb per què que qui com
on quan i o ni no pas em et es ens us se li hi ho meu meva teu teva seu seva nostre vostre
aquest aquesta aquests aquestes aquell aquella això allò ja molt més menys tan tant també sí
doncs però sinó perquè si quin quina quins quines ha he has hem heu han era eres som sou son és
ser estar fer dir va van vaig vas vam vau cap tot tota tots totes altre altra me te nos vos lo
los ara abans després sobre sota entre fins des cada algun alguna""".split())


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def cat(t):
    return [w for w in re.findall(r"[a-zàáèéíïòóúüçñ']+", (t or "").lower()) if len(w) > 1]


def amaz(t):
    return [w for w in re.findall(r"[^\W\d_]+", (t or "").lower(), re.UNICODE) if len(w) > 1]


def del_tifinag(t):
    fora = []
    for c in (t or ""):
        if c in TIF:
            fora.append(TIF[c])
        elif unicodedata.name(c, "").startswith("TIFINAGH"):
            fora.append("")
        else:
            fora.append(c)
    return "".join(fora)


def rica(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()


# ------------------------------------------------------- les candidates (com al camí invers)
nc, na = Counter(), Counter()
junts = defaultdict(Counter)
for l in io.open(BIBLIO, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    c, a = cat(x.get("catala")), amaz(x.get("text"))
    if not (c and a and len(a) <= 12):
        continue
    for w in set(c):
        nc[w] += 1
        for f in set(a):
            junts[w][f] += 1
    for f in set(a):
        na[f] += 1
candidates = defaultdict(set)
for w, fs in junts.items():
    if w in BUIDES or nc[w] < MIN_COPS:
        continue
    for f, n in fs.items():
        if n >= MIN_COPS and 2 * n / (nc[w] + na[f]) >= MIN_DICE and len(f) >= 3:
            candidates[w].add(f)
for e in json.load(io.open(WIKI, encoding="utf-8")).get("entrades", []):
    forma = (e.get("llati") or "").strip().lower()
    if len(forma) < 3:
        continue
    tr = e.get("traduccions") or {}
    for t in (tr.values() if isinstance(tr, dict) else tr):
        for w in cat(t if isinstance(t, str) else str(t)):
            if w not in BUIDES:
                candidates[w].add(forma)

# ------------------------------------------------------- partir per on diu el significat
per_cap = defaultdict(list)
tocades = talls = 0
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    ull = rica(del_tifinag(x.get("tifinag")))
    dit = rica(x.get("sentit"))
    if not ull or not dit or not (x.get("catala") or "").strip():
        continue
    vol = [w for w in cat(x.get("catala")) if w not in BUIDES and w in candidates]
    nou, canviat = [], False
    for p in dit.split():
        if len(p) < MIN_CADENA or not vol:
            nou.append(p)
            continue
        ep = esquelet(p)
        millor = None
        for w in vol:
            for f in candidates[w]:
                ef = esquelet(f)
                #: la forma hi ha de ser sencera, i ha de deixar un tros a banda i banda o a un
                #: costat: si ocupa tota la cadena no hi ha res a partir
                if len(ef) >= 3 and ef in ep and len(ef) < len(ep):
                    if millor is None or len(ef) > len(millor):
                        millor = ef
        if millor is None:
            nou.append(p)
            continue
        #: tornar de l'esquelet a les lletres: on comenca i on s'acaba dins de la cadena
        pos, i, ini, fi = ep.index(millor), 0, None, None
        vist = 0
        for i, c in enumerate(p):
            if esquelet(c):
                if vist == pos and ini is None:
                    ini = i
                if vist == pos + len(millor) - 1:
                    fi = i + 1
                    break
                vist += 1
        if ini is None or fi is None or fi <= ini:
            nou.append(p)
            continue
        trossos = [t for t in (p[:ini], p[ini:fi], p[fi:]) if t]
        if len(trossos) > 1:
            canviat = True
            talls += len(trossos) - 1
        nou += trossos
    if not canviat:
        continue
    tocades += 1
    nou = " ".join(nou)
    per_cap[x.get("capitol")].append((lev(ull, dit), lev(ull, nou), len(ull),
                                      len(ull.split()),
                                      lev(ull.split(), dit.split()),
                                      lev(ull.split(), nou.split())))

tots = [p for v in per_cap.values() for p in v]
print(f"{tocades} rèpliques tocades · {talls} talls posats · {len(per_cap)} capítols\n")
if not tots:
    raise SystemExit("cap")

n = sum(x[2] for x in tots)
nw = sum(x[3] for x in tots)
ca, cb = sum(x[0] for x in tots) / n, sum(x[1] for x in tots) / n
wa, wb = sum(x[4] for x in tots) / nw, sum(x[5] for x in tots) / nw
print(f"sobre les rèpliques tocades, contra el que diu l'ull:")
print(f"   CER  abans {ca:.4f}  →  després {cb:.4f}   ({cb-ca:+.4f})")
print(f"   WER  abans {wa:.4f}  →  després {wb:.4f}   ({wb-wa:+.4f})")

caps = sorted(per_cap)
rnd = random.Random(20261120)
reps = []
for _ in range(VEGADES):
    t = [p for _ in caps for p in per_cap[rnd.choice(caps)]]
    m = max(1, sum(x[2] for x in t))
    reps.append((sum(x[1] for x in t) - sum(x[0] for x in t)) / m)
reps.sort()
lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES) - 1]
diu = "AJUDA" if hi < 0 else ("FA NOSA" if lo > 0 else "no es pot dir")
print(f"\n   interval per capítol: [{lo:+.4f}, {hi:+.4f}]  →  {diu}")
