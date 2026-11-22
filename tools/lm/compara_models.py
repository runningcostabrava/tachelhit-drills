# -*- coding: utf-8 -*-
"""Quin model de text ens fa la feina (16-11-2026): els models que tenim clau (DeepSeek directe:
deepseek-chat, deepseek-flash, deepseek-v4-pro) sobre UNA tasca nostra amb veritat: traduir al
català 60 frases de la biblioteca (30 taixelhit en tifinag de `tamazight.drills`, 30 tamazight de
Beni Mellal en llatí de l'Anki), amb i sense les fonts del diccionari al davant (`lexicon.grounding_lines`).
La veritat és el català que hi ha a la fitxa. Mesura: chrF (n-grames de caràcters 1-6, β=2) contra la
veritat, latència i fitxes gastades (preu de llista de DeepSeek en hora punta).
Gemini no es pot córrer (402: sense crèdit). Qwen per DashScope: compte «not in good standing».
HF Inference Providers: sense crèdits. Només DeepSeek contesta.
"""
import collections, io, json, os, random, re, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

AQUI = os.path.dirname(os.path.abspath(__file__))
ARREL = r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar"
sys.path.insert(0, os.path.join(ARREL, "backend"))
load_dotenv(r"C:\Users\josep\app2\nomatrails-seo-pipeline\.env")   # DEEPSEEK_API_KEY
KEY = os.environ["DEEPSEEK_API_KEY"]

MODELS = [("deepseek-chat", 400), ("deepseek-flash", 6000), ("deepseek-v4-pro", 6000)]
PREU = {"deepseek-chat": (0.30, 1.20), "deepseek-flash": (0.30, 1.20), "deepseek-v4-pro": (1.32, 3.96)}  # USD/M, punta

# ---------------------------------------------------------------- la mostra
tots = json.load(io.open(os.path.join(AQUI, "drills_prod.json"), encoding="utf-8"))
amb = [x for x in tots if (x.get("text_tachelhit") or "").strip() and (x.get("text_catalan") or "").strip()
       and 2 <= len(x["text_tachelhit"].split()) <= 12 and not x.get("is_correction_dataset")]
rnd = random.Random(1114)
a = [x for x in amb if x.get("author") == "tamazight.drills" and x.get("variety") == "shi"]
b = [x for x in amb if (x.get("author") or "").startswith("Anki")]
rnd.shuffle(a); rnd.shuffle(b)
mostra = a[:30] + b[:30]
print(len(mostra), "frases:", len(a[:30]), "shi (tifinag) +", len(b[:30]), "Beni Mellal (Anki)")

# ---------------------------------------------------------------- les fonts
import lexicon
lexicon.load()
print("lèxic:", {k: v for k, v in lexicon.status().items() if k in ("loaded", "dictionary_forms", "conj_forms", "dglai_forms")})
from transliteration import to_forms
for x in mostra:
    x["fonts"] = lexicon.grounding_lines(x["text_tachelhit"]) or lexicon.grounding_lines(to_forms(x["text_tachelhit"])["clean_latin"])
print("frases amb alguna font:", sum(1 for x in mostra if x["fonts"]), "de", len(mostra))

SISTEMA = ("Ets un traductor d'amazic (taixelhit i tamazight de l'Atles central, en tifinag o en lletres llatines) "
           "al català. Torna NOMÉS la traducció al català, en una sola línia, sense cometes ni comentaris. "
           "Si una paraula no la saps, tradueix el que puguis i no inventis.")


def prompt(x, amb_fonts):
    t = x["text_tachelhit"]
    if amb_fonts and x["fonts"]:
        return (f"Frase: {t}\n\nEl que diuen el diccionari de l'IRCAM i les taules de conjugació de les seves paraules "
                f"(poden ser coincidències aproximades):\n" + "\n".join("- " + l for l in x["fonts"][:14]) +
                "\n\nTraducció al català:")
    return f"Frase: {t}\n\nTraducció al català:"


def crida(model, max_tokens, text):
    body = {"model": model, "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": text}],
            "max_tokens": max_tokens, "temperature": 0}
    t0 = time.time()
    for intent in range(3):
        try:
            r = requests.post("https://api.deepseek.com/chat/completions", headers={"Authorization": "Bearer " + KEY},
                              json=body, timeout=180)
            if r.status_code == 200:
                d = r.json()
                ch = d["choices"][0]["message"]
                u = d.get("usage", {})
                linies = [l.strip() for l in (ch.get("content") or "").splitlines() if l.strip()]
                return {"dit": linies[0] if linies else "", "s": round(time.time() - t0, 2),
                        "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0),
                        "raona": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)}
            time.sleep(2 + 3 * intent)
        except Exception:
            time.sleep(2 + 3 * intent)
    return {"dit": "", "s": round(time.time() - t0, 2), "in": 0, "out": 0, "raona": 0, "error": True}


# ---------------------------------------------------------------- chrF
def neteja(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def ngrams(s, n):
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def chrf(hip, ref, N=6, beta=2.0):
    hip, ref = neteja(hip), neteja(ref)
    if not hip or not ref:
        return 0.0
    P = R = 0.0
    k = 0
    for n in range(1, N + 1):
        h, r = ngrams(hip, n), ngrams(ref, n)
        if not h or not r:
            continue
        comu = sum((h & r).values())
        P += comu / max(1, sum(h.values()))
        R += comu / max(1, sum(r.values()))
        k += 1
    if not k:
        return 0.0
    P, R = P / k, R / k
    if P + R == 0:
        return 0.0
    return (1 + beta ** 2) * P * R / (beta ** 2 * P + R)


# ---------------------------------------------------------------- córrer
feines = [(i, m, mt, c) for i in range(len(mostra)) for m, mt in MODELS for c in ("sense", "amb")]
res = {}


def una(f):
    i, m, mt, c = f
    return f, crida(m, mt, prompt(mostra[i], c == "amb"))


t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    for k, (f, r) in enumerate(ex.map(una, feines)):
        res[f] = r
        if k % 40 == 39:
            print(k + 1, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
print("crides fetes en", f"{time.time() - t0:.0f} s")

# ---------------------------------------------------------------- taula
sortida = []
files = []
for m, _ in MODELS:
    for c in ("sense", "amb"):
        rs = [res[(i, m, _, c)] for i in range(len(mostra))]
        sc = [chrf(r["dit"], mostra[i]["text_catalan"]) for i, r in enumerate(rs)]
        sc_a = [s for i, s in enumerate(sc) if i < 30]
        sc_b = [s for i, s in enumerate(sc) if i >= 30]
        cost = sum(r["in"] for r in rs) / 1e6 * PREU[m][0] + sum(r["out"] for r in rs) / 1e6 * PREU[m][1]
        files.append((m, c, statistics.mean(sc), statistics.mean(sc_a), statistics.mean(sc_b),
                      statistics.median(r["s"] for r in rs), sum(r["raona"] for r in rs), cost, sum(1 for r in rs if r.get("error"))))
        for i, r in enumerate(rs):
            sortida.append({"id": mostra[i]["id"], "font": "shi" if i < 30 else "beni-mellal", "amazic": mostra[i]["text_tachelhit"],
                            "veritat": mostra[i]["text_catalan"], "model": m, "fonts": c, "dit": r["dit"], "chrf": round(sc[i], 3), "s": r["s"]})
print()
print("| model | fonts | chrF (60) | chrF shi (30) | chrF Beni Mellal (30) | latència mediana | fitxes de raonament | cost 60 frases (USD, punta) | errors |")
print("|---|---|---|---|---|---|---|---|---|")
for f in files:
    print(f"| `{f[0]}` | {f[1]} | **{f[2]:.3f}** | {f[3]:.3f} | {f[4]:.3f} | {f[5]:.1f} s | {f[6]} | {f[7]:.4f} | {f[8]} |")
json.dump({"taula": files, "frases": sortida, "mostra": [x["id"] for x in mostra]},
          io.open(os.path.join(AQUI, "compara_resultat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
# les 8 frases on els models més discrepen (per mirar a ull)
per = collections.defaultdict(list)
for s in sortida:
    per[s["id"]].append(s)
print("\nMostra a ull (veritat | chat amb fonts | v4-pro amb fonts):")
for x in mostra[:6] + mostra[30:36]:
    d = {(s["model"], s["fonts"]): s["dit"] for s in per[x["id"]]}
    print(f"- {x['text_tachelhit'][:40]} → «{x['text_catalan'][:45]}» | chat: «{d[('deepseek-chat','amb')][:45]}» | pro: «{d[('deepseek-v4-pro','amb')][:45]}»")
