# -*- coding: utf-8 -*-
"""H-MT1 (#494, 16-11-2026): prepara les parelles amazic → català PRÒPIES per afinar el NLLB de Tamazight-NLP.
Del catàleg de producció (cataleg_prod.json, 12.202 files) en surten:
  - train.json       : parelles d'entrenament {id, tifinag, llati, catala, font, variety, passat_del_llati}
  - test200.json     : 200 parelles a l'atzar (llavor 1114) reservades com a test-dins, mateix format
  - mostra60.json    : les 60 frases de sempre {id, grup, tifinag, catala}
  - resum.json       : comptes per font
Regles (les del cap de la feina + les que han calgut en mirar les dades, totes dites a l'INFORME):
  dins: text_tachelhit i text_catalan no buits
  fora: les 60 de la mostra; `sense text`; `traduit-per-maquina` sense `traduit-per-auditors`;
        `traduccio-descartada`; is_correction_dataset; autor «Auto Capture» (lectura automàtica amb català de màquina
        sense etiqueta); autor «Sean» (8 frases en irlandès); «Curs bàsic (sintètic)».
  neteja del català: fora «(lit. …)», «[?]», i els claudàtors (es queda el que hi ha dins).
  files amb « // » (l'Anki posa dues variants): es parteixen si tots dos costats en tenen el mateix nombre; si no, fora.
  tifinag: el que hi ha si ja és tifinag; si no, transliteration.to_forms(llatí)["tifinagh"] del backend.
ÚS: prepara_parelles.py <carpeta_sortida>
"""
import collections, io, json, os, random, re, sys, unicodedata

ARREL = r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar"
sys.path.insert(0, os.path.join(ARREL, "backend"))
from transliteration import to_forms  # noqa: E402

CATALEG = r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors\cataleg_prod.json"
MOSTRA = r"C:\Users\josep\Veus-tachelhit\_escoltats\models\mostra60.json"
SORTIDA = sys.argv[1]
os.makedirs(SORTIDA, exist_ok=True)
TIF = re.compile("[\u2d30-\u2d7f]")


def tags(r):
    return {t.strip() for t in (r.get("tag") or "").split(",") if t.strip()}


def neteja_catala(s):
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\((lit\.?|literalment)[^)]*\)", " ", s, flags=re.I)
    s = s.replace("[?]", " ")
    s = re.sub(r"\[([^\]]*)\]", r"\1", s)
    return " ".join(s.split()).strip()


def font_de(r):
    t = tags(r)
    a = r.get("author") or ""
    if "benimellal-anki" in t:
        return "Beni Mellal (Anki)"
    if "mtnra" in t:
        return "MTNRA (auditors)"
    if "common-voice" in t:
        return "Common Voice (auditors)"
    if "metode-cd" in t:
        return "Mètode CD"
    if "del llibre" in t or any(x.startswith("metode-") for x in t):
        return "Mètode del llibre"
    if "ircam-tamawalt" in t:
        return "IRCAM tamawalt"
    if "Aït Mraw" in t:
        return "Aït Mraw"
    if "Classe d'Azilal" in t:
        return "Classe d'Azilal"
    if "ILoveLanguages" in t:
        return "ILoveLanguages"
    if "Driss" in t or a == "Driss":
        return "Driss"
    if "Halima" in t or a == "Halima":
        return "Halima"
    if "tutlait" in t:
        return "TutlAit"
    if a.startswith("Tamazight For All") or "conte-del-canal" in t:
        return "Tamazight For All"
    if "traduit-per-auditors" in t:
        return "altres (auditors)"
    return "altres (" + (a or "sense autor") + ")"


cat = json.load(io.open(CATALEG, encoding="utf-8"))
mostra = json.load(io.open(MOSTRA, encoding="utf-8"))
ids_mostra = {x["id"] for x in mostra}
fora = collections.Counter()
cand = []
for r in cat:
    t = tags(r)
    tz = (r.get("text_tachelhit") or "").strip()
    ca = (r.get("text_catalan") or "").strip()
    if not tz or not ca:
        fora["sense amazic o sense català"] += 1
        continue
    if r["id"] in ids_mostra:
        fora["mostra de 60"] += 1
        continue
    if "sense text" in t:
        fora["sense text"] += 1
        continue
    if "traduit-per-maquina" in t and "traduit-per-auditors" not in t:
        fora["català de màquina no confirmat"] += 1
        continue
    if "traduccio-descartada" in t:
        fora["traducció descartada"] += 1
        continue
    if r.get("is_correction_dataset"):
        fora["is_correction_dataset"] += 1
        continue
    if (r.get("author") or "") == "Auto Capture":
        fora["Auto Capture"] += 1
        continue
    if (r.get("author") or "") == "Sean":
        fora["Sean (frases en irlandès, no amazic)"] += 1
        continue
    if "Curs bàsic (sintètic)" in t:
        fora["Curs bàsic (sintètic)"] += 1
        continue
    cand.append(r)

parelles, vistes = [], set()
for r in cand:
    tz, ca = r["text_tachelhit"].strip(), neteja_catala(r["text_catalan"])
    if not ca:
        fora["català buit després de netejar"] += 1
        continue
    if "//" in tz or "//" in ca:
        a, b = [x.strip() for x in tz.split("//")], [x.strip() for x in ca.split("//")]
        if len(a) != len(b) or not all(a) or not all(b):
            fora["« // » desaparellat"] += 1
            continue
        trossos = list(zip(a, b))
        fora["« // » partit en parelles"] += len(trossos) - 1
    else:
        trossos = [(tz, ca)]
    for tz_, ca_ in trossos:
        if len(tz_) > 300 or len(ca_) > 300:
            fora["massa llarg (>300 car.)"] += 1
            continue
        es_tif = bool(TIF.search(tz_))
        if es_tif:
            tif, lat = unicodedata.normalize("NFC", tz_), (r.get("text_tachelhit_latin") or "").strip() or to_forms(tz_)["clean_latin"]
        else:
            lat, tif = tz_, to_forms(tz_)["tifinagh"]
        tif = " ".join(tif.split())
        if not TIF.search(tif):
            fora["el transliterador no en treu tifinag"] += 1
            continue
        clau = (tif, ca_.lower())
        if clau in vistes:
            fora["duplicat exacte"] += 1
            continue
        vistes.add(clau)
        parelles.append({"id": r["id"], "tifinag": tif, "llati": lat, "catala": ca_, "font": font_de(r),
                         "variety": r.get("variety"), "passat_del_llati": not es_tif})

rnd = random.Random(1114)
rnd.shuffle(parelles)
test, train = parelles[:200], parelles[200:]


# v2 (16-11, nit): FUITA. El catàleg té la mateixa frase sota ids diferents (dues veus, `dos-catalans`, l'Anki repetit),
# i 12 de les 60 (17 pel català) i 8 de les 200 (34 pel català) eren també a train. Fora de train tota parella que tingui
# el mateix amazic O el mateix català (normalitzats com `neteja` de compara.py) que una frase de la mostra o del test.
def clau_n(s):
    return " ".join(re.sub(r"[^\w\s]", " ", (s or "").lower()).split())


prohibit_tif = {clau_n(x["text_tachelhit"]) for x in mostra} | {clau_n(TIF.search(x["text_tachelhit"]) and x["text_tachelhit"] or to_forms(x["text_tachelhit"])["tifinagh"]) for x in mostra} | {clau_n(p["tifinag"]) for p in test}
prohibit_ca = {clau_n(x["text_catalan"]) for x in mostra} | {clau_n(p["catala"]) for p in test}
n_abans = len(train)
train = [p for p in train if clau_n(p["tifinag"]) not in prohibit_tif and clau_n(p["catala"]) not in prohibit_ca]
fora["fuita: mateix amazic o català que la mostra o el test"] = n_abans - len(train)

m60 = []
for i, x in enumerate(mostra):
    tz = x["text_tachelhit"].strip()
    tif = tz if TIF.search(tz) else to_forms(tz)["tifinagh"]
    m60.append({"id": x["id"], "grup": "shi" if i < 30 else "beni-mellal", "tifinag": " ".join(unicodedata.normalize("NFC", tif).split()),
                "amazic_original": tz, "catala": x["text_catalan"]})

per_font = collections.Counter(p["font"] for p in parelles)
per_font_train = collections.Counter(p["font"] for p in train)
per_font_test = collections.Counter(p["font"] for p in test)
resum = {"candidates_despres_dels_filtres": len(cand), "parelles": len(parelles), "train": len(train), "test200": len(test),
         "en_tifinag_d_origen": sum(1 for p in parelles if not p["passat_del_llati"]),
         "passades_del_llati": sum(1 for p in parelles if p["passat_del_llati"]),
         "fora": dict(fora), "per_font": dict(per_font.most_common()),
         "per_font_train": dict(per_font_train.most_common()), "per_font_test": dict(per_font_test.most_common()),
         "per_variety": dict(collections.Counter(str(p["variety"]) for p in parelles).most_common()),
         "paraules_amazic_mitjana": round(sum(len(p["llati"].split()) for p in parelles) / len(parelles), 2)}
for nom, obj in [("train.json", train), ("test200.json", test), ("mostra60.json", m60), ("resum.json", resum)]:
    json.dump(obj, io.open(os.path.join(SORTIDA, nom), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(json.dumps(resum, ensure_ascii=False, indent=1))
print("\nmostra de 12 parelles de train:")
for p in rnd.sample(train, 12):
    print(f"  {p['font']:24} | {p['tifinag'][:40]:40} | {p['llati'][:35]:35} | {p['catala'][:50]}")
