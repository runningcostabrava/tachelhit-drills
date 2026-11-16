# -*- coding: utf-8 -*-
"""L'àrab de TutlAit → català amb qwen3.8-max (Model Studio, sense raonar, temperatura 0). Una
traducció de màquina: va a traduccions.jsonl i després la jutgen els auditors (audita_arab.py). Reprèn
si es talla. Salta els talls que ja són a producció.
ÚS: tradueix_ar_ca.py [<carpeta>]   (LIMIT=n per provar)"""
import io, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import requests
from dotenv import load_dotenv

CARPETA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
load_dotenv(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", override=True)
KEY, BASE = os.environ["DASHSCOPE_API_KEY"].strip(), os.environ["DASHSCOPE_BASE_URL"].rstrip("/")
MODEL = "qwen3.8-max"
SISTEMA = ("Ets un traductor de l'àrab al català. T'arriba la traducció àrab (àrab estàndard, de vegades amb "
           "trets marroquins) d'una frase dita en amazic per algú del Marroc: una frase de conversa, un conte, "
           "una dita o una frase solta. Torna NOMÉS la traducció al català, en una sola línia, natural i correcta, "
           "sense cometes ni comentaris. Deixa els noms propis tal com són; «إن شاء الله» és «si Déu vol». "
           "Si l'àrab és incomplet o no té sentit, tradueix el que hi ha sense inventar res.")


def crida(text):
    body = {"model": MODEL, "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": f"Àrab: {text}\n\nCatalà:"}],
            "max_tokens": 300, "temperature": 0, "enable_thinking": False}
    t0 = time.time()
    err = ""
    for intent in range(4):
        try:
            r = requests.post(BASE + "/chat/completions", headers={"Authorization": "Bearer " + KEY}, json=body, timeout=90)
            if r.status_code == 200:
                cont = (r.json()["choices"][0]["message"].get("content") or "").strip()
                linies = [l.strip().strip("«»\"") for l in cont.splitlines() if l.strip()]
                return {"ca": linies[0] if linies else "", "s": round(time.time() - t0, 1)}
            if r.status_code in (429, 500, 502, 503):
                time.sleep(5 + 10 * intent)
                continue
            return {"ca": "", "s": round(time.time() - t0, 1), "error": f"{r.status_code} {r.text[:100]}"}
        except Exception as e:
            err = str(e)[:100]
            time.sleep(3 + 5 * intent)
    return {"ca": "", "s": round(time.time() - t0, 1), "error": "esgotat " + err}


def main():
    files = [json.loads(l) for l in io.open(os.path.join(CARPETA, "metadades.jsonl"), encoding="utf-8") if l.strip()]
    files = [x for x in files if not x["ja_a_produccio"] and x["text_arabic"]]
    LIMIT = int(os.environ.get("LIMIT") or 0)
    if LIMIT:
        files = files[:LIMIT]
    sortida = os.path.join(CARPETA, "prova_traduccions.jsonl" if LIMIT else "traduccions.jsonl")
    fets = set()
    if os.path.exists(sortida):
        for l in io.open(sortida, encoding="utf-8"):
            if l.strip():
                fets.add(json.loads(l)["id"])
    feines = [x for x in files if x["id"] not in fets]
    print("talls", len(files), "pendents", len(feines), flush=True)
    pany = threading.Lock()
    t0 = time.time()
    n = 0
    with io.open(sortida, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=6) as ex:
        for x, r in zip(feines, ex.map(lambda x: crida(x["text_arabic"]), feines)):
            with pany:
                out.write(json.dumps({"id": x["id"], "text_arabic": x["text_arabic"], "text_catalan": r["ca"], "model": MODEL,
                                      "s": r["s"], "error": r.get("error")}, ensure_ascii=False) + "\n")
                out.flush()
                n += 1
                if n % 500 == 0:
                    print(n, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
    print("fet en", f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
