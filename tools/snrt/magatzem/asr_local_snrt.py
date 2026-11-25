"""ASR (mms-1b-all + adaptador shi_zouhir_b) sobre els talls del SNRT, en CPU i a casa (#763).

El mateix que kaggle/veu-ar-cadena-asr.py, pero sense quota ni sessio que s'esborri: escriu una fila
per tall a mesura que avanca i, si es torna a engegar, salta els talls que ja te. Primer test (per
mesurar la triangulacio), despres dev i train (per fabricar el subconjunt filtrat).

    E:/tamazight/venv_asr/Scripts/python.exe -X utf8 tools/snrt/magatzem/asr_local_snrt.py [test dev train]
"""
import io
import json
import os
import sys
import time

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForCTC, AutoProcessor

DADES = "E:/tamazight/_magatzem/veu_ar"
ADAPTADOR = "E:/tamazight/_escoltats/zouhir/kernels/adaptador_shi_zouhir_b.pt"
SORTIDA = "E:/tamazight/_magatzem/tirades/triangulacio/asr_snrt.jsonl"
PARTS = sys.argv[1:] or ["test", "dev", "train"]
PREC = "int8"

torch.set_num_threads(os.cpu_count() or 8)
os.makedirs(os.path.dirname(SORTIDA), exist_ok=True)
fets = set()
if os.path.exists(SORTIDA):
    for l in io.open(SORTIDA, encoding="utf-8"):
        if l.strip():
            fets.add(json.loads(l)["so"])

proc = AutoProcessor.from_pretrained("facebook/mms-1b-all")
proc.tokenizer.set_target_lang("shi")
# int8 dynamic: fp32 (~4 GB) got the job reaped for low memory on this 18 GB machine, and bf16 is emulated
# on this CPU (55 cuts in 30 min). Rows carry "prec" so the analysis can check the switch moves nothing.
model = AutoModelForCTC.from_pretrained("facebook/mms-1b-all", low_cpu_mem_usage=True)
model.load_adapter("shi")
ad = torch.load(ADAPTADOR, map_location="cpu")
coneguts = dict(model.named_parameters())
assert all(k in coneguts for k in ad), "claus de l'adaptador que el model no te"
model.load_state_dict(ad, strict=False)
del ad, coneguts
model = torch.ao.quantization.quantize_dynamic(model.eval(), {torch.nn.Linear}, dtype=torch.qint8)


def so(cami):
    d, sr = sf.read(cami, dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d[: 16000 * 30]


fora = io.open(SORTIDA, "a", encoding="utf-8")
T0 = time.time()
for part in PARTS:
    files = [json.loads(l) for l in io.open(f"{DADES}/{part}.jsonl", encoding="utf-8") if l.strip()]
    pendents = [x for x in files if os.path.basename(x["so"]) not in fets]
    print(f"{part}: {len(files)} files, {len(pendents)} pendents", flush=True)
    for i, x in enumerate(pendents, 1):
        nom = os.path.basename(x["so"])
        ent = proc(so(f"{DADES}/so/{nom}"), sampling_rate=16000, return_tensors="pt")
        with torch.inference_mode():
            lg = model(ent.input_values).logits
        txt = proc.batch_decode(lg.argmax(-1))[0]
        fora.write(json.dumps({"part": part, "so": nom, "asr": txt, "prec": PREC}, ensure_ascii=False) + "\n")
        fora.flush()
        if i % 100 == 0:
            print(f"   {part} {i}/{len(pendents)} · {time.time() - T0:.0f} s", flush=True)
    print(f"{part} fet · {time.time() - T0:.0f} s", flush=True)
fora.close()
print("fet", flush=True)
