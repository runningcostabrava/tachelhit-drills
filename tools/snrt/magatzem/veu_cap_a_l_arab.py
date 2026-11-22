"""Via 3: de la VEU directament a l'arab, saltant-se el text amazic.

La idea surt d'aqui: del tifinag escrit es tradueix a chrF 0,319 i del que sent l'orella a
0,131. La cadena multiplica errors. Pero les mateixes 17,9 hores estan alineades amb **arab**,
de manera que son un corpus de **traduccio de veu**: entrada el so, sortida l'arab, sense cap
text amazic pel mig. Aixi l'error de l'orella no hi entra.

Aixo mesura el **punt de partida**: que fa el Whisper d'ara quan se li demana arab d'un audio
amazic que no ha sentit mai. Es el numero a batre si despres s'afina.

S'hi proven dues maneres, perque no es el mateix:
  * `transcribe` amb language='ar' -- li diem que l'audio es arab (no ho es): li fem dir el que
    sent amb lletres arabs;
  * `translate` -- la tasca de traduccio de Whisper, que **nomes sap anar a l'angles**, i es
    mesura contra l'arab nomes per veure que no serveix.

    veu_cap_a_l_arab.py [quants]
"""
import io
import json
import os
import sys
import time
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")
TEST = Path(r"E:/tamazight/_magatzem/zgh_ar/test.jsonl")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
sys.path.insert(0, r"C:/Users/josep/app2/tachelhit-drills.worktrees/tradueix/tools/snrt/fabrica")
from comu import chrf                                   # noqa: E402

import numpy as np                                      # noqa: E402
import soundfile as sf                                  # noqa: E402
from faster_whisper import WhisperModel                 # noqa: E402


def so(cami):
    """El tall a 16 kHz mono, llegit aqui: la versio d'`av` d'aquesta maquina no la sap obrir
    `faster_whisper` (`open() got an unexpected keyword argument 'metadata_errors'`), pero
    accepta un vector de numpy."""
    d, sr = sf.read(cami, dtype="float32", always_2d=False)
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d

#: les linies del test que tenen el so al disc
files = []
for l in io.open(TEST, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    cap = x["capitol"]
    #: el tall es diu <capitol>_<k>.wav dins de talls/
    p = ARREL / cap / "subtitols.jsonl"
    files.append(x)
#: cal el cami del tall: es torna a llegir el subtitols.jsonl de cada capitol
talls = {}
for cap in {x["capitol"] for x in files}:
    for l in io.open(ARREL / cap / "subtitols.jsonl", encoding="utf-8"):
        if l.strip():
            y = json.loads(l)
            if y.get("tall") and (y.get("tifinag") or "").strip():
                talls[(cap, (y.get("tifinag") or "").strip())] = ARREL / cap / y["tall"]

amb_so = []
for x in files:
    p = talls.get((x["capitol"], x["zgh"]))
    if p and p.exists():
        amb_so.append({**x, "wav": str(p)})
print(f"{len(files)} línies de test · {len(amb_so)} amb el so al disc")
amb_so = amb_so[:N]
print(f"se'n proven {len(amb_so)}\n")

model = WhisperModel("small", device="cpu", compute_type="int8",
                     download_root=os.path.expanduser("~/.cache/huggingface/hub"))

sortida = {"ar": [], "en": []}
t0 = time.time()
for i, x in enumerate(amb_so, 1):
    w = so(x["wav"])
    seg, _ = model.transcribe(w, language="ar", task="transcribe", beam_size=4)
    sortida["ar"].append(" ".join(t.text.strip() for t in seg).strip())
    seg, _ = model.transcribe(w, task="translate", beam_size=4)
    sortida["en"].append(" ".join(t.text.strip() for t in seg).strip())
    if i % 15 == 0:
        print(f"   {i}/{len(amb_so)} · {time.time()-t0:.0f}s", flush=True)

print(f"\n{'manera':<34}{'chrF contra l arab':>20}")
for k, nom in (("ar", "Whisper dient-li «es àrab»"), ("en", "Whisper traduint (va a l'anglès)")):
    cs = [chrf(x["ar"], s) for x, s in zip(amb_so, sortida[k])]
    print(f"{nom:<34}{sum(cs)/len(cs):>20.4f}")

print("\nTres exemples:")
for x, a, e in list(zip(amb_so, sortida["ar"], sortida["en"]))[:3]:
    print(f"   pantalla: {x['ar'][:52]}")
    print(f"   whisper ar: {a[:52]}")
    print(f"   whisper en: {e[:52]}")
json.dump([{"ar_pantalla": x["ar"], "whisper_ar": a, "whisper_en": e}
           for x, a, e in zip(amb_so, sortida["ar"], sortida["en"])],
          io.open(r"E:/tamazight/_magatzem/zgh_ar/veu_base.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nescrit zgh_ar/veu_base.json")
