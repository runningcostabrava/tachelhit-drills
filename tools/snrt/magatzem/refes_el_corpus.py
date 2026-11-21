"""Refa el corpus amb el millor text de cada capitol i aparellant per ORDRE.

Dues coses canvien respecte del corpus d'abans (`acord_26.jsonl` / `corpus_grau_a.jsonl`):

1. L'ull ja no es el text de la fabrica sino el TRIAT (`text_triat.jsonl`): per cada capitol, el
   que mes s'acorda amb l'orella entre el de la fabrica (720p, consens de fotogrames) i la
   relectura (1080p, desempat topologic). Quatre capitols que donaven 0,0% ara donen 17-30%.
2. Les paraules s'aparellen amb l'alineacio global per ORDRE (Needleman-Wunsch sobre l'esquelet
   consonantic), no cadascuna amb la mes semblant de la linia. Aixo es la llico del 29-10: el
   veinatge per semblança inventa parelles (`nnk` amb `ungal`).

Graus, que no han canviat:
  per replica  A = l'ull i l'orella casen (CER <= 0,35)   B = <= 0,6   C = pitjor
  per paraula  A = l'orella segura (>= 0,85) i l'ull hi casa   B = segura i no hi casa
               C = insegura pero la forma es repeteix 3 vegades o mes   D = esperar

Surt `acord_triat.jsonl`, `ocurrencies_triat.jsonl` i `corpus_grau_a_triat.jsonl`.
"""
import io, json, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
SEGUR = 0.85


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

triat = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        triat[x["id"]] = x
print(f"replicas amb text triat: {len(triat)} · talls sentits: {len(sentit)}")

graus, per_cap = Counter(), defaultdict(Counter)
corpus = []
with io.open(MAG / "acord_triat.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for ident, x in triat.items():
        cap = x["capitol"]
        s = sentit.get(ident, {})
        ull, orella = (x.get("tifinag") or "").strip(), (s.get("sentit") or "").strip()
        eu, eo = esquelet(ull), esquelet(orella)
        if not eu or not eo:
            graus["sense"] += 1
            per_cap[cap]["sense"] += 1
            continue
        cer = lev(eu, eo) / max(len(eu), len(eo))
        g = "A" if cer <= .35 else ("B" if cer <= .6 else "C")
        graus[g] += 1
        per_cap[cap][g] += 1
        r = {"id": ident, "capitol": cap, "grau": g, "cer": round(cer, 3), "tifinag": ull,
             "sentit": orella, "catala": x.get("catala"), "arab": x.get("arab"),
             "conf": s.get("conf"), "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi"),
             "d_on": x.get("d_on")}
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if g == "A" and x.get("catala"):
            corpus.append(r)

n = sum(graus.values())
print(f"\nper replica (de {n}):")
for k in ("A", "B", "C", "sense"):
    print(f"   {k:6s} {graus[k]:6d}  {100*graus[k]/max(1,n):5.1f}%")

rep = Counter()
for x in sentit.values():
    for p in x.get("paraules", []):
        e = esquelet(p["p"])
        if len(e) >= 2:
            rep[e] += 1

gp = Counter()
with io.open(MAG / "ocurrencies_triat.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for ident, x in triat.items():
        s = sentit.get(ident, {})
        paraules = s.get("paraules") or []
        if not paraules:
            continue
        ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
        #: alinea() torna parelles d'INDEXS (i, j); la distancia la calcula qui crida.
        for i, j in alinea([p["p"] for p in paraules], ull):
            p = paraules[i]
            norma = ull[j] if j is not None else None
            dist = prop(esquelet(p["p"]), esquelet(ull[j])) if j is not None else None
            e = esquelet(p["p"])
            if p["c"] >= SEGUR:
                g = "A" if (norma is not None and dist is not None and dist <= .35) else "B"
            elif len(e) >= 2 and rep[e] >= 3:
                g = "C"
            else:
                g = "D"
            gp[g] += 1
            f.write(json.dumps({"id": ident, "capitol": x["capitol"], "sentit": p["p"],
                                "esquelet": e, "conf": p["c"], "grau": g, "norma": norma,
                                "dist": round(dist, 3) if dist is not None else None,
                                "repeticions": rep[e], "catala": x.get("catala"),
                                "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi")},
                               ensure_ascii=False) + "\n")
np_ = sum(gp.values())
print(f"\nper paraula (de {np_}):")
for k in "ABCD":
    print(f"   {k}: {gp[k]:6d}  {100*gp[k]/max(1,np_):5.1f}%")

with io.open(MAG / "corpus_grau_a_triat.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for r in corpus:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
segons = sum((float(r["t_fi"]) - float(r["t_ini"])) for r in corpus
             if r.get("t_ini") is not None and r.get("t_fi") is not None)
print(f"\ncorpus de grau A amb significat: {len(corpus)} replicas, {segons/3600:.2f} h")
print(f"formes diferents sentides: {len(rep)}")
