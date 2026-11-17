# -*- coding: utf-8 -*-
"""Ablació de la v3 (#494, 17-11-2026): el MATEIX dataset v3 (train.json, test200.json, mostra60.json) amb un sol canvi:
fora del train les parelles amb origen «auditors 16-11» (les 302 MTNRA/CV confirmades que prepara_parelles_v3.py afegeix
al pas v3.2). Res més canvia: mateix test-dins, mateixa mostra, mateix ordre de la resta del train.
ÚS: prepara_ablacio.py <dataset_v3> <carpeta_sortida>"""
import collections, io, json, os, shutil, sys

V3, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
train = json.load(io.open(os.path.join(V3, "train.json"), encoding="utf-8"))
fora = [p for p in train if p.get("origen") == "auditors 16-11"]
dins = [p for p in train if p.get("origen") != "auditors 16-11"]
print(f"train v3: {len(train)} · fora (auditors 16-11): {len(fora)} · queden: {len(dins)}")
print("fora per font:", dict(collections.Counter(p["font"] for p in fora)))
json.dump(dins, io.open(os.path.join(OUT, "train.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for nom in ("test200.json", "mostra60.json"):
    shutil.copy(os.path.join(V3, nom), os.path.join(OUT, nom))
resum = json.load(io.open(os.path.join(V3, "resum.json"), encoding="utf-8"))
resum["ablacio"] = {"que": "v3 sense les parelles d'origen «auditors 16-11»", "fora": len(fora), "train": len(dins),
                    "per_font_train": dict(collections.Counter(p["font"] for p in dins).most_common())}
json.dump(resum, io.open(os.path.join(OUT, "resum.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
# el mateix test i la mateixa mostra, byte a byte
for nom in ("test200.json", "mostra60.json"):
    assert open(os.path.join(V3, nom), "rb").read() == open(os.path.join(OUT, nom), "rb").read()
print("test200 i mostra60 idèntics a la v3; resum.versio =", resum.get("versio"))
