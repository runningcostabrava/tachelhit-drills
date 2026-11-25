"""Triangulacio (#763): on l'ASR (que nomes sent el so) coincideix amb el tifinag de la pantalla, el triplet es mes coherent?

Coherencia = chrF de la traduccio NLLB del tifinag de pantalla (cadena_text.json, sec. 56) contra el subtitol
arab del mateix fotograma. ASR de asr_local_snrt.py. Nomes test_snrt: el tram es tria aqui, no s'hi entrena.

    backend/venv/Scripts/python.exe -X utf8 tools/snrt/magatzem/triangulacio.py
"""
import json, os, random, statistics, sys
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "backend"))
from transliteration import to_forms

ARREL = "E:/tamazight/_magatzem"


def chrf(hip, ref, n=6):
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        com = sum((Counter(h) & Counter(r)).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    return 0.0 if p + r == 0 else 5 * p * r / (4 * p + r)


def ed(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def rangs(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rangs(a), rangs(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0.0


# CER ASR<->pantalla per tall, calculat a Kaggle (kaggle/triangulacio-asr-test.py + transliteracio, fp16; contra
# els 605 talls fets a casa en fp32: 595 iguals, diferencia mitjana 0,08 punts) i portat en ordre alfabetic de tall.
# La coherencia (chrF NLLB(pantalla) contra l'arab) i el control barrejat es calculen a casa: coh_test.json.
CER = [int(v) for v in open(f"{ARREL}/tirades/triangulacio/cer_kaggle_test.txt").read().split()]
COH = json.load(open(f"{ARREL}/tirades/triangulacio/coh_test.json"))
assert len(CER) == len(COH["so"]) == 2091 and sum(CER) == 131156
TEST = {json.loads(l)["so"]: json.loads(l) for l in open(f"{ARREL}/veu_ar/test.jsonl", encoding="utf-8") if l.strip()}
rng = random.Random(1114)
F = []
for so, c, h, bj, n in zip(COH["so"], CER, COH["coh"], COH["bar"], COH["len"]):
    if n < 4 or c < 0:
        continue
    F.append({"so": so, "cer": c / 100, "len": n, "coh": h / 1000, "barrejat": bj / 1000,
              "zgh": TEST[so]["zgh"], "ar": TEST[so]["ar"]})
print(f"TRI files {len(F)} de {len(CER)} (tifinag >=4 lletres i ASR no buit)", flush=True)

TRAMS = [(0, .1), (.1, .2), (.2, .35), (.35, .5), (.5, .75), (.75, 99)]
for lo, hi in TRAMS:
    g = [f for f in F if lo <= f["cer"] < hi]
    if not g:
        continue
    bs = []
    for _ in range(1000):
        s = [rng.choice(g)["coh"] for _ in g]
        bs.append(sum(s) / len(s))
    bs.sort()
    print(f"TRI cer [{lo:.2f},{hi:.2f}) n {len(g):4d} · llarg {statistics.mean(f['len'] for f in g):5.1f} · "
          f"coh {statistics.mean(f['coh'] for f in g):.3f} [{bs[25]:.3f},{bs[974]:.3f}] · "
          f"barrejat {statistics.mean(f['barrejat'] for f in g):.3f}", flush=True)

# control de llargada: diferencia acord-alt menys la resta dins de cada tercil de llargada
ll = sorted(f["len"] for f in F)
t1, t2 = ll[len(ll) // 3], ll[2 * len(ll) // 3]
for nom, cond in (("curtes", lambda f: f["len"] < t1), ("mitjanes", lambda f: t1 <= f["len"] < t2), ("llargues", lambda f: f["len"] >= t2)):
    g = [f for f in F if cond(f)]
    a = [f["coh"] for f in g if f["cer"] < .2]
    b = [f["coh"] for f in g if f["cer"] >= .2]
    if len(a) < 5:
        print(f"TRI {nom}: acord alt n {len(a)} massa poques", flush=True)
        continue
    ds = []
    for _ in range(1000):
        sa = [rng.choice(a) for _ in a]
        sb = [rng.choice(b) for _ in b]
        ds.append(sum(sa) / len(sa) - sum(sb) / len(sb))
    ds.sort()
    print(f"TRI {nom} (llarg {min(f['len'] for f in g)}-{max(f['len'] for f in g)}): cer<0,2 n {len(a)} coh {statistics.mean(a):.3f} · resta n {len(b)} coh {statistics.mean(b):.3f} · "
          f"dif {statistics.mean(a) - statistics.mean(b):+.3f} [{ds[25]:+.3f},{ds[974]:+.3f}]", flush=True)

cs, hs = [f["cer"] for f in F], [f["coh"] for f in F]
rho = spearman(cs, hs)
bs = []
for _ in range(500):
    idx = [rng.randrange(len(F)) for _ in F]
    bs.append(spearman([cs[i] for i in idx], [hs[i] for i in idx]))
bs.sort()
print(f"TRI spearman(cer, coh) {rho:+.3f} [{bs[12]:+.3f},{bs[487]:+.3f}]", flush=True)
for f in rng.sample([f for f in F if f["cer"] < .1], min(5, sum(1 for f in F if f["cer"] < .1))):
    print(f"TRIM cer {f['cer']:.2f} coh {f['coh']:.2f} | pantalla {f['zgh']} | ar {f['ar']}", flush=True)
json.dump(F, open(f"{ARREL}/tirades/triangulacio/triangulacio_test.json", "w", encoding="utf-8"), ensure_ascii=False)
print("TRI fet", flush=True)
