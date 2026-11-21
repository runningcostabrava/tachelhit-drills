# -*- coding: utf-8 -*-
"""El visor del SNRT no serveix tarifit: és una altra llengua.

No s'esborra res de la base de dades — amagar dades esborrant-les és pitjor que no servir-les.
El que es comprova aquí és que no surtin i que no es puguin demanar pel nom.
"""
import json
import os

import pytest
from fastapi.testclient import TestClient

import main as m


@pytest.fixture()
def client():
    return TestClient(m.app)


def _fora():
    m.snrt_fora.cache_clear()
    return m.snrt_fora()


def test_la_llista_te_els_onze_slugs_sencers():
    fora = _fora()
    assert len(fora) == 11, f"n'hi hauria d'haver 11 i n'hi ha {len(fora)}"
    #: els slugs de forja.ma fan 40 caràcters; un de retallat no casaria amb res i el filtre
    #: no faria res sense dir-ho
    assert all(len(s) == 40 for s in fora), sorted(s for s in fora if len(s) != 40)


def test_el_fitxer_diu_la_varietat_i_d_on_surt():
    cami = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(m.__file__))),
                        "backend", "data", "varietats_snrt.json")
    if not os.path.exists(cami):
        cami = os.path.join(os.path.dirname(os.path.abspath(m.__file__)), "data",
                            "varietats_snrt.json")
    d = json.load(open(cami, encoding="utf-8"))
    assert d["d_on_surt"], "ha de dir d'on surt la classificació"
    assert set(d["no_es_serveixen"]) == set(d["varietat"])
    assert set(d["varietat"].values()) == {"tarifit"}


def test_un_episodi_tarifit_no_es_llista_ni_es_pot_demanar(client, monkeypatch):
    """Amb un slug de la llista, els tres camins han de dir que no hi és."""
    slug = sorted(_fora())[0]
    r = client.get("/snrt-privat/")
    assert r.status_code == 200
    assert slug not in [e["slug"] for e in r.json()["episodis"]]
    assert client.get(f"/snrt-privat/{slug}").status_code == 404
    #: el vídeo demana sessió d'administrador; el que importa és que no doni mai 200
    assert client.get(f"/snrt-privat/{slug}/video").status_code != 200


def test_un_slug_que_no_hi_es_segueix_passant(client):
    """El filtre no pot amagar res més: un episodi qualsevol no hi ha de ser afectat."""
    assert "aquest-no-hi-es" not in _fora()
    assert client.get("/snrt-privat/aquest-no-hi-es").status_code == 404


def test_sense_el_fitxer_no_peta_i_no_amaga_res(monkeypatch, tmp_path):
    """Si el fitxer desapareix, el visor ha de seguir servint, no quedar-se buit."""
    m.snrt_fora.cache_clear()
    monkeypatch.setattr(m.os.path, "dirname", lambda *a, **k: str(tmp_path))
    try:
        assert m.snrt_fora() == set()
    finally:
        monkeypatch.undo()
        m.snrt_fora.cache_clear()
