"""L'abecedari: cada lletra, com sona, i on es pot sentir (#368).

El que es prova aquí és el que fa que l'instrument valgui: que una paraula es casi amb la lletra
pels seus SONS i no per les lletres escrites (si no, «gh», «c» i «3» farien desaparèixer mitja
biblioteca), que una lletra que no sona ho digui en comptes d'amagar-se, i que les parelles que
es distingeixen per una sola lletra surtin de la biblioteca i no de la nostra imaginació.
"""
import main  # noqa: F401
from test_api import client, register


def _mot(hdr, text, meaning, at):
    """Una paraula gravada: un drill amb veu, i la fila que diu on sona dins la gravació."""
    d = client.post("/drills/", headers=hdr, json={
        "text_catalan": meaning, "text_tachelhit": text, "author": "Halima",
        "region": "Aït Mraw (Azilal)",
        "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/alfabet-{at}.mp3",
    }).json()
    from main import SessionLocal
    from models import WordAudio
    import word_audio
    with SessionLocal() as db:
        db.add(WordAudio(key=word_audio.key_of(text), word=text, drill_id=d["id"],
                         start_ms=0, end_ms=800, speaker="Halima", source="library"))
        db.commit()
    return d


def _refresca():
    """L'índex es guarda una estona; una prova que acaba d'escriure vol el d'ara."""
    import alfabet
    from main import SessionLocal
    with SessionLocal() as db:
        alfabet._mots(db, refresca=True)


def test_una_paraula_es_casa_amb_la_lletra_pel_so_i_no_per_la_grafia():
    """«agh» i «aɣ» són la mateixa paraula escrita per dues mans (#364). Si l'abecedari comparés
    lletres, la ⵖ no sonaria enlloc tot i tenir gravacions."""
    hdr = {"X-User-Token": register("alfabet_sons")}
    _mot(hdr, "aghrum", "pa", 1)          # escrit amb «gh»
    _mot(hdr, "3afak", "si us plau", 2)   # escrit amb «3», que és la ⵄ
    _refresca()

    r = client.get("/alfabet/ⵖ").json()
    assert r["lat"] == "ɣ" and r["sona"] is True
    assert any(e["word"] == "aghrum" for e in r["exemples"]), r["exemples"]

    # i s'hi arriba igual pel llatí i per com l'escriu la gent
    assert client.get("/alfabet/ɣ").json()["tif"] == "ⵖ"
    assert client.get("/alfabet/gh").json()["tif"] == "ⵖ"

    ayn = client.get("/alfabet/ⵄ").json()
    assert ayn["sona"] is True and any(e["word"] == "3afak" for e in ayn["exemples"])

    assert client.get("/alfabet/ⵠ").status_code == 404, "una lletra que no és de l'abecedari ho diu"


def test_labecedari_diu_quines_lletres_no_sonen_en_comptes_damagar_les():
    """De les paraules soles gravades, cap no porta ḍ, ḥ, ɛ, ṛ, ɣ, ṣ, ṭ ni ẓ (#302). Una lletra
    muda amagada és una feina que ningú no sap que falta; una lletra muda que ho diu és una
    petició concreta: «ens falta algú que digui una paraula amb ṣ»."""
    _refresca()
    r = client.get("/alfabet").json()

    assert r["total"] == len(r["lletres"]) == 33, "les 33 lletres del neotifinag"
    assert [l["tif"] for l in r["lletres"]][:3] == ["ⴰ", "ⴱ", "ⴳ"], "en l'ordre de l'IRCAM"
    assert all(l["com"] for l in r["lletres"]), "cada lletra diu com sona"
    assert "ⵯ" in r["que_es"]["cos"][3], "i es diu què és aquesta escriptura abans de les lletres"

    mudes = set(r["mudes"])
    assert mudes, "amb la biblioteca de la prova n'hi ha, i es diuen"
    assert all(not l["sona"] and not l["exemples"] for l in r["lletres"] if l["lat"] in mudes)
    assert all(l["sona"] for l in r["lletres"] if l["lat"] not in mudes)
    assert r["amb_so"] + len(mudes) == r["total"]


def test_les_parelles_surten_de_la_biblioteca_i_no_de_la_imaginacio():
    """Una parella de paraules gairebé idèntiques és el que ensenya a sentir la diferència entre
    dos sons que s'assemblen. Inventada, ensenyaria a sentir una diferència entre dues paraules
    que ningú no ha dit mai."""
    hdr = {"X-User-Token": register("alfabet_parelles")}
    _mot(hdr, "tamurt", "el país", 11)
    _mot(hdr, "ṭamurt", "el país (emfàtica, de prova)", 12)
    _refresca()

    grups = {g["so_a"] + g["so_b"]: g for g in client.get("/alfabet/parelles").json()["parelles"]}
    tt = grups["tṭ"]
    assert tt["tif_a"] == "ⵜ" and tt["tif_b"] == "ⵟ"
    trobada = next((p for p in tt["parelles"]
                    if {p["a"]["word"], p["b"]["word"]} == {"tamurt", "ṭamurt"}), None)
    assert trobada, tt["parelles"]
    assert trobada["a"]["word"] == "tamurt", "la del primer so va primer"
    assert trobada["posicio"] == 0, "i es diu en quina posició es diferencien"
    assert trobada["a"]["audio_url"] and trobada["b"]["audio_url"], "totes dues se senten"
