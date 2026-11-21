"""Una TERCERA orella, de base completament diferent: Whisper afinat en rifeny.

La prova «les dues orelles coincideixen entre elles i no amb el subtitol» (0,4 % contra 67,6 %)
te una objeccio justa: el model rifeny es un afinament del MATEIX `facebook/mms-1b-all` que fem
servir, de manera que comparteixen la representacio acustica i part d'aquell 67,6 % es parentiu.

`maghreb-ai-research/whisper-small-tarifit` no comparteix res: arquitectura diferent
(codificador-decodificador amb atencio, no CTC), base diferent, entrenament diferent. Si TAMBE
sent el mateix que les altres dues i tampoc no casa amb el subtitol, el parentiu deixa de ser una
objeccio.

Nota tecnica: aquell diposit no porta `preprocessor_config.json`, de manera que l'extractor de
caracteristiques es construeix amb els parametres estandard del Whisper (80 bandes mel, 16 kHz).
Si el model fos de la generacio de 128 bandes, es diu i es prova amb 128.

    orella_whisper.py [limit_de_talls]
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

MODEL = "maghreb-ai-research/whisper-small-tarifit"
DADES = Path(r"E:/tamazight/_magatzem/prova_adaptadors/dades")
DESTI = Path(r"E:/tamazight/_magatzem/prova_adaptadors/sortida/sentit_whisper.jsonl")
SR = 16000
#: `limit` sol agafaria nomes els primers episodis (l'index va per episodi), de manera que hi ha
#: un pas per repartir la mostra entre tots: orella_whisper.py <limit> <pas>
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
PAS = int(sys.argv[2]) if len(sys.argv) > 2 else 1

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

from transformers import (AutoTokenizer, WhisperFeatureExtractor,  # noqa: E402
                          WhisperForConditionalGeneration)

files = json.load(io.open(DADES / "index.json", encoding="utf-8"))
if PAS > 1:
    files = files[::PAS]
if LIMIT:
    files = files[:LIMIT]
print(f"{len(files)} talls", flush=True)

model = WhisperForConditionalGeneration.from_pretrained(MODEL)
model.eval()
tok = AutoTokenizer.from_pretrained(MODEL)
bandes = getattr(model.config, "num_mel_bins", 80)
fe = WhisperFeatureExtractor(feature_size=bandes, sampling_rate=SR)
#: el `generation_config.json` d'aquest diposit posa la llengua a None i el model es posa a
#: endevinar-la: surt kannada i devanagari. El `config.json` SI que la porta
#: (`forced_decoder_ids` amb el token 50265, que es el del francès: l'afinament va fer servir la
#: casella del francès per al rifeny, que es un truc habitual). S'agafa d'alla.
FORÇATS = getattr(model.config, "forced_decoder_ids", None) or [[1, 50265], [2, 50359]]
print("descodificador forçat a:", FORÇATS, flush=True)
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
print(f"model carregat · {bandes} bandes mel · {torch.get_num_threads()} fils", flush=True)


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
            f.write(json.dumps({"id": x["id"], "sentit": ""}, ensure_ascii=False) + "\n")
            continue
        ent = fe(w, sampling_rate=SR, return_tensors="pt")
        with torch.no_grad():
            ids = model.generate(ent.input_features, max_new_tokens=110,
                                 forced_decoder_ids=FORÇATS)
        text = tok.batch_decode(ids, skip_special_tokens=True)[0]
        f.write(json.dumps({"id": x["id"], "sentit": text.strip()},
                           ensure_ascii=False) + "\n")
        fets += 1
        if fets % 20 == 0:
            f.flush()
            fet = time.time() - t0
            print(f"{fets}/{len(files)} · {fet:.0f}s · queden "
                  f"{fet/fets*(len(files)-fets)/60:.0f} min", flush=True)
print(f"fet {fets} de {len(files)} en {(time.time()-t0)/60:.0f} min · {DESTI}", flush=True)
