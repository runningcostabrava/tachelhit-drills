# TRIANGULACIO (#763), ASR del test_snrt a Kaggle: s'enganxa a la consola d'una sessio interactiva de
# veu-ar-cadena-asr (la que te snrt-veu-ar i adaptador_shi_zouhir_b com a entrades). Transcriu els 2.091 talls
# (els 730 que ja tenim de casa, en fp32, serveixen per comprovar que el fp16 d'aqui no canvia res) i ho treu
# per la consola com una sola linia gzip+base64 entre TRI64< i >TRI64, perque la sessio interactiva no deixa sortida.
import base64, gzip, io, json, os, time
import numpy as np, soundfile as sf, torch
from transformers import AutoModelForCTC, AutoProcessor

T0 = time.time()
TEST, ON, AD = None, {}, None
for arrel, _, fitxers in os.walk("/kaggle/input"):
    for f in fitxers:
        p = os.path.join(arrel, f)
        if f.endswith(".wav"):
            ON[f] = p
        elif f == "adaptador_shi_zouhir_b.pt":
            AD = p
        elif f == "test.jsonl" and "snrt-veu-ar" in arrel:
            TEST = p
assert TEST and AD, (TEST, AD)
files = [json.loads(l) for l in io.open(TEST, encoding="utf-8") if l.strip()]
for x in files:
    x["so"] = os.path.basename(x["so"])
print("TRI test", len(files), "sense so", sum(x["so"] not in ON for x in files), flush=True)
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
json.dump(out, open("/kaggle/working/asr_test_snrt.json", "w", encoding="utf-8"), ensure_ascii=False)
b = base64.b64encode(gzip.compress(json.dumps(out, ensure_ascii=False).encode("utf-8"))).decode()
print(f"TRI fet {len(out)} en {time.time() - T0:.0f} s · {len(b)} caracters", flush=True)
print("TRI64<" + b + ">TRI64", flush=True)
