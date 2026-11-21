# -*- coding: utf-8 -*-
"""La mateixa prova de `compara.py` (60 frases, amb i sense fonts, chrF contra el català de la fitxa),
ara amb els models de Model Studio d'Alibaba (compte nou, 16-11, quota gratuïta) pel punt d'accés de
l'espai de treball. Es comparen amb els resultats desats de DeepSeek sobre les MATEIXES frases."""
import collections, io, json, os, re, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests
from dotenv import load_dotenv

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar\backend")
load_dotenv(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", override=True)
KEY, BASE = os.environ["DASHSCOPE_API_KEY"].strip(), os.environ["DASHSCOPE_BASE_URL"]

#: (nom, pensa?) — als Qwen se'ls apaga el raonament (enable_thinking=False) perquè no es quedin sense
#: resposta; el DeepSeek servit per Alibaba raona sempre i se li dóna sostre gran.
MODELS = [("qwen4-max", False), ("qwen3.8-max", False), ("qwen3.8-flash", False), ("qwen3.8-27b", False),
          ("qwen4-max", True), ("deepseek-v4.1-flash", True)]

vell = json.load(io.open(os.path.join(AQUI, "compara_resultat.json"), encoding="utf-8"))
ids = vell["mostra"]
drills = {x["id"]: x for x in json.load(io.open(os.path.join(AQUI, "drills_prod.json"), encoding="utf-8"))}
mostra = [drills[i] for i in ids]
import lexicon
from transliteration import to_forms
lexicon.load()
for x in mostra:
    x["fonts"] = lexicon.grounding_lines(x["text_tachelhit"]) or lexicon.grounding_lines(to_forms(x["text_tachelhit"])["clean_latin"])

SISTEMA = ("Ets un traductor d'amazic (taixelhit i tamazight de l'Atles central, en tifinag o en lletres llatines) "
           "al català. Torna NOMÉS la traducció al català, en una sola línia, sense cometes ni comentaris. "
           "Si una paraula no la saps, tradueix el que puguis i no inventis.")


def prompt(x, amb_fonts):
    t = x["text_tachelhit"]
    if amb_fonts and x["fonts"]:
        return (f"Frase: {t}\n\nEl que diuen el diccionari de l'IRCAM i les taules de conjugació de les seves paraules "
                f"(poden ser coincidències aproximades):\n" + "\n".join("- " + l for l in x["fonts"][:14]) + "\n\nTraducció al català:")
    return f"Frase: {t}\n\nTraducció al català:"


def crida(model, pensa, text):
    body = {"model": model, "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": text}],
            "max_tokens": 8000 if pensa else 400, "temperature": 0}
    if model.startswith("qwen"):
        body["enable_thinking"] = pensa
    t0 = time.time()
    for intent in range(3):
        try:
            r = requests.post(BASE + "/chat/completions", headers={"Authorization": "Bearer " + KEY}, json=body, timeout=300)
            if r.status_code == 200:
                d = r.json()
                ch = d["choices"][0]["message"]
                u = d.get("usage", {})
                linies = [l.strip() for l in (ch.get("content") or "").splitlines() if l.strip()]
                return {"dit": linies[0] if linies else "", "s": round(time.time() - t0, 2), "in": u.get("prompt_tokens", 0),
                        "out": u.get("completion_tokens", 0), "fi": d["choices"][0].get("finish_reason")}
            if r.status_code == 429:
                time.sleep(5 + 5 * intent)
            else:
                return {"dit": "", "s": round(time.time() - t0, 2), "in": 0, "out": 0, "error": r.text[:120]}
        except Exception as e:
            time.sleep(3 + 3 * intent)
    return {"dit": "", "s": round(time.time() - t0, 2), "in": 0, "out": 0, "error": "esgotat"}


def neteja(s):
    s = re.sub(r"[^\w\s]", " ", (s or "").lower())
    return " ".join(s.split())


def ngrams(s, n):
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def chrf(hip, ref, N=6, beta=2.0):
    hip, ref = neteja(hip), neteja(ref)
    if not hip or not ref:
        return 0.0
    P = R = 0.0; k = 0
    for n in range(1, N + 1):
        h, r = ngrams(hip, n), ngrams(ref, n)
        if not h or not r:
            continue
        comu = sum((h & r).values())
        P += comu / max(1, sum(h.values())); R += comu / max(1, sum(r.values())); k += 1
    if not k:
        return 0.0
    P, R = P / k, R / k
    return 0.0 if P + R == 0 else (1 + beta ** 2) * P * R / (beta ** 2 * P + R)


feines = [(i, m, p, c) for i in range(len(mostra)) for m, p in MODELS for c in ("sense", "amb")]
res = {}
t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    for k, (f, r) in enumerate(ex.map(lambda f: (f, crida(f[1], f[2], prompt(mostra[f[0]], f[3] == "amb"))), feines)):
        res[f] = r
        if k % 60 == 59:
            print(k + 1, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
print("crides fetes en", f"{time.time() - t0:.0f} s")

# DeepSeek sobre les mateixes frases (per a la columna de comparació)
ds = {(s["id"], s["model"], s["fonts"]): s for s in vell["frases"]}
sortida, files = [], []
print("\n| model | raona | fonts | buits | chrF (60, buit=0) | chrF contestades | v4-pro sobre les mateixes | flash | chat | latència | fitxes de sortida |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for m, p in MODELS:
    for c in ("sense", "amb"):
        rs = [(i, res[(i, m, p, c)]) for i in range(len(mostra))]
        sc = {i: chrf(r["dit"], mostra[i]["text_catalan"]) for i, r in rs}
        ple = [i for i, r in rs if r["dit"]]
        def mitj_ds(model):
            v = [ds[(mostra[i]["id"], model, c)]["chrf"] for i in ple if ds[(mostra[i]["id"], model, c)]["dit"]]
            return statistics.mean(v) if v else 0
        fila = (m, p, c, 60 - len(ple), statistics.mean(sc.values()), statistics.mean(sc[i] for i in ple) if ple else 0,
                mitj_ds("deepseek-v4-pro"), mitj_ds("deepseek-flash"), mitj_ds("deepseek-chat"),
                statistics.median(r["s"] for _, r in rs), sum(r["out"] for _, r in rs), sum(1 for _, r in rs if r.get("error")))
        files.append(fila)
        print(f"| `{m}` | {'sí' if p else 'no'} | {c} | {fila[3]} | {fila[4]:.3f} | **{fila[5]:.3f}** | {fila[6]:.3f} | {fila[7]:.3f} | {fila[8]:.3f} | {fila[9]:.1f} s | {fila[10]} | errors {fila[11]} |")
        for i, r in rs:
            sortida.append({"id": mostra[i]["id"], "font": "shi" if i < 30 else "beni-mellal", "amazic": mostra[i]["text_tachelhit"],
                            "veritat": mostra[i]["text_catalan"], "model": m, "raona": p, "fonts": c, "dit": r["dit"], "chrf": round(sc[i], 3), "s": r["s"], "fi": r.get("fi"), "error": r.get("error")})
json.dump({"taula": files, "frases": sortida}, io.open(os.path.join(AQUI, "compara_qwen_resultat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("\nMostra a ull (veritat | qwen4-max amb fonts | deepseek-v4-pro amb fonts):")
per = {(s["id"], s["model"], s["raona"], s["fonts"]): s["dit"] for s in sortida}
for x in mostra[:6] + mostra[30:36]:
    print(f"- {x['text_tachelhit'][:36]} → «{x['text_catalan'][:42]}» | qwen4: «{per[(x['id'], 'qwen4-max', False, 'amb')][:42]}» | pro: «{ds[(x['id'], 'deepseek-v4-pro', 'amb')]['dit'][:42]}»")
