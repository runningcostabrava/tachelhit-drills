"""Les 14 imatges de l'obra de l'app, de Cloudinary a R2 (#693).

El #577 va moure 21.002 fitxers, però només els que la base de dades esmentava **a les
frases**. L'obra no hi és: viu a `app_settings` (`artwork_home`, `artwork_method`) i, com a
còpia avançada perquè la portada no surti buida mentre el Render s'aixeca, escrita a mà al
`HomePage.tsx`. El 5 de desembre Cloudinary esborra el compte i la portada es quedaria amb
sis forats i el Mètode amb vuit.

Fa tres coses, i cap no toca el Cloudinary:

1. **Baixa** les 14 que `GET /artwork` diu, i mira que siguin el que diuen: un `.webp` ha de
   començar amb `RIFF....WEBP`. Ja ens han enganyat amb 2.673 WebM dient-se `.wav`, i un
   fitxer de zero bytes puja sense queixar-se.
2. **Puja** cadascuna a R2 amb **la mateixa ruta** que tenia (`tachelhit/app/<nom>.webp`), que
   és el conveni del #577 i el que `magatzem.clau_de_cloudinary()` dóna per fet.
3. **Escriu** el mapa nou a producció amb `PUT /artwork/{home,method}`, i abans el desa a un
   fitxer perquè es pugui desfer.

Les portes, en el mateix ordre que el `reescriu_a_r2.py`:

- el fitxer s'ha d'haver pujat i tornat a llegir bé **abans** de tocar la base de dades;
- el servidor ha de saber servir `/mitjans/...` (es prova amb una ruta acabada de pujar);
- el que no sigui de Cloudinary no es toca;
- i es pot desfer des del full desat.

    python tools/puja_obra_a_r2.py --env backend/.env              # en sec: diu què faria
    python tools/puja_obra_a_r2.py --env backend/.env --puja       # baixa i puja a R2
    python tools/puja_obra_a_r2.py --env backend/.env --escriu --testimoni <fitxer>
    python tools/puja_obra_a_r2.py --env backend/.env --desfes obra_abans.json --testimoni <f>

El testimoni d'administrador surt d'un fitxer, mai de la línia d'ordres: el que s'escriu a la
línia queda a l'historial del terminal.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://tachelhit-drills-api.onrender.com"

#: Els primers bytes de cada mena. `webp` és un contenidor RIFF: «RIFF», quatre bytes de mida,
#: i «WEBP». Per això es mira en dos trossos i no d'una tirada.
SIGNATURES = {
    ".webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    ".png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n",
    ".jpg": lambda b: b[:3] == b"\xff\xd8\xff",
    ".jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
}

#: `https://res.cloudinary.com/<compte>/<mena>/upload/v<versió>/<ruta>` -> `<ruta>`.
#: La versió (`v1792770886`) no forma part de la ruta: és el segell de Cloudinary.
CLOUDINARY = re.compile(
    r"^https?://res\.cloudinary\.com/[^/]+/(?:image|video|raw)/upload/(?:v\d+/)?(.+)$")


def clau_de_cloudinary(adreca):
    m = CLOUDINARY.match(adreca or "")
    return m.group(1) if m else None


def demana(cami, dades=None, testimoni=None, metode=None):
    cos = json.dumps(dades, ensure_ascii=False).encode() if dades is not None else None
    cap = {"User-Agent": "tachelhit-ops/1.0"}
    if cos:
        cap["Content-Type"] = "application/json"
    if testimoni:
        cap["X-User-Token"] = testimoni
    req = urllib.request.Request(API + cami, data=cos, headers=cap,
                                 method=metode or ("PUT" if cos else "GET"))
    with urllib.request.urlopen(req, timeout=180) as r:
        text = r.read().decode("utf-8", "replace")
    return json.loads(text) if text.strip() else {}


def client_i_bust(env):
    from dotenv import load_dotenv
    load_dotenv(env) if env else load_dotenv()
    import boto3
    compte, bust = os.getenv("R2_ACCOUNT_ID"), os.getenv("R2_BUCKET")
    if not (compte and bust and os.getenv("R2_ACCESS_KEY_ID")
            and os.getenv("R2_SECRET_ACCESS_KEY")):
        sys.exit("R2 no està configurat: falten claus (passa --env backend/.env)")
    return boto3.client("s3", endpoint_url=f"https://{compte}.r2.cloudflarestorage.com",
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                        region_name="auto"), bust


def mena_de(clau):
    ext = os.path.splitext(clau)[1].lower()
    return {".webp": "image/webp", ".png": "image/png",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "application/octet-stream")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--env", help="d'on surten les claus de R2")
    p.add_argument("--puja", action="store_true", help="baixa de Cloudinary i puja a R2")
    p.add_argument("--escriu", action="store_true", help="canvia les adreces a producció")
    p.add_argument("--testimoni", help="fitxer amb el testimoni d'administrador")
    p.add_argument("--desfes", help="full desat d'abans, per tornar-hi")
    p.add_argument("--full", default="obra_abans.json", help="on es desa el d'abans")
    a = p.parse_args()

    testimoni = None
    if a.testimoni:
        testimoni = io.open(a.testimoni, encoding="utf-8").read().strip()
        if not testimoni:
            sys.exit("el fitxer del testimoni és buit")

    # ---- desfer ----------------------------------------------------------
    if a.desfes:
        if not testimoni:
            sys.exit("per desfer cal --testimoni")
        abans = json.load(io.open(a.desfes, encoding="utf-8"))
        for quin, mapa in abans.items():
            demana(f"/artwork/{quin}", {"covers": mapa}, testimoni)
            print(f"{quin}: tornades {len(mapa)} adreces com estaven")
        return

    obra = demana("/artwork")
    feina = []
    for quin, mapa in obra.items():
        for nom, adreca in (mapa or {}).items():
            clau = clau_de_cloudinary(adreca)
            if clau:
                feina.append((quin, nom, adreca, clau))
    print(f"obra: {sum(len(m or {}) for m in obra.values())} imatges, "
          f"{len(feina)} encara a Cloudinary")
    if not feina:
        print("res a fer")
        return

    client, bust = client_i_bust(a.env)
    ja = set()
    for pag in client.get_paginator("list_objects_v2").paginate(Bucket=bust,
                                                                Prefix="tachelhit/app/"):
        ja.update(o["Key"] for o in pag.get("Contents", []))
    print(f"a R2, sota tachelhit/app/: {len(ja)} objectes")

    if not a.puja and not a.escriu:
        for quin, nom, _, clau in feina:
            print(f"   {quin}/{nom:18s} -> {clau} {'(ja hi és)' if clau in ja else ''}")
        print("\nen sec: no s'ha tocat res. --puja per moure els fitxers.")
        return

    # ---- 1 i 2: baixar, comprovar, pujar ---------------------------------
    if a.puja:
        for quin, nom, adreca, clau in feina:
            if clau in ja:
                print(f"   {clau}: ja hi era")
                continue
            try:
                req = urllib.request.Request(adreca, headers={"User-Agent": "tachelhit-ops"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    dades = r.read()
            except urllib.error.HTTPError as e:
                print(f"   {clau}: NO es baixa ({e.code}); el deixo estar")
                continue
            ext = os.path.splitext(clau)[1].lower()
            mira = SIGNATURES.get(ext)
            if not dades:
                print(f"   {clau}: zero bytes; no el pujo")
                continue
            if mira and not mira(dades):
                print(f"   {clau}: els primers bytes no són de {ext}; no el pujo")
                continue
            client.put_object(Bucket=bust, Key=clau, Body=dades, ContentType=mena_de(clau))
            #: tornar-lo a llegir: pujar sense queixa no vol dir que hi sigui sencer
            tornat = client.head_object(Bucket=bust, Key=clau)["ContentLength"]
            estat = "✓" if tornat == len(dades) else f"MIDA DIFERENT ({tornat} vs {len(dades)})"
            print(f"   {clau}: {len(dades):,} B  {estat}")
            if tornat == len(dades):
                ja.add(clau)

    # ---- 3: les adreces --------------------------------------------------
    if not a.escriu:
        print("\nfitxers moguts. --escriu (amb --testimoni) per canviar les adreces.")
        return
    if not testimoni:
        sys.exit("per escriure cal --testimoni")

    #: La porta del #581: que el servidor sàpiga servir-ho. Es prova amb una ruta acabada de
    #: pujar, no amb una de qualsevol: el 13-11 producció contestava 404 perquè les claus no
    #: eren a Render, i reescriure aquell dia hauria deixat l'app muda.
    prova = next((c for _, _, _, c in feina if c in ja), None)
    if not prova:
        sys.exit("cap fitxer a R2: no toco les adreces")
    try:
        req = urllib.request.Request(f"{API}/mitjans/{prova}",
                                     headers={"User-Agent": "ops", "Range": "bytes=0-63"})
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status not in (200, 206) or not r.read(1):
                sys.exit(f"producció contesta {r.status} a /mitjans/{prova}: no toco res")
    except urllib.error.HTTPError as e:
        sys.exit(f"producció contesta {e.code} a /mitjans/{prova}: no toco res")
    print(f"producció serveix /mitjans/{prova}")

    json.dump(obra, io.open(a.full, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"el d'abans, desat a {a.full}")

    for quin, mapa in obra.items():
        nou = dict(mapa or {})
        canviats = 0
        for nom, adreca in (mapa or {}).items():
            clau = clau_de_cloudinary(adreca)
            if clau and clau in ja:
                nou[nom] = f"/mitjans/{clau}"
                canviats += 1
        if canviats:
            demana(f"/artwork/{quin}", {"covers": nou}, testimoni)
            print(f"{quin}: {canviats} adreces canviades")

    queda = sum(1 for m in demana("/artwork").values()
                for v in (m or {}).values() if clau_de_cloudinary(v))
    print(f"\ncomprovació: queden {queda} adreces de Cloudinary a /artwork")


if __name__ == "__main__":
    main()
