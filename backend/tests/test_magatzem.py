"""El magatzem: l'únic lloc que sap on viuen els fitxers (#577).

El que es guarda aquí és la raresa de Cloudinary —que tracta el so com si fos vídeo—, i la
gràcia és justament que no surti d'aquell fitxer. Si algun dia es muda a un altre dipòsit,
aquestes proves han de continuar passant sense tocar-les: descriuen què demanem al magatzem,
no com ho fa.
"""
import pytest

import magatzem


def test_el_so_es_desa_com_a_video_perque_aixo_ho_demana_cloudinary(monkeypatch):
    """Qui crida diu «so»; que per sota se'n digui vídeo és cosa del magatzem."""
    vist = {}

    def fals(contingut, folder, public_id, resource_type):
        vist.update(contingut=contingut, folder=folder,
                    public_id=public_id, resource_type=resource_type)
        return {"secure_url": "https://exemple/una.webm"}

    monkeypatch.setattr(magatzem.cloudinary.uploader, "upload", fals)

    url = magatzem.puja(b"uns bytes", "tachelhit/audio", "audio_7_123", "so")

    assert url == "https://exemple/una.webm"
    assert vist["resource_type"] == "video"
    assert vist["folder"] == "tachelhit/audio"
    assert vist["public_id"] == "audio_7_123"


@pytest.mark.parametrize("nostra,seva", [
    ("so", "video"), ("video", "video"), ("imatge", "image"), ("auto", "auto"),
])
def test_cada_mena_va_on_toca(monkeypatch, nostra, seva):
    vist = {}
    monkeypatch.setattr(
        magatzem.cloudinary.uploader, "upload",
        lambda contingut, folder, public_id, resource_type: (
            vist.update(resource_type=resource_type), {"secure_url": "https://exemple/x"})[1])

    magatzem.puja(b"x", "carpeta", "nom", nostra)

    assert vist["resource_type"] == seva


def test_una_mena_inventada_peta_de_seguida_i_no_puja_res(monkeypatch):
    """Val més un error aquí que un fitxer desat on no toca i descobrir-ho mesos després."""
    def no_hi_ha_de_passar(*a, **k):
        raise AssertionError("no s'havia de pujar res")

    monkeypatch.setattr(magatzem.cloudinary.uploader, "upload", no_hi_ha_de_passar)

    with pytest.raises(ValueError, match="mena desconeguda"):
        magatzem.puja(b"x", "carpeta", "nom", "sooo")


def test_esborrar_demana_el_nom_intern_no_ladreca(monkeypatch):
    vist = {}
    monkeypatch.setattr(
        magatzem.cloudinary.uploader, "destroy",
        lambda identificador, resource_type: vist.update(
            id=identificador, resource_type=resource_type))

    magatzem.esborra("tachelhit/video/video_7_123", "video")

    assert vist == {"id": "tachelhit/video/video_7_123", "resource_type": "video"}


def test_sense_diposit_configurat_el_magatzem_ho_diu(monkeypatch):
    """Quan no n'hi ha, qui crida desa en local — i ha de poder saber-ho."""
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    assert magatzem.disponible() is False
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "un-diposit")
    assert magatzem.disponible() is True




# ---------------------------------------------------------------------------
# R2 (#577): el segon dipòsit.
#
# Cap d'aquestes proves no substitueix res del mòdul. No és per elegància: les pujades de
# l'aplicació passen en fils de fons —el TTS d'una frase acabada de crear, per exemple—, i
# una prova que canviés `_r2` a tot el mòdul faria que una pujada d'una altra prova, caiguda
# just en aquell moment, se n'anés al dipòsit de mentida. Això va tombar set proves d'altres
# fitxers l'11-11-2026, i només amb cert ordre.
#
# Per això `clau_de` i `_puja_r2` estan separats de `puja`: es poden provar tal com són, amb
# un client passat per paràmetre.
# ---------------------------------------------------------------------------

class _FalsR2:
    """Un R2 de mentida que apunta què li demanen. No hi ha xarxa enlloc."""

    def __init__(self):
        self.desats = []
        self.esborrats = []

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803 (ho diu així boto3)
        self.desats.append({"bust": Bucket, "clau": Key, "tipus": ContentType,
                            "bytes": Body.read() if hasattr(Body, "read") else Body})

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.esborrats.append((Bucket, Key))


def test_la_clau_del_fitxer_porta_la_carpeta_i_lextensio():
    clau = magatzem.clau_de(b"ID3uns bytes", "tachelhit/audio", "audio_7_123", "so")

    assert clau == "tachelhit/audio/audio_7_123.mp3"


@pytest.mark.parametrize("bytes_, espera", [
    (b"\x89PNG\r\n\x1a\n...", ".png"),
    (b"\xff\xd8\xff\xe0", ".jpg"),
    (b"ID3\x04\x00", ".mp3"),
    (b"OggS\x00\x02", ".ogg"),
    (b"\x1a\x45\xdf\xa3\x01", ".webm"),
    (b"\x00\x00\x00\x20ftypM4A ", ".m4a"),
    (b"\x00\x00\x00\x18ftypmp42", ".mp4"),
])
def test_lextensio_surt_dels_bytes_quan_no_ens_la_diuen(bytes_, espera):
    """Les imatges dibuixades i les gravacions del mòbil arriben sense nom de fitxer."""
    assert magatzem.clau_de(bytes_, "c", "n", "auto") == "c/n" + espera


def test_lextensio_que_ens_diuen_mana_per_damunt_dels_bytes():
    """El mòbil ja l'ha validada; no cal que el magatzem endevini."""
    assert magatzem.clau_de(b"xxxx no es res conegut", "c", "n", "so", "wav") == "c/n.wav"


def test_lextensio_surt_del_cami_quan_ens_donen_un_fitxer():
    assert magatzem.clau_de(r"C:\tmp\una cosa.WAV", "c", "n", "so") == "c/n.wav"


def test_un_contingut_desconegut_cau_a_lextensio_de_la_seva_mena():
    assert magatzem.clau_de(b"xxxx", "c", "n", "video") == "c/n.mp4"


def test_el_tipus_que_arriba_al_diposit_surt_de_lextensio():
    """Amb Cloudinary el so es deia «vídeo». Aquí el navegador rep el tipus de debò."""
    fals = _FalsR2()

    magatzem._puja_r2(fals, "un-bust", "tachelhit/audio/a.mp3", b"ID3x")

    assert fals.desats == [{"bust": "un-bust", "clau": "tachelhit/audio/a.mp3",
                            "tipus": "audio/mpeg", "bytes": b"ID3x"}]


def test_de_ladreca_desada_sen_treu_la_clau_del_bust():
    """El que guardem a la base de dades és `/mitjans/...`; el bust no en sap res d'això."""
    assert magatzem.clau_de_ladreca("/mitjans/tachelhit/video/v_7_1.mp4") ==         "tachelhit/video/v_7_1.mp4"


def test_esborrar_demana_la_clau_al_bust():
    fals = _FalsR2()

    magatzem._esborra_r2(fals, "un-bust", "tachelhit/video/v_7_1.mp4")

    assert fals.esborrats == [("un-bust", "tachelhit/video/v_7_1.mp4")]


def test_sense_claus_no_hi_ha_r2(monkeypatch):
    """Si el servidor encara no les té posades, ha de seguir anant a Cloudinary."""
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.delenv(k, raising=False)

    assert magatzem.a_r2() is False
