# -*- coding: utf-8 -*-
"""H-MT1 v3 (#494, 16-11-2026, nit): les parelles de la v2 amb tres canvis al TRAIN (el test-dins de 200 és el
MATEIX que a la v2, per comparar-hi):
  1. fora del train el vocabulari sol: una sola paraula amaziga o una sola paraula catalana, tot l'IRCAM tamawalt
     (mots aïllats), i les glosses múltiples amb «/» o «;» a qualsevol costat;
  2. s'hi afegeixen les 341 parelles MTNRA / Common Voice confirmades pels dos auditors de màquina (canvis.json,
     `mena` = confirmada), amb el català CONFIRMAT pels auditors (no el que hi ha a prod);
  3. mateixa neteja de fuita per text normalitzat (amazic o català) contra les 60 de mostra60.json i les 200 de test.
Escriu a <carpeta_sortida>: train.json, test200.json, mostra60.json, resum.json.
ÚS: prepara_parelles_v3.py <carpeta_sortida>
"""
import collections, io, json, os, random, re, sys, unicodedata

ARREL = r"C:\Users\josep\app2\tachelhit-drills.worktrees\mirar"
sys.path.insert(0, os.path.join(ARREL, "backend"))
from transliteration import to_forms  # noqa: E402

AUDITORS = r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"
CATALEG = os.path.join(AUDITORS, "cataleg_prod.json")
CANVIS = os.path.join(AUDITORS, "canvis.json")
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


def clau_n(s):
    return " ".join(re.sub(r"[^\w\s]", " ", (s or "").lower()).split())


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


def parella(r, tz, ca, font=None, origen=None):
    """Una fila del catàleg + el seu amazic i català → la parella (o None si no en surt tifinag)."""
    es_tif = bool(TIF.search(tz))
    if es_tif:
        tif, lat = unicodedata.normalize("NFC", tz), (r.get("text_tachelhit_latin") or "").strip() or to_forms(tz)["clean_latin"]
    else:
        lat, tif = tz, to_forms(tz)["tifinagh"]
    tif = " ".join(tif.split())
    if not TIF.search(tif):
        return None
    return {"id": r["id"], "tifinag": tif, "llati": lat, "catala": ca, "font": font or font_de(r), "variety": r.get("variety"),
            "passat_del_llati": not es_tif, "origen": origen or "catàleg"}


# ---------------------------------------------------------------- la v2, tal qual, fins al tall train/test
cat = json.load(io.open(CATALEG, encoding="utf-8"))
per_id = {r["id"]: r for r in cat}
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
        p = parella(r, tz_, ca_)
        if p is None:
            fora["el transliterador no en treu tifinag"] += 1
            continue
        clau = (p["tifinag"], ca_.lower())
        if clau in vistes:
            fora["duplicat exacte"] += 1
            continue
        vistes.add(clau)
        parelles.append(p)

rnd = random.Random(1114)
rnd.shuffle(parelles)
test, train = parelles[:200], parelles[200:]
assert len(parelles) == 4910 and test[0]["id"] == 8187, "el tall train/test ha de ser el de la v2"
n_v2 = len(train)

# ---------------------------------------------------------------- v3.1: fora el vocabulari sol (només del train)
def es_vocabulari(p):
    if p["font"] == "IRCAM tamawalt":
        return "IRCAM (mot aïllat)"
    if "/" in p["catala"] or ";" in p["catala"] or "/" in p["llati"] or ";" in p["llati"]:
        return "glosses múltiples (/ ;)"
    if len(p["llati"].split()) == 1 or len(p["catala"].split()) == 1:
        return "una sola paraula"
    return None


fora_vocab = collections.Counter()
train_net = []
for p in train:
    m = es_vocabulari(p)
    if m:
        fora_vocab[m] += 1
    else:
        train_net.append(p)
train = train_net

# ---------------------------------------------------------------- v3.2: les 341 confirmades pels dos auditors
canvis = json.load(io.open(CANVIS, encoding="utf-8"))
conf = [c for c in canvis if c.get("mena") == "confirmada" and (c.get("text_catalan") or "").strip()]
afegides, fora_conf = [], collections.Counter()
for c in conf:
    r = per_id.get(c["id"])
    if r is None:
        fora_conf["id no és al catàleg"] += 1
        continue
    if c["id"] in ids_mostra:
        fora_conf["és a la mostra de 60"] += 1
        continue
    tz = (r.get("text_tachelhit") or "").strip()
    ca = neteja_catala(c["text_catalan"])
    if not tz or not ca:
        fora_conf["sense amazic o català"] += 1
        continue
    if len(tz) > 300 or len(ca) > 300:
        fora_conf["massa llarg"] += 1
        continue
    rr = dict(r)
    rr["tag"] = c.get("tag") or r.get("tag")
    p = parella(rr, tz, ca, origen="auditors 16-11")
    if p is None:
        fora_conf["sense tifinag"] += 1
        continue
    if es_vocabulari(p):
        fora_conf["vocabulari"] += 1
        continue
    afegides.append(p)
train += afegides

# ---------------------------------------------------------------- v3.3: fuita per text normalitzat, i duplicats
prohibit_tif = {clau_n(x["text_tachelhit"]) for x in mostra} | {clau_n(x["tifinag"]) for x in test}
for x in mostra:
    tz = x["text_tachelhit"].strip()
    prohibit_tif.add(clau_n(tz if TIF.search(tz) else to_forms(tz)["tifinagh"]))
prohibit_ca = {clau_n(x["text_catalan"]) for x in mostra} | {clau_n(p["catala"]) for p in test}
n_abans = len(train)
train = [p for p in train if clau_n(p["tifinag"]) not in prohibit_tif and clau_n(p["catala"]) not in prohibit_ca]
n_fuita = n_abans - len(train)
vistes, train_dedup = set(), []
for p in train:
    k = (clau_n(p["tifinag"]), clau_n(p["catala"]))
    if k in vistes:
        continue
    vistes.add(k)
    train_dedup.append(p)
n_dup = len(train) - len(train_dedup)
train = train_dedup
rnd.shuffle(train)

# comprovació final: cap fuita
tif_tr = {clau_n(p["tifinag"]) for p in train}
ca_tr = {clau_n(p["catala"]) for p in train}
fuita_60 = sum(1 for x in mostra if clau_n(x["text_tachelhit"]) in tif_tr or clau_n(x["text_catalan"]) in ca_tr)
fuita_200 = sum(1 for x in test if clau_n(x["tifinag"]) in tif_tr or clau_n(x["catala"]) in ca_tr)
assert fuita_60 == 0 and fuita_200 == 0, (fuita_60, fuita_200)

m60 = []
for i, x in enumerate(mostra):
    tz = x["text_tachelhit"].strip()
    tif = tz if TIF.search(tz) else to_forms(tz)["tifinagh"]
    m60.append({"id": x["id"], "grup": "shi" if i < 30 else "beni-mellal", "tifinag": " ".join(unicodedata.normalize("NFC", tif).split()),
                "amazic_original": tz, "catala": x["text_catalan"]})

resum = {"versio": "v3", "train_v2_abans_de_res": n_v2, "fora_vocabulari": dict(fora_vocab.most_common()),
         "confirmades_a_canvis": len(conf), "afegides_dels_auditors": len(afegides), "fora_de_les_confirmades": dict(fora_conf),
         "fora_per_fuita": n_fuita, "duplicats_despres_d_afegir": n_dup, "train": len(train), "test200": len(test),
         "fuita_final": {"mostra60": fuita_60, "test200": fuita_200},
         "en_tifinag_d_origen": sum(1 for p in train if not p["passat_del_llati"]),
         "passades_del_llati": sum(1 for p in train if p["passat_del_llati"]),
         "per_font_train": dict(collections.Counter(p["font"] for p in train).most_common()),
         "per_font_afegides": dict(collections.Counter(p["font"] for p in afegides).most_common()),
         "per_font_test": dict(collections.Counter(p["font"] for p in test).most_common()),
         "paraules_amazic_mitjana_train": round(sum(len(p["llati"].split()) for p in train) / len(train), 2),
         "fora_v2": dict(fora)}
for nom, obj in [("train.json", train), ("test200.json", test), ("mostra60.json", m60), ("resum.json", resum)]:
    json.dump(obj, io.open(os.path.join(SORTIDA, nom), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(json.dumps({k: v for k, v in resum.items() if k != "fora_v2"}, ensure_ascii=False, indent=1))
print("\nmostra de 8 afegides:")
for p in rnd.sample(afegides, 8):
    print(f"  {p['font']:24} | {p['llati'][:45]:45} | {p['catala'][:70]}")
