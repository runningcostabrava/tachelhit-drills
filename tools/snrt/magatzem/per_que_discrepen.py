"""Per què un capítol té 0,8 % d'acord i un altre 39 %, amb el mateix model escoltant.

Si fos l'OCR, es veuria al text (i al capítol dolent `tskla` surt 10 de 10: l'OCR va bé).
Queden dues explicacions i s'han de separar:

  a) **l'àudio**: el model no entén el que sent (confiança baixa) o els talls no casen amb les
     línies, i llavors no hi ha res a comparar;
  b) **la parla**: el model entén perfectament, però el que es diu no és el que s'escriu.

Es distingeixen per la CONFIANÇA. Si el capítol dolent té confiança baixa, és (a). Si la té
alta i tot i així discrepa, és (b) — i llavors no és cap avaria: és la llengua.

També es mira la durada dels talls i quantes paraules sent per segon: un tall que no casa amb
la línia dona poques paraules per a molt de so.
"""
import io
import json
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
ACORD = MAG / "acord_26.jsonl"

sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

per_cap = defaultdict(lambda: {"A": 0, "n": 0, "conf": [], "paraules": 0, "segons": 0.0,
                               "buides": 0})
for l in io.open(ACORD, encoding="utf-8"):
    if not l.strip():
        continue
    r = json.loads(l)
    c = per_cap[r["capitol"]]
    c["n"] += 1
    c["A"] += r["grau"] == "A"
    s = sentit.get(r["id"], {})
    if s.get("conf") is not None:
        c["conf"].append(s["conf"])
    c["paraules"] += len(s.get("paraules") or [])
    if r.get("t_ini") is not None and r.get("t_fi") is not None:
        c["segons"] += float(r["t_fi"]) - float(r["t_ini"])
    if not (s.get("sentit") or "").strip():
        c["buides"] += 1

print(f"{'capítol':<18}{'acord':>7}{'conf mitjana':>14}{'par/s':>8}{'buides':>8}{'s/rèplica':>11}")
files = []
for cap, c in per_cap.items():
    if c["n"] < 50:
        continue
    conf = sum(c["conf"]) / len(c["conf"]) if c["conf"] else 0
    pps = c["paraules"] / c["segons"] if c["segons"] else 0
    files.append((c["A"] / c["n"], cap, conf, pps, c["buides"] / c["n"], c["segons"] / c["n"]))
files.sort(reverse=True)
for a, cap, conf, pps, buides, spr in files:
    print(f"{cap[:16]:<18}{100*a:6.1f}%{conf:14.3f}{pps:8.2f}{100*buides:7.1f}%{spr:11.1f}")

#: la pregunta: l'acord va amb la confiança, o no?
import statistics  # noqa: E402

if len(files) > 3:
    xs = [f[2] for f in files]
    ys = [f[0] for f in files]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    print(f"\ncorrelació acord ↔ confiança: {num/den if den else 0:+.2f}")
    xs2 = [f[3] for f in files]
    mx2 = statistics.mean(xs2)
    num2 = sum((x - mx2) * (y - my) for x, y in zip(xs2, ys))
    den2 = (sum((x - mx2) ** 2 for x in xs2) * sum((y - my) ** 2 for y in ys)) ** .5
    print(f"correlació acord ↔ paraules per segon: {num2/den2 if den2 else 0:+.2f}")
    print("\n(una correlació alta amb la confiança vol dir que el problema és l'àudio;")
    print(" una de baixa vol dir que el model entén i el que canvia és què es diu)")
