"""El corpus de VEU -> ARAB amb tot el material que hi ha, no nomes el de la SNRT.

**Per que.** La via 3 (`corpus_veu_arab.py`) es va muntar com un experiment sobre la SNRT:
12,7 h d'entrenament. Pero el TutlAit es exactament la mateixa tasca -- so amazic, arab escrit
que en diu el significat -- i fa 20,8 h que ja son al disc. El seu arab es arab de debo, no
transliteracio: el 80 % de les frases porten paraules funcionals arabs, igual que el 79 % dels
subtitols de la SNRT (`quin_arab_es_el_del_tutlait.py`, quadern §51).

**Que fa.** Ajunta els manifests; no copia cap so. Cada fila diu d'on ve (`font`), quina
varietat es si se sap, i quin grup la lliga (capitol a la SNRT, parlant al TutlAit).

**Les tres coses que es vigilen**, perque totes tres ja ens han mossegat:

  * **La particio es per grup, no per fila.** La SNRT ja va partida per capitols. El TutlAit
    porta la seva particio, i aqui es comprova que cap parlant sigui a dos costats.
  * **La fuita per text.** Al TutlAit molta gent llegeix les mateixes frases: una frase del
    test pot ser a l'entrenament amb una altra veu, i en traduccio aixo es saber-se la
    resposta. Es treu de l'entrenament tota fila amb un arab que, normalitzat, surti a
    qualsevol dev o test -- de qualsevol de les dues fonts. (La llicó del 16-11: excloure per
    id no tanca la fuita.)
  * **Els tests no es barregen.** `test_snrt` segueix sent comparable amb la via del text, i
    `test_tutlait` amb l'article del TutlAit. Un test barrejat no seria comparable amb res.

**El que NO fa:** triar el so de la SNRT. Avui apunta als talls sencers de `veu_ar/so`; quan
l'alineacio acabi i l'experiment del retall digui si retallar val, es canvia la carpeta i prou.

    python corpus_veu_arab_combinat.py
"""
import io
import json
import re
import unicodedata
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
SNRT = MAG / "veu_ar"
TUT = Path(r"E:/tamazight/_paquets/tutlait")
FORA = MAG / "veu_ar_combinat"

DUR_MIN, DUR_MAX = 1.0, 20.0     #: les mateixes portes que el corpus de la SNRT


def norma(t):
    """L'arab reduit al que el fa «la mateixa frase»: sense vocals, tatweel ni puntuacio."""
    t = unicodedata.normalize("NFKC", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("\u0640", "")
    t = re.sub("[\u0623\u0625\u0622\u0671]", "\u0627", t)      # totes les alef, una
    t = t.replace("\u0649", "\u064a").replace("\u0629", "\u0647")
    t = re.sub(r"[^\u0600-\u06ff\s]", " ", t)
    t = re.sub(r"[\u060c\u061b\u061f\u06d4]", " ", t)
    return " ".join(t.split())


def llegeix(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]


files = {"train": [], "dev": [], "test_snrt": [], "test_tutlait": []}
informe = {}

#: --- la SNRT, tal com la va partir corpus_veu_arab.py (per capitols)
for nom, desti in (("train", "train"), ("dev", "dev"), ("test", "test_snrt")):
    for x in llegeix(SNRT / f"{nom}.jsonl"):
        files[desti].append({"so": x["so"], "font": "snrt", "ar": x["ar"],
                             "grup": x["capitol"], "varietat": None,
                             "durada": x["durada"]})
informe["snrt"] = {k: sum(1 for x in v if x["font"] == "snrt") for k, v in files.items()}

#: --- el TutlAit, amb la seva particio
meta = llegeix(TUT / "metadades.jsonl")
fora = {"durada": 0, "arab curt": 0, "sense so": 0}
tut = {"train": [], "validation": [], "test": []}
for x in meta:
    ar = (x.get("text_arabic") or "").strip()
    dur = float(x.get("duration") or 0)
    if not (DUR_MIN <= dur <= DUR_MAX):
        fora["durada"] += 1
        continue
    if len(ar.split()) < 2:
        fora["arab curt"] += 1
        continue
    if not (TUT / "audio" / f"{x['id']}.flac").exists():
        fora["sense so"] += 1
        continue
    tut[x["split"]].append({"so": f"{x['id']}.flac", "font": "tutlait", "ar": ar,
                            "grup": x["speaker"], "varietat": x.get("variety"),
                            "durada": dur})
informe["tutlait_fora_de_porta"] = fora

#: cap parlant a dos costats: si n'hi ha, es diu i es treu de l'entrenament
parlants = {k: {x["grup"] for x in v} for k, v in tut.items()}
dobles = parlants["train"] & (parlants["validation"] | parlants["test"])
informe["tutlait_parlants"] = {k: len(v) for k, v in parlants.items()}
informe["tutlait_parlants_a_dos_costats"] = sorted(dobles)
if dobles:
    abans = len(tut["train"])
    tut["train"] = [x for x in tut["train"] if x["grup"] not in dobles]
    informe["tutlait_tret_per_parlant"] = abans - len(tut["train"])

files["train"] += tut["train"]
files["dev"] += tut["validation"]
files["test_tutlait"] += tut["test"]

#: --- la fuita per text: res de l'entrenament pot dir el que diu un dev o un test
jutges = {norma(x["ar"]) for k in ("dev", "test_snrt", "test_tutlait") for x in files[k]}
abans = len(files["train"])
tret = [x for x in files["train"] if norma(x["ar"]) in jutges]
files["train"] = [x for x in files["train"] if norma(x["ar"]) not in jutges]
informe["tret_per_fuita_de_text"] = {
    "total": abans - len(files["train"]),
    "snrt": sum(1 for x in tret if x["font"] == "snrt"),
    "tutlait": sum(1 for x in tret if x["font"] == "tutlait")}

#: --- escriure
FORA.mkdir(parents=True, exist_ok=True)
for k, v in files.items():
    with io.open(FORA / f"{k}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for x in v:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

print(f"{'':<14}{'files':>8}{'hores':>8}{'snrt':>8}{'tutlait':>9}")
informe["parts"] = {}
for k, v in files.items():
    h = sum(x["durada"] for x in v) / 3600
    s = sum(1 for x in v if x["font"] == "snrt")
    informe["parts"][k] = {"files": len(v), "hores": round(h, 2), "snrt": s,
                           "tutlait": len(v) - s}
    print(f"{k:<14}{len(v):>8}{h:>7.1f}h{s:>8}{len(v) - s:>9}")

var = {}
for x in files["train"]:
    var[x["varietat"] or "sense dir (snrt)"] = var.get(x["varietat"] or "sense dir (snrt)", 0) + x["durada"]
informe["train_hores_per_varietat"] = {k: round(v / 3600, 2) for k, v in var.items()}

print(f"\nTutlAit fora de porta: {fora}")
print(f"parlants del TutlAit: {informe['tutlait_parlants']} · a dos costats: {len(dobles)}")
print(f"tret de l'entrenament per fuita de text: {informe['tret_per_fuita_de_text']}")
print(f"hores d'entrenament per varietat: {informe['train_hores_per_varietat']}")
json.dump(informe, io.open(FORA / "informe.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n-> {FORA}")
