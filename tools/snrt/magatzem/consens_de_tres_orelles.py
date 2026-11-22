"""El pseudo-transcrit de consens dels episodis rifenys.

Les 7,67 hores de tarifit del SNRT no tenen transcripcio utilitzable: el subtitol es una
TRADUCCIO a la norma de l'IRCAM i cap orella no hi casa (0,4 %, mesurat amb dues orelles
diferents i confirmat amb una tercera que no comparteix ni arquitectura ni ortografia).

El que si que es pot fer es preguntar-ho a tres orelles independents i quedar-se amb el que
coincideixen. Aixo no es veritat: es un **consens**, que es grau C (catalogat, no verificat). Pero
es l'unic transcrit que aquest material pot tenir sense una persona del Rif.

Les tres orelles, totes sobre els mateixos 3.517 talls (feina del 20-11 a les 05:28):
  * `shi`  = MMS-1b-all + adaptador shi + el nostre afinat (la nostra orella de sempre)
  * `kab`  = MMS-1b-all + adaptador kab (cabil, la llengua amaziga mes propera al rifeny de les
             que l'MMS porta)
  * `rif`  = un model entrenat en rifeny, d'una altra base

PREDICCIO, escrita abans de mesurar-ho: `kab` i `rif` han de coincidir mes entre ells que
qualsevol dels dos amb `shi`, perque el cabil i el rifeny son llengues del nord i el tachelhit es
del sud. Si surt que `shi` i `rif` s'assemblen mes, la meva idea de per que aquests episodis no
casen esta malament.

Surt `corpus_consens_rifeny.jsonl`: una replica per tall amb el text de consens, de quantes
orelles ve, i el significat (del catala, que ve de l'arab i no de cap d'aquestes orelles).
"""
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SORTIDA = MAG / "prova_dolents" / "sortida"
ORELLES = ("shi", "kab", "rif")
PROP = .35          #: dues orelles «diuen el mateix» si els esquelets disten <= 0,35


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


sent = {o: {} for o in ORELLES}
for o in ORELLES:
    for l in io.open(SORTIDA / f"sentit_{o}.jsonl", encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            sent[o][x["id"]] = (x.get("sentit") or "").strip()

#: el text del subtitol i el catala, del mateix lloc d'on van sortir els talls
triat = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        triat[x["id"]] = x

ids = sorted(set(sent["shi"]) & set(sent["kab"]) & set(sent["rif"]))
print(f"{len(ids)} talls sentits per les tres orelles\n")

#: quant s'assemblen entre elles, i cadascuna amb el subtitol
parelles = [("shi", "kab"), ("shi", "rif"), ("kab", "rif")]
print(f"{'parella':<12}{'casen':>8}{'%':>7}   (esquelet, <= 0,35)")
for a, b in parelles:
    n = ok = 0
    for i in ids:
        if sent[a][i] and sent[b][i]:
            n += 1
            ok += prop(esquelet(sent[a][i]), esquelet(sent[b][i])) <= PROP
    print(f"{a}~{b:<8}{ok:8d}{100*ok/max(1,n):7.1f}")

print(f"\n{'orella':<12}{'amb el subtitol':>17}{'%':>7}")
for o in ORELLES:
    n = ok = 0
    for i in ids:
        ull = (triat.get(i, {}).get("tifinag") or "").strip()
        if ull and sent[o][i]:
            n += 1
            ok += prop(esquelet(ull), esquelet(sent[o][i])) <= PROP
    print(f"{o:<12}{ok:17d}{100*ok/max(1,n):7.1f}")

#: --- el consens ---
corpus = []
quants = Counter()
for i in ids:
    dits = {o: sent[o][i] for o in ORELLES if sent[o][i]}
    if len(dits) < 2:
        quants["cap acord possible"] += 1
        continue
    #: qui coincideix amb qui
    millor, suport = None, 0
    for o, t in dits.items():
        n = 1 + sum(1 for p, u in dits.items()
                    if p != o and prop(esquelet(t), esquelet(u)) <= PROP)
        #: amb empat mana la que te mes suport i, si tambe empaten, la mes llarga
        if n > suport or (n == suport and millor is not None and len(t) > len(millor[1])):
            millor, suport = (o, t), n
    if suport < 2:
        quants["cap parella no casa"] += 1
        continue
    #: `shi` i `kab` son el MATEIX model base amb adaptadors diferents: que coincideixin no es
    #: una segona opinio, es la mateixa maquina dues vegades. Nomes compta com a independent si
    #: el `rif` (altra base, altra ortografia) hi es a dins.
    qui = {o for o, t in dits.items()
           if o == millor[0] or prop(esquelet(t), esquelet(millor[1])) <= PROP}
    independent = "rif" in qui and len(qui) >= 2
    quants[f"{suport} orelles" + ("" if independent else " (nomes shi+kab, mateixa base)")] += 1
    x = triat.get(i, {})
    corpus.append({"id": i, "capitol": x.get("capitol"), "text": millor[1],
                   "orella": millor[0], "suport": suport, "independent": independent,
                   "catala": x.get("catala"), "arab": x.get("arab"),
                   "tifinag_norma": x.get("tifinag"),
                   "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi"), "grau": "C"})

print("\nel consens:")
for k, v in sorted(quants.items(), key=lambda kv: -kv[1]):
    print(f"   {k:<22}{v:6d}")
indep = [r for r in corpus if r["independent"]]
print(f"   amb suport INDEPENDENT (hi es el rif): {len(indep)} de {len(corpus)}")
amb_catala = [r for r in indep if (r.get("catala") or "").strip()]
segons = sum(float(r["t_fi"]) - float(r["t_ini"]) for r in amb_catala
             if r.get("t_ini") is not None and r.get("t_fi") is not None)
print(f"\nrepliques de consens: {len(corpus)}  ·  amb significat en catala: {len(amb_catala)}"
      f"  ({segons/3600:.2f} h)")

with io.open(MAG / "corpus_consens_rifeny.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for r in corpus:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("escrit corpus_consens_rifeny.jsonl")
print("\nGRAU C: tres maquines que s'hi assemblen no son una persona que ho confirmi.")
