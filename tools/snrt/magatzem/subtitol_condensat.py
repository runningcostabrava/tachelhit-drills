"""El subtitol d'aquells episodis es un resum del que es diu?

Mecanisme que explicaria tot el que s'ha vist sense que res estigui espatllat: si el subtitol
es CONDENSAT -- el convidat diu dotze paraules i la pantalla n'escriu sis -- l'orella pot
encertar i l'acord s'esfondra igualment, perque la regla compara cadenes senceres. I el text
sentit no casaria amb cap linia de l'episodi, que es exactament el que passa.

Es mesura amb una divisio: quantes paraules sent l'orella per cada paraula que escriu l'ull, i
quants segons de so hi ha per paraula escrita. Si als episodis dolents la rao es el doble que
als bons, el subtitol es un resum i aixo no te arranjament tecnic: nomes vol dir que d'aquells
episodis no se'n pot aprendre so paraula per paraula.
"""
import io, json, os, glob, sys, statistics
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

per_cap = {}
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    s = sentit.get(x["id"], {})
    ull = [w for w in (x.get("tifinag") or "").split() if esquelet(w)]
    orella = [p for p in (s.get("paraules") or []) if esquelet(p["p"])]
    if not ull or not orella:
        continue
    eu, eo = esquelet(x.get("tifinag") or ""), esquelet(s.get("sentit") or "")
    d = per_cap.setdefault(x["capitol"], {"raons": [], "A": 0, "n": 0, "segons": [], "cons": []})
    d["raons"].append(len(orella) / len(ull))
    d["cons"].append(len(eo) / max(1, len(eu)))
    d["n"] += 1
    if eu and eo:
        d["A"] += (lev(eu, eo) / max(len(eu), len(eo))) <= .35
    if x.get("t_ini") is not None and x.get("t_fi") is not None:
        d["segons"].append((float(x["t_fi"]) - float(x["t_ini"])) / len(ull))

print(f"{'convidat':<26}{'acord':>7}{'paraules oides':>16}{'consonants':>12}{'s/paraula':>11}")
print(f"{'':<26}{'':>7}{'per escrita':>16}{'oides/escrites':>12}{'escrita':>11}")
files = sorted(per_cap.items(), key=lambda kv: -(kv[1]["A"] / max(1, kv[1]["n"])))
for cap, d in files:
    if d["n"] < 50:
        continue
    print(f"{titols.get(cap, cap)[:24]:<26}{100*d['A']/d['n']:6.1f}%"
          f"{statistics.median(d['raons']):16.2f}{statistics.median(d['cons']):12.2f}"
          f"{statistics.median(d['segons']) if d['segons'] else 0:11.2f}")

bons = [d for c, d in files[:8] if d["n"] >= 50]
dolents = [d for c, d in files[-10:] if d["n"] >= 50]
mb = statistics.median([r for d in bons for r in d["raons"]])
md = statistics.median([r for d in dolents for r in d["raons"]])
print(f"\nparaules oides per escrita: als vuit millors {mb:.2f}, als deu pitjors {md:.2f}")
print("si el subtitol fos un resum, als pitjors seria clarament mes gran")
