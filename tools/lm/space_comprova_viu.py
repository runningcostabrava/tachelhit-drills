# -*- coding: utf-8 -*-
"""Comprova que el Space serveix l'adaptador H4b: 6 rètols de RzG-vYOY2L8 (fora de l'entrenament) pel
Space (/transcribe_mms, greedy) contra el que el nucli H4b va dir «després» pels mateixos talls i
contra el que deia el lector d'abans (greedy del nucli de mesura). Si el Space = «després» del nucli,
l'adaptador viu és el bo."""
import io, json, os, subprocess, sys, tempfile, time
import requests
sys.path.insert(0, r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar\tools\lm")
import h3_puntua

S = os.path.dirname(os.path.abspath(__file__))
Z = os.path.join(os.path.dirname(S), "zouhir")
VID = "RzG-vYOY2L8"
SPACE = "https://josepabloucr-huggingface-asr-space.hf.space"
mesura = json.load(io.open(os.path.join(Z, "mesura", VID + ".json"), encoding="utf-8"))["versos"]
h4b = json.load(io.open(r"C:\Users\josep\Veus-tachelhit\_escoltats\zouhir\kernels\h4b_sortides.json", encoding="utf-8"))
despres = {(x["video"], round(x["de"], 2)): x["dit"] for x in h4b if x["model"] == "després" and x["prova"] == "zouhir-fora"}
wav = os.path.join(S, "wav", VID + ".wav")
tmp = tempfile.mkdtemp()
tria = [v for v in mesura if v["mena"] == "parlat" and 1.5 <= v["a"] - v["de"] <= 4.0][:6]
files = []
for v in tria:
    tros = os.path.join(tmp, f"{v['n']}.wav")
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{max(0, v['de'] - 0.1):.3f}", "-to", f"{v['a'] + 0.1:.3f}",
                    "-i", wav, "-ac", "1", "-ar", "16000", tros], check=True)
    t0 = time.time()
    try:
        r = requests.post(SPACE + "/transcribe_mms", files={"audio_file": ("c.wav", io.open(tros, "rb").read(), "audio/wav")}, timeout=600)
        viu = (r.json().get("text") or "").strip()
    except Exception as e:
        viu = f"[{type(e).__name__}]"
    s = time.time() - t0
    files.append((v, viu, s))
    print(f"{v['n']:3} {s:5.0f}s | veritat {v['veritat'][:38]:38} | abans {v['greedy'][:38]:38} | viu {viu[:38]:38} | nucli H4b {despres.get((VID, round(v['de'], 2)), '?')[:38]}", flush=True)


def cer(h, v):
    return h3_puntua.cer(h3_puntua.net(h), h3_puntua.net(v))


print("CER abans (greedy nucli de mesura):", round(sum(cer(v["greedy"], v["veritat"]) for v, _, _ in files) / len(files), 3))
print("CER viu (Space ara):               ", round(sum(cer(viu, v["veritat"]) for v, viu, _ in files) / len(files), 3))
print("CER nucli H4b «després»:           ", round(sum(cer(despres.get((VID, round(v["de"], 2)), ""), v["veritat"]) for v, _, _ in files) / len(files), 3))
print("viu == nucli H4b (text plegat):", sum(1 for v, viu, _ in files if h3_puntua.plega(h3_puntua.net(viu)) == h3_puntua.plega(h3_puntua.net(despres.get((VID, round(v["de"], 2)), "")))), "de", len(files))
