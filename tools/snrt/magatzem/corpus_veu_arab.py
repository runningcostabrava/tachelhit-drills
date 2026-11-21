"""El corpus de VEU -> ARAB: el so i l'arab de la pantalla, sense text amazic pel mig.

La via 3. El que la fa valuosa no es el que te, sino el que **no** necessita: no li cal
tifinag. Aixo vol dir que, a mes de les 48 h de Tadfi, hi caben les **67 h de programes amb
subtitol nomes en arab** que per a l'orella no servien de res.

Es parteix **pels mateixos capitols** que el corpus de text (zgh_ar), perque els dos
experiments es puguin comparar sobre les mateixes frases.

Portes: ha d'haver-hi so al disc, arab de la pantalla, no credits, i una durada raonable. **No
es demana tifinag**: justament la gracia es que no cal.

Surt una carpeta amb els wav i un manifest, a punt per pujar a Kaggle.

    corpus_veu_arab.py [hores_maximes]
"""
import io
import json
import os
import shutil
import sys
import wave
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
ZGH_AR = Path(r"E:/tamazight/_magatzem/zgh_ar")
FORA = Path(r"E:/tamazight/_magatzem/veu_ar")
MAX_H = float(sys.argv[1]) if len(sys.argv) > 1 else 99.0

#: la mateixa particio per capitols que el corpus de text
parts = {}
for nom in ("train", "dev", "test"):
    caps = set()
    for l in io.open(ZGH_AR / f"{nom}.jsonl", encoding="utf-8"):
        if l.strip():
            caps.add(json.loads(l)["capitol"])
    parts[nom] = caps
print({k: len(v) for k, v in parts.items()}, "capítols")

files = {"train": [], "dev": [], "test": []}
fora_porta = {"sense so": 0, "sense àrab": 0, "crèdits": 0, "durada": 0}
for d in sorted(os.listdir(ARREL)):
    p = ARREL / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0:
        continue
    quin = next((k for k, v in parts.items() if d in v), None)
    if quin is None:
        continue
    #: el corpus de text ja exclou el Rif, aixi que si un capitol no hi es tampoc hi ha de ser
    #: aqui; aquesta linia hi es per si algu refa nomes aquest fitxer
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        ar = (x.get("arab") or "").strip()
        if x.get("credits"):
            fora_porta["crèdits"] += 1
            continue
        if not ar or len(ar.split()) < 2:
            fora_porta["sense àrab"] += 1
            continue
        t = x.get("tall")
        wav = (ARREL / d / t) if t else None
        if not wav or not wav.exists():
            fora_porta["sense so"] += 1
            continue
        dur = float(x.get("durada") or 0)
        if not (1.0 <= dur <= 20.0):
            fora_porta["durada"] += 1
            continue
        files[quin].append({"wav": str(wav), "ar": ar, "capitol": d,
                            "zgh": (x.get("tifinag") or "").strip(), "durada": dur})

for k, v in fora_porta.items():
    print(f"   fora per {k}: {v}")
for k, v in files.items():
    h = sum(x["durada"] for x in v) / 3600
    print(f"{k}: {len(v)} talls · {h:.1f} h")

#: retallar el train si demana massa
h = sum(x["durada"] for x in files["train"]) / 3600
if h > MAX_H:
    files["train"].sort(key=lambda x: -len(x["ar"]))
    acc, retall = 0.0, []
    for x in files["train"]:
        if acc / 3600 >= MAX_H:
            break
        retall.append(x)
        acc += x["durada"]
    files["train"] = retall
    print(f"train retallat a {acc/3600:.1f} h")

if FORA.exists():
    shutil.rmtree(FORA)
(FORA / "so").mkdir(parents=True)
n = 0
for quin, v in files.items():
    with io.open(FORA / f"{quin}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for x in v:
            nom = f"{x['capitol']}_{os.path.basename(x['wav'])}"
            shutil.copy2(x["wav"], FORA / "so" / nom)
            n += 1
            f.write(json.dumps({"so": nom, "ar": x["ar"], "zgh": x["zgh"],
                                "capitol": x["capitol"], "durada": x["durada"]},
                               ensure_ascii=False) + "\n")
mida = sum(f.stat().st_size for f in (FORA / "so").glob("*.wav")) / 2 ** 30
print(f"\n{n} fitxers de so copiats · {mida:.2f} GB a {FORA}")
