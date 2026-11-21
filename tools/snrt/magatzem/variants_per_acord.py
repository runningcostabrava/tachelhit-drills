"""La variacio treta de l'ACORD, no del desacord.

La taula de grau B no va donar res: busca la variacio alla on l'ull i l'orella DISCREPEN, que es
el lloc mes dèbil, i s'omple d'artefactes d'alineacio (les vuit parelles que sobrevivien eren
totes la frase *tutlayt tamazight* desplaçada un lloc).

Hi ha una manera millor i ha sortit mirant l'index: **dues formes sentides diferents que casen
totes dues amb la MATEIXA paraula escrita**, i cada una acordada diverses vegades. Com *nnḫ*
(56 vegades) i *nnġ* (128), que van les dues a ⵏⵏⵖ «nostre». Aixo no es desacord: son dos
acords, i la diferencia entre ells es la variacio.

Es demana que cada forma estigui acordada 2+ vegades (si no, pot ser un error de l'orella que
per casualitat casa) i que les formes es diferencien de debo en consonants, no nomes en vocals,
perque el subtitol no escriu les vocals neutres i aixo sol no diria res.

Surt `variants.tsv`.
"""
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MIN_ACORD = 2

per_escrit = defaultdict(list)
for i, l in enumerate(io.open(MAG / "index_paraules.tsv", encoding="utf-8")):
    if i == 0 or not l.strip():
        continue
    c = l.rstrip("\n").split("\t")
    if len(c) < 7:
        continue
    sentit, escrit, veg, acord, boques, conf, ex = c[:7]
    if not escrit or int(acord) < MIN_ACORD:
        continue
    per_escrit[escrit].append({"sentit": sentit, "veg": int(veg), "acord": int(acord),
                               "boques": int(boques), "conf": float(conf), "ex": ex})

grups = []
for escrit, formes in per_escrit.items():
    if len(formes) < 2:
        continue
    #: han de diferir en CONSONANTS: el subtitol no escriu les vocals neutres i una
    #: diferencia nomes de vocals no diria res de la parla
    esquelets = {esquelet(f["sentit"]) for f in formes}
    if len(esquelets) < 2:
        continue
    formes.sort(key=lambda f: -f["acord"])
    grups.append((sum(f["acord"] for f in formes), escrit, formes))

grups.sort(reverse=True)
with io.open(MAG / "variants.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("escrit\tformes_sentides\tacords\texemple\n")
    for tot, escrit, formes in grups:
        f.write(f"{escrit}\t" + " / ".join(f"{x['sentit']}({x['acord']})" for x in formes)
                + f"\t{tot}\t{formes[0]['ex']}\n")

print(f"paraules escrites amb dues formes sentides o mes, cada una acordada {MIN_ACORD}+ "
      f"vegades i diferents en consonants: {len(grups)}")
print(f"\n{'escrit':<14}{'formes sentides (acords)':<44}{'total':>6}")
for tot, escrit, formes in grups[:28]:
    quines = " / ".join(f"{x['sentit']}({x['acord']})" for x in formes)
    print(f"{escrit[:13]:<14}{quines[:42]:<44}{tot:6d}")
print(f"\ndesat a {MAG / 'variants.tsv'}")
