# -*- coding: utf-8 -*-
"""Vigilància setmanal (#578): el que va fallar el 5 de novembre no va ser el dipòsit, va ser
que ningú no mirava. Això mira, cada setmana, i ho escriu on es llegeixi:

  1. el dipòsit de mitjans (R2): objectes i bytes contra el límit del pla, avís al 60 %;
  2. l'edat de l'última còpia fora (dataset de Hugging Face), avís passats 14 dies;
  3. que el servidor contesti (`/health`), i que un mitjà a l'atzar del bust es pugui obrir;
  4. que les credencials que fa servir siguin vives: una clau morta és un AVÍS, no un error.

No escriu res enlloc, no esborra res. Imprimeix un informe en Markdown; les línies que
comencen per «AVÍS» són les que demanen una persona. Sempre surt amb codi 0: el cron no ha
de «fallar», ha d'informar.

    python tools/vigilancia.py [--env backend/.env]
    Variables: R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET
               R2_LIMIT_GB (10 per omissió, el pla gratuït)   HF_TOKEN + HF_COPIA_DATASET (opcional)
               API_URL (https://tachelhit-drills-api.onrender.com per omissió)
"""
import datetime as dt
import os
import random
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ARREL, "backend"))
AVISOS = []


def avis(text):
    AVISOS.append(text)
    print(f"- **AVÍS** {text}")


def seccio_r2():
    from dotenv import load_dotenv  # noqa
    try:
        import magatzem
        c, bust = magatzem._r2(), magatzem._bust()
    except Exception as e:
        avis(f"R2: no es pot carregar el client ({type(e).__name__})")
        return
    if c is None:
        avis("R2: no hi ha claus (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET)")
        return
    try:
        n = total = 0
        claus = []
        for pagina in c.get_paginator("list_objects_v2").paginate(Bucket=bust):
            for o in pagina.get("Contents", []):
                n += 1
                total += o["Size"]
                if len(claus) < 2000:
                    claus.append(o["Key"])
    except Exception as e:
        avis(f"R2: la clau no serveix o el bust no contesta ({type(e).__name__}: {str(e)[:80]})")
        return
    limit = float(os.getenv("R2_LIMIT_GB", "10"))
    gb = total / 1e9
    pct = 100 * gb / limit if limit else 0
    print(f"- R2 `{bust}`: **{n:,} objectes, {gb:.2f} GB** ({pct:.0f} % de {limit:g} GB)")
    if pct >= 60:
        avis(f"R2 és al {pct:.0f} % del pla ({gb:.2f} de {limit:g} GB)")
    if n < 20000:
        avis(f"R2 té {n:,} objectes; la biblioteca n'espera més de 21.000 (#577)")
    #: obrir-ne un: que no sigui només una llista
    if claus:
        k = random.choice(claus)
        try:
            cos = c.get_object(Bucket=bust, Key=k)["Body"].read(64)
            print(f"- un mitjà a l'atzar s'obre: `{k}` ({len(cos)} bytes llegits)" if cos else f"- **AVÍS** `{k}` és buit")
            if not cos:
                AVISOS.append(f"{k} buit")
        except Exception as e:
            avis(f"no es pot obrir `{k}` ({type(e).__name__})")


def seccio_copia():
    nom = os.getenv("HF_COPIA_DATASET", "").strip()
    token = os.getenv("HF_TOKEN", "").strip()
    if not nom:
        print("- còpia fora (Hugging Face): `HF_COPIA_DATASET` no configurat; **no es vigila** (#576)")
        return
    try:
        from huggingface_hub import HfApi
        info = HfApi(token=token or None).dataset_info(nom, files_metadata=False)
        quan = info.last_modified
        dies = (dt.datetime.now(dt.timezone.utc) - quan).days if quan else None
        print(f"- còpia fora `{nom}`: última modificació {quan:%Y-%m-%d} ({dies} dies)")
        if dies is not None and dies > 14:
            avis(f"la còpia de Hugging Face té {dies} dies")
    except Exception as e:
        avis(f"Hugging Face: no es pot llegir `{nom}` ({type(e).__name__}: {str(e)[:80]}); clau morta o dataset mogut")


def seccio_servidor():
    import requests
    url = os.getenv("API_URL", "https://tachelhit-drills-api.onrender.com").rstrip("/")
    try:
        r = requests.get(url + "/health", timeout=90)
        print(f"- servidor `{url}/health`: {r.status_code}")
        if r.status_code != 200:
            avis(f"el servidor contesta {r.status_code}")
    except Exception as e:
        avis(f"el servidor no contesta ({type(e).__name__})")


if __name__ == "__main__":
    from dotenv import load_dotenv
    if "--env" in sys.argv:
        load_dotenv(sys.argv[sys.argv.index("--env") + 1])
    else:
        load_dotenv(os.path.join(ARREL, "backend", ".env"))
    print(f"## Vigilància {dt.date.today():%Y-%m-%d}\n")
    seccio_r2()
    seccio_copia()
    seccio_servidor()
    print()
    print(f"**{len(AVISOS)} avisos.**" if AVISOS else "**Tot bé.** Cap avís.")
