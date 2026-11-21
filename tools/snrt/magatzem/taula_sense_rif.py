"""La taula norma<->parla, refeta sense el tarifit, i que canvia.

Un peo va preguntar si la taula estandard<->dialecte estava contaminada. Comprovat: **si**.
Les 74.761 parelles alineades venen de 25 capitols, i **11 son del Rif**: 27.180 parelles, el
**36,4 %**. El tarifit es una altra llengua, i les seves marques son justament les que la
taula hauria de capturar com a «parla» (k->s, l->r), aixi que no es un detall.

Aqui es refa la taula nomes amb el tachelhit i l'Atles central, i es compara amb la vella:
quines correspondencies eren NOMES del Rif, quines canvien de compte, i quines s'aguanten.

No toca la taula vella: escriu `estandard_dialecte_sense_rif.jsonl` i l'informe.

    taula_sense_rif.py
"""
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
MIN_VEGADES = 5   #: el mateix llindar que la taula vella

vp = json.load(io.open(MAG / "varietat_produccio.json", encoding="utf-8"))
don = json.load(io.open(MAG / "don_son_els_nous.json", encoding="utf-8"))
RIF = ({k for k, x in vp.items() if x.get("varietat") == "tarifit"}
       | {k for k, x in don.items() if x.get("diu") == "rif"})

files = [json.loads(l) for l in io.open(MAG / "parelles_alineades.jsonl", encoding="utf-8")
         if l.strip()]
nets = [x for x in files if x["capitol"] not in RIF]
print(f"{len(files)} parelles · {len(nets)} sense el Rif "
      f"({100*(len(files)-len(nets))/len(files):.1f} % fora)")
print(f"capítols: {len({x['capitol'] for x in files})} -> "
      f"{len({x['capitol'] for x in nets})}\n")


def taula(fs):
    g = defaultdict(lambda: {"n": 0, "cap": set(), "ex": []})
    for x in fs:
        if x["norma"] == x["parla"]:
            continue
        v = g[(x["norma"], x["parla"])]
        v["n"] += 1
        v["cap"].add(x["capitol"])
        if len(v["ex"]) < 2 and x.get("catala"):
            v["ex"].append(x["catala"][:56])
    return {k: v for k, v in g.items() if v["n"] >= MIN_VEGADES}


vella, nova = taula(files), taula(nets)
print(f"correspondències: {len(vella)} -> {len(nova)}")

nomes_rif = sorted(set(vella) - set(nova), key=lambda k: -vella[k]["n"])
print(f"\n**{len(nomes_rif)} correspondències desapareixen en treure el Rif** "
      f"({100*len(nomes_rif)/len(vella):.0f} % de la taula)")
for k in nomes_rif[:12]:
    print(f"   «{k[0]}» -> «{k[1]}»  {vella[k]['n']:4d} cops, "
          f"{len(vella[k]['cap'])} capítols")

print("\nles que es queden, com els canvia el compte:")
quedan = sorted(nova, key=lambda k: -nova[k]["n"])
for k in quedan[:10]:
    print(f"   «{k[0]}» -> «{k[1]}»  {vella[k]['n']:4d} -> {nova[k]['n']:4d} cops")

with io.open(MAG / "estandard_dialecte_sense_rif.jsonl", "w", encoding="utf-8",
             newline="\n") as f:
    for k in quedan:
        v = nova[k]
        f.write(json.dumps({"norma": k[0], "parla": k[1], "vegades": v["n"],
                            "capitols": len(v["cap"]), "exemples": v["ex"]},
                           ensure_ascii=False) + "\n")
print(f"\nescrit estandard_dialecte_sense_rif.jsonl ({len(quedan)} files)")
