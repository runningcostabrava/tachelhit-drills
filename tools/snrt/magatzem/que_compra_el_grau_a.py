"""El filtre de grau A: quan diu que si, quantes vegades te rao?

Tota la ronda penja d'aquest llindar. Una paraula entra al corpus si l'esquelet de consonants de
l'orella i el de l'ull disten <= 0,35. Al SNRT no ho puc comprovar: no hi ha veritat humana i
l'unic jutge es el mateix parell que vull jutjar.

Pero a les proves amb veritat humana si: la `or` es el que va escriure una persona, i el `dit`
es el que sent el model. Aplicant-hi el MATEIX alineament i el MATEIX llindar, es pot preguntar
el que al SNRT no es pot:

  * **precisio**: de les paraules que el filtre accepta, quantes son EXACTAMENT la paraula de la
    persona (text ric, amb vocals)? I quantes ho son si nomes es mira l'esquelet?
  * **a canvi de que**: quantes paraules bones deixa fora (el record).
  * i **que entra de dolent**: les que passen el filtre sense ser la paraula.

PREDICCIO, escrita abans de mesurar-ho:
  el llindar es va triar per deixar passar la variacio consonantica real (k~s, l~r) sense deixar
  entrar paraules diferents. Espero una precisio d'esquelet molt alta (>90 %) i una precisio de
  text ric molt mes baixa (~60-70 %), perque les vocals son justament el que l'orella escriu a la
  seva manera. Si la precisio d'esquelet no arriba al 85 %, el llindar es massa generos i el
  corpus de la ronda porta brossa.

Es mira tambe que passa amb llindars mes durs, que es la decisio practica de la ronda 2.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

SORTIDA = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
AMB_VERITAT = ("zouhir-tests", "tfa-226", "cv-zgh-test", "test-fora")
LLINDARS = (0.35, 0.25, 0.15, 0.0)


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


files = json.load(io.open(SORTIDA, encoding="utf-8"))
parelles = defaultdict(list)          #: prova -> [(veritat, sentit, distancia d'esquelet)]
for x in files:
    if x.get("prova") not in AMB_VERITAT or (x.get("model") or "").startswith("abans"):
        continue
    veritat = [w for w in (x.get("or") or "").split() if w.strip()]
    orella = [w for w in (x.get("dit") or "").split() if w.strip()]
    for i, j in alinea(veritat, orella):
        if i is None or j is None:
            continue
        parelles[x["prova"]].append((veritat[i], orella[j],
                                     prop(esquelet(veritat[i]), esquelet(orella[j]))))

print("El filtre, contra veritat humana. «ric» = la paraula sencera, vocals incloses.\n")
print(f"{'prova':<15}{'parelles':>9}{'passen':>8}{'%':>6}"
      f"{'precisio esq.':>15}{'precisio ric':>14}{'record ric':>12}")
tot = []
for prova in AMB_VERITAT:
    p = parelles[prova]
    tot += p
    passen = [x for x in p if x[2] <= .35]
    esq_ok = sum(1 for v, o, _ in passen if esquelet(v) == esquelet(o))
    ric_ok = sum(1 for v, o, _ in passen if v.lower() == o.lower())
    ric_tot = sum(1 for v, o, _ in p if v.lower() == o.lower())
    print(f"{prova:<15}{len(p):9d}{len(passen):8d}{100*len(passen)/max(1,len(p)):6.1f}"
          f"{100*esq_ok/max(1,len(passen)):14.1f}%{100*ric_ok/max(1,len(passen)):13.1f}%"
          f"{100*ric_ok/max(1,ric_tot):11.1f}%")

print(f"\n{'-'*72}\nTotes juntes ({len(tot)} parelles de paraula), per llindar:\n")
print(f"{'llindar':>8}{'passen':>9}{'%':>7}{'precisio esq.':>15}{'precisio ric':>14}"
      f"{'record ric':>12}")
ric_tot = sum(1 for v, o, _ in tot if v.lower() == o.lower())
for L in LLINDARS:
    passen = [x for x in tot if x[2] <= L]
    esq_ok = sum(1 for v, o, _ in passen if esquelet(v) == esquelet(o))
    ric_ok = sum(1 for v, o, _ in passen if v.lower() == o.lower())
    print(f"{L:8.2f}{len(passen):9d}{100*len(passen)/max(1,len(tot)):7.1f}"
          f"{100*esq_ok/max(1,len(passen)):14.1f}%{100*ric_ok/max(1,len(passen)):13.1f}%"
          f"{100*ric_ok/max(1,ric_tot):11.1f}%")

#: el que entra de dolent amb el llindar de la ronda: no un numero, exemples per mirar-los
dolentes = [(v, o, d) for v, o, d in tot if d <= .35 and esquelet(v) != esquelet(o)]
dolentes.sort(key=lambda x: -x[2])
print(f"\nEl que passa el filtre SENSE ser la paraula ({len(dolentes)} de "
      f"{sum(1 for x in tot if x[2] <= .35)}), les pitjors primer:")
for v, o, d in dolentes[:15]:
    print(f"   persona «{v}»  ·  orella «{o}»   (esquelets «{esquelet(v)}» ~ «{esquelet(o)}», {d:.2f})")
