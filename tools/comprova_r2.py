"""Que la còpia de R2 és de debò: comptar-la, i obrir-ne unes quantes (#576, #579).

El 5 de novembre de 2026 Cloudinary va desactivar el compte i va programar l'esborrat de tots
els fitxers per al **5 de desembre**. A dins hi havia 11.307 gravacions de veu humana i cap
còpia enlloc. El #577 les va moure a R2; aquest guió respon la pregunta que ve després i que
ningú no havia fet mai: **la còpia és sencera, i els fitxers són el que diuen ser?**

«Hi ha 21.002 objectes al bust» no és una resposta. Ja ens han enganyat dues vegades:

- 2.673 fitxers eren WebM dient-se `.wav` (`puja_corpus_v3.py`);
- un fitxer de zero bytes puja sense queixar-se i es llista com qualsevol altre.

Per això això fa tres coses, i la tercera és la que val:

1. **Compta** el bust (objectes i bytes), i els compara amb el que la biblioteca espera.
2. **Casa** cada adreça de la biblioteca amb un objecte del bust, i diu quines falten.
3. **N'obre** unes quantes a l'atzar: les baixa de debò i mira la mida i els primers bytes.
   Un `.mp3` que comença amb `OggS` no és un `.mp3`, i un de zero bytes no és res.

No escriu res enlloc. No esborra res. Només mira.

    cd backend
    python ../tools/comprova_r2.py                 # compta, casa, i n'obre 10 a l'atzar
    python ../tools/comprova_r2.py --obre 40       # n'obre 40
    python ../tools/comprova_r2.py --obre 0        # només compta i casa
    python ../tools/comprova_r2.py --full comprovacio.csv   # el recompte, fitxer a fitxer

Les claus surten de `backend/.env` (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
R2_BUCKET), que és d'on les treu el servidor. No se n'escriu cap ni se'n diu cap.
"""
import argparse
import csv
import io
import os
import random
import sys

# Els primers bytes de cada mena de fitxer, i quines extensions hi corresponen. És la mateixa
# llista que `backend/magatzem.py`, amb la mirada girada: allà serveix per posar l'extensió,
# aquí per comprovar que la que hi ha no menteixi.
SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
    (b"GIF8", "gif"),
    (b"ID3", "mp3"),
    (b"\xff\xfb", "mp3"), (b"\xff\xf3", "mp3"), (b"\xff\xf2", "mp3"), (b"\xff\xe3", "mp3"),
    (b"OggS", "ogg"),
    (b"\x1a\x45\xdf\xa3", "webm"),
    (b"fLaC", "flac"),
    # RIFF no diu què és: cal mirar el byte 8. Un `.webp` i un `.wav` comencen exactament igual,
    # i la primera passada d'això va acusar un `.webp` perfectament sà de ser un `.wav`.
]

#: Què hi ha al byte 8 quan els quatre primers són RIFF.
RIFF = {b"WEBP": "webp", b"WAVE": "wav", b"AVI ": "avi"}

#: Extensions que de fet són la mateixa cosa, i que per tant no són cap engany.
IGUALS = [{"jpg", "jpeg"}, {"mp4", "m4a", "mov"}, {"webm", "mkv"}, {"ogg", "oga", "opus"}]


def mena_pels_bytes(cap: bytes):
    """Què són aquests bytes, o None si no ho sabem dir."""
    if cap.startswith(b"RIFF"):
        return RIFF.get(bytes(cap[8:12]))
    for marca, nom in SIGNATURES:
        if cap.startswith(marca):
            return nom
    # L'MP4 i companyia porten `ftyp` al byte 4, no al 0.
    if len(cap) >= 12 and cap[4:8] == b"ftyp":
        return "mp4"
    return None


def menteix(extensio: str, pels_bytes: str) -> bool:
    e, b = (extensio or "").lower().lstrip("."), (pels_bytes or "").lower()
    if not e or not b or e == b:
        return False
    return not any(e in grup and b in grup for grup in IGUALS)


def client_i_bust(env=None):
    sys.path.insert(0, os.path.abspath("."))
    from dotenv import load_dotenv
    # `--env` hi és perquè una còpia de treball (un `git worktree`) no porta el `.env`: les claus
    # viuen només al dipòsit de debò, i no se'n fan còpies escampades.
    load_dotenv(env) if env else load_dotenv()
    import magatzem
    c = magatzem._r2()
    if c is None:
        sys.exit("R2 no està configurat: falten claus a backend/.env "
                 "(R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET).")
    return c, magatzem._bust()


def tot_el_bust(c, bust):
    """Tots els objectes, amb la mida. Paginat: 21.000 no caben en una resposta."""
    fora = {}
    sortida = c.get_paginator("list_objects_v2")
    for pagina in sortida.paginate(Bucket=bust):
        for o in pagina.get("Contents", []):
            fora[o["Key"]] = o["Size"]
    return fora


def ruta_de_r2(u: str, magatzem=None):
    """Quina ruta de R2 hauria de tenir aquesta adreça, o None si no és nostra.

    Compta les dues menes, i això és el que fa que la comprovació valgui **avui**:

    - `/mitjans/<ruta>`: les adreces noves, les que serveix el servidor des del #577.
    - les de Cloudinary: les 21.036 que encara hi ha a la base de dades. La pregunta que s'ha
      de poder contestar abans del 5 de desembre no és «què apunta a R2», és **«tot el que
      encara apunta a Cloudinary, és a R2?»**, perquè aquell dia Cloudinary ho esborra.

    La regla de Cloudinary surt de `magatzem.clau_de_cloudinary`, que és l'únic lloc del
    programa que sap on viuen els fitxers: aquí no se'n fa cap segona còpia.
    """
    u = (u or "").strip()
    if not u:
        return None
    tros = u.split("/mitjans/", 1)
    if len(tros) == 2 and tros[1]:
        return tros[1].split("?", 1)[0]
    if magatzem is None:
        import magatzem as magatzem_
        magatzem = magatzem_
    return magatzem.clau_de_cloudinary(u)


def el_que_espera_la_biblioteca(bib: str):
    """Les rutes de mitjans que la biblioteca esmenta, per camp.

    Surt del cau local (el mateix fitxer que fan servir els guions de tools/baba_ali) per no
    haver de demanar-li res al servidor: no és una comprovació que hagi de despertar Render.
    """
    import json
    camps = ["audio_url", "audio_tts_url", "audio_tts_shi_url", "image_url", "video_url"]
    espera = {}
    with io.open(bib, encoding="utf-8") as f:
        for d in json.load(f):
            for camp in camps:
                ruta = ruta_de_r2(d.get(camp))
                if ruta:
                    espera.setdefault(ruta, []).append((d.get("id"), camp))
    return espera


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--obre", type=int, default=10,
                   help="quants fitxers s'obren de debò (0 = cap). Per omissió 10.")
    p.add_argument("--full", help="escriu el recompte fitxer a fitxer en un CSV")
    p.add_argument("--biblioteca",
                   default=r"C:\Users\josep\Veus-tachelhit\_subtitols\_biblioteca.json",
                   help="el cau de la biblioteca, per casar les adreces")
    p.add_argument("--llavor", type=int, default=None,
                   help="per repetir exactament la mateixa tria a l'atzar")
    p.add_argument("--env", help="d'on surten les claus, si no s'executa des de backend/")
    a = p.parse_args()

    c, bust = client_i_bust(a.env)
    print(f"bust: {bust}")
    print("comptant…")
    objectes = tot_el_bust(c, bust)
    bytes_totals = sum(objectes.values())
    buits = [k for k, v in objectes.items() if v == 0]
    print(f"  {len(objectes):,} objectes, {bytes_totals / 1e9:.2f} GB")
    if buits:
        print(f"  ATENCIÓ: {len(buits)} de zero bytes:")
        for k in buits[:10]:
            print(f"    {k}")

    # --- el que la biblioteca espera trobar-hi
    if os.path.exists(a.biblioteca):
        espera = el_que_espera_la_biblioteca(a.biblioteca)
        falten = [r for r in espera if r not in objectes]
        print(f"\nla biblioteca esmenta {len(espera):,} rutes de R2")
        print(f"  hi són:  {len(espera) - len(falten):,}")
        print(f"  FALTEN:  {len(falten):,}")
        for r in falten[:15]:
            qui = espera[r][0]
            print(f"    {r}   (frase {qui[0]}, camp {qui[1]})")
        sobren = len(objectes) - (len(espera) - len(falten))
        print(f"  al bust n'hi ha {sobren:,} que la biblioteca no esmenta "
              f"(mitjans vells, talls, proves: el #579)")
    else:
        espera = {}
        print(f"\n(no hi ha el cau de la biblioteca a {a.biblioteca}: no es pot casar)")

    # --- obrir-ne unes quantes, que és l'única comprovació que val
    enganys = []
    if a.obre > 0 and objectes:
        rnd = random.Random(a.llavor)
        tria = rnd.sample(sorted(objectes), min(a.obre, len(objectes)))
        print(f"\nn'obro {len(tria)} a l'atzar:")
        for ruta in tria:
            mida = objectes[ruta]
            try:
                r = c.get_object(Bucket=bust, Key=ruta, Range="bytes=0-15")
                cap = r["Body"].read()
            except Exception as e:
                print(f"  ✗ {ruta}\n      no s'ha pogut obrir: {type(e).__name__}: {e}")
                enganys.append((ruta, "no s'obre"))
                continue
            ext = os.path.splitext(ruta)[1].lstrip(".").lower()
            diuen = mena_pels_bytes(cap)
            if mida == 0:
                print(f"  ✗ {ruta}\n      zero bytes")
                enganys.append((ruta, "buit"))
            elif diuen is None:
                print(f"  ? {ruta}  ({mida:,} B, .{ext}) — els primers bytes no diuen què és")
            elif menteix(ext, diuen):
                print(f"  ✗ {ruta}\n      es diu .{ext} i és un {diuen} ({mida:,} B)")
                enganys.append((ruta, f".{ext} però és {diuen}"))
            else:
                print(f"  ✓ {ruta}  ({mida:,} B, {diuen})")

    if a.full:
        with io.open(a.full, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ruta", "bytes", "la biblioteca l'esmenta"])
            for ruta, mida in sorted(objectes.items()):
                w.writerow([ruta, mida, "sí" if ruta in espera else "no"])
        print(f"\nrecompte fitxer a fitxer: {a.full}")

    print()
    if enganys:
        print(f"RESULTAT: {len(enganys)} dels oberts no són el que diuen ser.")
        return 1
    print("RESULTAT: el que s'ha obert és el que diu ser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
