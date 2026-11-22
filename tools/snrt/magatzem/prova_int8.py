"""Quantitzar MMS-1b a int8: va el doble de rapid i dona les mateixes fronteres?

Dues dreceres ja han fallat (energia, §46; MMS_FA, 5 % dins de 0,2 s) i totes dues fallaven
perque feien una feina DIFERENT. La quantitzacio dinamica no: es **el mateix model**, amb els
pesos de les capes lineals a int8. A CPU sol donar 2-3x. Si les fronteres no es mouen, les
26 h passen a ~10.

Es mesuren les dues coses alhora -- velocitat i acord -- sobre els mateixos talls, amb el
model normal i el quantitzat, a la mateixa maquina i la mateixa estona.
"""
import io
import json
import statistics as s
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, Wav2Vec2ForCTC

ALI = Path(r"E:/tamazight/_magatzem/alineacio_tot.jsonl")
ARREL = Path(r"E:/tamazight/talls_ecs")
QUANTS = 25

torch.set_num_threads(4)

ali = {}
for l in io.open(ALI, encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except Exception:
        continue
    if x.get("veu_ini") is not None:
        ali[x["so"]] = x

tria = []
for nom, a in ali.items():
    w = ARREL / a["capitol"] / "talls" / nom
    if w.exists():
        tria.append((nom, a, w))
    if len(tria) >= QUANTS:
        break
print(f"{len(tria)} talls per provar")

print("carregant MMS-1b…", flush=True)
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all", target_lang="shi")
mod = Wav2Vec2ForCTC.from_pretrained("facebook/mms-1b-all", target_lang="shi",
                                     ignore_mismatched_sizes=True)
mod.eval()


def emissions(m, x):
    iv = proc(x, sampling_rate=16000, return_tensors="pt")
    with torch.inference_mode():
        return torch.log_softmax(m(**iv).logits, dim=-1)[0]


def fronteres(em, durada):
    """Primer i ultim fotograma on el blanc NO guanya: la mateixa regla que l'ECS."""
    millor = em.argmax(dim=-1)
    viu = (millor != 0).nonzero().flatten()
    if len(viu) == 0:
        return None
    r = durada / em.shape[0]
    return float(viu[0]) * r, float(viu[-1] + 1) * r


res = {}
for etiqueta, m in (("normal", mod), ("int8", None)):
    if etiqueta == "int8":
        print("quantitzant…", flush=True)
        t0 = time.time()
        m = torch.quantization.quantize_dynamic(mod, {torch.nn.Linear}, dtype=torch.qint8)
        print(f"   quantitzat en {time.time()-t0:.0f} s", flush=True)
    fr, temps = {}, []
    for nom, a, w in tria:
        x, sr = sf.read(str(w), dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        t1 = time.time()
        em = emissions(m, x)
        temps.append(time.time() - t1)
        f = fronteres(em, len(x) / sr)
        if f:
            fr[nom] = f
    res[etiqueta] = (fr, s.mean(temps))
    print(f"   {etiqueta}: {s.mean(temps):.2f} s per tall · {len(fr)} fronteres", flush=True)

a, b = res["normal"][0], res["int8"][0]
comuns = sorted(set(a) & set(b))
dini = [b[k][0] - a[k][0] for k in comuns]
dfi = [b[k][1] - a[k][1] for k in comuns]
print(f"\n   {len(comuns)} talls comparables")
print(f"   velocitat: {res['normal'][1]:.2f} s -> {res['int8'][1]:.2f} s "
      f"({res['normal'][1]/max(res['int8'][1],1e-9):.2f}x)")
print(f"\n   {'':<10}{'mediana':>9}{'|error| mitjà':>15}{'dins 0,1 s':>12}{'dins 0,05 s':>13}")
for nom, d in (("inici", dini), ("final", dfi)):
    print(f"   {nom:<10}{s.median(d):>9.3f}{s.mean([abs(v) for v in d]):>15.3f}"
          f"{100*sum(1 for v in d if abs(v)<=0.1)/len(d):>11.0f} %"
          f"{100*sum(1 for v in d if abs(v)<=0.05)/len(d):>12.0f} %")
