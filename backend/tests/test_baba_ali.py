"""El visor del Baba Ali: la sèrie del canal amb el nostre text a sota.

El que es prova aquí és el que es pot equivocar sense que es vegi: l'ordre de les línies, les
duplicades de la biblioteca, el desplaçament del vídeo i —sobretot— que les esmenes del text
es facin en servir i NO a la biblioteca (ADR 0003).
"""
import json

import baba_ali
import main
from models import Drill
from test_api import client


def _linia(ep, marca, ca, ar, so="https://res.cloudinary.com/x/a.mp3", am=None, lectures=None):
    db = main.SessionLocal()
    try:
        d = Drill(tag="baba-ali, forja, font externa",
                  source_playlist=f"Baba Ali · {ep}",
                  source_title=f"Baba Ali · {ep} · {marca}",
                  text_catalan=ca, text_arabic=ar, audio_url=so,
                  text_tachelhit_suggested=am,
                  esborranys=json.dumps(lectures, ensure_ascii=False) if lectures else None,
                  region="Souss (sèrie Baba Ali, SNRT)")
        db.add(d)
        db.commit()
        return d.id
    finally:
        db.close()


def _esborra(*ids):
    db = main.SessionLocal()
    try:
        db.query(Drill).filter(Drill.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_la_llista_diu_els_episodis_i_de_quins_sabem_el_video():
    a = _linia("episodi 5", "2:03", "Bon dia", "صباح الخير")
    b = _linia("episodi 99", "1:00", "Una prova", "اختبار")
    try:
        r = client.get("/baba-ali/")
        assert r.status_code == 200, r.text
        v = r.json()
        per_nom = {e["episodi"]: e for e in v["episodis"]}
        assert per_nom["episodi-5"]["linies"] == 1
        assert per_nom["episodi-5"]["video"], "l'episodi 5 té el vídeo mesurat"
        assert per_nom["episodi-99"]["video"] is None, "un episodi inventat no té vídeo"
        assert v["font"]["obra"].startswith("Baba Ali")
        #: l'ordre és per número, que «episodi-10» no vagi davant de «episodi-5»
        noms = [e["episodi"] for e in v["episodis"]]
        assert noms.index("episodi-5") < noms.index("episodi-99")
    finally:
        _esborra(a, b)


def test_les_linies_van_en_ordre_i_no_s_encavalquen():
    ids = [_linia("episodi 77", m, c, "نص") for m, c in
           [("0:30", "tercera"), ("0:10", "primera"), ("0:12", "segona")]]
    try:
        v = client.get("/baba-ali/episodi-77").json()
        assert [l["ca"] for l in v["linies"]] == ["primera", "segona", "tercera"]
        assert v["linies"][0]["fi"] <= v["linies"][1]["t"], "una línia s'acaba quan comença la següent"
        assert v["linies"][1]["fi"] - v["linies"][1]["t"] <= 6.0, "cap línia s'aguanta més de sis segons"
        assert v["linies"][0]["fi"] > v["linies"][0]["t"], "i cap no dura zero"
    finally:
        _esborra(*ids)


def test_una_linia_duplicada_de_la_biblioteca_surt_un_sol_cop():
    """Onze frases del Baba Ali són a la biblioteca dues vegades, amb el mateix segon i el
    mateix text. Al visor hi han de sortir una sola vegada, i la pàgina ho diu."""
    a = _linia("episodi 78", "3:00", "la mateixa", "نفس النص")
    b = _linia("episodi 78", "3:00", "la mateixa", "نفس النص")
    c = _linia("episodi 78", "3:00", "una altra cosa", "شيء آخر")
    try:
        v = client.get("/baba-ali/episodi-78").json()
        assert len(v["linies"]) == 2, "la repetida s'ha tret, la del mateix segon amb un altre text no"
        assert v["duplicades_tretes"] == 1
    finally:
        _esborra(a, b, c)


def test_el_nom_del_mercader_s_esmena_en_servir_i_la_biblioteca_no_es_toca():
    """L'OCR va llegir «بلقاسم» les 42 vegades que surt; la pantalla escriu «أبي القاسم».

    Es mostra bé, i a la biblioteca el text queda tal com el va deixar la màquina: ADR 0003,
    el text no és nostre per esmenar-lo d'ofici."""
    a = _linia("episodi 79", "5:00",
               "Belkacem el mercader és a la plaça", "التاجر بلقاسم في الساحة")
    try:
        v = client.get("/baba-ali/episodi-79").json()
        l = v["linies"][0]
        assert "أبي القاسم" in l["ar"] and "بلقاسم" not in l["ar"]
        assert "Abu-l-Qàssim" in l["ca"] and "Belkacem" not in l["ca"]
        assert l["esmenat"] is True
        assert v["esmenades"] == 1

        db = main.SessionLocal()
        try:
            desat = db.query(Drill).filter(Drill.id == a).first()
            assert desat.text_arabic == "التاجر بلقاسم في الساحة", "la biblioteca no s'ha tocat"
            assert desat.text_catalan == "Belkacem el mercader és a la plaça"
        finally:
            db.close()
    finally:
        _esborra(a)


def test_la_formula_islamica_no_es_torna_una_advocacio_mariana():
    """La màquina convertia «ما شاء الله» en «Mare de Déu»: una advocacio mariana dins d'una
    sèrie marroquina. La regla mira l'àrab i esmena el començament del català."""
    a = _linia("episodi 80", "6:00", "Mare de Déu, que n'és de maca!", "ما شاء الله ما أجملها")
    b = _linia("episodi 80", "6:30", "Mare meva, quin ensurt!", "يا لطيف")
    try:
        linies = client.get("/baba-ali/episodi-80").json()["linies"]
        assert linies[0]["ca"].startswith("Maixal·lah")
        assert linies[1]["ca"].startswith("Valga'm Déu")
    finally:
        _esborra(a, b)


def test_el_que_no_es_religios_es_queda_com_estava():
    """«يا للهول» vol dir «quin horror» i no invoca ningú: allà «Mare meva» hi escau."""
    a = _linia("episodi 81", "7:00", "Mare meva, quina desgràcia!", "يا للهول")
    try:
        l = client.get("/baba-ali/episodi-81").json()["linies"][0]
        assert l["ca"] == "Mare meva, quina desgràcia!"
        assert l["esmenat"] is False
    finally:
        _esborra(a)


def test_un_episodi_que_no_tenim_ho_diu_amb_un_404():
    r = client.get("/baba-ali/episodi-inventat")
    assert r.status_code == 404
    assert "línia" in r.json()["detail"]


def test_una_linia_sense_marca_de_temps_no_entra_al_visor():
    """Sense segon no es pot posar a sota del vídeo; però la frase segueix a la biblioteca."""
    a = _linia("episodi 82", "8:00", "amb marca", "نص")
    db = main.SessionLocal()
    try:
        d = Drill(tag="baba-ali", source_playlist="Baba Ali · episodi 82",
                  source_title="Baba Ali · episodi 82", text_catalan="sense marca",
                  text_arabic="نص")
        db.add(d)
        db.commit()
        b = d.id
    finally:
        db.close()
    try:
        v = client.get("/baba-ali/episodi-82").json()
        assert [l["ca"] for l in v["linies"]] == ["amb marca"]
        #: a la llista hi compta igualment: és una frase de l'episodi
        llista = {e["episodi"]: e for e in client.get("/baba-ali/").json()["episodis"]}
        assert llista["episodi-82"]["linies"] == 2
    finally:
        _esborra(a, b)


def test_el_desplacament_del_video_ve_de_la_taula_mesurada():
    """El segon del vídeo és `t + desplacament`, i el desplaçament surt de la mesura."""
    taula = baba_ali.pujades()
    assert taula, "la taula de pujades s'ha de poder llegir"
    a = _linia("episodi 5", "2:03", "Bon dia", "صباح الخير")
    try:
        v = client.get("/baba-ali/episodi-5").json()
        assert v["video"] == taula["episodi-5"]["video"]
        assert v["desplacament"] == taula["episodi-5"]["desplacament"]
    finally:
        _esborra(a)


def test_cada_pujada_de_la_taula_porta_les_seves_proves():
    """Un vídeo sense proves no hi pot ser: el visor diu a qui mira per què creu que és aquell.

    N'hi ha de dues menes. La del SO és la de sempre. La de la IMATGE és per a les dues pujades
    que YouTube serveix mudes: allà es compta quantes de les nostres marques cauen on canvia el
    subtítol de la pantalla, i s'exigeix que el desplaçament bo en casi clarament més que el
    millor de tots els altres possibles, i que algú hagi llegit la pantalla per comprovar-ho."""
    for ep, p in baba_ali.pujades().items():
        assert p.get("video"), f"{ep} és a la taula sense vídeo"
        assert isinstance(p.get("desplacament"), (int, float)), ep
        proves = p.get("proves") or {}
        assert proves.get("com") in ("so", "imatge"), f"{ep}: les proves no diuen de quina mena són"
        assert proves["dispersio"] <= 1.0, f"{ep}: les proves no diuen el mateix segon"
        if proves["com"] == "so":
            assert proves.get("talls_dacord", 0) >= 3, \
                f"{ep}: amb menys de tres talls no es diu que casi"
            assert proves.get("falsos_esperats", 1) < 1e-3, f"{ep}: massa probable per atzar"
        else:
            assert proves["sigmes"] >= 5, \
                f"{ep}: el desplaçament no destaca prou de tots els altres possibles"
            assert proves["marques_amb_canvi"] >= 1.4 * proves["millor_dels_altres_desplacaments"], \
                f"{ep}: un altre desplaçament hi casa gairebé igual"
            assert proves["frases_comprovades_a_la_pantalla"] >= 3, \
                f"{ep}: no s'ha llegit prou pantalla per dir que és aquell vídeo"
            assert proves["exemple"], f"{ep}: la prova de la pantalla no es pot repetir"


def test_els_dos_episodis_muts_tenen_video_i_diuen_com_s_ha_sabut():
    """El 7 i el 9 van estar sense vídeo mentre la prova era el so; ara la prova és la imatge."""
    for ep in ("episodi-7", "episodi-9"):
        p = baba_ali.pujades().get(ep)
        assert p and p["video"], f"{ep} hauria de tenir vídeo"
        assert p["proves"]["com"] == "imatge", f"{ep}: s'ha casat per la imatge, no pel so"
        assert ep not in baba_ali.sense_video(), f"{ep} ja no és dels que no tenen vídeo"
    assert "com_els_muts" in baba_ali.com_s_ha_mesurat(), \
        "la mesura ha d'explicar també com es casen les pujades mudes"


def test_el_que_la_maquina_hi_sent_va_a_part_i_no_es_fa_passar_per_text_nostre():
    """La lectura de l'ASR surt al visor, però com a lectura de màquina (#535).

    El camp del parlant (`text_tachelhit`) segueix buit: ningú no ha dit que allò sigui el que
    es diu. Això és ADR 0003 vist des del visor."""
    a = _linia("episodi 83", "1:00", "Bon dia", "صباح الخير",
               am="sbaḥlxir", lectures=[{"text": "sbaḥlxir", "model": "MMS afinat (shi)"}])
    try:
        v = client.get("/baba-ali/episodi-83").json()
        l = v["linies"][0]
        assert l["am"] == "sbaḥlxir"
        assert l["am_models"] == 1
        assert l["am_acord"] is False, "una sola lectura no és cap acord"
        assert v["amb_veu_sentida"] == 1 and v["acords"] == 0

        db = main.SessionLocal()
        try:
            desat = db.query(Drill).filter(Drill.id == a).first()
            assert not desat.text_tachelhit, "el camp del parlant no s'ha omplert amb la màquina"
        finally:
            db.close()
    finally:
        _esborra(a)


def test_dos_models_que_senten_el_mateix_van_marcats_i_els_espais_no_compten():
    """L'acord és l'únic senyal que tenim: 50 línies de 2.727.

    Els models tallen els mots on volen, i «ur ɣid illi» i «urɣidilli» són la mateixa lectura.
    El que NO es plega és cap lletra: ɣ, ɛ, ḥ i les emfàtiques distingeixen paraules, i plegar-les
    faria passar per acord el que no ho és."""
    a = _linia("episodi 84", "1:00", "No hi és", "ليس هنا", am="ur ɣid illi",
               lectures=[{"text": "ur ɣid illi", "model": "MMS afinat (shi)"},
                         {"text": "urɣidilli", "model": "MMS adaptador ric (shi_ric)"}])
    b = _linia("episodi 84", "2:00", "És aquí", "هو هنا", am="iga ɣid",
               lectures=[{"text": "iga ɣid", "model": "MMS afinat (shi)"},
                         {"text": "iga gid", "model": "MMS adaptador ric (shi_ric)"}])
    try:
        v = client.get("/baba-ali/episodi-84").json()
        dacord, no = v["linies"][0], v["linies"][1]
        assert dacord["am_acord"] is True, "els espais no fan dues lectures diferents"
        assert no["am_acord"] is False, "ɣ i g no són la mateixa lletra"
        assert v["acords"] == 1 and v["amb_veu_sentida"] == 2
    finally:
        _esborra(a, b)


def test_una_linia_sense_lectura_de_maquina_no_s_inventa_res():
    a = _linia("episodi 85", "1:00", "Res", "لا شيء")
    try:
        l = client.get("/baba-ali/episodi-85").json()["linies"][0]
        assert l["am"] is None and l["am_models"] == 0 and l["am_acord"] is False
    finally:
        _esborra(a)


def test_les_lectures_mal_desades_no_tomben_el_visor():
    """`esborranys` és text lliure: si un dia hi ha un JSON trencat, el visor ha de servir igual."""
    assert baba_ali.lectures(None) == []
    assert baba_ali.lectures("no soc json") == []
    assert baba_ali.lectures('{"text": "a"}') == [], "un objecte sol no és una llista de lectures"
    assert baba_ali.lectures('[{"model": "x"}]') == [], "sense text no és una lectura"
    #: dos cops el mateix model no és acord: és la mateixa veu dues vegades
    dues = baba_ali.lectures('[{"text": "a", "model": "m"}, {"text": "a", "model": "m"}]')
    assert len(dues) == 1 and baba_ali.hi_ha_acord(dues) is False
    assert baba_ali.hi_ha_acord(baba_ali.lectures('[{"text": "  ", "model": "m"}]')) is False


def test_l_esmena_no_toca_el_que_no_hi_surt():
    ca, ar, tocada = baba_ali.esmena("Res a veure", "لا شيء")
    assert (ca, ar, tocada) == ("Res a veure", "لا شيء", False)


# ---------------------------------------------------------------------------------------------
# «La veu diu el mateix que el subtítol» (#535).
#
# El subtítol és àrab llegit de la IMATGE; la lectura és taixelhit tret del SO. Quan les dues
# coincideixen, la línia té una confirmació que no surt de nosaltres. Aquestes proves guarden
# les fronteres de la comparació, que és on es pot espatllar sense que es noti.

def _lexic_de_mentida(monkeypatch, paraules):
    """Un diccionari petit i nostre, per provar LA REGLA i no el diccionari.

    Les proves d'això no poden fer servir el lèxic de debò, per dues raons que vam trobar el
    13-11-2026 executant la passada sencera: el carrega una altra prova i el deixa tocat (soles
    passaven, totes juntes fallaven), i sobretot **el baixa d'Internet** — 50.000 entrades que
    la CI no ha de demanar a ningú per comprovar una regla de dues línies.
    """
    import lexicon
    monkeypatch.setattr(lexicon, "status", lambda: {"loaded": True})
    monkeypatch.setattr(lexicon, "lookup",
                        lambda mot, max_words=1: (
                            [{"ircam": [{"arabic": paraules[mot]}]}] if mot in paraules else []))
    baba_ali._CAU_GLOSES.clear()


def test_troba_la_paraula_que_les_dues_vies_comparteixen(monkeypatch):
    """`tafukt` vol dir `شمس`; si el subtítol parla del sol, les dues vies diuen el mateix."""
    _lexic_de_mentida(monkeypatch, {"tafukt": "شمس"})
    assert baba_ali.acord_de_significat("tella tafukt", "تحرق الشمس اليوم") == "شمس"


def test_amb_un_subtitol_que_parla_d_una_altra_cosa_no_hi_ha_acord(monkeypatch):
    """La prova que fa que la marca vulgui dir alguna cosa: si casés sempre, no diria res."""
    _lexic_de_mentida(monkeypatch, {"tafukt": "شمس"})
    assert baba_ali.acord_de_significat("tella tafukt", "أين ذهب هذا الولد ؟") is None


def test_sense_lexic_no_diu_res(monkeypatch):
    """Si el diccionari no està carregat, això calla. És un extra, i no ha de fer caure una
    pantalla ni esperar-se que es baixin 50.000 entrades.

    Es comprova que amb el diccionari SÍ que hi hauria acord, perquè si no la prova passaria
    igual amb la comprovació treta i no diria el que vol dir."""
    import lexicon
    _lexic_de_mentida(monkeypatch, {"tafukt": "شمس"})
    assert baba_ali.acord_de_significat("tafukt", "تحرق الشمس اليوم") == "شمس"

    monkeypatch.setattr(lexicon, "status", lambda: {"loaded": False})
    baba_ali._CAU_GLOSES.clear()
    assert baba_ali.acord_de_significat("tafukt", "تحرق الشمس اليوم") is None


def test_les_paraules_de_tot_arreu_no_compten():
    """«aquest», «el que», «era» surten a totes les frases: si comptessin, tot casaria amb tot
    i la marca no voldria dir res."""
    for corrent in ("هذا", "الذي", "كان", "ما"):
        assert corrent not in baba_ali.paraules_ar(f"{corrent} البيت"), corrent
    assert "بيت" in baba_ali.paraules_ar("في البيت")
    assert "البيت" not in baba_ali.paraules_ar("في البيت")   # se'n treu l'article


def test_l_article_i_les_vocals_no_fan_dues_paraules():
    """`الشمس` i `شمس` són la mateixa paraula. Si es comparessin tal qual, la meitat dels acords
    de debò es perdrien."""
    assert baba_ali.paraules_ar("الشَّمس") == baba_ali.paraules_ar("شمس")


def test_sense_subtitol_o_sense_lectura_no_hi_ha_acord():
    for lec, sub in [("", "الشمس"), ("tafukt", ""), (None, None), ("tafukt", "   ")]:
        assert baba_ali.acord_de_significat(lec, sub) is None
