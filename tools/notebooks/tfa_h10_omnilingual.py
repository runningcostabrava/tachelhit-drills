"""H10: un lector millor? Omnilingual ASR (Meta, 1.600 llengües, Apache-2.0) sobre els mateixos
226 versos narrats + 15 cantats amb veritat humana que han mesurat el nostre MMS (CER 0,207,
WER 0,712 greedy; 0,198 / 0,640 amb el lèxic al feix).

Tres intents abans d'aquest (15-11): fairseq2 no té roda per al Python 3.13 de Kaggle (ni amb
torch 2.11 ni baixant a 2.9), i els CTC exportats a ONNX (sherpa-onnx) escriuen l'amazic en
lletres àrabs perquè no admeten condició de llengua. v4: un Python 3.12 a part, instal·lat amb
uv dins del kernel, amb torch 2.9 + fairseq2 + omnilingual-asr; els LLM 1B i 3B condicionats a
tachelhit (`shi_Latn`) i a tamazight de l'Atles central (`tzm_Latn`). Es desen els textos; es
puntua a casa amb h3_puntua.py.
"""

# %%
import subprocess, sys, os, time
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "uv", "soundfile"], check=False)
PY = "/kaggle/working/py312/bin/python"
passos = [
    ["uv", "venv", "/kaggle/working/py312", "--python", "3.12", "--seed"],
    ["uv", "pip", "install", "--python", PY, "torch==2.8.0", "torchaudio==2.8.0", "--index-url", "https://download.pytorch.org/whl/cu128"],
    ["uv", "pip", "install", "--python", PY, "fairseq2==0.6", "omnilingual-asr", "soundfile", "numpy<2", "pyarrow==20.0.0",
     "--extra-index-url", "https://fair.pkg.atmeta.com/fairseq2/whl/pt2.8.0/cu128"],
]
OK = True
for p in passos:
    r = subprocess.run(p, capture_output=True, text=True)
    print(" ".join(p[:4]), "rc", r.returncode, "\n   stdout:", (r.stdout or "")[-300:].replace("\n", " | "),
          "\n   stderr:", (r.stderr or "")[-900:].replace("\n", " | "), flush=True)
    if r.returncode != 0:
        OK = False
        break
print("entorn 3.12 llest:", OK, f"{time.time()-t0:.0f} s")
if OK:
    r = subprocess.run([PY, "-c", "import torch, fairseq2, omnilingual_asr; print(torch.__version__, torch.cuda.is_available())"], capture_output=True, text=True)
    print(r.stdout, (r.stderr or "")[-300:])

# %%
import glob, json
import numpy as np, soundfile as sf

DADES = None
for arrel, carpetes, fitxers in os.walk("/kaggle/input"):
    if "veritat_parlat.json" in fitxers:
        DADES = arrel
        break
assert DADES
FORA = "/kaggle/working"
TMP = "/kaggle/working/talls"
os.makedirs(TMP, exist_ok=True)
versos = json.load(open(os.path.join(DADES, "veritat_parlat.json"), encoding="utf-8"))
for v in versos:
    v["mena"] = "parlat"
for v in json.load(open(os.path.join(DADES, "veritat_cancons.json"), encoding="utf-8")):
    if os.path.exists(os.path.join(DADES, v["video"] + ".wav")):
        v["mena"] = "cantat"
        versos.append(v)
SR = 16000
wavs = {}
camins = []
for i, v in enumerate(versos):
    if v["video"] not in wavs:
        wavs[v["video"]], sr = sf.read(os.path.join(DADES, v["video"] + ".wav"), dtype="float32")
        assert sr == SR
    w = wavs[v["video"]]
    a, b = max(0, int((v["de"] - 0.1) * SR)), min(len(w), int((v["a"] + 0.1) * SR))
    p = os.path.join(TMP, f"{i:04}.wav")
    sf.write(p, np.ascontiguousarray(w[a:b]), SR)
    camins.append(p)
    v["greedy"] = v.get("shi") or ""
json.dump(camins, open("/kaggle/working/camins.json", "w"))
print(len(versos), "versos tallats")

# %%
RUNNER = r'''
import json, sys, time, gc, torch
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
camins = json.load(open("/kaggle/working/camins.json"))
try:
    from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
    print(len(supported_langs), "llengues;", [l for l in supported_langs if l.split("_")[0] in ("shi", "tzm", "zgh", "kab", "rif", "taq", "ber")], flush=True)
except Exception as e:
    print("supported_langs:", e, flush=True)
CONFIGS = [("llm1b_shi", "omniASR_LLM_1B", "shi_Latn"), ("llm1b_tzm", "omniASR_LLM_1B", "tzm_Latn"),
           ("llm3b_shi", "omniASR_LLM_3B", "shi_Latn"), ("llm3b_tzm", "omniASR_LLM_3B", "tzm_Latn")]
res = {}
for nom, card, lang in CONFIGS:
    t0 = time.time()
    try:
        pipe = ASRInferencePipeline(model_card=card)
        out = []
        for k in range(0, len(camins), 8):
            lot = camins[k:k + 8]
            out.extend(pipe.transcribe(lot, lang=[lang] * len(lot), batch_size=8))
        res[nom] = [(t or "").strip() for t in out]
        print(nom, "fet en", round(time.time() - t0), "s · ex:", repr(res[nom][0]), flush=True)
        del pipe; gc.collect(); torch.cuda.empty_cache()
    except Exception as e:
        print(nom, "ERROR", type(e).__name__, str(e)[:400], flush=True)
    json.dump(res, open("/kaggle/working/h10_llm.json", "w", encoding="utf-8"), ensure_ascii=False)
'''
fets = []
if OK:
    open("/kaggle/working/omni_run.py", "w").write(RUNNER)
    r = subprocess.run([PY, "/kaggle/working/omni_run.py"], capture_output=True, text=True)
    print(r.stdout[-3000:]); print("--- stderr", (r.stderr or "")[-1500:])
    if os.path.exists("/kaggle/working/h10_llm.json"):
        res = json.load(open("/kaggle/working/h10_llm.json", encoding="utf-8"))
        for nom, textos in res.items():
            for v, t in zip(versos, textos):
                v[nom] = t
            fets.append(nom)
json.dump({"configs": fets, "versos": versos}, open(os.path.join(FORA, "h10_resultats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("desat h10_resultats.json:", fets)
#: la sortida del kernel es baixa SENCERA: l'entorn (GB) i els talls no hi han de quedar
import shutil
for d in ("/kaggle/working/py312", "/kaggle/working/talls"):
    shutil.rmtree(d, ignore_errors=True)
for f in ("/kaggle/working/camins.json", "/kaggle/working/omni_run.py"):
    if os.path.exists(f):
        os.remove(f)
print("sortida neta:", os.listdir("/kaggle/working"))
