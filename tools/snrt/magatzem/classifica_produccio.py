"""De quina varietat son els episodis de produccio que no estaven classificats.

En Pablo: «treu tarifit del visor i de la app». A produccio hi ha 39 episodis: 11 ja marcats
tarifit, 11 tachelhit, 3 de l'Atles central i **14 sense classificar**. Abans de treure res
cal saber de quina varietat son els 14, que si no se'n quedaria algun de tarifit o se'n
trauria algun de bo.

S'hi fa servir el senyal que no passa pel tifinag normalitzat: **els toponims a l'arab**
(el mateix criteri que va descobrir que el corpus d'entrenament tenia el dev 100 % tarifit).

No toca res: escriu `varietat_produccio.json`.

    classifica_produccio.py
"""
import io
import json
import time
import urllib.request
from collections import Counter
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
API = "https://tachelhit-drills-api.onrender.com"

RIF = ["الريف", "تفرسيت", "الناظور", "الحسيمة", "ميضار", "بركان", "تمسمان", "أجدير",
       "الدريوش", "تاوريرت", "امزورن", "نكور"]
SUS = ["سوس", "أكادير", "اكادير", "تزنيت", "تارودانت", "اشتوكة", "شتوكة", "تافراوت",
       "تيزنيت", "ايت باها", "ماسة", "كلميم"]
ATLES = ["الأطلس", "خنيفرة", "ميدلت", "أزيلال", "بني ملال", "الراشيدية", "تنغير",
         "ورزازات", "زاكورة", "كلعة"]


def demana(cami, intents=3):
    for i in range(intents):
        try:
            with urllib.request.urlopen(API + cami, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == intents - 1:
                print(f"   {cami}: {type(e).__name__}")
            time.sleep(3)
    return None


var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
nous = json.load(io.open(MAG / "don_son_els_nous.json", encoding="utf-8"))
nom = {"rif": "tarifit", "sus": "tachelhit", "atles": "Atles central"}

d = demana("/snrt-privat/")
eps = (d or {}).get("episodis") or []
print(f"{len(eps)} episodis a producció")

sortida = {}
per_mirar = []
for e in eps:
    s = e["slug"]
    v = var.get(s) or nom.get((nous.get(s) or {}).get("diu"), "")
    if v:
        sortida[s] = {"varietat": v, "d_on": "ja classificat",
                      "titol": (e.get("titol") or "")[:60]}
    else:
        per_mirar.append(e)
print(f"{len(per_mirar)} per classificar\n")

for i, e in enumerate(per_mirar, 1):
    s = e["slug"]
    x = demana(f"/snrt-privat/{s}")
    linies = (x or {}).get("linies") or (x or {}).get("repliques") or []
    tot = " ".join((l.get("arab") or "") for l in linies)
    c = Counter()
    quins = Counter()
    for grup, taula in (("rif", RIF), ("sus", SUS), ("atles", ATLES)):
        for t in taula:
            k = tot.count(t)
            if k:
                c[grup] += k
                quins[t] += k
    diu = max(c, key=c.get) if c and max(c.values()) >= 2 else "cap senyal"
    sortida[s] = {"varietat": nom.get(diu, ""), "d_on": "topònims a l'àrab",
                  "titol": (e.get("titol") or "")[:60],
                  "rif": c["rif"], "sus": c["sus"], "atles": c["atles"]}
    print(f"   {i:2d}. {s[:16]} {(e.get('titol') or '')[:34]:<36}"
          f"rif {c['rif']:3d} sus {c['sus']:3d} atles {c['atles']:3d}  -> "
          f"{nom.get(diu, 'cap senyal')}", flush=True)

json.dump(sortida, io.open(MAG / "varietat_produccio.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
c = Counter(v["varietat"] or "cap senyal" for v in sortida.values())
print(f"\n{dict(c)}")
rif = [s for s, v in sortida.items() if v["varietat"] == "tarifit"]
print(f"\ntarifit a produccio: {len(rif)}")
print("escrit varietat_produccio.json")
