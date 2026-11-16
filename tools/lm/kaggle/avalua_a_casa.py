# -*- coding: utf-8 -*-
"""H-MT1 (#494, 16-11-2026), el tram de casa: a partir de nllb_sortides.json (una entrada per frase × prova × model, amb
`ca` = català directe i `en` = anglès) del nucli `nllb-afina-propi`:
  1. chrF (neteja + chrf copiats de compara.py) del català directe, per model i prova;
  2. pont: l'anglès → català amb deepseek-chat (mateix encàrrec que el peó del 16-11: una línia, sense comentaris),
     amb memòria cau per no repetir crides; chrF del pont;
  3. Δ abans → després amb IC 95 % per bootstrap aparellat (llavor 1114, 2.000 mostres) sobre les 60 (i shi / Beni
     Mellal) i les 200 de test-dins, per a cada «després» (ritme, època) i cada camí (directe, pont).
Escriu taula.md (les taules en markdown), pont_cau.json (la memòria cau de DeepSeek) i resultats_casa.json.
ÚS: avalua_a_casa.py <carpeta amb nllb_sortides.json i nllb_resultat.json>  [--sense-pont]
"""
import collections, io, json, os, random, re, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

CARPETA = sys.argv[1]
SENSE_PONT = "--sense-pont" in sys.argv
load_dotenv(r"C:\Users\josep\app2\nomatrails-seo-pipeline\.env")
KEY = os.environ.get("DEEPSEEK_API_KEY", "")
SISTEMA_DS = ("Ets un traductor de l'anglès al català. Torna NOMÉS la traducció al català, en una sola línia, "
              "sense cometes ni comentaris.")


# ---------------------------------------------------------------- chrF, copiat literalment de compara.py
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


# ---------------------------------------------------------------- pont en→ca
CAU_P = os.path.join(CARPETA, "pont_cau.json")
cau = json.load(io.open(CAU_P, encoding="utf-8")) if os.path.exists(CAU_P) else {}


def deepseek_en_ca(text):
    if not text.strip():
        return ""
    if text in cau and cau[text]:
        return cau[text]
    body = {"model": "deepseek-chat", "messages": [{"role": "system", "content": SISTEMA_DS}, {"role": "user", "content": text}],
            "max_tokens": 200, "temperature": 0}
    for intent in range(4):
        try:
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers={"Authorization": "Bearer " + KEY}, json=body, timeout=120)
            if r.status_code == 200:
                c = r.json()["choices"][0]["message"].get("content") or ""
                l = [s.strip() for s in c.splitlines() if s.strip()]
                cau[text] = l[0] if l else ""
                return cau[text]
        except Exception:
            pass
        time.sleep(2 + 3 * intent)
    return ""


# ---------------------------------------------------------------- dades
sortides = json.load(io.open(os.path.join(CARPETA, "nllb_sortides.json"), encoding="utf-8"))
res_nucli = json.load(io.open(os.path.join(CARPETA, "nllb_resultat.json"), encoding="utf-8"))
models = []
for s in sortides:
    if s["model"] not in models:
        models.append(s["model"])
per = {}   # (prova, id) -> {model: entrada}
for s in sortides:
    per.setdefault((s["prova"], s["id"]), {})[s["model"]] = s
print("models:", models)
print("proves:", collections.Counter(k[0] for k in per))

# pont només per a «abans» i per a l'última època de cada ritme (són els que compten); la resta, català directe
EPOQUES = res_nucli["config"]["epoques"]
amb_pont = ["abans"] + [m for m in models if m.endswith(f"-ep{EPOQUES}")]
# v3: els models es diuen ep1..ep5, millor, millor-ct2int8; es pot dir quins porten pont amb --pont a,b,c
for a in sys.argv:
    if a.startswith("--pont="):
        amb_pont = [m for m in a[len("--pont="):].split(",") if m in models]
if not SENSE_PONT:
    textos = sorted({s["en"] for s in sortides if s["model"] in amb_pont})
    pendents = [t for t in textos if not cau.get(t)]
    print(f"pont: {len(textos)} frases angleses distintes, {len(pendents)} per traduir")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for k, _ in enumerate(ex.map(deepseek_en_ca, pendents)):
            if k % 100 == 99:
                print("  ", k + 1, f"{time.time() - t0:.0f} s", flush=True)
                json.dump(cau, io.open(CAU_P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(cau, io.open(CAU_P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    buits = sum(1 for t in textos if not cau.get(t))
    print("pont fet en %.0f s; buits: %d" % (time.time() - t0, buits))

for s in sortides:
    s["chrf_ca"] = chrf(s["ca"], s["veritat"])
    if s["model"] in amb_pont and not SENSE_PONT:
        s["pont"] = cau.get(s["en"], "")
        s["chrf_pont"] = chrf(s["pont"], s["veritat"])


# ---------------------------------------------------------------- bootstrap aparellat
def ic(a, b, n=2000):
    """a, b: chrF per frase (mateix ordre). → mitjana a, mitjana b, Δ, IC 95 % de Δ, milloren, empitjoren."""
    rnd = random.Random(1114)
    N = len(a)
    d = [y - x for x, y in zip(a, b)]
    boots = []
    for _ in range(n):
        idx = [rnd.randrange(N) for _ in range(N)]
        boots.append(sum(d[i] for i in idx) / N)
    boots.sort()
    return (sum(a) / N, sum(b) / N, sum(d) / N, boots[int(0.025 * n)], boots[int(0.975 * n)],
            sum(1 for x in d if x > 0.0005), sum(1 for x in d if x < -0.0005))


GRUPS = {"60 frases": lambda k, e: k[0] == "mostra60", "shi (30)": lambda k, e: k[0] == "mostra60" and e["grup"] == "shi",
         "Beni Mellal (30)": lambda k, e: k[0] == "mostra60" and e["grup"] == "beni-mellal", "test-dins (200)": lambda k, e: k[0] == "test200"}
taula, linies = [], []
linies.append("| camí | grup | model | abans | després | Δ | IC 95 % | milloren / empitjoren |")
linies.append("|---|---|---|---|---|---|---|---|")
for cami, clau in [("català directe", "chrf_ca"), ("pont anglès + deepseek-chat", "chrf_pont")]:
    for m in models:
        if m == "abans" or (clau == "chrf_pont" and (SENSE_PONT or m not in amb_pont)):
            continue
        for gnom, filtre in GRUPS.items():
            claus = [k for k, v in per.items() if filtre(k, v["abans"]) and "abans" in v and m in v]
            a = [per[k]["abans"][clau] for k in claus]
            b = [per[k][m][clau] for k in claus]
            ma, mb, d, lo, hi, mill, pitj = ic(a, b)
            taula.append({"cami": cami, "grup": gnom, "model": m, "n": len(claus), "abans": ma, "despres": mb, "delta": d, "ic": [lo, hi],
                          "milloren": mill, "empitjoren": pitj})
            linies.append(f"| {cami} | {gnom} | {m} | {ma:.3f} | {mb:.3f} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {mill} / {pitj} |")
print("\n".join(linies))

# els exemples: 10 de la mostra de 60 (5 shi + 5 Beni Mellal), amb el millor «després» pel test-dins del nucli
millor = res_nucli["config"].get("millor_ritme_per_test200")
m_final = f"{millor}-ep{EPOQUES}" if millor else [m for m in models if m != "abans"][-1]
for a in sys.argv:
    if a.startswith("--exemples="):
        m_final = a[len("--exemples="):]
ex = []
m60 = [k for k in per if k[0] == "mostra60"]
rnd = random.Random(1114)
tria = rnd.sample([k for k in m60 if per[k]["abans"]["grup"] == "shi"], 5) + rnd.sample([k for k in m60 if per[k]["abans"]["grup"] == "beni-mellal"], 5)
ex.append(f"Model «després» dels exemples: `{m_final}`.\n")
ex.append("| amazic | parlant | abans (directe) | després (directe) | abans (pont) | després (pont) |")
ex.append("|---|---|---|---|---|---|")
for k in tria:
    a, b = per[k]["abans"], per[k][m_final]
    ex.append(f"| {a['amazic']} | {a['veritat']} | {a['ca']} | {b['ca']} | {a.get('pont', '—')} | {b.get('pont', '—')} |")
print("\n".join(ex))

io.open(os.path.join(CARPETA, "taula.md"), "w", encoding="utf-8").write("\n".join(linies) + "\n\n" + "\n".join(ex) + "\n")
json.dump({"taula": taula, "models": models, "amb_pont": amb_pont, "frases": sortides},
          io.open(os.path.join(CARPETA, "resultats_casa.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("escrit", os.path.join(CARPETA, "taula.md"))
