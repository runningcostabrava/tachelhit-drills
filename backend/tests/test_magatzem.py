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
