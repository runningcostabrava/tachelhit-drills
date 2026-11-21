"""Separar la VARIACIO de l'ESCAPÇAMENT, mecanicament.

A `variants.tsv` hi ha dues coses barrejades:

  - variacio de debo: `nnš` contra `nnk` (la palatalitzacio k->š), `nnḫ` contra `nnġ`,
    `taḍfi` contra `taṭfi`, `wawal` contra `wawar`, `tmdyazt` contra `tmdyast`;
  - escapçaments de l'orella: `ns` per `nns`, `skla` per `tskla`, `tir` per `tirra`.

No cal decidir-ho a ull: un escapçament es un TROS de la forma plena (el seu esquelet hi es a
dins, en ordre i sense res de nou), i una variant no ho es -- te alguna consonant que l'altra no
te al seu lloc. La mateixa consonant canviada es el que volem: aixi surt la llista de canvis
(k->š, ḫ->ġ, ḍ->ṭ, l->r, z->s) comptada, i no opinada.

Surt `variacio.tsv` i el recompte de canvis de consonant.
"""
import io
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")


def es_tros(curt, llarg):
    """El curt es un tros del llarg: hi es tot, en ordre, sense res de nou."""
    i = 0
    for c in llarg:
        if i < len(curt) and curt[i] == c:
            i += 1
    return i == len(curt)


def canvi(a, b):
    """Si a i b son iguals llevat d'UNA consonant al mateix lloc, torna el canvi."""
    if len(a) != len(b):
        return None
    dif = [(x, y) for x, y in zip(a, b) if x != y]
    return dif[0] if len(dif) == 1 else None


files = []
for i, l in enumerate(io.open(MAG / "variants.tsv", encoding="utf-8")):
    if i == 0 or not l.strip():
        continue
    c = l.rstrip("\n").split("\t")
    if len(c) < 4:
        continue
    escrit, formes_txt, tot, ex = c[:4]
    formes = []
    for t in formes_txt.split(" / "):
        t = t.strip()
        if "(" in t and t.endswith(")"):
            nom, n = t[:t.rindex("(")], t[t.rindex("(") + 1:-1]
            if n.isdigit():
                formes.append((nom, int(n)))
    for j in range(len(formes)):
        for k in range(j + 1, len(formes)):
            (fa, na), (fb, nb) = formes[j], formes[k]
            ea, eb = esquelet(fa), esquelet(fb)
            if not ea or not eb or ea == eb:
                continue
            curt, llarg = (ea, eb) if len(ea) <= len(eb) else (eb, ea)
            #: el filtre s'ha de fer contra la paraula ESCRITA, no entre les dues formes: `ns` i
            #: `nn` son tots dos trossos de `nns`, i comparats entre ells semblen un canvi n~s.
            ee = esquelet(escrit)
            tots_dos_trossos = (ee and len(ea) < len(ee) and len(eb) < len(ee)
                                and es_tros(ea, ee) and es_tros(eb, ee))
            mena = ("escapçament" if (es_tros(curt, llarg) or tots_dos_trossos)
                    else "variacio")
            files.append({"escrit": escrit, "a": fa, "na": na, "b": fb, "nb": nb,
                          "mena": mena, "canvi": canvi(ea, eb), "ex": ex})

canvis = Counter()
with io.open(MAG / "variacio.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("escrit\tforma_a\tacords_a\tforma_b\tacords_b\tmena\tcanvi\texemple\n")
    for r in sorted(files, key=lambda r: (r["mena"], -min(r["na"], r["nb"]))):
        c = f"{r['canvi'][0]}>{r['canvi'][1]}" if r["canvi"] else ""
        f.write(f"{r['escrit']}\t{r['a']}\t{r['na']}\t{r['b']}\t{r['nb']}\t{r['mena']}\t{c}\t"
                f"{r['ex']}\n")
        if r["mena"] == "variacio" and r["canvi"]:
            canvis[tuple(sorted(r["canvi"]))] += min(r["na"], r["nb"])

n_var = sum(1 for r in files if r["mena"] == "variacio")
print(f"parelles de formes: {len(files)} · variacio {n_var} · "
      f"escapçament {len(files) - n_var}")

print(f"\n{'escrit':<13}{'forma A':<12}{'forma B':<12}{'canvi':>7}  significat")
for r in sorted([r for r in files if r["mena"] == "variacio" and r["canvi"]],
                key=lambda r: -min(r["na"], r["nb"]))[:22]:
    c = f"{r['canvi'][0]}>{r['canvi'][1]}"
    print(f"{r['escrit'][:12]:<13}{r['a'][:10]+'('+str(r['na'])+')':<12}"
          f"{r['b'][:10]+'('+str(r['nb'])+')':<12}{c:>7}  {r['ex'][:34]}")

print("\nels canvis de consonant, pel pes de la parella mes feble:")
for (x, y), n in canvis.most_common(14):
    print(f"   {x} ~ {y}   {n}")
print(f"\ndesat a {MAG / 'variacio.tsv'}")
