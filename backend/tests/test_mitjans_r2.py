"""Servir els mitjans de R2: l'adreça estable i el desviament signat (#577).

El que es prova aquí és la part que no es pot veure mirant `magatzem.py`: que l'adreça que
guardem a la base de dades surti sencera cap al món, i que demanar-la porti al fitxer.

Per què importa que surti sencera: el frontend es serveix d'un altre domini (Vercel) i el
servidor d'un altre (Render). Una adreça relativa, al navegador, es resol contra el domini
del frontend — i allà no hi ha cap fitxer.
"""
import magatzem
import main
from test_api import client


def test_ladreca_desada_surt_sencera_cap_al_mon():
    """A la base de dades hi ha `/mitjans/...`; qui la rep l'ha de poder demanar tal qual."""
    sortida = main.normalize_media_url("/mitjans/tachelhit/audio/a_7_1.mp3")

    assert sortida == main.API_BASE + "/mitjans/tachelhit/audio/a_7_1.mp3"
    assert sortida.startswith("http")


def test_si_ja_venia_sencera_no_es_duplica_el_davant():
    """La mateixa adreça passada dues vegades pel normalitzador ha de sortir igual."""
    un_cop = main.normalize_media_url("/mitjans/tachelhit/audio/a.mp3")
    dos_cops = main.normalize_media_url(un_cop)

    assert dos_cops == un_cop


def test_les_de_cloudinary_segueixen_intactes():
    """Mentre no es reescriguin, la majoria d'adreces encara són d'allà."""
    vella = "https://res.cloudinary.com/du26ppvh0/video/upload/v1/tachelhit/audio/a.mp3"

    assert main.normalize_media_url(vella) == vella


def test_demanar_un_mitja_porta_al_fitxer_signat(monkeypatch):
    monkeypatch.setattr(magatzem, "a_r2", lambda: True)
    monkeypatch.setattr(magatzem, "adreca_signada",
                        lambda clau, segons=None: f"https://r2.exemple/{clau}?signat")

    r = client.get("/mitjans/tachelhit/audio/a_7_1.mp3", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "https://r2.exemple/tachelhit/audio/a_7_1.mp3?signat"


def test_el_desviament_no_es_permanent(monkeypatch):
    """L'adreça de darrere caduca: si el navegador es guardés el desviament, demà no aniria."""
    monkeypatch.setattr(magatzem, "a_r2", lambda: True)
    monkeypatch.setattr(magatzem, "adreca_signada", lambda clau, segons=None: "https://x/y")

    r = client.get("/mitjans/a.mp3", follow_redirects=False)

    assert r.status_code == 307  # i no 301, que el navegador es queda per sempre


def test_sense_r2_configurat_contesta_que_no_hi_es(monkeypatch):
    monkeypatch.setattr(magatzem, "a_r2", lambda: False)

    assert client.get("/mitjans/a.mp3", follow_redirects=False).status_code == 404


def test_no_es_pot_sortir_de_la_carpeta(monkeypatch):
    """`..` dins d'una clau no ha d'arribar mai a signar-se.

    Es crida la funció directament i no pas per l'adreça: el client HTTP escurça el `..` pel
    camí i no arribaria mai al servidor, o sigui que per allà la prova no provaria res.
    """
    import pytest
    from fastapi import HTTPException

    monkeypatch.setattr(magatzem, "a_r2", lambda: True)
    monkeypatch.setattr(magatzem, "adreca_signada",
                        lambda *a, **k: pytest.fail("no s'havia de signar res"))

    with pytest.raises(HTTPException) as e:
        main.serveix_mitja("tachelhit/../secret.mp3")

    assert e.value.status_code == 400


def test_si_el_diposit_no_respon_no_es_queda_penjat(monkeypatch):
    monkeypatch.setattr(magatzem, "a_r2", lambda: True)

    def peta(clau, segons=None):
        raise RuntimeError("el bust no hi és")

    monkeypatch.setattr(magatzem, "adreca_signada", peta)

    assert client.get("/mitjans/a.mp3", follow_redirects=False).status_code == 502
