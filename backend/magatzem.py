"""On viuen els fitxers: l'únic lloc del programa que ho sap.

Fins ara `cloudinary.uploader.upload` es cridava des de **deu llocs** de `main.py`: el TTS,
les imatges, el `upload_media` del mòbil, el treballador de vídeo, el retallador d'àudio...
Deu còpies de la mateixa decisió. Això és exactament el que ens va portar al desastre del
novembre de 2026: quan el compte de Cloudinary es va desactivar per haver passat els
crèdits, no hi havia cap lloc on tocar per moure's a un altre dipòsit — n'hi havia deu.

És la mateixa lliçó del #557, on la graella desava bé la lectura de la màquina i l'editor
del mòbil l'escrivia damunt del text del parlant, perquè la regla vivia duplicada.

Qui hagi de desar un fitxer, que cridi `puja()` i no pensi mai més on va a parar.

## Dos dipòsits (#577)

Si hi ha les claus de **R2** configurades, s'hi desa. Si no, Cloudinary, com sempre. Els
fitxers que ja són a Cloudinary segueixen servint-se d'allà: aquí no s'esborra res.

**L'adreça que torna R2 NO és la del bust.** És `/mitjans/<ruta>`, una adreça nostra, i qui
la demana rep un desviament cap a una adreça signada que dura una hora. Hi ha dues raons:

1. El bust és privat. Una adreça signada caduca, i a la base de dades les adreces hi viuen
   per sempre: desar-n'hi una seria desar una cosa que demà no va.
2. Si algun dia canviem de dipòsit una altra vegada, **no caldrà tornar a tocar cap adreça**
   de la base de dades. Aquest cop ens ha tocat reescriure'n 21.002.
"""
import io
import mimetypes
import os
import re

import cloudinary
import cloudinary.uploader

#: Com en diem nosaltres -> com en diu Cloudinary. Cloudinary tracta el so com si fos vídeo:
#: és una raresa seva que no ha de sortir d'aquí.
MENES = {
    "so": "video",
    "video": "video",
    "imatge": "image",
    "auto": "auto",
}

#: Quan no se sap l'extensió de cap altra manera. Val més això que no pas cap: el navegador
#: decideix si sap reproduir un fitxer pel tipus que li arriba, i el tipus surt de l'extensió.
PER_DEFECTE = {"so": ".mp3", "video": ".mp4", "imatge": ".jpg", "auto": ".bin"}

#: Els primers bytes de cada mena de fitxer. Serveix quan ens donen el contingut i no un camí
#: (les imatges dibuixades i les gravacions del mòbil arriben així).
SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
    (b"ID3", ".mp3"),
    (b"\xff\xfb", ".mp3"),
    (b"\xff\xf3", ".mp3"),
    (b"\xff\xf2", ".mp3"),
    (b"OggS", ".ogg"),
    (b"\x1a\x45\xdf\xa3", ".webm"),
    (b"fLaC", ".flac"),
]

SEGONS_SIGNADA = int(os.getenv("R2_SEGONS_SIGNADA", "3600"))


def _r2():
    """El client de R2, o None si no està configurat.

    El client es guarda per no refer-lo a cada fitxer, però **lligat als valors de l'entorn**
    i no a la primera crida: si no, una prova que posa les claus després d'una que no en tenia
    es trobaria el cau buit i diria que R2 no hi és.
    """
    compte = os.getenv("R2_ACCOUNT_ID")
    clau = os.getenv("R2_ACCESS_KEY_ID")
    secret = os.getenv("R2_SECRET_ACCESS_KEY")
    ara = (compte, clau, secret, os.getenv("R2_BUCKET"))
    if getattr(_r2, "_de", None) == ara:
        return _r2._client
    _r2._de = ara
    _r2._client = None
    if not all(ara):
        return None
    try:
        import boto3
        from botocore.config import Config
    except ImportError:  # el servidor encara no té boto3: que no caigui, que vagi a Cloudinary
        return None
    _r2._client = boto3.client(
        "s3",
        endpoint_url=f"https://{compte}.r2.cloudflarestorage.com",
        aws_access_key_id=clau,
        aws_secret_access_key=secret,
        region_name="auto",
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )
    return _r2._client


def _bust():
    return os.getenv("R2_BUCKET", "")


def _extensio(contingut, mena, extensio=None):
    """Quina extensió ha de portar el fitxer: la que ens diuen, la del camí, o la dels bytes."""
    if extensio:
        return "." + extensio.lstrip(".").lower()
    if isinstance(contingut, (str, os.PathLike)):
        sufix = os.path.splitext(str(contingut))[1]
        if sufix:
            return sufix.lower()
    cap = b""
    if isinstance(contingut, (bytes, bytearray)):
        cap = bytes(contingut[:16])
    elif hasattr(contingut, "read") and hasattr(contingut, "seek"):
        lloc = contingut.tell()
        cap = contingut.read(16)
        contingut.seek(lloc)
    for marca, sufix in SIGNATURES:
        if cap.startswith(marca):
            return sufix
    #: el MP4 i companyia porten `ftyp` al byte 4, no al 0
    if len(cap) >= 12 and cap[4:8] == b"ftyp":
        return ".m4a" if cap[8:11] == b"M4A" else ".mp4"
    return PER_DEFECTE.get(mena, ".bin")


def disponible() -> bool:
    """Que hi hagi un dipòsit configurat. Si no, qui crida desa en local, com sempre."""
    return bool(_r2()) or bool(os.getenv("CLOUDINARY_CLOUD_NAME"))


def a_r2() -> bool:
    """Si el dipòsit d'ara és R2. Només per a qui ho hagi de dir (`/version`, proves)."""
    return bool(_r2())


def clau_de(contingut, carpeta: str, nom: str, mena: str = "auto", extensio=None) -> str:
    """On anirà el fitxer dins del bust. Separat de `puja` per poder-ho provar sense res al mig.

    Les proves d'això no toquen cap variable global del mòdul, i això no és una manicura:
    les pujades de l'aplicació passen en **fils de fons** (el TTS d'una frase acabada de
    crear, per exemple). Una prova que substituís `_r2` per un de fals a tot el mòdul faria
    que una pujada d'una altra prova, caiguda just en aquell moment, se n'anés al dipòsit de
    mentida. Això va fer caure set proves d'altres fitxers l'11-11-2026, i només amb cert
    ordre, que és la pitjor manera de descobrir-ho.
    """
    return f"{carpeta.strip('/')}/{nom}{_extensio(contingut, mena, extensio)}"


def _puja_r2(client, bust: str, clau: str, contingut) -> None:
    """Deixa el fitxer al bust. Rep el client, no el busca: així es pot provar amb un de fals."""
    tipus = mimetypes.guess_type(clau)[0] or "application/octet-stream"
    if isinstance(contingut, (str, os.PathLike)):
        with io.open(contingut, "rb") as f:
            client.put_object(Bucket=bust, Key=clau, Body=f, ContentType=tipus)
    else:
        client.put_object(Bucket=bust, Key=clau, Body=contingut, ContentType=tipus)


def puja(contingut, carpeta: str, nom: str, mena: str = "auto", extensio=None) -> str:
    """Desa un fitxer i torna la seva adreça.

    `contingut` pot ser un camí, els bytes, o un fitxer obert: tant li fa.
    `carpeta` i `nom` són on i com s'ha de dir, sense extensió.
    `mena` és una de MENES.
    `extensio` només cal quan qui crida la sap i el contingut no la delata (el mòbil).

    Amb R2 torna `/mitjans/<carpeta>/<nom><ext>`; amb Cloudinary, l'adreça seva de sempre.
    """
    if mena not in MENES:
        raise ValueError(f"mena desconeguda: {mena!r} (n'hi ha {sorted(MENES)})")

    client = _r2()
    if client:
        clau = clau_de(contingut, carpeta, nom, mena, extensio)
        _puja_r2(client, _bust(), clau, contingut)
        return "/mitjans/" + clau

    resultat = cloudinary.uploader.upload(
        contingut,
        folder=carpeta,
        public_id=nom,
        resource_type=MENES[mena],
    )
    return resultat["secure_url"]


def clau_de_ladreca(adreca: str) -> str:
    """De `/mitjans/tachelhit/video/v.mp4` a `tachelhit/video/v.mp4`."""
    return adreca[len("/mitjans/"):] if adreca.startswith("/mitjans/") else adreca.lstrip("/")


#: `.../upload/[transformacions/]v1793634203/tachelhit/audio/a.aac` -> el que ve despres de la
#: versio. La versio es el numero que Cloudinary hi posa davant i que no forma part del nom.
_CLOUDINARY = re.compile(r"/upload/(?:[^/]+/)*?v\d+/(.+)$")


def clau_de_cloudinary(adreca: str):
    """Quina clau de R2 li toca a una adreca de Cloudinary, o None si no n'es cap.

    La migracio del #577 va pujar els fitxers a R2 **amb la mateixa ruta** que tenien a
    Cloudinary, i aixo es el que permet casar-los sense cap taula pel mig. Viu aqui, i no en un
    guio de tools/, perque aquest modul es l'unic lloc del programa que sap on viuen els fitxers:
    la lliço del novembre de 2026 va ser que aquesta decisio no pot viure duplicada.

    Es el pont entre el que la base de dades diu ENCARA (21.036 adreces de Cloudinary) i el que
    el diposit te de debo. El 5 de desembre de 2026 Cloudinary esborra els fitxers.
    """
    adreca = (adreca or "").split("?", 1)[0]
    if "res.cloudinary.com" not in adreca:
        return None
    m = _CLOUDINARY.search(adreca)
    return m.group(1) if m else None


def _esborra_r2(client, bust: str, clau: str) -> None:
    """Treu el fitxer del bust. Rep el client, com `_puja_r2` i pel mateix motiu."""
    client.delete_object(Bucket=bust, Key=clau)


def adreca_signada(clau: str, segons: int = None) -> str:
    """Una adreça de R2 que dura una estona. La fa servir `/mitjans/...` per desviar-hi."""
    client = _r2()
    if not client:
        raise RuntimeError("R2 no està configurat")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": _bust(), "Key": clau.lstrip("/")},
        ExpiresIn=segons or SEGONS_SIGNADA,
    )


def esborra(identificador: str, mena: str = "video") -> None:
    """Treu un fitxer del dipòsit. `identificador` és el nom intern, no l'adreça."""
    if identificador.startswith("/mitjans/"):
        client = _r2()
        if client:
            _esborra_r2(client, _bust(), clau_de_ladreca(identificador))
        return
    cloudinary.uploader.destroy(identificador, resource_type=MENES.get(mena, mena))
