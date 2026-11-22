"""Validar el sostre: l'acord d'esquelet contra VERITAT HUMANA, no contra el subtitol.

Tota la nit he mesurat l'acord ull-orella dins del SNRT, i he conclos que el sostre del
27-38 % el posa el subtitulador (que escriu la norma de l'IRCAM) i no la nostra orella.
Aixo es una explicacio, i una explicacio es prova amb material d'una ALTRA procedencia.

Les sortides de la ronda porten cinc proves, i tres d'elles tenen veritat humana:
  - `zouhir-tests`: retols transcrits a ma (H4)
  - `tfa-226`: transcripcio humana de Tamazight For All
  - `cv-zgh-test`: frases llegides, amb el text escrit abans de llegir-les
i una porta subtitol normalitzat (`snrt-retingut`), que es el cas que vull explicar.

PREDICCIO, escrita abans de mesurar-ho:
  si el sostre es del subtitulador, l'acord de grau A (paraules amb CER d'esquelet <= 0,35)
  contra veritat humana ha de ser MOLT per sobre del 38 % del SNRT tachelhit -- cosa de 70 %
  amunt. Si surt semblant al 38 %, la meva explicacio es falsa i el sostre es nostre.

Confusio que no puc treure del tot i que deixo dita: aquestes proves tambe tenen so mes net
i domini mes facil que el SNRT. Per aixo la fila del `snrt-retingut` es al costat, mesurada
amb el MATEIX codi, i per aixo es mira tambe el repartiment paraula a paraula.
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402


def prop(a, b):
    #: la mateixa distancia d'esquelet que fa servir el corpus (`refes_el_corpus.py`)
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))
from alinea_paraules import alinea  # noqa: E402

SORTIDA = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
LLINDAR = .35

files = json.load(io.open(SORTIDA, encoding="utf-8"))
print(f"{'prova':<16}{'frases':>7}{'paraules':>9}{'grau A':>8}{'%':>7}"
      f"{'sense parella':>15}{'CER esq. mediana':>18}")
for prova in ("zouhir-tests", "tfa-226", "cv-zgh-test", "test-fora", "snrt-retingut"):
    files_p = [x for x in files if x.get("prova") == prova
               and (x.get("model") or "").startswith("despres")]
    if not files_p:
        files_p = [x for x in files if x.get("prova") == prova
                   and not (x.get("model") or "").startswith("abans")]
    n_fr = n_par = n_a = n_sol = 0
    dists = []
    for x in files_p:
        veritat = [w for w in (x.get("or") or "").split() if w.strip()]
        orella = [w for w in (x.get("dit") or "").split() if w.strip()]
        if not veritat:
            continue
        n_fr += 1
        n_par += len(veritat)
        for i, j in alinea(veritat, orella):
            if i is None:
                continue
            if j is None:
                n_sol += 1
                continue
            d = prop(esquelet(veritat[i]), esquelet(orella[j]))
            dists.append(d)
            if d <= LLINDAR:
                n_a += 1
    med = sorted(dists)[len(dists) // 2] if dists else float("nan")
    print(f"{prova:<16}{n_fr:7d}{n_par:9d}{n_a:8d}{100*n_a/max(1,n_par):7.1f}"
          f"{n_sol:15d}{med:18.3f}")
print("\nper comparar, el SNRT mesurat contra el SUBTITOL (anit):")
print("   tachelhit 27,2 % · Atles central 19,3 % · tarifit 1,6 %")
