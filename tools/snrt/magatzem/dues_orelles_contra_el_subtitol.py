"""Les dues orelles coincideixen entre elles mes que amb el subtitol?

El resultat «el rifeny casa amb el tifinag igual de malament que el tachelhit» te dues lectures
que no es poden separar amb aquell numero sol:

  a) el subtitol esta traduit a la norma i cap orella no hi pot casar;
  b) el model rifeny es massa fluix (WER 0,72) i no casaria amb res.

Aqui es separen amb la logica que ha funcionat tota la nit: **dos testimonis independents**. El
`shi` i el rifeny estan entrenats per gent diferent, amb dades diferents i varietats diferents.
Si tots dos senten el MATEIX i cap dels dos no casa amb el subtitol, el que queda fora es el
subtitol -- lectura (a). Si no coincideixen entre ells, cadascu diu una cosa i el rifeny nomes fa
soroll -- lectura (b).

Es compara, per episodi: orella contra orella, i cada orella contra el tifinag, amb la mateixa
regla (esquelet de consonants, distancia <= 0,35).
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else MAG / "prova_adaptadors" / "sortida"

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
titols = {r["capitol"]: r["titol"]
          for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

ull = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        ull[x["id"]] = x.get("tifinag") or ""


def llegeix(nom):
    d = {}
    p = SORTIDA / f"sentit_{nom}.jsonl"
    if not p.exists():
        return d
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            d[x["id"]] = (x.get("sentit") or "").strip()
    return d


def casa(a, b):
    ea, eb = esquelet(a), esquelet(b)
    if not ea or not eb:
        return None
    return (lev(ea, eb) / max(len(ea), len(eb))) <= .35


shi, rif = llegeix("shi"), llegeix("rif")
comuns = [i for i in rif if i in shi and ull.get(i)]
print(f"talls amb les dues orelles i text a la pantalla: {len(comuns)}")

per = {}
for i in comuns:
    cap = i.split(":")[0]
    c = per.setdefault(cap, {"n": 0, "sh_ull": 0, "rf_ull": 0, "sh_rf": 0})
    a = casa(shi[i], ull[i])
    b = casa(rif[i], ull[i])
    d = casa(shi[i], rif[i])
    if a is None or b is None or d is None:
        continue
    c["n"] += 1
    c["sh_ull"] += a
    c["rf_ull"] += b
    c["sh_rf"] += d

print(f"\n{'episodi':<24}{'varietat':<12}{'shi~ull':>9}{'rif~ull':>9}{'shi~rif':>9}{'talls':>7}")
grups = {}
for cap in sorted(per, key=lambda c: (var.get(c, "z"), titols.get(c, c))):
    c = per[cap]
    if c["n"] < 20:
        continue
    v = var.get(cap, "?")
    print(f"{titols.get(cap, cap)[:22]:<24}{v[:10]:<12}"
          f"{100*c['sh_ull']/c['n']:8.1f}%{100*c['rf_ull']/c['n']:8.1f}%"
          f"{100*c['sh_rf']/c['n']:8.1f}%{c['n']:7d}")
    g = grups.setdefault(v, [0, 0, 0, 0])
    for k, j in (("sh_ull", 0), ("rf_ull", 1), ("sh_rf", 2)):
        g[j] += c[k]
    g[3] += c["n"]

print(f"\n{'varietat':<24}{'shi~ull':>9}{'rif~ull':>9}{'shi~rif':>9}{'talls':>7}")
for v, g in sorted(grups.items()):
    print(f"{v[:22]:<24}{100*g[0]/g[3]:8.1f}%{100*g[1]/g[3]:8.1f}%{100*g[2]/g[3]:8.1f}%{g[3]:7d}")

for v, g in sorted(grups.items()):
    sh_ull, rf_ull, sh_rf, n = (100 * g[0] / g[3], 100 * g[1] / g[3], 100 * g[2] / g[3], g[3])
    if sh_rf > max(sh_ull, rf_ull) * 1.5:
        quin = "les dues orelles coincideixen MES entre elles que amb el subtitol"
    elif sh_rf < min(sh_ull, rf_ull):
        quin = "les orelles no es posen d'acord: el rifeny fa soroll"
    else:
        quin = "ni una cosa ni l'altra"
    print(f"\n{v}: {quin}")
    print(f"   shi~ull {sh_ull:.1f}% · rif~ull {rf_ull:.1f}% · shi~rif {sh_rf:.1f}%  (n={n})")
