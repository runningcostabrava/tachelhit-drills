"""De quina varietat son els 16 capitols nous collits pel PC.

**Aixo va abans de construir cap corpus, i no es opcional.** El 20-11 vaig muntar un corpus
d'entrenament amb el **dev 100 % tarifit** per no haver-ho mirat; en Pablo ho va haver de
recordar. El tarifit es una altra llengua i no entra enlloc.

El metode: **els toponims a l'arab**. El classificador pel lexic no serveix (te 117 marques
tachelhit contra 39 tarifit, i el tifinag esta normalitzat per l'IRCAM, que es on les marques
dialectals s'esborren): va dir «tachelhit» als 27 capitols i 8 eren del Rif.

No toca res: escriu `varietat_dels_16.json`.
"""
import io
import json
from collections import Counter
from pathlib import Path

FEINA = Path(r"E:/tamazight/fabrica/td_tv")
CAT = Path(r"E:/tamazight/fabrica/cataleg/capitols.jsonl")
FORA = Path(r"E:/tamazight/_magatzem/varietat_dels_16.json")

RIF = ["الريف", "تفرسيت", "الناظور", "الحسيمة", "ميضار", "بركان", "تمسمان", "أجدير",
       "الدريوش", "تاوريرت", "امزورن", "نكور", "الحوز"]
SUS = ["سوس", "أكادير", "اكادير", "تزنيت", "تارودانت", "اشتوكة", "شتوكة", "تافراوت",
       "تيزنيت", "ايت باها", "ماسة", "كلميم", "اداوتنان", "أيت ملول"]
ATLES = ["الأطلس", "خنيفرة", "ميدلت", "أزيلال", "بني ملال", "الراشيدية", "تنغير",
         "ورزازات", "زاكورة", "كلعة", "دمنات", "بولمان", "إفران"]

titols = {}
for l in io.open(CAT, encoding="utf-8"):
    if l.strip():
        c = json.loads(l)
        titols[c.get("slug_forja")] = (c.get("titol"), c.get("programa"))

fora = {}
print(f"{'capítol':<16}{'programa':<22}{'rif':>5}{'sus':>5}{'atles':>7}   diu")
for d in sorted(FEINA.iterdir()):
    sub = d / "subtitols.jsonl"
    if not sub.exists() or sub.stat().st_size == 0:
        continue
    L = [json.loads(x) for x in io.open(sub, encoding="utf-8") if x.strip()]
    tot = " ".join((x.get("arab") or "") for x in L)
    c = Counter()
    quins = Counter()
    for grup, taula in (("rif", RIF), ("sus", SUS), ("atles", ATLES)):
        for t in taula:
            k = tot.count(t)
            if k:
                c[grup] += k
                quins[t] += k
    diu = max(c, key=c.get) if c and max(c.values()) >= 2 else "cap senyal"
    nom = {"rif": "tarifit", "sus": "tachelhit", "atles": "Atles central"}.get(diu, "?")
    titol, prog = titols.get(d.name, (None, None))
    fora[d.name] = {"diu": diu, "varietat": nom, "programa": prog,
                    "titol": titol, "linies": len(L),
                    "rif": c["rif"], "sus": c["sus"], "atles": c["atles"],
                    "toponims": dict(quins.most_common(4))}
    print(f"{d.name[:14]:<16}{str(prog)[:21]:<22}{c['rif']:>5}{c['sus']:>5}"
          f"{c['atles']:>7}   {nom}")

json.dump(fora, io.open(FORA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{dict(Counter(v['varietat'] for v in fora.values()))}")
print(f"escrit {FORA.name}")
rif = [k for k, v in fora.items() if v["varietat"] == "tarifit"]
if rif:
    print(f"\nTARIFIT ({len(rif)}): NO entren al corpus")
    for k in rif:
        print(f"   {k[:14]} · {str(fora[k]['titol'])[:40]} · {fora[k]['toponims']}")
