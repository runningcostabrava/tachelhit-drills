# TRIANGULACIO (#763), pas 3: dos trains per a la via 3 (veu -> arab) que nomes es diferencien en QUINES files de la
# SNRT es treuen. Filtrat: el terc de la SNRT on l'ASR menys s'assembla al tifinag de pantalla. Control: el mateix
# nombre de files de la SNRT triades a l'atzar (llavor 1114). Dev i tests, intactes. Si el filtrat guanya el control
# als tests congelats, l'acord ASR<->pantalla serveix per netejar el train; si empaten, era soroll.
import io, json, os, random, shutil
from collections import Counter

D = "E:/tamazight/_magatzem/veu_ar"
BASE = "E:/tamazight/_magatzem/veu_ar_combinat"
OUT = "E:/tamazight/_magatzem/tirades/triangulacio/filtre"
codi = open("E:/tamazight/_magatzem/tirades/triangulacio/cer_kaggle_traindev.txt").read()
fs = []
for part in ("train", "dev"):
    for l in io.open(f"{D}/{part}.jsonl", encoding="utf-8"):
        if l.strip():
            x = json.loads(l); fs.append((part, os.path.basename(x["so"])))
fs.sort()
assert len(fs) == len(codi) == 7519 and sum(map(ord, codi)) == 830524
BIN = {so: k for (part, so), k in zip(fs, codi)}

train = [json.loads(l) for l in io.open(f"{BASE}/train.jsonl", encoding="utf-8") if l.strip()]
snrt = [x for x in train if x["font"] == "snrt"]
sense = [x for x in snrt if x["so"] not in BIN]
assert not sense, f"{len(sense)} files de la SNRT sense CER"
amb = [x for x in snrt if BIN[x["so"]] != "x"]
N = len(snrt) // 3
rng = random.Random(1114)
ordre = sorted(amb, key=lambda x: (BIN[x["so"]], rng.random()), reverse=True)
fora_f = {x["so"] for x in ordre[:N]}
# el control treu el mateix nombre de files de CADA durada que el filtrat, perque la durada no expliqui la diferencia
per_durada = {}
for x in amb:
    per_durada.setdefault(x.get("durada"), []).append(x)
ra, fora_a = random.Random(1114), set()
for dur, n in Counter(x.get("durada") for x in ordre[:N]).items():
    fora_a |= {x["so"] for x in ra.sample(per_durada[dur], n)}
assert len(fora_a) == N
print(f"train {len(train)} · snrt {len(snrt)} · amb CER {len(amb)} · es treuen {N}")
print("pitjor bin que es queda al filtrat:", BIN[ordre[N]["so"]], "· bins trets:", dict(sorted(Counter(BIN[s] for s in fora_f).items())))
print("solapament filtrat/atzar:", len(fora_f & fora_a))
for nom, fora in (("filtrat", fora_f), ("atzar", fora_a)):
    d = f"{OUT}/{nom}"
    os.makedirs(d, exist_ok=True)
    with io.open(f"{d}/train.jsonl", "w", encoding="utf-8") as f:
        for x in train:
            if x["so"] not in fora:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    for g in ("dev.jsonl", "test_snrt.jsonl", "test_tutlait.jsonl"):
        shutil.copy(f"{BASE}/{g}", f"{d}/{g}")
    hores = sum(x.get("durada") or 0 for x in train if x["so"] not in fora) / 3600
    print(f"{nom}: train {len(train) - len(fora)} files · {hores:.1f} h")
