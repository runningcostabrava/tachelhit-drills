# -*- coding: utf-8 -*-
"""Bucle del transcriptor (#601, §6.5 de docs/recerca/tamazight-tv-fabrica-especificacio.md).

Afina l'adaptador MMS `shi` amb parelles so <-> tifinag de Tamazight TV (SNRT) llegides per la fàbrica de l'ECS, i
només l'accepta si guanya la regla numèrica. Només biblioteca estàndard (corre a l'ECS amb el python del sistema;
el CLI de Kaggle és a /root/venv-kaggle). Reprenible: cada subordre deixa un fitxer i la següent el llegeix.

  construeix  llegeix <arrel>/*/subtitols.jsonl, tria les rèpliques aptes per a l'ASR, parteix PER CAPÍTOL
              (llavor 1114), congela la llista d'ids (particio.json + hash) i escriu rows.json + audio FLAC
  puja        crea/versiona el dataset PRIVAT de Kaggle amb el resultat
  llanca      puja el nucli (tools/lm/kaggle/transcriptor_snrt.py amb la recepta A o B) i el posa a córrer
  espera      espera que el nucli acabi (avisa si no comença en 90 min) i baixa la sortida
  avalua      aplica la regla (bootstrap aparellat) i escriu el veredicte; mai desplega res
  cicle       tot l'anterior, i apunta el resultat a registre.jsonl

Cap pas publica ni desplega: el model entrenat amb so de la SNRT és de recerca (docs/PERMISOS.md); es queda a Kaggle
privat. El Space d'ASR i Render no es toquen mai des d'aquí.
"""
import argparse
import collections
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import wave
from concurrent.futures import ThreadPoolExecutor

LLAVOR = 1114
FRAC_TEST, FRAC_DEV = 0.10, 0.05
CONF_MIN, DUBTOSOS_MAX, DURADA_MIN = 0.85, 2, 0.8        # §5
PARAULES_MIN, PARAULES_MAX = 2, 30                       # §5 (porta del traductor, que l'ASR hereta)
MIN_APTES_CAPITOL = 50                                   # un capítol amb menys no és un capítol llegit
MARGE_TALL = 0.5                                         # 0,25 s a cada banda (etapa 03)
FILTRE_CER = None                                        # §5 diu 0,4, però buida el train (vegeu el nucli): apagat fins que el director decideixi
MILLORA_CV_MAX_IC = 0.0                                  # límit superior de l'IC de Δ CER a CV zgh ha de ser < 0
EMPITJORA_FORA_MAX = 0.005                               # test-fora: Δ no pot passar de +0,005
USUARI_KAGGLE = "josepabloucr"
DATASET = "snrt-transcriptor"
NUCLI = {"A": "snrt-transcriptor-a", "B": "snrt-transcriptor-b", "CONC": "snrt-concordanca"}
DATASETS_NUCLI = ["josepabloucr/adaptador-shi-zouhir-b", "josepabloucr/tfa-veritat-h3", "josepabloucr/corpus-v4-amb-cv-zgh",
                  "josepabloucr/cv-zgh-test-256", "josepabloucr/zouhir-veritat"]
ESPERA_COMENCA_MAX = 90 * 60
FIN_NUCLI = ("complete", "error", "cancel")

TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε",
           "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ",
           "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}


def rica(t):
    """Text ric (lletres sense plegar): la mateixa funció que usa el nucli i els nuclis d'H4/H4b/H5."""
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


# ------------------------------------------------------------------ dades: aptes i partició
def apta(r, wav_ok=True):
    """Una rèplica és apta per a l'ASR (§5): no crèdit, tifinag amb confiança >= 0,85 i <= 2 glifs dubtosos,
    durada >= 0,8 s, 2..30 paraules, i el wav hi és i quadra. (El filtre CER <= 0,4 es fa dins del nucli.)"""
    if r.get("credits"):
        return False, "crèdit"
    if not r.get("tifinag"):
        return False, "sense tifinag"
    if not wav_ok:
        return False, "sense so"
    if (r.get("tifinag_conf") or 0) < CONF_MIN:
        return False, "confiança"
    if (r.get("tifinag_dubtosos") or 0) > DUBTOSOS_MAX:
        return False, "dubtosos"
    if (r.get("durada") or 0) < DURADA_MIN:
        return False, "curta"
    n = len(rica(r["tifinag"]).split())
    if not PARAULES_MIN <= n <= PARAULES_MAX:
        return False, "paraules"
    return True, ""


def duracio_wav(cami):
    with wave.open(cami, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def fi_02(estat):
    """Instant (epoch, hora local de la màquina on corre) en què va acabar l'etapa 02 d'aquest capítol, o None:
    cap tall anterior a aquest instant pot venir de les files d'ara."""
    try:
        return time.mktime(time.strptime(estat["02_llegeix"]["fi"], "%Y-%m-%d %H:%M:%S"))
    except (KeyError, TypeError, ValueError):
        return None


def wav_quadra(r, carpeta, t02=None):
    """El wav existeix, dura durada + 0,5 s (menys als extrems del vídeo) i, si es coneix, NO és anterior al final de l'etapa 02
    d'ara: la 03 és reprenible per id i no refà els talls que ja hi són, de manera que quan l'etapa 02 es refà
    queden talls VELLS sota els mateixos ids (17-11: 486 de 700 files a Hasnae Fatni). Un tall vell és una veritat falsa."""
    cami = os.path.join(carpeta, r.get("tall", "x"))
    if not os.path.exists(cami):
        return False
    if t02 is not None and os.path.getmtime(cami) < t02 - 1:
        return False
    try:
        d = duracio_wav(cami)
    except Exception:
        return False
    esperat = (r.get("durada") or 0) + MARGE_TALL
    return esperat - 0.3 <= d <= esperat + 0.1


def alineacio_ok(r, carpeta):
    """Porta d'alineació (tools/snrt/fabrica/porta_alineacio.py): només entren els talls que la porta ha marcat «ok».
    Sense talls/alineacio.json el capítol no és apte (18-11: els intervals són d'1 s i el so pot no ser el del text)."""
    try:
        with open(os.path.join(carpeta, "talls", "alineacio.json"), encoding="utf-8") as f:
            return json.load(f)["talls"].get(r["id"], {}).get("v") == "ok"
    except (OSError, ValueError, KeyError):
        return False


def particio(slugs, llavor=LLAVOR):
    """Partició PER CAPÍTOL: ~10 % de capítols sencers a test, ~5 % a dev, la resta a train (mai per línia).
    Amb pocs capítols en cau almenys 1 a test i 1 a dev; l'ordre és determinista (slugs ordenats, llavor 1114)."""
    s = sorted(slugs)
    random.Random(llavor).shuffle(s)
    n = len(s)
    if n < 3:
        raise ValueError("calen almenys 3 capítols per partir (train, dev, test)")
    nt = max(1, round(n * FRAC_TEST))
    nd = max(1, round(n * FRAC_DEV))
    return {"test": sorted(s[:nt]), "dev": sorted(s[nt:nt + nd]), "train": sorted(s[nt + nd:])}


def treu_repetits(files_per_split):
    """Treu del train (i del dev) tota rèplica el text ric de la qual és a una part «més alta» (test, després dev)."""
    vist_test = {rica(r["tifinag"]) for r in files_per_split["test"]}
    dev = [r for r in files_per_split["dev"] if rica(r["tifinag"]) not in vist_test]
    vist = vist_test | {rica(r["tifinag"]) for r in dev}
    train = [r for r in files_per_split["train"] if rica(r["tifinag"]) not in vist]
    return {"train": train, "dev": dev, "test": files_per_split["test"]}, {
        "dev": len(files_per_split["dev"]) - len(dev), "train": len(files_per_split["train"]) - len(train)}


def sha_fitxer(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def llegeix_capitols(arrel):
    """{slug: {"carpeta", "files", "sha", "estat"}} dels capítols que tenen 02 i 03 fets i sense error."""
    res = {}
    for nom in sorted(os.listdir(arrel)):
        c = os.path.join(arrel, nom)
        sub, est = os.path.join(c, "subtitols.jsonl"), os.path.join(c, "estat.json")
        if not (os.path.isfile(sub) and os.path.isfile(est)):
            continue
        try:
            estat = json.load(open(est, encoding="utf-8"))
        except ValueError:
            continue
        if not all((estat.get(k) or {}).get("fi") and not (estat.get(k) or {}).get("error") for k in ("02_llegeix", "03_talla")):
            continue
        files = [json.loads(l) for l in open(sub, encoding="utf-8") if l.strip()]
        res[nom] = {"carpeta": c, "files": files, "sha": sha_fitxer(sub), "estat": estat}
    return res


def selecciona(capitols):
    """-> (aptes per capítol, diagnòstic per capítol). Un capítol amb < MIN_APTES_CAPITOL aptes queda fora."""
    aptes, diag = {}, {}
    for slug, c in capitols.items():
        motius = collections.Counter()
        bones = []
        for r in c["files"]:
            ok_wav = wav_quadra(r, c["carpeta"], fi_02(c["estat"])) if r.get("tifinag") and not r.get("credits") else True
            ok, motiu = apta(r, ok_wav)
            if ok and not alineacio_ok(r, c["carpeta"]):
                ok, motiu = False, "alineació"
            if ok:
                bones.append(r)
            else:
                motius[motiu] += 1
        diag[slug] = {"titol": c["estat"].get("titol"), "files": len(c["files"]), "aptes": len(bones),
                      "hores": round(sum(r["durada"] for r in bones) / 3600, 3), "descartades": dict(motius)}
        if len(bones) >= MIN_APTES_CAPITOL:
            aptes[slug] = bones
        else:
            diag[slug]["fora"] = f"menys de {MIN_APTES_CAPITOL} aptes"
    return aptes, diag


def fila_dataset(r, split):
    return {"id": r["id"], "slug": r["slug"], "split": split, "tifinag": r["tifinag"], "durada": r["durada"],
            "conf": r.get("tifinag_conf"), "dubtosos": r.get("tifinag_dubtosos"), "fitxer": f"audio/{r['slug']}/{r['id']}.flac"}


def construeix(arrel, sortida, copia_audio=True):
    capitols = llegeix_capitols(arrel)
    aptes, diag = selecciona(capitols)
    part = particio(aptes)
    per_split = {s: [fila_dataset(r, s) for slug in part[s] for r in aptes[slug]] for s in part}
    per_split, repetits = treu_repetits(per_split)
    os.makedirs(os.path.join(sortida, "ds"), exist_ok=True)
    files = per_split["train"] + per_split["dev"] + per_split["test"]
    if copia_audio:
        feines = []
        for f in files:
            origen = os.path.join(capitols[f["slug"]]["carpeta"], "talls", f["id"] + ".wav")
            dest = os.path.join(sortida, "ds", f["fitxer"])
            if not os.path.exists(dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                feines.append((origen, dest))
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(lambda t: subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", t[0], "-ar", "16000", "-ac", "1", t[1]],
                                                 check=True), feines))
    hores = {s: round(sum(f["durada"] for f in per_split[s]) / 3600, 3) for s in per_split}
    resum = {"llavor": LLAVOR, "capitols": part, "hores": hores, "files": {s: len(per_split[s]) for s in per_split},
             "repetits_treta": repetits, "diagnostic": diag, "sha_subtitols": {s: capitols[s]["sha"] for s in aptes},
             "ids": {s: sorted(f["id"] for f in per_split[s]) for s in per_split}}
    resum["hash_ids"] = hashlib.sha256(json.dumps(resum["ids"], sort_keys=True).encode()).hexdigest()
    json.dump(files, open(os.path.join(sortida, "ds", "rows.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(resum, open(os.path.join(sortida, "particio.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return resum


# ------------------------------------------------------------------ regla de decisió
def dist(a, b):
    if a == b:
        return 0
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def parells_per_prova(sortides):
    """sortides: [{prova, video, de, or, dit, model}] -> {prova: [(or, abans, després)]}, només els talls amb els dos models."""
    per = {}
    for x in sortides:
        de = round(x["de"], 2) if isinstance(x["de"], (int, float)) else str(x["de"])
        per.setdefault((x["prova"], x["video"], de), {})[x["model"]] = x
    res = collections.defaultdict(list)
    for (prova, _, _), m in per.items():
        if "abans" in m and "després" in m:
            res[prova].append((m["abans"]["or"], m["abans"]["dit"], m["després"]["dit"]))
    return res


def bootstrap(parells, n=2000, llavor=LLAVOR):
    """Δ CER (després - abans) agregat amb IC 95 % per bootstrap aparellat sobre els talls."""
    rnd = random.Random(llavor)
    da = [dist(o, a) for o, a, _ in parells]
    db = [dist(o, b) for o, _, b in parells]
    ln = [len(o) for o, _, _ in parells]
    N = len(parells)
    tot = max(1, sum(ln))
    cer_a, cer_b = sum(da) / tot, sum(db) / tot
    boots = []
    for _ in range(n):
        idx = [rnd.randrange(N) for _ in range(N)]
        boots.append((sum(db[i] for i in idx) - sum(da[i] for i in idx)) / max(1, sum(ln[i] for i in idx)))
    boots.sort()
    return {"n": N, "abans": cer_a, "despres": cer_b, "delta": cer_b - cer_a, "ic_lo": boots[int(0.025 * n)], "ic_hi": boots[int(0.975 * n) - 1],
            "milloren": sum(1 for x, y in zip(da, db) if y < x), "empitjoren": sum(1 for x, y in zip(da, db) if y > x)}


def decideix(stats):
    """Regla §6.5: s'adopta si CV zgh baixa amb IC (límit alt < 0) I test-fora no empitjora més de 0,005
    I els capítols retinguts no empitjoren (salvaguarda del pla). stats: {prova: bootstrap(...)}."""
    motius, ok = [], True
    cv = stats.get("cv-zgh-test")
    if not cv:
        return {"adopta": False, "motius": ["falta la prova cv-zgh-test"]}
    if cv["ic_hi"] < MILLORA_CV_MAX_IC:
        motius.append(f"CV zgh millora: Δ {cv['delta']:+.4f} IC [{cv['ic_lo']:+.4f}, {cv['ic_hi']:+.4f}]")
    else:
        ok = False
        motius.append(f"CV zgh NO millora amb IC: Δ {cv['delta']:+.4f} IC [{cv['ic_lo']:+.4f}, {cv['ic_hi']:+.4f}]")
    fora = stats.get("test-fora")
    if fora is None:
        motius.append("test-fora absent: no es pot comprovar (no compta com a vist-i-plau)")
        ok = False
    elif fora["delta"] > EMPITJORA_FORA_MAX:
        ok = False
        motius.append(f"test-fora empitjora {fora['delta']:+.4f} (> {EMPITJORA_FORA_MAX})")
    else:
        motius.append(f"test-fora no empitjora més del compte: Δ {fora['delta']:+.4f}")
    ret = stats.get("snrt-retingut")
    if ret is None:
        ok = False
        motius.append("capítols retinguts absents")
    elif ret["delta"] > 0:
        ok = False
        motius.append(f"els capítols retinguts empitjoren {ret['delta']:+.4f}")
    else:
        motius.append(f"capítols retinguts: Δ {ret['delta']:+.4f}")
    return {"adopta": ok, "motius": motius}


def mostra_a_ull(sortides, prova="snrt-retingut", n=30, llavor=LLAVOR):
    """n talls de la prova (llavor 1114) amb referència, abans i després: per mirar-los (i escoltar-los) a ull."""
    per = {}
    for x in sortides:
        if x["prova"] == prova:
            per.setdefault((x["video"], x["de"]), {})[x["model"]] = x
    claus = sorted(k for k, m in per.items() if "abans" in m and "després" in m)
    random.Random(llavor).shuffle(claus)
    return [{"video": k[0], "id": k[1], "ref": per[k]["abans"]["or"], "abans": per[k]["abans"]["dit"], "despres": per[k]["després"]["dit"]}
            for k in claus[:n]]


def avalua(fitxer_sortides):
    sortides = json.load(open(fitxer_sortides, encoding="utf-8"))
    stats = {p: bootstrap(par) for p, par in sorted(parells_per_prova(sortides).items())}
    return {"stats": stats, "decisio": decideix(stats), "a_ull": mostra_a_ull(sortides)}


# ------------------------------------------------------------------ Kaggle (ECS)
def kaggle(*args, cwd=None, cli=None, check=True):
    cli = cli or os.environ.get("KAGGLE_CLI", "/root/venv-kaggle/bin/kaggle")
    p = subprocess.run([cli, *args], capture_output=True, text=True, cwd=cwd)
    if check and p.returncode:
        raise RuntimeError(f"kaggle {' '.join(args)}: {p.stdout[-400:]} {p.stderr[-400:]}")
    return p.stdout


def puja(sortida):
    ds = os.path.join(sortida, "ds")
    shutil.copy(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "snrt", "concordanca.py"), ds)   # el nucli CONC l'importa
    json.dump({"title": "SNRT transcriptor", "id": f"{USUARI_KAGGLE}/{DATASET}", "licenses": [{"name": "other"}], "isPrivate": True},
              open(os.path.join(ds, "dataset-metadata.json"), "w"))
    ja = DATASET in kaggle("datasets", "list", "--mine", "-s", DATASET, check=False)
    if ja:
        return kaggle("datasets", "version", "-p", ds, "-m", f"cicle {time.strftime('%Y-%m-%d %H:%M')}", "-r", "tar")
    return kaggle("datasets", "create", "-p", ds, "-r", "tar")   # privat per omissió; mai --public


def prepara_nucli(sortida, recepta, arrel_repo):
    """Directori del nucli amb la recepta escrita a la línia RECEPTA del guió."""
    d = os.path.join(sortida, f"nucli_{recepta}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    if recepta == "CONC":   # només escolta i puntua (tools/snrt/concordanca.py), no entrena
        nou = open(os.path.join(arrel_repo, "tools", "lm", "kaggle", "concordanca_snrt.py"), encoding="utf-8").read()
    else:
        font = open(os.path.join(arrel_repo, "tools", "lm", "kaggle", "transcriptor_snrt.py"), encoding="utf-8").read()
        nou, n = re.subn(r'^RECEPTA = "[AB]"$', f'RECEPTA = "{recepta}"', font, flags=re.M)
        assert n == 1, "no trobo la línia RECEPTA al nucli"
    codi = f"snrt-transcriptor-{recepta.lower()}.py"
    open(os.path.join(d, codi), "w", encoding="utf-8").write(nou)
    json.dump({"id": f"{USUARI_KAGGLE}/{NUCLI[recepta]}", "title": NUCLI[recepta].replace("-", " "), "code_file": codi, "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
               "dataset_sources": [f"{USUARI_KAGGLE}/{DATASET}"] + DATASETS_NUCLI, "kernel_sources": [], "competition_sources": []},
              open(os.path.join(d, "kernel-metadata.json"), "w"))
    return d


def llanca(sortida, recepta, arrel_repo):
    return kaggle("kernels", "push", "-p", prepara_nucli(sortida, recepta, arrel_repo), "--accelerator", "NvidiaTeslaT4")


def estat_nucli(recepta):
    s = kaggle("kernels", "status", f"{USUARI_KAGGLE}/{NUCLI[recepta]}", check=False).lower()
    for k in ("complete", "error", "cancel", "running", "queued"):
        if k in s:
            return k
    return "desconegut"


def espera(sortida, recepta, avisa=print, dorm=lambda s: time.sleep(s)):
    t0, ha_comencat = time.time(), False
    while True:
        e = estat_nucli(recepta)
        if e in FIN_NUCLI:
            break
        if e == "running":
            ha_comencat = True
        if not ha_comencat and time.time() - t0 > ESPERA_COMENCA_MAX:
            avisa(f"el nucli {NUCLI[recepta]} porta més de 90 min sense començar: cal avisar el cap d'equip")
            ha_comencat = True   # un sol avís
        dorm(60)
    out = os.path.join(sortida, f"sortida_{recepta}")
    os.makedirs(out, exist_ok=True)
    kaggle("kernels", "output", f"{USUARI_KAGGLE}/{NUCLI[recepta]}", "-p", out)
    return e, out


def registra(sortida, entrada):
    with open(os.path.join(sortida, "registre.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def cicles_sense_millora(sortida):
    """Quants cicles seguits (comptant des del darrer) s'han descartat o han fallat; la regla del pla atura a 2."""
    p = os.path.join(sortida, "registre.jsonl")
    if not os.path.exists(p):
        return 0
    n = 0
    for l in reversed([json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]):
        if l.get("adopta"):
            break
        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordre", choices=["construeix", "puja", "llanca", "espera", "avalua", "cicle"])
    ap.add_argument("--arrel", default="/root/tamazight_tv")
    ap.add_argument("--sortida", default="/root/transcriptor")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--recepta", choices=["A", "B", "CONC"], default="A", help="CONC: nucli de concordància (només escolta); no passa per «cicle»")
    ap.add_argument("--sortides", help="avalua: fitxer *_sortides.json")
    ap.add_argument("--forca", action="store_true", help="salta la parada de 2 cicles sense millora")
    a = ap.parse_args(argv)
    if a.ordre == "construeix":
        r = construeix(a.arrel, a.sortida)
        print(json.dumps({k: r[k] for k in ("hores", "files", "repetits_treta", "capitols", "hash_ids")}, ensure_ascii=False, indent=1))
    elif a.ordre == "puja":
        print(puja(a.sortida))
    elif a.ordre == "llanca":
        print(llanca(a.sortida, a.recepta, a.repo))
    elif a.ordre == "espera":
        print(espera(a.sortida, a.recepta))
    elif a.ordre == "avalua":
        print(json.dumps(avalua(a.sortides), ensure_ascii=False, indent=1))
    else:
        if a.recepta == "CONC":
            sys.exit("CONC no entrena: usa construeix, puja, llanca, espera (en aquest ordre)")
        if cicles_sense_millora(a.sortida) >= 2 and not a.forca:
            sys.exit("parat: dos cicles seguits sense millora (regla del pla); --forca per saltar-ho")
        r = construeix(a.arrel, a.sortida)
        puja(a.sortida)
        llanca(a.sortida, a.recepta, a.repo)
        e, out = espera(a.sortida, a.recepta)
        entrada = {"data": time.strftime("%Y-%m-%d %H:%M"), "recepta": a.recepta, "nucli": e, "hash_ids": r["hash_ids"], "hores": r["hores"]}
        s = os.path.join(out, f"snrt_{a.recepta}_sortides.json")
        if e == "complete" and os.path.exists(s):
            v = avalua(s)
            json.dump(v, open(os.path.join(a.sortida, f"veredicte_{a.recepta}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            entrada["adopta"] = v["decisio"]["adopta"]
            entrada["motius"] = v["decisio"]["motius"]
        else:
            entrada["adopta"] = False
            entrada["motius"] = ["el nucli no ha acabat bé"]
        registra(a.sortida, entrada)
        print(json.dumps(entrada, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
