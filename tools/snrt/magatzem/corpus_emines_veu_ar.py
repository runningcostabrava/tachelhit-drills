"""EMINES -> files d'ENTRENAMENT per a veu->arab (via 3). Res d'EMINES va a dev ni a test.

Per que nomes train: la seva particio train/test comparteix els 60 videos (tots dos en tenen de
cada video), tres parells de videos son el mateix video dues vegades (37/38, 39/40, 41/42), i el
32 % de les frases del parlant spk_010 del TutlAit hi son identiques (mateix material de serie).
Els nostres tests (test_snrt, test_tutlait) queden congelats; d'EMINES es treu tota fila el text
normalitzat de la qual surti a dev o a un test nostre.
"""
import io, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalitza_arab import norma

DUPLICATS = {"video38", "video40", "video42"}
MINIM_S = 0.5
em = [json.loads(l) for l in io.open(r"E:/tamazight/_magatzem/emines/text.jsonl", encoding="utf-8")]
vetat = set()
for nom in ["dev", "test_snrt", "test_tutlait"]:
    for l in io.open(rf"E:/tamazight/_magatzem/veu_ar_combinat_baba/{nom}.jsonl", encoding="utf-8"):
        vetat.add(norma(json.loads(l)["ar"]))
fora = Counter(); bo = []
for x in em:
    if x["source"] in DUPLICATS: fora["video duplicat"] += 1; continue
    if x["duration"] < MINIM_S: fora["< 0,5 s"] += 1; continue
    if not norma(x["ar"]).strip(): fora["sense text"] += 1; continue
    if norma(x["ar"]) in vetat: fora["text a dev/test nostre"] += 1; continue
    bo.append({"so": f"emines:{x['fitxer']}:{x['idx']}", "font": "emines", "ar": x["ar"].strip(),
               "grup": f"EMINES · {x['source']}", "varietat": None, "durada": x["duration"]})
io.open(r"E:/tamazight/_magatzem/emines/train_emines.jsonl", "w", encoding="utf-8", newline="\n").write(
    "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in bo))
print("files:", len(bo), "· hores:", round(sum(x["durada"] for x in bo) / 3600, 2), "· fora:", dict(fora))
