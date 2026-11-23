"""La segona tirada de la via 3: el corpus combinat MES Baba Ali, i res mes canviat.

**Per que una tirada a part.** La primera (SNRT + TutlAit) dona el numero de referencia. Aquesta
afegeix nomes Baba Ali a l'entrenament; dev i tests son **els mateixos fitxers, copiats sense
tocar**. La diferencia als tests fixos diu quant aporta el material de serie de la SNRT abans de
collir-ne setanta hores (pla dels models, pas 2b).

**La fuita per text** es torna a tancar: tota repl ica de Baba Ali amb un arab que, normalitzat,
surti en algun dev o test, fora. Es la mateixa `norma()` que el corpus combinat.

    python corpus_veu_arab_amb_baba.py
"""
import io
import json
import shutil
import sys
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalitza_arab import norma  # noqa: E402  (la mateixa normalitzacio, no una copia)

V1 = MAG / "veu_ar_combinat"
BABA = MAG / "baba_veu_ar" / "train.jsonl"
FORA = MAG / "veu_ar_combinat_baba"


def llegeix(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]


FORA.mkdir(parents=True, exist_ok=True)
for nom in ("dev", "test_snrt", "test_tutlait"):
    shutil.copy2(V1 / f"{nom}.jsonl", FORA / f"{nom}.jsonl")

jutges = {norma(x["ar"]) for nom in ("dev", "test_snrt", "test_tutlait")
          for x in llegeix(V1 / f"{nom}.jsonl")}
baba = llegeix(BABA)
nets = [x for x in baba if norma(x["ar"]) not in jutges]
train = llegeix(V1 / "train.jsonl") + nets

with io.open(FORA / "train.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for x in train:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")

h = lambda v: sum(x["durada"] for x in v) / 3600  # noqa: E731
informe = {"baba_ali": len(baba), "baba_ali_tret_per_fuita": len(baba) - len(nets),
           "train_files": len(train), "train_hores": round(h(train), 2),
           "baba_ali_hores": round(h(nets), 2)}
json.dump(informe, io.open(FORA / "informe.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(informe, indent=1))
print(f"-> {FORA}  (dev i tests copiats sense tocar de {V1.name})")
