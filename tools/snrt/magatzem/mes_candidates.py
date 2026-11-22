"""Fins on es pot afluixar el filtre de candidates sense que la via del significat menteixi.

El cami invers dispara al 7,3 % de les cadenes i el que el limita no es el metode sino les
candidates significat<->forma: 7.210 parelles. S'indueixen de la biblioteca per coocurrencia
(Dice) amb dos llindars triats a ull -- `MIN_COPS = 2` i `MIN_DICE = 0,22`.

Aqui no es trien: es **mesuren**. Per a cada combinacio es compta quantes cadenes toca i, sobre
les formes que hi troba, **quantes confirma l'ull** -- que no ha sentit res i es per tant un
testimoni independent. Afluixar nomes val la pena si l'encert aguanta.

    mes_candidates.py
"""
import io
import json
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
MIN_CADENA = 11

BUIDES = set("""el la els les un una uns unes de del dels d a al als en amb per què que qui com
on quan i o ni no pas em et es ens us se li hi ho meu meva teu teva seu seva nostre vostre
aquest aquesta aquests aquestes aquell aquella això allò ja molt més menys tan tant també sí
doncs però sinó perquè si quin quina quins quines ha he has hem heu han era eres som sou son és
ser estar fer dir va van vaig vas vam vau cap tot tota tots totes altre altra me te nos vos lo
los ara abans després sobre sota entre fins des cada algun alguna""".split())


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


#: els comptatges es fan UN cop; despres nomes canvia el filtre
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

wiki = defaultdict(set)
for e in json.load(io.open(WIKI, encoding="utf-8")).get("entrades", []):
    forma = (e.get("llati") or "").strip().lower()
    if len(forma) < 3:
        continue
    tr = e.get("traduccions") or {}
    for t in (tr.values() if isinstance(tr, dict) else tr):
        for w in cat(t if isinstance(t, str) else str(t)):
            if w not in BUIDES:
                wiki[w].add(forma)

files = [json.loads(l) for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8") if l.strip()]
feina = []
for x in files:
    llargues = [w for w in amaz(x.get("sentit")) if len(w) >= MIN_CADENA]
    if llargues and (x.get("catala") or "").strip():
        feina.append((llargues, cat(x.get("catala")),
                      esquelet(del_tifinag(x.get("tifinag") or ""))))
cadenes = sum(len(c) for c, _, _ in feina)
print(f"{cadenes} cadenes de {MIN_CADENA}+ lletres amb significat\n")

print(f"{'cops':>5}{'dice':>7}{'candidates':>12}{'toca':>7}{'%':>7}"
      f"{'formes':>8}{'confirma l’ull':>16}")
for min_cops in (1, 2, 3):
    for min_dice in (0.10, 0.15, 0.22, 0.30):
        cand = defaultdict(set)
        for w, fs in junts.items():
            if w in BUIDES or nc[w] < min_cops:
                continue
            for f, n in fs.items():
                if n >= min_cops and 2 * n / (nc[w] + na[f]) >= min_dice and len(f) >= 3:
                    cand[w].add(f)
        n_ind = sum(len(v) for v in cand.values())
        for w, fs in wiki.items():
            cand[w] |= fs
        toca = trob = conf = amb_ull = 0
        for llargues, paraules, ull in feina:
            vol = [w for w in paraules if w not in BUIDES and w in cand]
            if not vol:
                continue
            for c in llargues:
                ec = esquelet(c)
                dins = [esquelet(f) for w in vol for f in cand[w]
                        if len(esquelet(f)) >= 3 and esquelet(f) in ec]
                if not dins:
                    continue
                toca += 1
                for ef in dins:
                    trob += 1
                    if ull:
                        amb_ull += 1
                        if ef in ull:
                            conf += 1
        pc = 100 * conf / max(1, amb_ull)
        marca = "  <-- el d'ara" if (min_cops, min_dice) == (2, 0.22) else ""
        print(f"{min_cops:>5}{min_dice:>7.2f}{n_ind:>12}{toca:>7}{100*toca/max(1,cadenes):>6.1f}%"
              f"{trob:>8}{pc:>15.0f}%{marca}")
print("\nAfluixar només val si l'encert de l'ull aguanta: l'ull no ha sentit res.")
