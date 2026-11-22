"""Un video sencer per la cadena de debo: la nostra orella i despres la traduccio.

Es el que en Pablo demana: agafar un video de Tamazight For All **sense cap subtitol** i veure
que en treu el millor que tenim.

  1. es talla l'audio per **silencis** (no a trossos iguals: tallar enmig d'una paraula
     l'espatlla, i la fabrica talla per subtitol, que aqui no hi es);
  2. cada tall va a l'Space `/transcribe_mms`, que es el model que fa servir l'aplicacio;
  3. el que surt es tradueix amb el NLLB afinat nostre (amazic -> catala).

    transcriu_un_video.py <fitxer.wav> [segons_per_tall]
"""
import io
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

WAV = Path(sys.argv[1])
MAX_TALL = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
SPACE = "https://josepabloucr-huggingface-asr-space.hf.space"
MODEL = Path(r"E:/tamazight/TD_TV/models/nllb-ca-ct2")
FORA = WAV.with_suffix(".transcripcio.json")

import requests                                        # noqa: E402

#: --- 1. on hi ha silenci ---
p = subprocess.run(["ffmpeg", "-i", str(WAV), "-af", "silencedetect=noise=-32dB:d=0.35",
                    "-f", "null", "-"], capture_output=True, text=True)
fins = []
for l in (p.stderr or "").split("\n"):
    if "silence_start" in l:
        try:
            fins.append(float(l.split("silence_start:")[1].strip()))
        except ValueError:
            pass
with wave.open(str(WAV)) as w:
    durada = w.getnframes() / w.getframerate()
print(f"{WAV.name}: {durada:.0f} s · {len(fins)} silencis")

talls, ini = [], 0.0
for s in fins + [durada]:
    if s - ini >= 2.0:
        #: si el tros es massa llarg, es parteix, pero mai per sota de dos segons
        while s - ini > MAX_TALL:
            talls.append((ini, ini + MAX_TALL))
            ini += MAX_TALL
        talls.append((ini, s))
        ini = s
talls = [(a, b) for a, b in talls if b - a >= 1.0]
print(f"{len(talls)} talls d'entre 1 i {MAX_TALL:.0f} s\n")

#: --- 2. l'orella ---
sortida, t0 = [], time.time()
for i, (a, b) in enumerate(talls, 1):
    tros = WAV.with_name(f"_tall_{i:03d}.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-to", str(b), "-i", str(WAV),
                    "-ar", "16000", "-ac", "1", "-y", str(tros)], capture_output=True)
    text = ""
    try:
        with io.open(tros, "rb") as f:
            r = requests.post(SPACE + "/transcribe_mms",
                              files={"audio_file": (tros.name, f, "application/octet-stream")},
                              timeout=300)
        text = ((r.json() or {}).get("text") or "").strip() if r.status_code == 200 else ""
        if r.status_code != 200:
            print(f"   {i}: l'Space diu {r.status_code}", flush=True)
    except Exception as e:
        print(f"   {i}: {type(e).__name__}: {e}", flush=True)
    sortida.append({"de": round(a, 2), "a": round(b, 2), "sentit": text})
    tros.unlink(missing_ok=True)
    if i % 5 == 0:
        print(f"   {i}/{len(talls)} · {time.time()-t0:.0f}s", flush=True)

amb = [x for x in sortida if x["sentit"]]
print(f"\n{len(amb)} talls de {len(talls)} amb text")

#: --- 3. la traduccio ---
if amb:
    import ctranslate2
    import transformers
    tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
    tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
    desti = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["cat_Latn"]))
    fitxes = [tok.convert_ids_to_tokens(tok.encode(x["sentit"])) for x in amb]
    res = tr.translate_batch(fitxes, target_prefix=[desti] * len(amb), beam_size=4,
                             max_decoding_length=150)
    for x, r in zip(amb, res):
        h = r.hypotheses[0]
        if h and h[0] == "cat_Latn":
            h = h[1:]
        x["catala"] = tok.decode(tok.convert_tokens_to_ids(h)).strip()

json.dump(sortida, io.open(FORA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{'temps':>12}  el que sent l'orella / el que en surt en català")
for x in sortida:
    print(f"{x['de']:6.1f}-{x['a']:5.1f}  {x['sentit'][:72] or '(res)'}")
    if x.get("catala"):
        print(f"{'':>14}-> {x['catala'][:72]}")
print(f"\nescrit {FORA.name}")
