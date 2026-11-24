"""La cadena real de la veu cap a l'arab: so -> ASR -> tifinag -> NLLB -> arab, sobre els tests congelats.

El 0,2614 / 0,2634 de «la via del text» tradueix el subtitol ESCRIT, que vol dir una
transcripcio perfecta. Aqui es mesuren, sobre les MATEIXES files que el model directe
(test_snrt 2.091, test_tutlait 547) i amb el MATEIX chrF del quadern (`chrf(hip, ref)`, beta 2):

  * `text`: el tifinag llegit de la pantalla (columna `zgh` de veu_ar/test.jsonl) -> NLLB.
    Nomes test_snrt: el TutlAit no porta text amazic. Es el sostre de la cadena.
  * `asr`: el que sent MMS-1b-all + adaptador shi (kaggle/veu-ar-cadena-asr.py, en llati) ->
    tifinag (backend/transliteration.to_forms) -> NLLB.

El traductor es el del punt de partida de text (nllb-ca-ct2, que demanat en arab fa 0,2634):
el NLLB afinat a 0,3470 no es pot recuperar de Kaggle.

    cadena_tradueix.py text
    cadena_tradueix.py asr E:/tamazight/_magatzem/tirades/cadena/asr_tests.jsonl
"""
import io
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
from transliteration import to_forms                    # noqa: E402

import ctranslate2                                      # noqa: E402
import transformers                                     # noqa: E402

MODEL = Path(r"E:/tamazight/TD_TV/models/nllb-ca-ct2")
SNRT = Path(r"E:/tamazight/_magatzem/veu_ar/test.jsonl")
TUTLAIT = Path(r"E:/tamazight/_magatzem/veu_ar_combinat/test_tutlait.jsonl")
FORA = Path(r"E:/tamazight/_magatzem/tirades/cadena")


def chrf(hip, ref, n=6, beta=2.0):
    """El mateix que els quaderns de la via 3 (veu-ar-afina*.py), en el mateix ordre."""
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        ch, cr = Counter(h), Counter(r)
        com = sum((ch & cr).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def llegeix(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]


tok = transformers.AutoTokenizer.from_pretrained(str(MODEL), src_lang="zgh_Tfng")
tr = ctranslate2.Translator(str(MODEL), device="cpu", compute_type="int8")
pref = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["arb_Arab"]))


def tradueix(textos, LOT=24):
    sortida, t0 = [], time.time()
    for i in range(0, len(textos), LOT):
        lot = textos[i:i + LOT]
        fitxes = [tok.convert_ids_to_tokens(tok.encode(t or ".")) for t in lot]
        res = tr.translate_batch(fitxes, target_prefix=[pref] * len(lot), beam_size=4,
                                 max_decoding_length=150)
        for t, r in zip(lot, res):
            h = r.hypotheses[0]
            if h and h[0] == "arb_Arab":
                h = h[1:]
            #: res a traduir vol dir res traduit: una frase buida no ha de puntuar
            sortida.append(tok.decode(tok.convert_tokens_to_ids(h)).strip() if t.strip() else "")
        if (i // LOT) % 20 == 0:
            print(f"   {min(i + LOT, len(textos))}/{len(textos)} · {time.time() - t0:.0f}s", flush=True)
    return sortida


def informa(nom, files, entrada, hip):
    cs = [chrf(h, x["ar"]) for x, h in zip(files, hip)]
    plens = [c for c, e in zip(cs, entrada) if e.strip()]
    print(f"\n{nom}: chrF {sum(cs) / len(cs):.4f} sobre {len(cs)} files · >=0,5 "
          f"{sum(1 for c in cs if c >= .5)} · amb entrada no buida {len(plens)}: "
          f"{sum(plens) / max(1, len(plens)):.4f}")
    for x, e, h in zip(*zip(*random.Random(1114).sample(list(zip(files, entrada, hip)), 5))):
        print(f"   ref:  {x['ar']}\n   ent:  {e}\n   hip:  {h}\n")
    return {"chrf": sum(cs) / len(cs), "files": len(cs), "no_buides": len(plens),
            "detall": [{"so": x["so"], "ar": x["ar"], "entrada": e, "model": h}
                       for x, e, h in zip(files, entrada, hip)]}


FORA.mkdir(parents=True, exist_ok=True)
mode = sys.argv[1]
snrt = llegeix(SNRT)
assert len(snrt) == 2091, len(snrt)
if mode == "text":
    ent = [x.get("zgh") or "" for x in snrt]
    r = {"test_snrt": informa("TEXT (pantalla) -> NLLB, test_snrt", snrt, ent, tradueix(ent))}
else:
    asr = {}
    for l in io.open(sys.argv[2], encoding="utf-8"):
        if l.strip():
            y = json.loads(l)
            asr[(y["test"], y["so"])] = y["asr"]
    r = {}
    for k, files in (("test_snrt", snrt), ("test_tutlait", llegeix(TUTLAIT))):
        for x in files:
            x["so"] = Path(x["so"]).name
        lat = [asr.get((k, x["so"]), "") for x in files]
        print(f"{k}: {sum(1 for t in lat if t)} de {len(files)} amb transcripcio", flush=True)
        ent = [to_forms(t)["tifinagh"] if t else "" for t in lat]
        r[k] = informa(f"ASR -> tifinag -> NLLB, {k}", files, ent, tradueix(ent))
        for d, t in zip(r[k]["detall"], lat):
            d["asr"] = t
json.dump(r, io.open(FORA / f"cadena_{mode}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"escrit {FORA / f'cadena_{mode}.json'}")
