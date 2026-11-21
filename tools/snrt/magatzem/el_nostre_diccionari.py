"""El diccionari, en un sol fitxer: la forma, que vol dir, i com de segur n'estem.

Fins ara hi havia dues meitats que no es parlaven:

  * `fitxa_fiabilitat.tsv` -- 39.274 formes que **es diuen**, amb el seu suport (quants cops,
    quantes boques, acord amb l'ull, si un diccionari huma la te). **No diu que volen dir.**
  * `glossari_del_significat.tsv` -- 296 parelles **forma<->significat** confirmades per l'ull,
    que surten del cami invers des de l'arab. No diu amb quina forca es diu.

Aqui es creuen per esquelet, amb el llindar que la mesura va donar (quatre consonants: a tres,
el 28 % dels casaments son casualitat).

**Les columnes de fiabilitat, i d'on surt cadascuna** -- cap d'elles no surt nomes de la nostra
orella:

  vegades, boques   quant es diu i en quants capitols (l'orella, pero comptada)
  acord             quantes vegades casa amb el que l'ull va llegir (testimoni independent)
  diccionari        si un diccionari huma la te (Viccionari amazic / IRCAM)
  vol_dir           que vol dir, confirmat per l'ull sobre el significat de l'arab
  capitols_sig      en quants capitols diferents s'ha confirmat aquell significat

    el_nostre_diccionari.py
"""
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet      # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MIN_ESQ = 4                   #: mesurat: a 3 consonants el 28 % son casualitat


def llegeix(nom):
    p = MAG / nom
    if not p.exists():
        return []
    return list(csv.DictReader(io.open(p, encoding="utf-8", newline=""), delimiter="\t"))


#: el significat, per esquelet; si dos hi casen, mana el que surt en mes capitols
sig = {}
for r in llegeix("glossari_del_significat.tsv"):
    k = esquelet(r.get("forma") or "")
    if len(k) < MIN_ESQ:
        continue
    caps = int(r.get("capitols") or 0)
    if k not in sig or caps > sig[k][1]:
        sig[k] = (r.get("vol_dir") or "", caps)
print(f"{len(sig)} significats amb esquelet de {MIN_ESQ}+ consonants")

files = llegeix("fitxa_fiabilitat.tsv")
print(f"{len(files)} formes a la fitxa")

fora, amb_sig = [], 0
for r in files:
    forma = (r.get("forma") or "").strip()
    if not forma:
        continue
    k = esquelet(forma)
    v = sig.get(k)
    if v:
        amb_sig += 1
    fora.append({
        "forma": forma,
        "escrit": r.get("escrit", ""),
        "vol_dir": v[0] if v else "",
        "capitols_sig": v[1] if v else "",
        "verdicte": r.get("verdicte", ""),
        "vegades": r.get("vegades", ""),
        "boques": r.get("boques", ""),
        "acord": r.get("acord", ""),
        "motiu": r.get("motiu", ""),
    })

#: primer el que mes sabem: amb significat i amb veredicte fort
ordre = {"de llibre": 0, "potser al diccionari": 1, "sòlida": 2,
         "la norma no l'escriu": 3, "per mirar": 4, "poca cosa": 5}
fora.sort(key=lambda r: (0 if r["vol_dir"] else 1, ordre.get(r["verdicte"], 9),
                         -int(r["vegades"] or 0)))

camps = ["forma", "escrit", "vol_dir", "capitols_sig", "verdicte", "vegades", "boques",
         "acord", "motiu"]
with io.open(MAG / "diccionari.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=camps, delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(fora)

print(f"\n{amb_sig} formes amb significat")
amb_tot = [r for r in fora if r["vol_dir"] and r["verdicte"] in
           ("de llibre", "potser al diccionari", "sòlida", "la norma no l'escriu")]
print(f"{len(amb_tot)} amb significat I suport -- el nucli del diccionari\n")
print(f"{'forma':<16}{'vol dir':<18}{'veredicte':<22}{'cops':>6}{'boques':>8}")
for r in amb_tot[:16]:
    print(f"{r['forma'][:15]:<16}{r['vol_dir'][:17]:<18}{r['verdicte']:<22}"
          f"{r['vegades']:>6}{r['boques']:>8}")
print("\nescrit diccionari.tsv")
