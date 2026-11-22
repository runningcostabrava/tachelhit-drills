"""Passar els talls per una orella de RIFENY, que es la prova de la hipotesi de la nit.

La hipotesi: els deu convidats que la nostra orella no enten no parlen tachelhit. Hi apunten dues
marques fonetiques independents mesurades al seu propi so (k->š i l->r, correlacio +0,58 entre
elles i -0,46 amb l'acord), i cap dels quatre adaptadors de l'MMS no els toca -- entre altres
coses perque l'MMS **no porta `rif`**.

`iukocha/mms-tachebdant-from-tarifit` es un afinament del MATEIX model base que fem servir
(facebook/mms-1b-all) cap al rifeny. Llicencia CC-BY-NC-4.0: recerca si, desplegar no, que es
exactament el marc d'aquest treball (docs/PERMISOS.md). No toca produccio ni cap Space.

**La predicció, escrita abans de mesurar-la:** si aquells convidats parlen una varietat del Rif,
aquesta orella n'ha de treure mes acord que el `shi` (que hi fa 0-2 %), i als dos controls de
tachelhit n'ha de treure menys que el `shi` (que hi fa 35-40 %). Si no passa cap de les dues
coses, la hipotesi cau i cal dir-ho.

Corre a la CPU d'aqui, que evita la cua de GPU de Kaggle. Els talls ja son PCM de 16 kHz mono,
aixi que es llegeixen amb la biblioteca estandard i no cal librosa.

    orella_rifenya.py [limit_de_talls]
"""
import io
import json
import os
import sys
import time
import wave
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCTC, AutoProcessor

MODEL = "iukocha/mms-tachebdant-from-tarifit"
DADES = Path(r"E:/tamazight/_magatzem/prova_adaptadors/dades")
DESTI = Path(r"E:/tamazight/_magatzem/prova_adaptadors/sortida/sentit_rif.jsonl")
SR = 16000
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

files = json.load(io.open(DADES / "index.json", encoding="utf-8"))
if LIMIT:
    files = files[:LIMIT]
print(f"{len(files)} talls", flush=True)

proc = AutoProcessor.from_pretrained(MODEL)
model = AutoModelForCTC.from_pretrained(MODEL)
model.eval()
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
print(f"model carregat · {torch.get_num_threads()} fils de CPU", flush=True)


def llegeix(p):
    with wave.open(str(p)) as w:
        n, sr = w.getnframes(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a, sr


DESTI.parent.mkdir(parents=True, exist_ok=True)
t0, fets = time.time(), 0
with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for x in files:
        try:
            w, sr = llegeix(DADES / x["fitxer"])
        except Exception as e:
            f.write(json.dumps({"id": x["id"], "error": type(e).__name__}) + "\n")
            continue
        if w.size < SR // 10 or sr != SR:
            f.write(json.dumps({"id": x["id"], "sentit": "", "conf": None,
                                "paraules": []}, ensure_ascii=False) + "\n")
            continue
        ent = proc(w, sampling_rate=SR, return_tensors="pt")
        with torch.no_grad():
            lg = model(**ent).logits[0].float()
        millor = torch.softmax(lg, -1).max(-1).values.numpy()
        ids = lg.argmax(-1).numpy()
        try:
            d = proc.tokenizer.decode(ids, output_word_offsets=True)
            text, trossos = d.text, d.word_offsets
        except Exception:
            text, trossos = proc.tokenizer.decode(ids), []
        paraules = []
        for t in trossos:
            a, b = int(t["start_offset"]), int(t["end_offset"])
            if b > a:
                paraules.append({"p": t["word"], "c": round(float(millor[a:b].mean()), 4)})
        conf = round(float(np.mean([p["c"] for p in paraules])), 4) if paraules else None
        f.write(json.dumps({"id": x["id"], "sentit": text.strip(), "conf": conf,
                            "paraules": paraules}, ensure_ascii=False) + "\n")
        fets += 1
        if fets % 25 == 0:
            f.flush()
            fet = time.time() - t0
            print(f"{fets}/{len(files)} · {fet:.0f}s · queden "
                  f"{fet/fets*(len(files)-fets)/60:.0f} min", flush=True)
print(f"fet {fets} de {len(files)} en {(time.time()-t0)/60:.0f} min · {DESTI}", flush=True)
