"""Les dues cares de l'experiment que ha de dir si el retall val: sencer contra retallat.

**La pregunta que queda oberta.** La §45 mesura que un model JA ENTRENAT transcriu millor un
so retallat (-0,2235 de CER). El que no se sap es si **entrenar** amb talls retallats dona un
model millor. Es molt probable -- si el 51 % de cada clip es una altra persona parlant, el
model aprèn a casar so equivocat amb text -- pero no esta provat, i aquest projecte ja ha
tingut prou hipotesis raonables que eren falses.

⚠️ **Dels dos numeros del paragraf de dalt, cap no mesura el que diu** (quadern, §48 i §49), i
aixo fa aquest experiment mes necessari, no menys. El 51 % venia d'una alineacio que no va rebre
mai la frase (vocabulari llati, text en tifinag: alineava els separadors), aixi que no se sap si
el que es llenca es una altra persona parlant o silenci. I el -0,2235 el va donar una
comparacio que canviava la durada de l'entrada: amb el CER de partida per sobre d'1, escurcar el
so baixa el CER encerti o no la frontera -- menjar-se 0,3 s de veu real guanya tres vegades mes.
Aixi que **aquest es l'unic jutge que queda**: dos entrenaments i un test de durada fixa, el
mateix sencer als dos costats. El guany real del retall esta sense mesurar.

**Com es prova net.** Dos corpus **identics en tot** menys en una cosa: els mateixos capitols,
les mateixes files, la mateixa particio, el mateix text. L'unic que canvia es si el wav va
sencer o retallat a `[veu_ini - 0,15 s, veu_fi + 0,15 s]`. Dos entrenaments, el mateix test.

**La particio es per CAPITOLS, no per files.** Dues files del mateix capitol comparteixen
convidat, tema i vocabulari; partir per files posaria el mateix convidat als dos costats i el
numero sortiria massa bo. (§42: el 20-11 el dev va quedar 100 % tarifit per no mirar aixo.)

**El test es el MATEIX per als dos**, i va sencer als dos casos: el que es compara es quin
entrenament dona el millor model, no quin test es mes facil.

    python prepara_experiment.py [--min-capitols 6]
"""
import argparse
import io
import json
import random
import shutil
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
ARREL = Path(r"E:/tamazight/talls_ecs")
#: per defecte, el MMS_FA de tot el corpus local. El fitxer del model gran serveix igual i es
#: passa amb `--alineacio`; el que NO val es cap `*_NOMES_SEPARADORS.jsonl`, que son les
#: fronteres que alineaven els espais entre paraules (quadern, §48).
ALI = MAG / "alineacio_mms_fa_tot.jsonl"
FORA = MAG / "experiment_retall"
MARGE = 0.15
LLAVOR = 1114


def alineacio(cami=None):
    cami = Path(cami or ALI)
    assert "NOMES_SEPARADORS" not in cami.name, (
        f"{cami.name} porta fronteres que alineaven els espais entre paraules, no la frase")
    d = {}
    for l in io.open(cami, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            x = json.loads(l)
        except Exception:
            continue
        if x.get("veu_ini") is not None and x.get("veu_fi") is not None:
            d[x["so"]] = x
    return d


def text_dels_talls():
    t = {}
    for p in ARREL.glob("*/subtitols.jsonl"):
        for l in io.open(p, encoding="utf-8"):
            if not l.strip():
                continue
            f = json.loads(l)
            if f.get("tall"):
                t[Path(f["tall"]).name] = f
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alineacio", default=str(ALI),
                    help="el fitxer de fronteres: MMS_FA o el del model gran")
    ap.add_argument("--marge", type=float, default=MARGE,
                    help="s de coixi a banda i banda de la frontera")
    ap.add_argument("--min-capitols", type=int, default=6,
                    help="per sota d'això no hi ha prou capítols per partir-los bé")
    a = ap.parse_args()

    import numpy as np
    import soundfile as sf

    ali = alineacio(a.alineacio)
    text = text_dels_talls()
    print(f"{len(ali)} talls alineats · {len(text)} amb text")

    #: només capítols alineats del tot: un capítol a mitges partiria el test
    per_cap = {}
    for nom, x in ali.items():
        per_cap.setdefault(x["capitol"], []).append(nom)
    sencers = []
    for c, noms in per_cap.items():
        tot = len(list((ARREL / c / "talls").glob("*.wav"))) if (ARREL / c / "talls").is_dir() else 0
        if tot and len(noms) >= tot * 0.98:
            sencers.append(c)
    print(f"   {len(per_cap)} capítols tocats · {len(sencers)} alineats del tot")

    if len(sencers) < a.min_capitols:
        print(f"\n   NOMÉS {len(sencers)} capítols sencers: en calen {a.min_capitols} per")
        print("   partir train/dev/test sense que el mateix convidat caigui als dos costats.")
        print("   L'alineació encara corre: torna-hi quan n'hi hagi més.")
        return 1

    sencers.sort()
    random.Random(LLAVOR).shuffle(sencers)
    n_test = max(1, len(sencers) // 5)
    n_dev = max(1, len(sencers) // 6)
    parts = {"test": sencers[:n_test], "dev": sencers[n_test:n_test + n_dev],
             "train": sencers[n_test + n_dev:]}
    for k, v in parts.items():
        print(f"   {k}: {len(v)} capítols")

    if FORA.exists():
        shutil.rmtree(FORA)
    for cara in ("sencer", "retallat"):
        (FORA / cara / "so").mkdir(parents=True, exist_ok=True)

    files = {"sencer": {k: [] for k in parts}, "retallat": {k: [] for k in parts}}
    saltats = 0
    for part, caps in parts.items():
        for c in caps:
            for nom in sorted(per_cap[c]):
                f = text.get(nom)
                if not f:
                    saltats += 1
                    continue
                zgh = (f.get("tifinag") or "").strip()
                if len(zgh.split()) < 2:
                    saltats += 1
                    continue
                w = ARREL / c / "talls" / nom
                if not w.exists():
                    saltats += 1
                    continue
                x, sr = sf.read(str(w), dtype="float32")
                if x.ndim > 1:
                    x = x.mean(axis=1)
                v = ali[nom]
                i0 = max(0, int((v["veu_ini"] - a.marge) * sr))
                i1 = min(len(x), int((v["veu_fi"] + a.marge) * sr))
                if i1 - i0 < sr * 0.3:
                    saltats += 1
                    continue
                for cara, senyal in (("sencer", x), ("retallat", x[i0:i1])):
                    sf.write(str(FORA / cara / "so" / nom), senyal, sr)
                    files[cara][part].append(
                        {"so": nom, "zgh": zgh, "ar": (f.get("arab") or "").strip(),
                         "capitol": c, "durada": round(len(senyal) / sr, 3)})

    for cara in ("sencer", "retallat"):
        for part in parts:
            p = FORA / cara / f"{part}.jsonl"
            with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
                for r in files[cara][part]:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        d = sum(r["durada"] for part in parts for r in files[cara][part]) / 3600
        n = sum(len(files[cara][part]) for part in parts)
        print(f"   {cara}: {n} talls · {d:.2f} h")

    print(f"   {saltats} saltats (sense text, massa curts o sense wav)")
    print(f"\nescrit a {FORA}")
    print("Les dues cares tenen les MATEIXES files i la MATEIXA partició: només canvia el so.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
