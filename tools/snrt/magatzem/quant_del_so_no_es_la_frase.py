"""Quant del so NO es la frase, amb fronteres que si que han vist la frase.

**Per que cal.** El numero que es feia servir fins ahir -- «el 51 % del so no es la frase», amb
0,79 s al davant i 0,97 s al darrere -- el va donar una alineacio que no va rebre mai la frase
(quadern, §48): el vocabulari de l'adaptador `shi` es llati, el text anava en tifinag, i
alineava nomes els separadors de paraula. La §48 va haver de retirar el numero i deixar la
pregunta oberta.

Aquesta es la pregunta, i ara es pot contestar sense model i sense CER: **nomes amb les
fronteres bones**, que ja n'hi ha de dues fonts independents.

    frase    [veu_ini, veu_fi]
    cap      [0, veu_ini]           el que hi ha abans de la frase
    cua      [veu_fi, durada]       el que hi ha despres

Es dona dues vegades: **arran** de la frontera, i amb el **marge de 0,15 s** que fa servir el
retall de debo, que es el que diu quant es llencaria realment.

No toca res: llegeix i compta.

    python quant_del_so_no_es_la_frase.py
"""
import glob
import io
import json
import statistics as st
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
MARGE = 0.15

#: les dues fonts de fronteres bones. Cap fitxer `*_NOMES_SEPARADORS.jsonl`: son les trencades.
FONTS = {
    "MMS_FA (300 M, PC)": sorted(glob.glob(str(MAG / "alineacio_mms_fa_tot_*de*.jsonl"))),
    "MMS-1b-all (4 GB, ECS)": [str(MAG / "alineacio_ecs_v2.jsonl")],
}


def llegeix(camins):
    d = {}
    for c in camins:
        if "NOMES_SEPARADORS" in c or not Path(c).exists():
            continue
        for l in io.open(c, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                x = json.loads(l)
            except ValueError:
                continue          # linia a mitges: l'alineador hi pot estar escrivint
            if x.get("veu_ini") is None or x.get("veu_fi") is None:
                continue
            if not x.get("durada"):
                continue
            d[x["so"]] = x
    return d


def conta(d, marge):
    cap = [x["veu_ini"] - marge for x in d.values()]
    cua = [x["durada"] - x["veu_fi"] - marge for x in d.values()]
    cap = [max(0.0, v) for v in cap]
    cua = [max(0.0, v) for v in cua]
    tot = sum(x["durada"] for x in d.values())
    fora = sum(cap) + sum(cua)
    return {
        "n": len(d),
        "fora_%": 100 * fora / tot if tot else 0,
        "cap_s": st.median(cap) if cap else 0,
        "cua_s": st.median(cua) if cua else 0,
        "amb_cap_%": 100 * sum(1 for v in cap if v > 0.3) / len(cap) if cap else 0,
        "amb_cua_%": 100 * sum(1 for v in cua if v > 0.3) / len(cua) if cua else 0,
        "durada_s": st.median(x["durada"] for x in d.values()) if d else 0,
    }


print("Quant del so no es la frase, segons les fronteres bones\n")
for nom, camins in FONTS.items():
    d = llegeix(camins)
    if not d:
        print(f"{nom}: cap tall encara\n")
        continue
    print(f"{nom} · {len(d)} talls · durada mediana {conta(d, 0)['durada_s']:.2f} s")
    print(f"   {'':<10}{'fora de la frase':>18}{'cap':>9}{'cua':>9}"
          f"{'amb cap >0,3':>14}{'amb cua >0,3':>14}")
    for etiq, m in (("arran", 0.0), (f"marge {MARGE}", MARGE)):
        r = conta(d, m)
        print(f"   {etiq:<10}{r['fora_%']:>17.1f} %{r['cap_s']:>8.2f}s{r['cua_s']:>8.2f}s"
              f"{r['amb_cap_%']:>13.0f} %{r['amb_cua_%']:>13.0f} %")
    print()

#: les dues fonts no miren els mateixos talls -- l'ECS va per ordre i el MMS_FA reparteix per
#: index -- aixi que els dos numeros de dalt no son comparables entre ells. Sobre els talls que
#: tenen totes dues si, i aixi es veu si les dues fonts diuen el mateix o nomes s'hi assembla.
fonts = {nom: llegeix(c) for nom, c in FONTS.items()}
noms = list(fonts)
comu = set(fonts[noms[0]]) & set(fonts[noms[1]])
if comu:
    print(f"Els mateixos {len(comu)} talls, mesurats per les dues fonts\n")
    print(f"   {'':<24}{'fora de la frase':>18}{'cap':>9}{'cua':>9}")
    for nom in noms:
        d = {k: v for k, v in fonts[nom].items() if k in comu}
        r = conta(d, MARGE)
        print(f"   {nom:<24}{r['fora_%']:>17.1f} %{r['cap_s']:>8.2f}s{r['cua_s']:>8.2f}s")
    a, b = (fonts[n] for n in noms)
    di = [abs(a[k]["veu_ini"] - b[k]["veu_ini"]) for k in comu]
    df = [abs(a[k]["veu_fi"] - b[k]["veu_fi"]) for k in comu]
    prop = sum(1 for i, f in zip(di, df) if i <= 0.2 and f <= 0.2)
    print(f"\n   les dues fronteres a <=0,2 s: {100*prop/len(comu):.0f} % dels talls")
    print(f"   desacord median: {st.median(di):.3f} s a l'inici · {st.median(df):.3f} s al final")
    print()
else:
    print("Encara no hi ha talls mesurats per totes dues fonts.\n")

print("Per comparar: el numero retirat deia 51 % fora, 0,79 s de cap (al 84 %) i 0,97 s de")
print("cua (al 95 %), i el va donar una alineacio que alineava els separadors (quadern, §48).")
