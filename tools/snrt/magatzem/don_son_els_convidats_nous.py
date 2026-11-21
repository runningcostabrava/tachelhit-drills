"""D'on son els convidats dels 27 capitols, llegit a l'ARAB.

El classificador pel lexic diu «tachelhit» als 27, i no me'n refio per dues raons:

  * el lexic diferencial te **117 marques tachelhit contra 39 tarifit**: tres vegades mes
    oportunitats de puntuar cap a un costat;
  * el subtitol en tifinag esta **normalitzat per l'IRCAM**, que es justament on les marques
    dialectals desapareixen. Un rifeny subtitulat en amazic estandard s'escriu com un
    tachelhit.

Aqui es mira una cosa que no passa per cap d'aquests dos filtres: **els topònims a l'arab**.
Si l'episodi parla de Nador, Alhucemas, Tafersit o el Rif, el convidat es del Rif; si parla
d'Agadir, Tiznit, Taroudant o el Sus, es del Sus, que es el pais del tachelhit.

No decideix res sol: posa un senyal independent al costat de l'altre.

    don_son_els_convidats_nous.py
"""
import io
import json
import os
from collections import Counter
from pathlib import Path

ARREL = Path(r"E:/tamazight/TD_TV")

RIF = {"الريف": "Rif", "تفرسيت": "Tafersit", "الناظور": "Nador", "الحسيمة": "Alhucemas",
       "ميضار": "Midar", "بركان": "Berkane", "تمسمان": "Temsamane", "أجدير": "Ajdir",
       "الدريوش": "Driouch", "تاوريرت": "Taourirt", "امزورن": "Imzouren", "نكور": "Nekor"}
SUS = {"سوس": "Sus", "أكادير": "Agadir", "اكادير": "Agadir", "تزنيت": "Tiznit",
       "تارودانت": "Taroudant", "اشتوكة": "Chtouka", "شتوكة": "Chtouka", "تافراوت": "Tafraout",
       "تيزنيت": "Tiznit", "ايت باها": "Aït Baha", "ماسة": "Massa", "كلميم": "Guelmim"}
ATLES = {"الأطلس": "Atles", "خنيفرة": "Khenifra", "ميدلت": "Midelt", "أزيلال": "Azilal",
         "بني ملال": "Beni Mellal", "الراشيدية": "Errachidia", "تنغير": "Tinghir",
         "ورزازات": "Ouarzazate", "زاكورة": "Zagora", "كلعة": "Kelaa"}

print(f"{'capítol':<16}{'Rif':>6}{'Sus':>6}{'Atles':>7}  llocs que hi surten")
sortida = {}
for d in sorted(os.listdir(ARREL)):
    p = ARREL / d / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0:
        continue
    text = []
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            if not x.get("credits"):
                text.append(x.get("arab") or "")
    tot = " ".join(text)
    c = Counter()
    noms = Counter()
    for grup, taula in (("rif", RIF), ("sus", SUS), ("atles", ATLES)):
        for ar, cat in taula.items():
            k = tot.count(ar)
            if k:
                c[grup] += k
                noms[cat] += k
    diu = max(c, key=c.get) if c and max(c.values()) >= 2 else "cap senyal"
    sortida[d] = {"rif": c["rif"], "sus": c["sus"], "atles": c["atles"], "diu": diu,
                  "llocs": dict(noms.most_common(4))}
    print(f"{d:<16}{c['rif']:>6}{c['sus']:>6}{c['atles']:>7}  "
          f"{', '.join(f'{k}×{v}' for k, v in noms.most_common(4))}")

json.dump(sortida, io.open(r"E:/tamazight/_magatzem/don_son_els_nous.json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{dict(Counter(v['diu'] for v in sortida.values()))}")
