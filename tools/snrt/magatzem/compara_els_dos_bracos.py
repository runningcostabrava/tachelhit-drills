"""Els dos braços de la ronda, cara a cara: llindar 0,35 contra 0,20.

Els dos surten del MATEIX M0, amb la mateixa recepta, la mateixa llavor i les mateixes proves.
L'unica diferencia es quin corpus del SNRT entra al train:

    0,35 -> 1.678 talls (el que ja ha corregut)
    0,20 ->   717 talls, etiquetes millors (CER ric de l'etiqueta 0,151 -> 0,127 a les proves
              amb veritat humana, §20.4)

La pregunta no es quin dels dos baixa mes respecte de M0 -- aixo ja ho diu cada ronda pel seu
compte -- sino **si la diferencia entre ells es distingible de zero**. Es mesura sobre les
MATEIXES frases: per a cada frase de cada prova, els errors del model A i els del model B, i es
remostreja la diferencia.

Si l'interval passa per zero, estrenyer el llindar no canvia res que es pugui mesurar amb aquest
material, i val mes quedar-se amb el corpus gran (mes material per a les rondes que vinguin). Si
el de 0,20 guanya, la §20.4 tenia rao i la ronda 3 ha d'anar per aqui.

    compara_els_dos_bracos.py [sortida_A] [sortida_B]
"""
import io
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

A = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:/tamazight/_magatzem/ronda/sortida")
B = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"E:/tamazight/_magatzem/ronda_020/sortida")
VEGADES = 2000


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


def carrega(carpeta):
    """Per prova i frase: els errors del model de DESPRES (el que la ronda ha entrenat)."""
    p = next(iter(carpeta.glob("*_sortides.json")), None)
    if not p:
        raise SystemExit(f"no hi ha cap *_sortides.json a {carpeta}")
    out = defaultdict(dict)
    for x in json.load(io.open(p, encoding="utf-8")):
        if (x.get("model") or "").startswith("abans"):
            continue
        clau = (x.get("video"), str(x.get("de")), x.get("or"))
        out[x["prova"]][clau] = (lev(x.get("or") or "", x.get("dit") or ""),
                                 len(x.get("or") or ""))
    return out


a, b = carrega(A), carrega(B)
print(f"A = {A.parent.name} (llindar 0,35)   ·   B = {B.parent.name} (llindar 0,20)\n")
print(f"{'prova':<16}{'frases':>7}{'CER A':>9}{'CER B':>9}{'B − A':>9}{'interval 95 %':>22}  diu")
rnd = random.Random(20261120)
for prova in sorted(set(a) | set(b)):
    totes = [(a[prova][k][0], b[prova][k][0], a[prova][k][1])
             for k in a.get(prova, {}) if k in b.get(prova, {})]
    if len(totes) < 30:
        print(f"{prova:<16}{len(totes):7d}   (massa poques frases comparables)")
        continue

    def cer(mostra, quin):
        return sum(x[quin] for x in mostra) / max(1, sum(x[2] for x in mostra))

    ca, cb = cer(totes, 0), cer(totes, 1)
    reps = sorted(
        (lambda m: cer(m, 1) - cer(m, 0))([totes[rnd.randrange(len(totes))] for _ in totes])
        for _ in range(VEGADES))
    baix, alt = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES)]
    diu = ("B (0,20) GUANYA" if alt < 0 else
           "A (0,35) guanya" if baix > 0 else "no es pot dir (passa per zero)")
    print(f"{prova:<16}{len(totes):7d}{ca:9.4f}{cb:9.4f}{cb-ca:+9.4f}"
          f"   [{baix:+.4f}, {alt:+.4f}]  {diu}")
print(f"\n(remostreig de {VEGADES} vegades sobre les mateixes frases; «B − A» negatiu vol dir "
      "que el braç estret llegeix millor)")
