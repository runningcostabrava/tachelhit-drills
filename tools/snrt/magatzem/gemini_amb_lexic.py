"""Gemini 2.5 Pro amb els nostres lexics a la peticio, contra el NLLB: tifinag -> arab, 200 linies.

A la prova a cegues de 40 linies (DESXIFRAT §56), Gemini 2.5 Pro feia 0,443 i el NLLB 0,333. Aqui
es mira si aguanta amb 200 linies noves del test net i si els lexics hi ajuden. Els lexics son els
de `backend/lexicon.grounding_lines` (Oulhaj, IRCAM-DGLAI, conjugacions IRCAM, Wikimawal), els
mateixos que ja fa servir el tutor de l'app.

Tres condicions sobre les mateixes linies i amb el mateix chrF dels quaderns de la via 3:
NLLB-ca (el punt de partida de text), Gemini Pro sense lexic, Gemini Pro amb lexic. Lots de 20
linies, una crida per lot i per condicio.

    python -X utf8 gemini_amb_lexic.py          # des de qualsevol lloc; fa servir backend/.env
"""
import io
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
CASA = Path(r"C:/Users/josep/app2/tachelhit-drills/backend")   # .env i lexics descarregats
sys.path.insert(0, str(ARREL / "backend"))
from dotenv import load_dotenv                          # noqa: E402
load_dotenv(CASA / ".env")
import gemini_client as g                               # noqa: E402
import lexicon                                          # noqa: E402

TEST = Path(r"E:/tamazight/_magatzem/zgh_ar/test.jsonl")
JA_VISTES = Path(r"E:/tamazight/_magatzem/tirades/cadena/cec_claude_40.json")
FORA = Path(r"E:/tamazight/_magatzem/tirades/cadena/gemini_amb_lexic.json")
NLLB = Path(r"E:/tamazight/TD_TV/models/nllb-ca-ct2")
N, LOT, LLAVOR = 200, 20, 2026


def chrf(hip, ref, n=6, beta=2.0):
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
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def interval(a, b, voltes=2000):
    d = [x - y for x, y in zip(a, b)]
    rng = random.Random(1)
    m = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(voltes))
    return sum(d) / len(d), m[int(voltes * .025)], m[int(voltes * .975)]


SISTEMA = ("Ets un traductor expert de taixelhit (amazic del Souss, escrit en tifinag) a l'àrab "
           "estàndard. Són subtítols d'un programa literari de la televisió marroquina (Tadfi n "
           "Tskla); el tifinag ve d'un lector automàtic i pot portar alguna lletra equivocada. "
           "Tradueix cada línia a l'àrab, una per línia, amb el número i un tabulador al davant. "
           "No afegeixis res més.")
AMB_LEXIC = (" Per a cada línia et dono entrades de diccionari de les seves paraules (poden ser "
             "d'una altra variant o d'un altre sentit: fes-les servir només si encaixen).")


def gemini(linies, lexic):
    parts = []
    for i, t in enumerate(linies, 1):
        parts.append(f"{i}\t{t}")
        if lexic:
            gl = lexicon.grounding_lines(t)[:12]
            if gl:
                parts.append("   diccionari:\n" + "\n".join("   " + x for x in gl))
    for intent in range(3):
        try:
            out = g.gemini_generate(SISTEMA + (AMB_LEXIC if lexic else ""),
                                    [{"role": "user", "text": "\n".join(parts)}],
                                    max_output_tokens=12000, temperature=0.2,
                                    thinking_budget=2048, timeout=300)
            break
        except Exception as e:
            print(f"   reintent {intent + 1}: {str(e)[:120]}", flush=True)
            time.sleep(20)
    else:
        raise RuntimeError("Gemini no respon")
    d = {}
    for l in out.splitlines():
        m = re.match(r"\s*(\d+)\s*[\t.\-:)]\s*(.*)", l)
        if m:
            d[int(m.group(1))] = m.group(2).strip()
    return [d.get(i, "") for i in range(1, len(linies) + 1)]


def nllb(linies):
    import ctranslate2
    import transformers
    tok = transformers.AutoTokenizer.from_pretrained(str(NLLB), src_lang="zgh_Tfng")
    tr = ctranslate2.Translator(str(NLLB), device="cpu", compute_type="int8")
    pref = tok.convert_ids_to_tokens(tok.convert_tokens_to_ids(["arb_Arab"]))
    out = []
    for i in range(0, len(linies), 24):
        res = tr.translate_batch([tok.convert_ids_to_tokens(tok.encode(t)) for t in linies[i:i + 24]],
                                 target_prefix=[pref] * len(linies[i:i + 24]), beam_size=4,
                                 max_decoding_length=150)
        for r in res:
            h = r.hypotheses[0]
            h = h[1:] if h and h[0] == "arb_Arab" else h
            out.append(tok.decode(tok.convert_tokens_to_ids(h)).strip())
    return out


g.GEMINI_MODEL = "gemini-2.5-pro"
lexicon.LEX_DIR = str(CASA / "knowledge" / "lexicon")
assert lexicon.load(), lexicon.status()
vistes = {x["zgh"] for x in json.load(io.open(JA_VISTES, encoding="utf-8"))}
files = [json.loads(l) for l in io.open(TEST, encoding="utf-8") if l.strip()]
files = [x for x in files if len(x["zgh"].split()) >= 3 and x["zgh"] not in vistes]
mostra = random.Random(LLAVOR).sample(files, N)
zgh = [x["zgh"] for x in mostra]
print(f"{len(files)} candidates (sense les 40 ja vistes) · mostra {N}", flush=True)

hip = {"nllb": nllb(zgh)}
print("NLLB fet", flush=True)
for nom, lexic in (("gemini_pro", False), ("gemini_pro_lexic", True)):
    hip[nom] = []
    for i in range(0, N, LOT):
        hip[nom] += gemini(zgh[i:i + LOT], lexic)
        print(f"   {nom}: {len(hip[nom])}/{N}", flush=True)

sc = {k: [chrf(h, x["ar"]) for h, x in zip(v, mostra)] for k, v in hip.items()}
for k, v in sc.items():
    buides = sum(1 for h in hip[k] if not h)
    print(f"{k:18s} chrF {sum(v) / N:.4f} · >=0,5 {sum(1 for c in v if c >= .5)}/{N} · buides {buides}")
for a, b in (("gemini_pro", "nllb"), ("gemini_pro_lexic", "nllb"), ("gemini_pro_lexic", "gemini_pro")):
    m, lo, hi = interval(sc[a], sc[b])
    print(f"{a} - {b}: {m:+.4f} [{lo:+.4f}, {hi:+.4f}]")
for i in random.Random(1114).sample(range(N), 10):
    print(f"\nref:   {mostra[i]['ar']}")
    for k in hip:
        print(f"{k}: {hip[k][i]}")
json.dump([dict(x, **{k: hip[k][i] for k in hip}) for i, x in enumerate(mostra)],
          io.open(FORA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nescrit {FORA}")
