# ModelScope (instancia GPU gratuita, o CPU si no n'hi ha): ASR mms-1b-all + adaptador shi_zouhir_b sobre els talls del SNRT (#763).
# El mateix que asr_local_snrt.py, que a casa moria per falta de memoria. Proposta de maquina, mai text de parlant.
# Puja el resultat a josepabloucr/pont cada 200 talls i, si es torna a engegar, recupera el que ja hi ha.
#
#   export HF_TOKEN=...   (o modelscope: variable d'entorn de la instancia)
#   python ms_snrt.py
import hashlib, io, json, os, subprocess, sys, tarfile, time

TOKEN = os.environ["HF_TOKEN"]
REPO = "josepabloucr/pont"
W = "/mnt/workspace/ms_snrt"
os.makedirs(W, exist_ok=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers<5", "soundfile", "huggingface_hub"], check=True)

import numpy as np, soundfile as sf, torch
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError
from transformers import AutoModelForCTC, AutoProcessor

api = HfApi(token=TOKEN)
baixa = lambda f: hf_hub_download(REPO, f, repo_type="dataset", token=TOKEN, force_download=True)
man = json.load(open(baixa("ms_snrt/manifest.json"), encoding="utf-8"))
pt = baixa("ms_snrt/adaptador_shi_zouhir_b.pt")
assert hashlib.sha256(open(pt, "rb").read()).hexdigest() == man["sha_adaptador"], "adaptador equivocat"
if not os.path.isdir(W + "/so"):
    tarfile.open(baixa("ms_snrt/audio.tgz")).extractall(W)
print("talls", len(man["talls"]), flush=True)

torch.set_num_threads(os.cpu_count() or 16)
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all"); proc.tokenizer.set_target_lang("shi")
m = AutoModelForCTC.from_pretrained("facebook/mms-1b-all"); m.load_adapter("shi")
ad = torch.load(pt, map_location="cpu")
known = dict(m.named_parameters())
assert not [k for k in ad if k not in known], "claus desconegudes"
canvi = sum(float((known[k].detach() - v).abs().sum()) for k, v in ad.items())
m.load_state_dict(ad, strict=False)
resta = sum(float((known[k].detach() - v).abs().sum()) for k, v in ad.items())
assert canvi > 0 and resta == 0, "l'adaptador no s'ha aplicat"
DEV = "cuda" if torch.cuda.is_available() else "cpu"
m.eval().to(DEV)
print("adaptador aplicat ·", DEV, flush=True)

SORTIDA = W + "/asr_snrt_ms.jsonl"
fets = {}
try:
    for l in open(baixa("ms_snrt/asr_snrt_ms.jsonl"), encoding="utf-8"):
        if l.strip():
            y = json.loads(l); fets[y["so"]] = y
except EntryNotFoundError:
    pass
print("recuperats", len(fets), flush=True)


def puja():
    with io.open(SORTIDA, "w", encoding="utf-8") as f:
        for y in fets.values():
            f.write(json.dumps(y, ensure_ascii=False) + "\n")
    api.upload_file(path_or_fileobj=SORTIDA, path_in_repo="ms_snrt/asr_snrt_ms.jsonl", repo_id=REPO,
                    repo_type="dataset", commit_message=f"ms_snrt {len(fets)}")


def so(nom):
    d, sr = sf.read(f"{W}/so/{nom}", dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d[: 16000 * 30]


T0, nous = time.time(), 0
for t in man["talls"]:
    if t["so"] in fets:
        continue
    ent = proc(so(t["fitxer"]), sampling_rate=16000, return_tensors="pt")
    with torch.inference_mode():
        lg = m(ent.input_values.to(DEV)).logits.cpu()
    fets[t["so"]] = {"part": t["part"], "so": t["so"], "asr": proc.batch_decode(lg.argmax(-1))[0], "prec": "fp32-ms-" + DEV}
    nous += 1
    if nous % 200 == 0:
        puja()
        print(f"{len(fets)}/{len(man['talls'])} · {nous / (time.time() - T0):.2f} talls/s", flush=True)
puja()
print("FET", len(fets), flush=True)
