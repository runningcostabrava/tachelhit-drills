"""Les 21.036 adreces de Cloudinary passen a ser nostres (#577).

El 5 de novembre de 2026 Cloudinary va desactivar el compte per haver passat els crèdits del
pla gratuït i va programar **l'esborrat definitiu per al 5 de desembre**. El #577 va pujar els
fitxers a R2 amb la mateixa ruta; el #581 va fer que el servidor els sàpiga servir. El que
queda és això: que la base de dades deixi d'assenyalar un lloc que d'aquí a tres setmanes
estarà buit.

Cada adreça `https://res.cloudinary.com/<compte>/<mena>/upload/v<versió>/<ruta>` passa a ser
`/mitjans/<ruta>`, que el servidor converteix en un desviament cap a una adreça signada d'una
hora. Res no s'esborra de Cloudinary: si això surt malament, es desfà i les adreces velles
tornen a funcionar fins al 5 de desembre.

## Les quatre portes

1. **El servidor ha de saber servir-ho.** Abans de tocar res es demana `/mitjans/<una ruta que
   sabem que hi és>` al servidor de debò. Si no contesta 307, s'atura. Això no és teoria: el
   13-11-2026 producció corria el codi del #581 i contestava **404 «Aquest servidor no serveix
   de R2»**, perquè les claus no eren a l'entorn de Render. Reescriure aquell dia hauria deixat
   l'app muda de cop.
2. **El fitxer ha de ser a R2.** Ruta per ruta, contra el llistat del bust. El que no hi sigui,
   no es toca: val més una adreça que caduca el 5 de desembre que una que no va des d'avui.
3. **Res que no sigui de Cloudinary.** Les 1.615 imatges de Wikimedia, els 1.201 vídeos de
   YouTube i les adreces que ja són `/mitjans/` es queden exactament com estan.
4. **Es pot desfer.** Cada canvi s'escriu a un CSV abans de desar-lo, i `--desfes` el torna
   enrere fil per randa.

## `updated_at`

Es toca a posta, i és important: el telèfon es baixa la biblioteca **pel que ha canviat des
de l'última vegada** (`/drills/?since=`). Si es canviessin les adreces sense tocar-lo, els
telèfons que ja tenen la biblioteca baixada es quedarien amb les adreces de Cloudinary per
sempre, i el 5 de desembre emmudirien tots alhora sense que el servidor hi pogués fer res.

## Com es fa servir

    cd backend
    python ../tools/reescriu_a_r2.py                      # mira i no toca res (per omissió)
    python ../tools/reescriu_a_r2.py --escriu             # ho fa
    python ../tools/reescriu_a_r2.py --desfes canvis.csv  # ho torna enrere

La base de dades surt de `DATABASE_URL`, com el servidor. Per a producció cal la de Render, i
qui l'executa ets tu: jo no escric a producció.
"""
import argparse
import csv
import io
import os
import sys

CAMPS = ["audio_url", "audio_tts_url", "audio_tts_shi_url", "image_url", "video_url"]

#: De quantes en quantes es desa. Petit a posta: el 29-10-2026 una càrrega massiva va passar
#: dels 512 MB de Render dues vegades en una tarda. Una sola cua, a poc a poc.
LOT = 200


def preparat(servidor: str, ruta: str) -> bool:
    """El servidor sap servir aquesta ruta des de R2? La porta número 1."""
    import requests
    adreca = servidor.rstrip("/") + "/mitjans/" + ruta.lstrip("/")
    try:
        r = requests.get(adreca, timeout=60, allow_redirects=False)
    except Exception as e:
        print(f"  no he pogut preguntar-li-ho: {type(e).__name__}: {e}")
        return False
    if r.status_code == 307:
        print(f"  {servidor} contesta 307: sap servir-ho.")
        return True
    detall = ""
    try:
        detall = " " + (r.json().get("detail") or "")
    except Exception:
        pass
    print(f"  {servidor} contesta {r.status_code}.{detall}")
    return False


def totes_les_claus(magatzem):
    """Tot el que hi ha al bust, per poder dir que una ruta hi és sense preguntar-ho una per una."""
    c = magatzem._r2()
    if c is None:
        sys.exit("R2 no està configurat aquí: falten claus a backend/.env")
    claus = set()
    for pagina in c.get_paginator("list_objects_v2").paginate(Bucket=magatzem._bust()):
        for o in pagina.get("Contents", []):
            claus.add(o["Key"])
    return claus


def adreces_de_lapi(servidor: str):
    """Les adreces de mitjans de totes les frases, demanades al servidor.

    Per a la passada en sec no cal entrar a la base: les adreces són al que l'API ja serveix a
    tothom, i així l'informe de **producció** es pot llegir sense cap credencial. De 500 en 500,
    que és com es demana la biblioteca des del #489 i per la raó del #566.

    Torna la mateixa forma que la base: una llista de (id, {camp: adreça}).
    """
    import requests
    fora, offset = [], 0
    while True:
        r = requests.get(servidor.rstrip("/") + "/drills/",
                         params={"limit": 500, "offset": offset}, timeout=180)
        r.raise_for_status()
        pagina = r.json()
        if not pagina:
            break
        for d in pagina:
            fora.append((d.get("id"), {c: (d.get(c) or "") for c in CAMPS}))
        total = r.headers.get("X-Total-Count")
        offset += 500
        print(f"  {len(fora):,}" + (f" de {total}" if total else "") + " frases")
        if len(pagina) < 500 or (total and offset >= int(total)):
            break
    print()
    return fora


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--escriu", action="store_true", help="desar de debò (per omissió, només mira)")
    p.add_argument("--desfes", metavar="CSV", help="torna enrere els canvis d'un full")
    p.add_argument("--full", default="reescriptura_a_r2.csv", help="on s'escriuen els canvis")
    p.add_argument("--servidor", default=os.getenv("API_BASE",
                   "https://tachelhit-drills-api.onrender.com"),
                   help="qui ha de saber servir els mitjans")
    p.add_argument("--sense-comprovar-el-servidor", action="store_true",
                   help="salta la porta 1. Només per a una base de proves.")
    p.add_argument("--env", help="d'on surten les claus, si no s'executa des de backend/")
    p.add_argument("--des-de-l-api", action="store_true",
                   help="llegeix les adreces del servidor en comptes de la base. Només per a la "
                        "passada en sec: no cal cap credencial de la base, i serveix per veure "
                        "l'informe de producció des de qualsevol lloc.")
    a = p.parse_args()

    sys.path.insert(0, os.path.abspath("."))
    from dotenv import load_dotenv
    load_dotenv(a.env) if a.env else load_dotenv()
    import magatzem
    from models import Drill as DrillModel
    from main import SessionLocal
    from datetime import datetime

    if a.desfes:
        return desfes(a.desfes, SessionLocal, DrillModel, a.escriu)

    print("llegint el bust…")
    claus = totes_les_claus(magatzem)
    print(f"  {len(claus):,} fitxers a {magatzem._bust()}")

    if a.des_de_l_api:
        if a.escriu:
            sys.exit("--des-de-l-api és només per a la passada en sec: per escriure cal la base.")
        print(f"demanant les adreces a {a.servidor}…")
        files = adreces_de_lapi(a.servidor)
        db = None
    else:
        db = SessionLocal()
        files = [(d.id, {c: (getattr(d, c, None) or "") for c in CAMPS})
                 for d in db.query(DrillModel).all()]
    try:
        print(f"  {len(files):,} frases")

        canvis, sense_fitxer, altres = [], [], 0
        for ident, camps in files:
            for camp in CAMPS:
                vell = (camps.get(camp) or "").strip()
                if not vell:
                    continue
                ruta = magatzem.clau_de_cloudinary(vell)
                if ruta is None:
                    altres += 1              # Wikimedia, YouTube, o ja és /mitjans/
                    continue
                if ruta not in claus:
                    sense_fitxer.append((ident, camp, vell, ruta))
                    continue
                canvis.append((ident, camp, vell, "/mitjans/" + ruta))

        print(f"\nadreces de Cloudinary que es poden reescriure: {len(canvis):,}")
        print(f"adreces de Cloudinary SENSE fitxer a R2:        {len(sense_fitxer):,}  (no es toquen)")
        print(f"adreces que no són de Cloudinary:               {altres:,}  (no es toquen)")
        for i, camp, vell, ruta in sense_fitxer[:10]:
            print(f"    frase {i}, {camp}: falta {ruta}")

        if not canvis:
            print("\nres a fer.")
            return 0

        # El full es desa SEMPRE, també quan només es mira: és el que es podrà llegir abans de
        # decidir, i el que servirà per desfer-ho.
        with io.open(a.full, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "camp", "abans", "despres"])
            w.writerows(canvis)
        print(f"\nel que es canviaria, fil per randa: {a.full}")

        if not a.escriu:
            print("\n(no s'ha tocat res. Amb --escriu es fa.)")
            return 0

        # --- porta 1: que el servidor ho sàpiga servir
        if not a.sense_comprovar_el_servidor:
            print(f"\npregunto a {a.servidor} si sap servir R2…")
            if not preparat(a.servidor, canvis[0][3][len("/mitjans/"):]):
                print("\nATURAT. Reescriure ara deixaria l'app muda: el servidor encara no serveix\n"
                      "els fitxers de R2. Cal posar R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,\n"
                      "R2_SECRET_ACCESS_KEY i R2_BUCKET a l'entorn del servidor i tornar-hi.")
                return 1

        print(f"\nescrivint {len(canvis):,} adreces, de {LOT} en {LOT}…")
        per_id = {}
        for i, camp, _vell, nou in canvis:
            per_id.setdefault(i, []).append((camp, nou))
        fets = 0
        ids = sorted(per_id)
        for inici in range(0, len(ids), LOT):
            for i in ids[inici:inici + LOT]:
                d = db.query(DrillModel).filter(DrillModel.id == i).first()
                if d is None:
                    continue
                for camp, nou in per_id[i]:
                    setattr(d, camp, nou)
                # Perquè els telèfons que ja tenen la biblioteca baixada se n'assabentin.
                d.updated_at = datetime.utcnow()
                fets += 1
            db.commit()
            print(f"  {min(inici + LOT, len(ids)):,}/{len(ids):,} frases")
        print(f"\nfet: {fets:,} frases, {len(canvis):,} adreces.")
        print(f"per desfer-ho:  python ../tools/reescriu_a_r2.py --desfes {a.full} --escriu")
        return 0
    finally:
        if db is not None:
            db.close()


def desfes(full, SessionLocal, DrillModel, escriu):
    """Torna cada camp al que hi havia, i només si ara hi ha el que hi vam posar.

    La condició importa: si algú ha tocat aquella adreça després, no és nostra per desfer.
    """
    from datetime import datetime
    with io.open(full, encoding="utf-8") as f:
        files = list(csv.DictReader(f))
    print(f"{len(files):,} canvis al full")
    db = SessionLocal()
    try:
        tornats, saltats = 0, 0
        for n, r in enumerate(files, 1):
            d = db.query(DrillModel).filter(DrillModel.id == int(r["id"])).first()
            if d is None or (getattr(d, r["camp"], None) or "") != r["despres"]:
                saltats += 1
                continue
            if escriu:
                setattr(d, r["camp"], r["abans"])
                d.updated_at = datetime.utcnow()
            tornats += 1
            if escriu and n % LOT == 0:
                db.commit()
        if escriu:
            db.commit()
        print(f"  tornats enrere: {tornats:,}")
        print(f"  saltats (ja no hi ha el que hi vam posar): {saltats:,}")
        if not escriu:
            print("\n(no s'ha tocat res. Amb --escriu es fa.)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
