# TRIANGULACIO (#763), pas 2: ASR del train i el dev del SNRT a la consola d'una sessio interactiva de veu-ar-cadena-asr.
# La sessio interactiva no deixa sortida i la consola no es pot copiar en base64, aixi que el CER contra el tifinag de
# pantalla es calcula aqui i en surt UN caracter per tall (ordre: part, despres nom del so):
#   'a'+min(int(cer*20),19)  ->  'a' = cer<0,05 ... 'p' = 0,75-0,80 ... 't' = >=0,95 ;  'x' = tifinag <4 lletres o ASR buit
import io, json, os, time, urllib.request, sys
import numpy as np, soundfile as sf, torch
from transformers import AutoModelForCTC, AutoProcessor

T0 = time.time()
urllib.request.urlretrieve("https://raw.githubusercontent.com/runningcostabrava/tachelhit-drills/main/backend/transliteration.py", "/tmp/transliteration.py")
sys.path.insert(0, "/tmp")
from transliteration import to_forms

PARTS, ON, AD = {}, {}, None
for arrel, _, fitxers in os.walk("/kaggle/input"):
    for f in fitxers:
        p = os.path.join(arrel, f)
        if f.endswith(".wav"):
            ON[f] = p
        elif f == "adaptador_shi_zouhir_b.pt":
            AD = p
        elif f in ("train.jsonl", "dev.jsonl") and "snrt-veu-ar" in arrel:
            PARTS[f[:-6]] = p
assert AD and len(PARTS) == 2, (AD, PARTS)
files = []
for part in ("train", "dev"):
    for l in io.open(PARTS[part], encoding="utf-8"):
        if l.strip():
            x = json.loads(l); x["so"] = os.path.basename(x["so"]); x["part"] = part; files.append(x)
print("TRI", {p: sum(x["part"] == p for x in files) for p in PARTS}, "sense so", sum(x["so"] not in ON for x in files), flush=True)
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all"); proc.tokenizer.set_target_lang("shi")
m = AutoModelForCTC.from_pretrained("facebook/mms-1b-all"); m.load_adapter("shi")
ad = torch.load(AD, map_location="cpu")
assert all(k in dict(m.named_parameters()) for k in ad)
m.load_state_dict(ad, strict=False)
m = m.half().cuda().eval()


def so(p):
    d, sr = sf.read(p, dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d[: 16000 * 30]


def ed(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


out = {}
hi = sorted([x for x in files if x["so"] in ON], key=lambda x: x.get("durada") or 0)
for i in range(0, len(hi), 8):
    lot = hi[i:i + 8]
    ent = proc([so(ON[x["so"]]) for x in lot], sampling_rate=16000, return_tensors="pt", padding=True)
    am = ent.get("attention_mask", None)
    with torch.no_grad():
        lg = m(ent.input_values.half().cuda(), attention_mask=am.cuda() if am is not None else None).logits
    for x, t in zip(lot, proc.batch_decode(lg.argmax(-1).cpu())):
        out[x["so"]] = t
    if i % 800 == 0:
        print(f"TRI {i}/{len(hi)} · {time.time() - T0:.0f} s", flush=True)
json.dump(out, open("/kaggle/working/asr_traindev_snrt.json", "w", encoding="utf-8"), ensure_ascii=False)

codi = []
for x in sorted(files, key=lambda x: (x["part"], x["so"])):
    z = (x.get("zgh") or "").replace(" ", "")
    a = out.get(x["so"], "")
    if len(z) < 4 or not a:
        codi.append("x"); continue
    t = to_forms(a)["tifinagh"].replace(" ", "")
    codi.append(chr(97 + min(int(ed(t, z) / len(z) * 20), 19)))
codi = "".join(codi)
open("/kaggle/working/cer_traindev.txt", "w").write(codi)
print(f"TRI fet {len(out)} en {time.time() - T0:.0f} s · codi {len(codi)} · suma {sum(ord(c) for c in codi)}", flush=True)
globals()["CODI"] = codi
