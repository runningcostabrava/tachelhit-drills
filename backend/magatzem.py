"""On viuen els fitxers: l'únic lloc del programa que ho sap.

Fins ara `cloudinary.uploader.upload` es cridava des de **deu llocs** de `main.py`: el TTS,
les imatges, el `upload_media` del mòbil, el treballador de vídeo, el retallador d'àudio...
Deu còpies de la mateixa decisió. Això és exactament el que ens va portar al desastre del
novembre de 2026: quan el compte de Cloudinary es va desactivar per haver passat els
crèdits, no hi havia cap lloc on tocar per moure's a un altre dipòsit — n'hi havia deu.

És la mateixa lliçó del #557, on la graella desava bé la lectura de la màquina i l'editor
del mòbil l'escrivia damunt del text del parlant, perquè la regla vivia duplicada.

Qui hagi de desar un fitxer, que cridi `puja()` i no pensi mai més on va a parar.

Ara mateix per sota hi ha Cloudinary, igual que abans. La mudança a R2 (#577) canvia
aquest fitxer i **només** aquest fitxer.
"""
import os

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


def disponible() -> bool:
    """Que hi hagi un dipòsit configurat. Si no, qui crida desa en local, com sempre."""
    return bool(os.getenv("CLOUDINARY_CLOUD_NAME"))


def puja(contingut, carpeta: str, nom: str, mena: str = "auto") -> str:
    """Desa un fitxer i torna la seva adreça pública.

    `contingut` pot ser un camí, els bytes, o un fitxer obert: tant li fa.
    `carpeta` i `nom` són on i com s'ha de dir, sense extensió.
    `mena` és una de MENES.

    Torna l'adreça tal com la dona el dipòsit. Qui la desi a la base de dades que hi
    passi `normalize_media_url`, com fins ara.
    """
    if mena not in MENES:
        raise ValueError(f"mena desconeguda: {mena!r} (n'hi ha {sorted(MENES)})")
    resultat = cloudinary.uploader.upload(
        contingut,
        folder=carpeta,
        public_id=nom,
        resource_type=MENES[mena],
    )
    return resultat["secure_url"]


def esborra(identificador: str, mena: str = "video") -> None:
    """Treu un fitxer del dipòsit. `identificador` és el nom intern, no l'adreça."""
    cloudinary.uploader.destroy(identificador, resource_type=MENES.get(mena, mena))
