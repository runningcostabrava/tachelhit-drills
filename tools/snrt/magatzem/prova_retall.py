"""El retall amb l'alineacio forcada: serveix o no?

**La pregunta.** L'alineacio de l'ECS diu que **el 51 % del so dels nostres talls no es la
frase** -- 0,79 s de silenci al davant (al 84 % dels talls) i 0,97 s al darrere (al 95 %).
Si aixo fa mal de debo, retallar ha de baixar el CER. Fins ara nomes ho sabiem d'un
diagnostic del 18-11 sobre talls **antics** (0,7370 -> 0,6581).

**Com es mesura.** Els mateixos 250 talls, el mateix model (MMS-1b-all + adaptador shi +
`adaptador_shi_zouhir_b`), la mateixa referencia. L'unica cosa que canvia es si el wav es
sencer o retallat a `[veu_ini, veu_fi]` amb un marge.

**La referencia** es el tifinag del subtitol passat pel nostre transliterador. No es veritat
humana -- es una traduccio normalitzada per l'IRCAM i l'oida s'equivoca -- pero **es la
MATEIXA als dos costats**, que es l'unic que cal per comparar.

No toca res: llegeix, mesura i escriu.
"""
import io
import json
import sys
from pathlib import Path

AQUI = Path(r"E:/tamazight/_magatzem/prova_retall")
BACK = Path(r"C:/Users/josep/app2/tachelhit-drills/backend")
sys.path.insert(0, str(BACK))
MARGE = 0.15          # s de coixi a banda i banda: la frontera no es exacta
QUANTS = 250

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from transformers import AutoProcessor, Wav2Vec2ForCTC  # noqa: E402

torch.set_num_threads(4)


def cer(ref, hip):
    if not ref:
        return 1.0
    d = range(len(hip) + 1)
    for i, c in enumerate(ref, 1):
        nd = [i]
        for j, k in enumerate(hip, 1):
            nd.append(min(d[j] + 1, nd[j - 1] + 1, d[j - 1] + (c != k)))
        d = nd
    return d[-1] / len(ref)


#: la referencia
sub = {}
for l in io.open(AQUI / "subtitols.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        if x.get("tall"):
            sub[Path(x["tall"]).name] = x

#: l'alineacio
ali = {}
for l in io.open(r"E:/tamazight/_magatzem/alineacio_ecs.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except Exception:
        continue
    ali[x["so"]] = x

wavs = sorted(AQUI.glob("so/*.wav"))[:QUANTS]
tenen = [w for w in wavs if w.name in ali]
print(f"{len(wavs)} talls · {len(tenen)} amb alineació · {len(sub)} amb text")

sys.path.insert(0, str(Path(r"E:/tamazight/fabrica/tools/snrt/fabrica")))
try:
    import transliterador as TR
    tifi = TR.tifinag_a_llati
except Exception:
    import re
    TAULA = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f",
             "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ɛ", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i",
             "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "ṛ",
             "ⵖ": "ɣ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w",
             "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "ʷ", "ⵒ": "p", "ⵖ": "ɣ"}
    def tifi(s):
        return re.sub(r"\s+", " ", "".join(TAULA.get(c, c if c == " " else "") for c in s)).strip()

print("carregant el model…", flush=True)
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all", target_lang="shi")
mod = Wav2Vec2ForCTC.from_pretrained("facebook/mms-1b-all", target_lang="shi",
                                     ignore_mismatched_sizes=True)
ad = BACK / "adaptador_shi_zouhir_b"
if ad.is_dir():
    try:
        from peft import PeftModel
        mod = PeftModel.from_pretrained(mod, str(ad))
        print("   amb adaptador_shi_zouhir_b")
    except Exception as e:
        print(f"   sense adaptador: {e}")
else:
    print("   sense adaptador (no és al disc)")
mod.eval()


def digues(x, sr=16000):
    iv = proc(x, sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        lo = mod(**iv).logits
    return proc.batch_decode(torch.argmax(lo, dim=-1))[0]


res = {"sencer": [], "retallat": []}
fora = []
for i, w in enumerate(tenen):
    s = sub.get(w.name)
    if not s or not (s.get("tifinag") or "").strip():
        continue
    ref = tifi(s["tifinag"]).lower().strip()
    if len(ref) < 4:
        continue
    x, sr = sf.read(str(w))
    if x.ndim > 1:
        x = x.mean(axis=1)
    a = ali[w.name]
    i0 = max(0, int((a["veu_ini"] - MARGE) * sr))
    i1 = min(len(x), int((a["veu_fi"] + MARGE) * sr))
    if i1 - i0 < sr * 0.3:
        continue
    for nom, senyal in (("sencer", x), ("retallat", x[i0:i1])):
        h = digues(senyal.astype(np.float32), sr).lower().strip()
        res[nom].append(cer(ref, h))
        if nom == "retallat":
            fora.append({"so": w.name, "ref": ref, "sencer_cer": res["sencer"][-1],
                         "retallat_cer": res["retallat"][-1]})
    if (i + 1) % 25 == 0:
        print(f"   {len(res['sencer'])} fets · sencer {np.mean(res['sencer']):.4f} · "
              f"retallat {np.mean(res['retallat']):.4f}", flush=True)

n = len(res["sencer"])
a, b = float(np.mean(res["sencer"])), float(np.mean(res["retallat"]))
print(f"\n   {n} talls")
print(f"   sencer    CER {a:.4f}")
print(f"   retallat  CER {b:.4f}")
print(f"   diferència     {b-a:+.4f}  ({100*(b-a)/a:+.1f} %)")
millors = sum(1 for f in fora if f["retallat_cer"] < f["sencer_cer"])
print(f"   millora en {millors} de {len(fora)} talls ({100*millors/max(len(fora),1):.0f} %)")
json.dump(fora, io.open(AQUI / "resultat.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
