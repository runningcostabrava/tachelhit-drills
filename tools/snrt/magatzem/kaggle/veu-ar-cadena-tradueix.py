# CADENA REAL, SEGONA MEITAT: s'enganxa a la consola de la sessio de veu-ar-cadena-asr.py un cop ha acabat
# (fa servir `tests` d'aquella sessio i /kaggle/working/asr_tests.jsonl). Cal /tmp/transliteration.py
# (copia de backend/transliteration.py). Tradueix amb el NLLB de Tamazight-NLP sense afinar, el mateix
# per al text de la pantalla i per a la sortida de l'ASR, i puntua amb el chrF dels quaderns de la via 3.
import io, json, os, sys, glob, random, statistics, torch
from collections import Counter
sys.path.insert(0, "/tmp")
from transliteration import to_forms
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
try:
    del model
except NameError:
    pass
torch.cuda.empty_cache()
M = "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch"
tk = AutoTokenizer.from_pretrained(M, src_lang="zgh_Tfng")
nm = AutoModelForSeq2SeqLM.from_pretrained(M).half().cuda().eval()
AR = tk.convert_tokens_to_ids("arb_Arab")


def trad(ts):
    out = []
    for i in range(0, len(ts), 32):
        lot = [t if t.strip() else "." for t in ts[i:i + 32]]
        e = tk(lot, return_tensors="pt", padding=True, truncation=True, max_length=128).to("cuda")
        with torch.no_grad():
            g = nm.generate(**e, forced_bos_token_id=AR, num_beams=4, max_new_tokens=128)
        out += tk.batch_decode(g, skip_special_tokens=True)
    return [o.strip() if t.strip() else "" for o, t in zip(out, ts)]


def chrf(hip, ref, n=6):
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        com = sum((Counter(h) & Counter(r)).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    return 0.0 if p + r == 0 else 5 * p * r / (4 * p + r)


def ed(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


asr = {}
for l in open("/kaggle/working/asr_tests.jsonl", encoding="utf-8"):
    y = json.loads(l)
    asr[(y["test"], y["so"])] = y["asr"]
P = [p for p in glob.glob("/kaggle/input/**/snrt-veu-ar/test.jsonl", recursive=True)][0]
snrt = [json.loads(l) for l in open(P, encoding="utf-8") if l.strip()]
for x in snrt:
    x["so"] = os.path.basename(x["so"])
tut = tests["test_tutlait"]
R, H = {}, {}


def puntua(nom, files, ent):
    h = trad(ent)
    cs = [chrf(a, x["ar"]) for a, x in zip(h, files)]
    R[nom] = sum(cs) / len(cs)
    H[nom] = h
    print(f"CAD {nom}: chrF {R[nom]:.4f} · >=0,5 {sum(c >= .5 for c in cs)}/{len(cs)}", flush=True)


zgh = [x.get("zgh") or "" for x in snrt]
la = [asr.get(("test_snrt", x["so"]), "") for x in snrt]
lb = [asr.get(("test_tutlait", x["so"]), "") for x in tut]
ea = [to_forms(t)["tifinagh"] if t else "" for t in la]
eb = [to_forms(t)["tifinagh"] if t else "" for t in lb]
print(f"CAD files: snrt {len(snrt)} (asr {sum(1 for t in la if t)}) · tutlait {len(tut)} (asr {sum(1 for t in lb if t)})", flush=True)
cer = [ed(a.replace(" ", ""), z.replace(" ", "")) / len(z.replace(" ", "")) for a, z in zip(ea, zgh) if z.replace(" ", "")]
print(f"CAD CER asr contra pantalla (tifinag): mitjana {statistics.mean(cer):.3f} · mediana {statistics.median(cer):.3f} · n {len(cer)}", flush=True)
puntua("snrt_text", snrt, zgh)
puntua("snrt_asr", snrt, ea)
puntua("tutlait_asr", tut, eb)
rng = random.Random(1114)
for i in rng.sample(range(len(snrt)), 4):
    print(f"CADM snrt ref {snrt[i]['ar']} | pantalla {zgh[i]} | asr {la[i]} | text>ar {H['snrt_text'][i]} | asr>ar {H['snrt_asr'][i]}", flush=True)
for i in rng.sample(range(len(tut)), 4):
    print(f"CADM tut ref {tut[i]['ar']} | asr {lb[i]} | asr>ar {H['tutlait_asr'][i]}", flush=True)
json.dump({"R": R, "snrt": [{"so": x["so"], "ar": x["ar"], "zgh": z, "asr": a, "text_ar": t, "asr_ar": b} for x, z, a, t, b in zip(snrt, zgh, la, H["snrt_text"], H["snrt_asr"])], "tutlait": [{"so": x["so"], "ar": x["ar"], "asr": a, "asr_ar": b} for x, a, b in zip(tut, lb, H["tutlait_asr"])]}, open("/kaggle/working/cadena.json", "w", encoding="utf-8"), ensure_ascii=False)
print("CAD fet", flush=True)
