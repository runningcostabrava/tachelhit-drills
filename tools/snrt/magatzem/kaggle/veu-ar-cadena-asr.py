# CADENA REAL, PRIMERA MEITAT: el que sent el nostre ASR als dos tests congelats de la via 3.
#
# El 0,2614 / 0,2634 que fem servir de «via del text» tradueix el subtitol ESCRIT: es la cadena
# amb una transcripcio perfecta. Per comparar-la de debo amb el model directe (veu -> arab) cal
# que la primera baula sigui l'orella: facebook/mms-1b-all + el nostre adaptador `shi`
# (adaptador_shi_zouhir_b.pt, el que hi ha al Space). Aqui nomes es transcriu; la traduccio
# (NLLB, la mateixa del 0,2634) es fa a casa amb CTranslate2.
#
# Sortida: /kaggle/working/asr_tests.jsonl, una fila per tall: {"test", "so", "asr"} en llati shi.
# Talla als 40 min de rellotge (queda poca quota): el que ja ha fet queda desat fila a fila.
import os, subprocess, sys, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44,<5", "soundfile"], check=False)
import io, json
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForCTC, AutoProcessor

T0 = time.time()
DADES, ON, ADAPTADOR = None, {}, None
for arrel, _, fitxers in os.walk("/kaggle/input"):
    if "test_tutlait.jsonl" in fitxers:
        DADES = arrel
    for f in fitxers:
        if f.endswith((".wav", ".flac")):
            ON[f] = os.path.join(arrel, f)
        if f == "adaptador_shi_zouhir_b.pt":
            ADAPTADOR = os.path.join(arrel, f)
assert DADES and ADAPTADOR, (DADES, ADAPTADOR)
print(f"manifests a {DADES} · {len(ON)} sons · adaptador {ADAPTADOR}", flush=True)


def llegeix(nom):
    files = [json.loads(l) for l in io.open(os.path.join(DADES, nom + ".jsonl"), encoding="utf-8") if l.strip()]
    for x in files:
        x["so"] = os.path.basename(x["so"])
    return files


tests = {"test_snrt": llegeix("test_snrt"), "test_tutlait": llegeix("test_tutlait")}
for k, v in tests.items():
    print(f"   {k}: {len(v)} files · sense so {sum(1 for x in v if x['so'] not in ON)}", flush=True)

BASE, LANG = "facebook/mms-1b-all", "shi"
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LANG)
model = AutoModelForCTC.from_pretrained(BASE)
model.load_adapter(LANG)
ad = torch.load(ADAPTADOR, map_location="cpu")
coneguts = dict(model.named_parameters())
assert all(k in coneguts for k in ad), "claus de l'adaptador que el model no te"
model.load_state_dict(ad, strict=False)
model = model.half().cuda().eval()
print(f"model carregat en {time.time() - T0:.0f} s", flush=True)


def so(nom):
    d, sr = sf.read(ON[nom], dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d[: 16000 * 30]


fora = io.open("/kaggle/working/asr_tests.jsonl", "w", encoding="utf-8")
LOT = 8
for k, v in tests.items():
    hi = [x for x in v if x["so"] in ON]
    hi.sort(key=lambda x: x.get("durada") or 0)
    fets = 0
    for i in range(0, len(hi), LOT):
        if time.time() - T0 > 40 * 60:
            print("   TALLAT per temps", flush=True)
            break
        lot = hi[i:i + LOT]
        ent = proc([so(x["so"]) for x in lot], sampling_rate=16000, return_tensors="pt", padding=True)
        with torch.no_grad():
            lg = model(ent.input_values.half().cuda(),
                       attention_mask=ent.get("attention_mask", None).cuda()
                       if ent.get("attention_mask", None) is not None else None).logits
        txt = proc.batch_decode(lg.argmax(-1).cpu())
        for x, t in zip(lot, txt):
            fora.write(json.dumps({"test": k, "so": x["so"], "asr": t}, ensure_ascii=False) + "\n")
        fora.flush()
        fets += len(lot)
    print(f"   {k}: {fets}/{len(hi)} transcrits · {time.time() - T0:.0f} s", flush=True)
fora.close()
print("fet", flush=True)
