# -*- coding: utf-8 -*-
"""Etapa 04: el català de cada rèplica (§4 i §3.3).

  python -X utf8 04_tradueix.py <carpeta_del_capitol> [--fils 4] [--nomes N]

- Àrab → català amb dos models (`qwen3.8-max` a Model Studio i `deepseek-chat`; temperatura 0; el prompt de
  tools/tutlait/tradueix_ar_ca.py): `catala_a`, `catala_b`, `model_a`, `model_b`, `chrf_ab`.
- Si 0,3 ≤ chrf_ab < 0,5, un tercer (`gemini-2.5-flash` només si hi ha crèdit, que avui no; si no, `qwen4-max`) i
  es queda el dels dos que coincideixi ≥ 0,5 amb el tercer (`catala_estat` = «tercer»). Si chrf_ab ≥ 0,5,
  `catala` = `catala_a` («confirmat»). Si no hi ha acord, «descartat» i `catala` buit.
- Tifinag → català amb el nostre Space, només per mesurar: `catala_de_tifinag` i `chrf_tif_ar` (contra `catala`).
Reprèn per id: una fila amb `catala_estat` i sense error no es repeteix; si l'àrab o el tifinag han canviat, sí.
Els crèdits no es tradueixen.
"""
import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "04_tradueix"
MODEL_A = os.environ.get("TD_MODEL_AR_A", "qwen3.8-max")
MODEL_B = os.environ.get("TD_MODEL_AR_B", "deepseek-chat")
MODEL_C = os.environ.get("TD_MODEL_AR_C", "qwen4-max")
SPACE = os.environ.get("TD_SPACE_NLLB", "josepabloucr/Finetuned-Quantized-NLLB")
CONFIRMAT, DUBTE = 0.5, 0.3
SISTEMA = ("Ets un traductor de l'àrab al català. T'arriba la traducció àrab (àrab estàndard, de vegades amb "
           "trets marroquins) d'una frase dita en amazic per algú del Marroc: una frase de conversa, un conte, "
           "una dita o una frase solta. Torna NOMÉS la traducció al català, en una sola línia, natural i correcta, "
           "sense cometes ni comentaris. Deixa els noms propis tal com són; «إن شاء الله» és «si Déu vol». "
           "Si l'àrab és incomplet o no té sentit, tradueix el que hi ha sense inventar res.")


def primera_linia(t):
    ls = [l.strip().strip('«»"') for l in (t or "").splitlines() if l.strip()]
    return ls[0] if ls else ""


def tradueix(model, text):
    msgs = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": f"Àrab: {text}\n\nCatalà:"}]
    if model.startswith("deepseek"):
        out, u = comu.xat(model, msgs, max_tokens=300, base=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                          key=os.environ.get("DEEPSEEK_API_KEY", ""))
    else:
        out, u = comu.xat(model, msgs, max_tokens=300)
    return primera_linia(out), u.get("total_tokens", 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--nomes", type=int, default=0)
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    log = comu.obre_log(carpeta)
    comu.etapa_inici(carpeta, ETAPA)
    t0 = time.time()
    try:
        files = comu.subtitols(carpeta)
        if not files:
            raise RuntimeError("sense subtitols.jsonl")
        te_b = bool(os.environ.get("DEEPSEEK_API_KEY"))
        comu.diu(log, f"== {ETAPA} {comu.ara()} {MODEL_A} + {MODEL_B if te_b else 'cap segon model (sense DEEPSEEK_API_KEY)'} + tercer {MODEL_C} + Space {SPACE}")
        fitxes = {MODEL_A: 0, MODEL_B: 0, MODEL_C: 0}
        pany = threading.Lock()

        def cal(f):
            if f.get("credits") or not f.get("arab"):
                return False
            if f.get("catala_estat") and not f.get("error_traduccio") and f.get("arab_traduit") == f["arab"]:
                return not f.get("tifinag") or f.get("tifinag_traduit") == f.get("tifinag")
            return True

        feines = [f for f in files if cal(f)]
        if a.nomes:
            feines = feines[:a.nomes]
        comu.diu(log, f"{len(files)} rèpliques, {len(feines)} a traduir")
        space = None
        if any(f.get("tifinag") for f in feines):
            try:
                from gradio_client import Client
                space = Client(SPACE)
            except Exception as e:
                comu.diu(log, f"Space no disponible: {e}")
        sem = threading.Semaphore(2)

        def tif_ca(text):
            if not text or space is None:
                return ""
            for intent in range(3):
                try:
                    with sem:
                        return space.predict(text, "Standard Moroccan Tamazight", "Catalan", 237, 4, 1.0, api_name="/predict")
                except Exception:
                    time.sleep(3 + 5 * intent)
            return ""

        def feina(f):
            err = None
            canvi_arab = f.get("arab_traduit") != f["arab"] or not f.get("catala_a")
            if canvi_arab:
                try:
                    f["catala_a"], n = tradueix(MODEL_A, f["arab"]); f["model_a"] = MODEL_A
                    with pany:
                        fitxes[MODEL_A] += n
                except Exception as e:
                    f["catala_a"] = ""; err = f"a: {str(e)[:80]}"
                f["catala_b"] = ""; f["model_b"] = None
                if te_b:
                    try:
                        f["catala_b"], n = tradueix(MODEL_B, f["arab"]); f["model_b"] = MODEL_B
                        with pany:
                            fitxes[MODEL_B] += n
                    except Exception as e:
                        err = (err or "") + f" b: {str(e)[:80]}"
                f["chrf_ab"] = comu.chrf(f["catala_b"], f["catala_a"]) if f["catala_a"] and f["catala_b"] else None
                f["catala_c"] = None
                if f["chrf_ab"] is None:
                    # un sol model: no hi ha acord possible; es guarda com a «tercer» només si el tercer hi coincideix
                    ok = False
                    if f["catala_a"]:
                        try:
                            f["catala_c"], n = tradueix(MODEL_C, f["arab"])
                            with pany:
                                fitxes[MODEL_C] += n
                            ok = comu.chrf(f["catala_c"], f["catala_a"]) >= CONFIRMAT
                        except Exception as e:
                            err = (err or "") + f" c: {str(e)[:80]}"
                    f["catala"], f["catala_estat"] = (f["catala_a"], "tercer") if ok else ("", "descartat")
                elif f["chrf_ab"] >= CONFIRMAT:
                    f["catala"], f["catala_estat"] = f["catala_a"], "confirmat"
                elif f["chrf_ab"] >= DUBTE:
                    try:
                        f["catala_c"], n = tradueix(MODEL_C, f["arab"])
                        with pany:
                            fitxes[MODEL_C] += n
                    except Exception as e:
                        f["catala_c"] = ""; err = (err or "") + f" c: {str(e)[:80]}"
                    ca, cb = comu.chrf(f["catala_c"], f["catala_a"]), comu.chrf(f["catala_c"], f["catala_b"])
                    if max(ca, cb) >= CONFIRMAT:
                        f["catala"], f["catala_estat"] = (f["catala_a"] if ca >= cb else f["catala_b"]), "tercer"
                    else:
                        f["catala"], f["catala_estat"] = "", "descartat"
                else:
                    f["catala"], f["catala_estat"] = "", "descartat"
                f["arab_traduit"] = f["arab"]
            if f.get("tifinag") and (f.get("tifinag_traduit") != f["tifinag"] or not f.get("catala_de_tifinag")):
                f["catala_de_tifinag"] = tif_ca(f["tifinag"]); f["tifinag_traduit"] = f["tifinag"]
            elif not f.get("tifinag"):
                f["catala_de_tifinag"] = ""
            ref = f.get("catala") or ""
            f["chrf_tif_ar"] = comu.chrf(f.get("catala_de_tifinag", ""), ref) if ref and f.get("catala_de_tifinag") else None
            f["error_traduccio"] = err
            return f

        n = 0
        with ThreadPoolExecutor(max_workers=a.fils) as ex:
            for _ in ex.map(feina, feines):
                n += 1
                if n % 100 == 0:
                    with pany:
                        comu.desa_subtitols(carpeta, files)
                    comu.diu(log, f"  {n}/{len(feines)} {time.time() - t0:.0f} s")
        comu.desa_subtitols(carpeta, files)
        dial = [f for f in files if not f.get("credits") and f.get("arab")]
        estats = {e: sum(1 for f in dial if f.get("catala_estat") == e) for e in ("confirmat", "tercer", "descartat")}
        ab = [f["chrf_ab"] for f in dial if f.get("chrf_ab") is not None]
        vell = comu.estat_llegeix(carpeta).get(ETAPA, {}).get("comptes", {})
        comptes = {"traduides": len(dial), "estats": estats, "chrf_ab_mitja": round(sum(ab) / len(ab), 4) if ab else None,
                   "fitxes_text": {m: fitxes[m] + (vell.get("fitxes_text") or {}).get(m, 0) for m in fitxes},
                   "model_a": MODEL_A, "model_b": MODEL_B if te_b else None, "model_c": MODEL_C, "space": SPACE,
                   "errors": sum(1 for f in dial if f.get("error_traduccio")), "segons": round(time.time() - t0)}
        comu.etapa_fi(carpeta, ETAPA, comptes)
        comu.diu(log, f"{ETAPA}: {estats}, chrf_ab {comptes['chrf_ab_mitja']}, {comptes['segons']} s")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {e}")
        raise


if __name__ == "__main__":
    main()
