# -*- coding: utf-8 -*-
"""Etapa 04: els catalans de cada subtítol i l'acord entre ells.

  python 04_tradueix.py <carpeta> [--model1 qwen3.8-max] [--model2 deepseek-chat|cap] [--space josepabloucr/Finetuned-Quantized-NLLB] [--fils 4]

- àrab → català amb DOS models de cases diferents (Model Studio i DeepSeek; «dos auditors i només l'acord»):
  `ca_ar1`, `ca_ar2` i `acord_ar` (chrF entre ells). Un acord baix assenyala un error d'OCR o un nom propi.
- tifinag → català amb el nostre Space NLLB afinat: `ca_tif`, i `chrf` contra `ca_ar1` (la mesura d'acord que
  tenim sense parlant; és el sostre del traductor amazic, no de l'OCR).
Reprèn per k des de `traduccions.jsonl`; refà una fila si l'àrab o el tifinag han canviat.
Claus: DASHSCOPE_API_KEY/DASHSCOPE_BASE_URL (model1), DEEPSEEK_API_KEY (model2; sense clau, es salta).
"""
import argparse
import io
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "04_tradueix"
SISTEMA = ("Ets un traductor de l'àrab al català. T'arriba el subtítol en àrab (àrab estàndard, de vegades amb trets "
           "marroquins) d'una rèplica dita en amazic en un programa de televisió marroquí. Torna NOMÉS la traducció "
           "al català, en una sola línia, natural i correcta, sense cometes ni comentaris. Deixa els noms propis tal "
           "com són; «إن شاء الله» és «si Déu vol». Si l'àrab és incomplet o no té sentit, tradueix el que hi ha sense "
           "inventar res.")


def primera_linia(t):
    ls = [l.strip().strip('«»"') for l in (t or "").splitlines() if l.strip()]
    return ls[0] if ls else ""


def tradueix_arab(model, text, casa):
    msgs = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": f"Àrab: {text}\n\nCatalà:"}]
    if casa == "deepseek":
        out, u = comu.xat(model, msgs, max_tokens=300, base=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                          key=os.environ.get("DEEPSEEK_API_KEY", ""))
    else:
        out, u = comu.xat(model, msgs, max_tokens=300)
    return primera_linia(out), u.get("total_tokens", 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--model1", default=os.environ.get("TD_MODEL_AR1", "qwen3.8-max"))
    ap.add_argument("--model2", default=os.environ.get("TD_MODEL_AR2", "deepseek-chat"), help="«cap» per saltar-lo")
    ap.add_argument("--space", default=os.environ.get("TD_SPACE_NLLB", "josepabloucr/Finetuned-Quantized-NLLB"))
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--nomes", type=int, default=0, help="només els primers N subtítols (per provar)")
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    log = io.open(os.path.join(carpeta, "fabrica.log"), "a", encoding="utf-8")
    files = comu.jsonl_llegeix(os.path.join(carpeta, "subtitols.jsonl"))
    if a.nomes:
        files = files[:a.nomes]
    model2 = None if a.model2.lower() in ("cap", "none", "") or not os.environ.get("DEEPSEEK_API_KEY") else a.model2
    comu.diu(log, f"== {ETAPA} {time.strftime('%Y-%m-%d %H:%M')} {a.model1} + {model2 or 'cap segon model'} + Space {a.space}")
    sortida = os.path.join(carpeta, "traduccions.jsonl")
    fets = {x["k"]: x for x in comu.jsonl_llegeix(sortida)}
    per_k = {f["k"]: f for f in files}

    def cal_refer(k):
        v = fets.get(k)
        if not v:
            return True
        f = per_k[k]
        return (v.get("arab") != f["arab"] or v.get("tifinag") != f["tifinag"] or v.get("error_ar1")
                or (model2 and not v.get("ca_ar2") and f["arab"]) or (f["tifinag"] and not v.get("ca_tif")))

    feines = [f["k"] for f in files if cal_refer(f["k"])]
    comu.diu(log, f"{len(files)} subtítols, {len(feines)} a traduir")
    if feines and fets:
        comu.jsonl_escriu(sortida, [fets[k] for k in sorted(fets) if k not in feines])
    space = None
    if any(per_k[k]["tifinag"] for k in feines):
        from gradio_client import Client
        space = Client(a.space)
    sem_space = threading.Semaphore(2)
    fitxes = {"ar1": 0, "ar2": 0}
    pany = threading.Lock()

    def tif_ca(text):
        if not text or space is None:
            return "", None
        err = ""
        for intent in range(3):
            try:
                with sem_space:
                    return space.predict(text, "Standard Moroccan Tamazight", "Catalan", 237, 4, 1.0, api_name="/predict"), None
            except Exception as e:
                err = str(e)[:120]; time.sleep(3 + 5 * intent)
        return "", err

    def feina(k):
        f = per_k[k]
        vell = fets.get(k) or {}
        r = {"k": k, "arab": f["arab"], "tifinag": f["tifinag"], "ca_ar1": vell.get("ca_ar1", ""), "ca_ar2": vell.get("ca_ar2", ""),
             "ca_tif": vell.get("ca_tif", ""), "error_ar1": None, "error_ar2": None, "error_tif": None}
        if f["arab"] and (vell.get("arab") != f["arab"] or not r["ca_ar1"]):
            try:
                r["ca_ar1"], n = tradueix_arab(a.model1, f["arab"], "modelstudio")
                with pany:
                    fitxes["ar1"] += n
            except Exception as e:
                r["error_ar1"] = str(e)[:120]
        if model2 and f["arab"] and (vell.get("arab") != f["arab"] or not r["ca_ar2"]):
            try:
                r["ca_ar2"], n = tradueix_arab(model2, f["arab"], "deepseek")
                with pany:
                    fitxes["ar2"] += n
            except Exception as e:
                r["error_ar2"] = str(e)[:120]
        if f["tifinag"] and (vell.get("tifinag") != f["tifinag"] or not r["ca_tif"]):
            r["ca_tif"], r["error_tif"] = tif_ca(f["tifinag"])
        r["acord_ar"] = comu.chrf(r["ca_ar2"], r["ca_ar1"]) if r["ca_ar1"] and r["ca_ar2"] else None
        r["chrf"] = comu.chrf(r["ca_tif"], r["ca_ar1"]) if r["ca_tif"] and r["ca_ar1"] else None
        return r

    t0 = time.time()
    n = 0
    with io.open(sortida, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=a.fils) as ex:
        for r in ex.map(feina, feines):
            with pany:
                out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
                fets[r["k"]] = r
                n += 1
                if n % 100 == 0:
                    comu.diu(log, f"  {n}/{len(feines)} {time.time() - t0:.0f} s")
    tot = [fets[k] for k in sorted(fets)]
    acord = [x["acord_ar"] for x in tot if x.get("acord_ar") is not None]
    ch = [x["chrf"] for x in tot if x.get("chrf") is not None]
    est = {"traduits": len(tot), "model1": a.model1, "model2": model2, "space": a.space,
           "fitxes_ar1": fitxes["ar1"] + (comu.estat_llegeix(carpeta).get(ETAPA, {}).get("fitxes_ar1", 0)),
           "fitxes_ar2": fitxes["ar2"] + (comu.estat_llegeix(carpeta).get(ETAPA, {}).get("fitxes_ar2", 0)),
           "acord_ar_mitja": round(sum(acord) / len(acord), 4) if acord else None,
           "chrf_tif_mitja": round(sum(ch) / len(ch), 4) if ch else None,
           "errors": sum(1 for x in tot if x.get("error_ar1") or x.get("error_tif")),
           "segons": round(time.time() - t0), "fet": not a.nomes}
    comu.estat_desa(carpeta, ETAPA, **est)
    comu.diu(log, f"{ETAPA}: {len(tot)} traduïts, acord àrab {est['acord_ar_mitja']}, chrF tifinag {est['chrf_tif_mitja']}, {est['segons']} s")


if __name__ == "__main__":
    main()
