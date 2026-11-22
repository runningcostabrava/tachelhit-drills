"""D'on es cada convidat, dit pel presentador.

Un testimoni que no he fet servir i que no te res a veure amb el nostre model: el programa
presenta cada convidat i sovint diu d'on es, i aixo ho tenim en catala (vingut de l'arab, que es
un cami independent del tifinag i de l'orella).

Si els convidats de poc acord son del Rif o de l'Atles i els de bon acord del Sus -- que es el
pais del tachelhit --, la hipotesi de la varietat queda confirmada per una via que no depen de
cap mesura meva.

Es busquen, a les primeres rèpliques de cada episodi (que es on hi ha la presentacio) i a tot
l'episodi, els noms de lloc i les families amazigues.
"""
import io
import json
import glob
import os
import re
from collections import defaultdict

#: llocs del pais tachelhit (Sus i Anti-Atles), de l'Atles central, i del Rif i l'est
LLOCS = {
    "sus / anti-atles": ["sous", "souss", "sus", "agadir", "taroudant", "tiznit", "tafraout",
                         "chtouka", "ait baha", "inezgane", "massa", "ifni", "guelmim",
                         "tata", "anti-atles", "anti atles", "ouarzazate", "taliouine",
                         "igherm", "biougra", "essaouira", "imintanout", "chichaoua"],
    "atles central": ["azilal", "beni mellal", "khenifra", "midelt", "ait merghad",
                      "ait mrabet", "ait ayach", "ait hadiddou", "imilchil", "errachidia",
                      "atles central", "khemisset", "ait seghrouchen", "boumalne",
                      "tinghir", "zaida", "ait izdeg", "ait yafelman"],
    "rif i est": ["rif", "nador", "al hoceima", "alhucemas", "driouch", "berkane", "oujda",
                  "taza", "temsamane", "ait waryaghel", "aït waryaghel", "guercif",
                  "figuig", "jerada", "tarifit", "rifeny", "rifenya", "ait said",
                  "beni snassen", "snassen", "bouarfa"],
}

titols = {}
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

acord = defaultdict(lambda: [0, 0])
for l in io.open(r"E:/tamazight/_magatzem/acord_triat.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        acord[r["capitol"]][1] += 1
        acord[r["capitol"]][0] += r["grau"] == "A"

per_cap = defaultdict(list)
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        per_cap[x["capitol"]].append(x)

files = []
for cap, linies in per_cap.items():
    linies.sort(key=lambda x: (x.get("t_ini") if x.get("t_ini") is not None else 0))
    trobat = defaultdict(list)
    for i, x in enumerate(linies):
        t = ((x.get("catala") or "") + " " + (x.get("arab") or "")).lower()
        for zona, noms in LLOCS.items():
            for nom in noms:
                if re.search(r"\b" + re.escape(nom) + r"\b", t):
                    trobat[zona].append((i, nom, (x.get("catala") or "")[:58]))
    a, n = acord[cap]
    files.append((a / max(1, n), titols.get(cap, cap), trobat))

files.sort(reverse=True)
print(f"{'convidat':<26}{'acord':>7}  zones que surten (vegades)")
for ac, t, trobat in files:
    quines = " · ".join(f"{z} {len(v)}" for z, v in sorted(trobat.items(), key=lambda kv: -len(kv[1])))
    print(f"{t[:24]:<26}{100*ac:6.1f}%  {quines or '—'}")

print("\nles mencions, amb la frase (les primeres de cada episodi):")
for ac, t, trobat in files:
    if not trobat:
        continue
    print(f"\n{t[:34]}  (acord {100*ac:.1f} %)")
    vistes = 0
    for zona, v in sorted(trobat.items(), key=lambda kv: -len(kv[1])):
        for i, nom, frase in v[:2]:
            print(f"   [{zona}] {nom}: {frase}")
            vistes += 1
            if vistes >= 4:
                break
        if vistes >= 4:
            break
