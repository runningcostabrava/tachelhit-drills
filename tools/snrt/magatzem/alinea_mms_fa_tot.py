"""Alinear **tot** el corpus local amb `torchaudio MMS_FA`, repartit en fluxos.

**Per que no amb el model gran.** MMS-1b-all a l'ECS fa 0,18 talls/s: els 20.547 talls son 32 h.
El MMS_FA es de 300 M i aqui fa 1,70 s per tall en un sol flux; el PC te 16 nuclis i tots els
talls al disc (`E:/tamazight/talls_ecs`), aixi que amb tres fluxos son ~3,5 h.

**Per que es pot confiar.** El 22-11 el MMS_FA es va descartar amb un 5 % de fronteres a 0,2 s
de les del model gran. Aquella referencia estava trencada (quadern, §48): refeta contra les
fronteres bones, el MMS_FA en dona el **62 %** dins de 0,2 s, amb mediana d'error **-0,016 s** a
l'inici i **+0,036 s** al final. Sense biaix.

**El que aixo NO resol:** si retallar val la pena. Aixo es una altra pregunta
(`prova_el_jutge.py`) i es contesta amb el mateix fitxer que surti d'aqui.

Cada flux escriu el **seu** fitxer, aixi que no es trepitgen -- dos `write` al mateix fitxer es
van barrejar a mig buffer el 23-11 i van deixar una linia trencada.

    python alinea_mms_fa_tot.py --part 0/3      (i 1/3, 2/3 en finestres a part)
"""
import argparse
import io
import json
import time
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from torchaudio.pipelines import MMS_FA

ARREL = Path(r"E:/tamazight/talls_ecs")

TIFI = {"\u2d30": "a", "\u2d31": "b", "\u2d33": "g", "\u2d37": "d", "\u2d39": "d", "\u2d3b": "e",
        "\u2d3c": "f", "\u2d3d": "k", "\u2d40": "h", "\u2d43": "h", "\u2d44": "a", "\u2d45": "x",
        "\u2d47": "q", "\u2d49": "i", "\u2d4a": "j", "\u2d4d": "l", "\u2d4e": "m", "\u2d4f": "n",
        "\u2d53": "u", "\u2d54": "r", "\u2d55": "r", "\u2d56": "g", "\u2d59": "s", "\u2d5a": "s",
        "\u2d5b": "c", "\u2d5c": "t", "\u2d5f": "t", "\u2d61": "w", "\u2d62": "y", "\u2d63": "z",
        "\u2d65": "z", "\u2d6f": "w", "\u2d52": "p", "\u2d36": "g", "\u2d4c": "j"}


def roman(t):
    fora = []
    for c in t or "":
        if c in TIFI:
            fora.append(TIFI[c])
        elif c.isspace():
            fora.append(" ")
        elif c.isascii() and c.isalpha():
            fora.append(c.lower())
        else:
            d = unicodedata.normalize("NFD", c)
            b = "".join(x for x in d if not unicodedata.combining(x))
            if b.isascii() and b.isalpha():
                fora.append(b.lower())
    return " ".join("".join(fora).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="0/1", help="quin flux de quants: 0/3, 1/3, 2/3")
    ap.add_argument("--fils", type=int, default=4)
    a = ap.parse_args()
    jo, de = (int(x) for x in a.part.split("/"))
    torch.set_num_threads(a.fils)

    desti = Path(f"E:/tamazight/_magatzem/alineacio_mms_fa_tot_{jo}de{de}.jsonl")

    #: la feina: tall per tall, amb el seu text
    feina = []
    for cap in sorted(ARREL.iterdir()):
        sub, talls = cap / "subtitols.jsonl", cap / "talls"
        if not (sub.exists() and talls.is_dir()):
            continue
        for l in io.open(sub, encoding="utf-8"):
            if not l.strip():
                continue
            x = json.loads(l)
            if not x.get("tall"):
                continue
            w = talls / Path(x["tall"]).name
            t = roman(x.get("tifinag") or "")
            if w.exists() and len(t) >= 3:
                feina.append((w, t, cap.name))
    #: el repartiment es per index, no per capitol: aixi els tres fluxos acaben alhora encara
    #: que els capitols siguin de mides molt diferents
    feina = [x for i, x in enumerate(feina) if i % de == jo]

    #: els fets es llegeixen de TOTS els fitxers de flux, no nomes del propi. El 23-11 tres
    #: fluxos van desar 2.317 talls i el sistema els va matar per memoria; amb un sol flux
    #: (`--part 0/1`) aquella feina no s'ha de repetir, encara que la desessin altres fitxers.
    fets = set()
    for p in sorted(desti.parent.glob("alineacio_mms_fa_tot_*de*.jsonl")):
        for l in io.open(p, encoding="utf-8"):
            try:
                fets.add(json.loads(l)["so"])
            except Exception:
                pass
    feina = [x for x in feina if x[0].name not in fets]
    print(f"flux {jo}/{de} · {len(feina)} talls per fer · {len(fets)} ja fets", flush=True)

    mod, tok = MMS_FA.get_model(), MMS_FA.get_tokenizer()
    alinea = MMS_FA.get_aligner()

    t0, n, fallats = time.time(), 0, 0
    with io.open(desti, "a", encoding="utf-8", newline="\n") as f:
        for w, t, cap in feina:
            try:
                xs, sr = sf.read(str(w), dtype="float32")
                if xs.ndim > 1:
                    xs = xs.mean(axis=1)
                x = torch.from_numpy(np.ascontiguousarray(xs)).unsqueeze(0)
                if sr != 16000:
                    x = torchaudio.functional.resample(x, sr, 16000)
                with torch.inference_mode():
                    em, _ = mod(x)
                    sp = alinea(em[0], tok(t.split()))
                rao = x.shape[1] / em.shape[1] / 16000
                f.write(json.dumps({"so": w.name, "capitol": cap,
                                    "durada": round(x.shape[1] / 16000, 2),
                                    "veu_ini": round(sp[0][0].start * rao, 2),
                                    "veu_fi": round(sp[-1][-1].end * rao, 2)},
                                   ensure_ascii=False) + "\n")
                f.flush()
                n += 1
            except Exception as ex:
                fallats += 1
                if fallats <= 5:
                    print(f"   {w.name}: {type(ex).__name__}", flush=True)
            if n and n % 200 == 0:
                v = n / (time.time() - t0)
                print(f"   {n}/{len(feina)} · {v:.2f} talls/s · queden "
                      f"{(len(feina)-n)/v/3600:.1f} h", flush=True)

    print(f"\nflux {jo}/{de}: {n} alineats · {fallats} fallats · "
          f"{(time.time()-t0)/60:.0f} min")


if __name__ == "__main__":
    main()
