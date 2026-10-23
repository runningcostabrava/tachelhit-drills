"""El Mètode: el catàleg dels deu capítols, i com s'omplen amb la nostra biblioteca.

El que aquestes proves guarden no és que el curs sigui bo —això ho diu una persona— sinó que no
hi entri res que no hi hagi d'entrar, i que el que un capítol diu que té sigui el que té.
"""
import method
from test_api import client


def test_el_cataleg_nomena_unitats_i_temes_que_existeixen():
    """Un slug mal escrit aquí no peta res: el capítol surt buit, i això es llegeix com «d'això
    encara no en tenim» quan el que passa és que el tema es diu d'una altra manera. Per això el
    catàleg es comprova sol, i per això la comprovació és una prova."""
    assert method.check() == []
    assert len(method.CHAPTERS) == 10
    assert [c["n"] for c in method.CHAPTERS] == list(range(1, 11))
    assert len(set(method.SLUGS)) == 10, "dos capítols amb el mateix nom curt"
    for c in method.CHAPTERS:
        assert c["functions"], f"el capítol {c['n']} no diu què en sabràs fer"
        assert c["title"] and c["about"]


def test_un_capitol_s_omple_amb_la_nostra_biblioteca_i_deixa_fora_el_que_toca():
    """Un capítol no porta ni una frase del manual: porta les NOSTRES que fan el que demana.

    El que queda fora és el que docs/SCOPE.md diu que queda fora: una llengua exclosa. El recull
    de Beni Mellal («private») SÍ que hi entra — l'amo en té permís, i aquella etiqueta protegeix
    la redistribució, no l'ensenyament (decisió de 23-10-2026).

    I l'ordre importa: les frases de la Halima i d'en Driss van davant. Són 69 de 3.390, i sense
    aquesta regla no es veurien mai entre les dues mil del recull.
    """
    hdr = {"X-User-Token": __import__("test_api").register("method_filler")}
    mine = client.post("/drills/", headers=hdr, json={
        "text_catalan": "bon dia", "text_tachelhit": "sbaḥ lxir", "grammar": "formules",
        "grammar_source": "owner", "topics": "salutacions", "topics_source": "owner",
        "author": "Halima",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/bd.mp3"}).json()
    from_deck = client.post("/drills/", headers=hdr, json={
        "text_catalan": "bona tarda", "text_tachelhit": "mslxir", "grammar": "formules",
        "grammar_source": "owner", "tag": "benimellal-anki, private",
        "author": "Anki: Tamazight - Beni Mellal Morocco",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/bt.mp3"}).json()
    foreign = client.post("/drills/", headers=hdr, json={
        "text_catalan": "hola", "text_tachelhit": "dia duit", "grammar": "formules",
        "grammar_source": "owner", "tag": "irish"}).json()

    r = client.get("/method/salutacions").json()
    here = {d["id"] for s in r["sections"] for d in s["sentences"]} | {d["id"] for d in r["also"]}
    assert mine["id"] in here
    assert from_deck["id"] in here, "el recull hi entra: n'hi ha permís"
    assert foreign["id"] not in here, "una llengua exclosa, no"

    # i les nostres veus davant: la de la Halima abans que la del recull
    order = [d["id"] for s in r["sections"] if s["slug"] == "formules" for d in s["sentences"]]
    assert order.index(mine["id"]) < order.index(from_deck["id"]),         "primer qui el projecte coneix"

    assert r["n"] == 2 and r["name"] == "Timinsiwin"
    assert [s["slug"] for s in r["sections"]] == ["formules", "pronoms-personals"]
    assert r["functions"], "ha de dir què en sabràs fer"


def test_el_capitol_diu_sempre_d_on_surt():
    """El Mètode és una adaptació d'un manual publicat (ADR 0004). La citació no és una nota a
    peu de la pàgina de crèdits: viatja amb cada capítol, de manera que no es pot ensenyar un
    capítol sense ensenyar d'on surt.

    I el que es llegeix és «Basat en…» i res més: la targeta d'un capítol diu d'on ve el
    material, no quins permisos tenim. Això és del registre intern, no de la pantalla."""
    r = client.get("/method/la-botiga").json()
    src = r["source"]
    assert "El Mountassir" in src["author"] and src["year"] == 2009
    assert src["based_on"] == "Basat en"
    assert "permís" not in " ".join(str(v) for v in src.values()).lower()
    assert "veus" in src["did_not_take"], "el que no ve del llibre són les veus"

    index = client.get("/method/").json()
    assert len(index["chapters"]) == 10 and index["source"]["author"] == src["author"]


def test_el_que_falta_es_mesura_amb_la_veu_no_amb_el_text():
    """Una secció amb vint frases i cap gravada no ensenya a dir res: ensenya a llegir-les, que
    no és el que fa un mètode. Per això «a punt» es compta amb les que es poden escoltar, i una
    unitat que cap frase de la biblioteca no porta es diu que no és enlloc en comptes de
    comptar com un forat d'aquest capítol."""
    r = client.get("/method/sons").json()
    thin = {t["slug"]: t for t in r["missing"]["thin"]}
    assert "sons-i-escriptura" in thin, "la fonètica no s'etiqueta a cap frase"
    assert thin["sons-i-escriptura"]["nowhere"] is True
    assert r["sections_ready"] <= r["sections_total"]

    assert client.get("/method/no-existeix").status_code == 404
