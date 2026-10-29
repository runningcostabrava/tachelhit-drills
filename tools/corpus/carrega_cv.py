"""El Common Voice zgh a la biblioteca: 1.474 drills, catalogats, amb l'audio dins.

## Com es cataloga cada drill

  text_tachelhit   la frase en tifinag que el parlant LLEGIA: escrita per una persona
  variety          shi si es declara taixelhit, tzm si Atles Central, other si no ho diu.
                   **Mai zgh**: «zgh» es el codi del projecte Common Voice (l'escriptura
                   estandard), no la varietat de qui parla. Si no s'omple, el servidor hi posa
                   la varietat de qui crea el drill, i tots sortirien amb la d'en Pablo.
  region           el mateix en paraules, dient que es declarat
  speaker          «Common Voice · <8 primers del client_id>», mes sexe i edat si els diu
  source_*         Mozilla Common Voice 27.0, amb l'enllac
  tag              common-voice, veu-que-llegeix, font externa
  text_catalan     buit: no tenim el significat i no s'inventa

## Com viatja l'audio

Els mp3 van en base64 dins de fitxers JSON de menys de 9 MB, que la pagina de l'app llegeix
(sense xarxa: pujats amb l'eina del navegador) i puja al servidor amb el token d'en Pablo, que
no surt del navegador.
"""
import base64, csv, glob, io, json, os

S = os.path.dirname(os.path.abspath(__file__))
D = glob.glob(os.path.join(S, "corpus_nous", "zgh", "*", "zgh"))[0]
ON = os.path.join(S, "carrega_cv")
os.makedirs(ON, exist_ok=True)
for f in os.listdir(ON):
    os.remove(os.path.join(ON, f))

SEXE = {"male_masculine": "home", "female_feminine": "dona", "male": "home", "female": "dona"}
EDAT = {"teens": "<20", "twenties": "20-29", "thirties": "30-39", "fourties": "40-49",
        "fifties": "50-59", "sixties": "60-69"}


def varietat(v):
    if "ⵛⵍⵃ" in v:
        return "shi", "Souss (taixelhit, declarat a Common Voice)"
    if "ⵟⵍⴰⵚ" in v:
        return "tzm", "Atles Central (declarat a Common Voice)"
    return "other", "Common Voice (varietat no declarada)"


rows = list(csv.DictReader(io.open(os.path.join(D, "validated.tsv"), encoding="utf-8"), delimiter="\t"))
items, mida, n = [], 0, 0
for r in rows:
    var, reg = varietat(r.get("variant") or "")
    parlant = "Common Voice · " + r["client_id"][:8]
    extra = [x for x in (SEXE.get(r.get("gender") or ""), EDAT.get(r.get("age") or "")) if x]
    if extra:
        parlant += " (" + ", ".join(extra) + ")"
    b = open(os.path.join(D, "clips", r["path"]), "rb").read()
    items.append({"clau": r["path"], "mp3": base64.b64encode(b).decode("ascii"), "cos": {
        "text_tachelhit": r["sentence"].strip(), "variety": var, "region": reg,
        "speaker": parlant, "source_channel": "Mozilla Common Voice",
        "source_title": "Common Voice 27.0 · zgh", "source_url": "https://commonvoice.mozilla.org/zgh",
        "tag": "common-voice, veu-que-llegeix, font externa"}})
    mida += len(items[-1]["mp3"])
    if mida > 8_500_000:
        json.dump(items, io.open(os.path.join(ON, "cv_%02d.json" % n), "w", encoding="utf-8"), ensure_ascii=False)
        n, items, mida = n + 1, [], 0
if items:
    json.dump(items, io.open(os.path.join(ON, "cv_%02d.json" % n), "w", encoding="utf-8"), ensure_ascii=False)
    n += 1
for f in sorted(os.listdir(ON)):
    print("%s  %.1f MB" % (f, os.path.getsize(os.path.join(ON, f)) / 1e6))
print("fitxers: %d · drills: %d" % (n, len(rows)))
