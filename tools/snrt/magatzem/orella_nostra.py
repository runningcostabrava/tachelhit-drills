"""La NOSTRA orella (MMS-1b-all + `shi` + l'adaptador afinat) en local, sobre una carpeta de talls.

Per que importa fer-ho amb l'adaptador i no amb el `shi` de serie: les transcripcions dels 25
capitols de Tadfi es van fer amb l'adaptador afinat, i el classificador per lexic compara formes.
Comparar sortides de dos models diferents faria que la diferencia fos del model i no de la
varietat.

    orella_nostra.py <carpeta_amb_index.json> [limit]
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

BASE, LLENGUA, SR = "facebook/mms-1b-all", "shi", 16000
ADAPT = Path(r"E:/tamazight/_magatzem/adaptador/adaptador_inici.pt")
DADES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_magatzem/prova_baba/dades")
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
DESTI = DADES.parent / "sentit_nostre.jsonl"

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

files = json.load(io.open(DADES / "index.json", encoding="utf-8"))
if LIMIT:
    files = files[:LIMIT]
print(f"{len(files)} talls", flush=True)

proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
if ADAPT.exists():
    #: `strict=False` perque l'adaptador nomes porta les capes seves; el que NO es tolera es que
    #: hi hagi claus que el model no reconeix: voldria dir que es d'una altra cosa.
    res = model.load_state_dict(torch.load(ADAPT, map_location="cpu"), strict=False)
    assert not res.unexpected_keys, res.unexpected_keys
    print(f"adaptador afinat posat ({ADAPT.name})", flush=True)
else:
    print("ATENCIO: sense adaptador afinat, les formes no seran comparables", flush=True)
model.eval()
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
print(f"model a punt · {torch.get_num_threads()} fils", flush=True)


def llegeix(p):
    with wave.open(str(p)) as w:
        n, sr = w.getnframes(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a, sr


t0, fets = time.time(), 0
with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for x in files:
        try:
            w, sr = llegeix(DADES / x["fitxer"])
        except Exception as e:
            f.write(json.dumps({"id": x["id"], "error": type(e).__name__}) + "\n")
            continue
        if w.size < SR // 10 or sr != SR:
            f.write(json.dumps({"id": x["id"], "sentit": "", "conf": None, "paraules": []},
                               ensure_ascii=False) + "\n")
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
                            "paraules": paraules, "catala": x.get("catala")},
                           ensure_ascii=False) + "\n")
        fets += 1
        if fets % 25 == 0:
            f.flush()
            fet = time.time() - t0
            print(f"{fets}/{len(files)} · {fet:.0f}s · queden "
                  f"{fet/fets*(len(files)-fets)/60:.0f} min", flush=True)
print(f"fet {fets} de {len(files)} en {(time.time()-t0)/60:.0f} min · {DESTI}", flush=True)
