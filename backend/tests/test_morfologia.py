# -*- coding: utf-8 -*-
"""El desfeidor de gramàtica: que trobi el que ha de trobar i que CALLI quan no ho sap.

El perill d'aquest mòdul no és que no trobi res: és que trobi massa. Una regla que accepta
qualsevol cosa dona significats falsos amb cara de bons, i això és pitjor que un buit —el
13-11-2026, sense la reixa de mena, `wid` («els de») es llegia «cadena» i `inllan` (forma del
verb ser) es llegia «henna». La meitat d'aquestes proves vigilen el silenci, no la troballa.

No toquen el lèxic de debò: el diccionari és un diccionari de mentida de deu paraules, així
les proves diuen sempre el mateix i no baixen 50.000 entrades a la CI.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import morfologia  # noqa: E402

#: forma → (significats, mena). Prou per a tots els casos d'aquest fitxer.
DICCIONARI = {
    "asif": (["riu"], "nom"),
    "argaz": (["home"], "nom"),
    "agafa": (["nord"], "nom"),
    "tamaziġt": (["llengua amaziga"], "nom"),
    "taguri": (["paraula"], "nom"),
    "amaziġ": (["amazic"], "nom"),
    "ssn": (["saber"], "verb"),
    "ffġ": (["sortir"], "verb"),
    "anlla": (["henna"], "nom"),
    "id": (["cadena"], "nom"),
}


def _significats(forma):
    return list(DICCIONARI.get(forma, ([], ""))[0])


def _es_verb(forma):
    return DICCIONARI.get(forma, ([], ""))[1] == "verb"


def _es_nom(forma):
    return DICCIONARI.get(forma, ([], ""))[1] == "nom"


def glossa(mot):
    return morfologia.glossa(mot, _significats, _es_verb, _es_nom)


# ----------------------------------------------------------------- el que ha de trobar
def test_la_forma_exacta_va_sense_regla():
    diu, com = glossa("asif")
    assert diu == "riu"
    assert com == "diccionari"


def test_desfa_lannexio_del_masculi():
    #: `wasif` = w + asif; `urgaz` = u + (a)rgaz. Les dues són annexió, no dues paraules.
    assert glossa("wasif")[0].startswith("riu")
    assert glossa("urgaz")[0].startswith("home")
    assert glossa("ugafa")[0].startswith("nord")
    assert glossa("wasif")[1] == "annexió"


def test_desfa_lannexio_del_femeni():
    assert glossa("tmaziġt")[0].startswith("llengua amaziga")


def test_desfa_el_plural():
    assert glossa("imaziġn")[0].startswith("amazic")


def test_el_plural_i_lannexio_es_componen():
    #: tguriwin → (plural) tguri → (annexió) taguri. Cap regla sola no hi arriba.
    diu, com = glossa("tguriwin")
    assert diu.startswith("paraula")
    assert "plural" in com


def test_treu_els_afixos_de_persona():
    assert glossa("nssn")[0].startswith("saber")      # n- : nosaltres
    assert glossa("ttffġn")[0].startswith("sortir")   # tt- habitual, -n: ells


def test_les_particules_no_surten_del_diccionari_sino_de_la_taula():
    #: `lexicon._STOP` esborra `da`, `ur`, `ad`… a posta. Si no fossin aquí, no hi serien.
    assert glossa("da") == ("partícula d'acció habitual", "partícula")
    assert glossa("ur")[0] == "no (negació)"
    assert glossa("nutni")[0] == "ells"


def test_la_preposicio_amb_el_pronom_enganxat():
    diu, com = glossa("dars")
    assert "ell/ella" in diu
    assert com == "preposició amb pronom"


# ----------------------------------------------------------------- el que ha de CALLAR
def test_no_diu_res_del_que_el_diccionari_no_confirma():
    #: la regla pot proposar el que vulgui; si el diccionari no la coneix, no hi ha glossa
    assert glossa("wzzzzz") is None
    assert glossa("tkkkkkt") is None


def test_un_afix_de_verb_no_es_treu_dun_nom():
    #: `anllaġ` no és «jo henno»: `anlla` és un nom, i treure-li la -ġ de primera persona és
    #: una lectura que no es pot fer. Sobre les paraules reals dels catorze vídeos, aquesta
    #: reixa atura 71 formes, entre elles `musaġ` = «tisoreta» i `nislman` = «peix».
    assert glossa("anllaġ") is None


def test_una_regla_no_pot_acabar_en_particula():
    #: `blan` → treure la -n → `bla` («sense») era una glossa que es donava, i és falsa:
    #: una partícula no porta afixos de persona.
    assert glossa("blan") is None


def test_una_arrel_de_dues_lletres_no_val():
    #: `tga` → `g`: qualsevol cosa casaria. MIN_ARREL ho barra.
    assert morfologia.MIN_ARREL >= 3
    for forma, _ in morfologia.candidates("tga"):
        assert len(forma) >= 2


def test_sense_la_reixa_de_mena_es_perd_precisio():
    #: la prova que la reixa serveix: sense `es_verb`/`es_nom`, `anllaġ` agafa «henna»
    fluix = morfologia.glossa("anllaġ", _significats)
    assert fluix is not None and "henna" in fluix[0]
    assert glossa("anllaġ") is None


def test_una_regla_ben_aplicada_pot_caure_en_la_paraula_equivocada():
    #: El límit del mètode, escrit perquè ningú no es pensi que està resolt: `inllan` és una
    #: forma del verb «ser», però el plural de `anlla` («henna») seria exactament això, i
    #: `anlla` és un nom de debò. La regla és correcta i el resultat és fals. L'única
    #: defensa és que la glossa digui que ha calgut una regla.
    diu, com = glossa("inllan")
    assert "henna" in diu
    assert com not in morfologia.SEGURES


def test_les_segures_son_les_que_no_han_calgut_cap_regla():
    assert set(morfologia.SEGURES) == {"diccionari", "partícula", "preposició amb pronom"}
    for mot in ("asif", "da", "dars"):
        assert glossa(mot)[1] in morfologia.SEGURES
    for mot in ("wasif", "imaziġn", "nssn"):
        assert glossa(mot)[1] not in morfologia.SEGURES


# --------------------------------------------- la partícula que l'ASR enganxa al davant
def test_parteix_la_particula_enganxada_al_davant():
    #: Les formes perdudes més freqüents de la llista de Tamazight For All no eren
    #: vocabulari rar: eren paraules sabudes amb una partícula al davant.
    diu, com = glossa("ntmaziġt")                  # n + tmaziġt, «de l'amazic»
    assert "llengua amaziga" in diu and diu.startswith("de")
    assert com == "partícula enganxada"
    assert glossa("swasif")[0].startswith("amb")   # s + wasif, «al riu»
    assert "riu" in glossa("swasif")[0]
    assert "saber" in glossa("danssn")[0]          # da + n-ssn, «(que) sabem»


def test_la_particula_enganxada_mai_no_es_segura():
    #: Jutjant-ne quaranta a mà el 14-11-2026, una de cada tres era falsa. Qui la llegeixi
    #: ho ha de poder saber.
    assert glossa("ntmaziġt")[1] not in morfologia.SEGURES


def test_no_es_parteix_el_que_ja_es_resol_sencer():
    #: `tmaziġt` és annexió de `tamaziġt`, i `nssn` és el verb amb la persona. Si el
    #: partidor hi arribés abans, `tmaziġt` sortiria com `ti`/`t` + una altra cosa.
    assert glossa("tmaziġt")[1] == "annexió"
    assert glossa("nssn")[1] == "verb"


def test_nomes_es_parteix_pel_davant():
    #: Tallar pel darrere és el que feia `musaġ` → «tisoreta» i `igddiġ` → «gos».
    for cap, resta in morfologia._particula_al_davant("swasif"):
        assert "swasif".startswith(cap)
        assert cap in morfologia.PARTICULES


def test_la_resta_mes_llarga_va_primera():
    #: `sudġar` sortia com `sudġ + ar` («conduir un animal») en comptes de `s + udġar`,
    #: «al lloc», perquè es provaven abans les partícules de dues lletres.
    talls = morfologia._particula_al_davant("sudġar")
    assert talls[0] == ("s", "udġar")


def test_no_es_parteix_dues_vegades():
    #: Dos talls seguits deixen una arrel de dues lletres, i amb dues lletres casa tot.
    #: `dnasif` només es resoldria partint `d` i després `n`; ha de callar.
    assert glossa("dnasif") is None


# ------------------------------- el `pos` del diccionari s'equivoca, i l'exemple el delata
def test_lexemple_amb_prefix_de_persona_fa_verb():
    #: `sawal` («parlar») consta al diccionari amb `pos: "n."` i la glossa «Tick», però el
    #: seu propi exemple diu `ar ukan tesawal tin tizi`: `tesawal` porta el prefix `te-` de
    #: persona, i un nom no en porta mai.
    assert morfologia._lexemple_el_conjuga(
        {"tashlhit": "sawal", "pos": "n.", "example": "ar ukan tesawal tin tizi"})
    assert morfologia._lexemple_el_conjuga(
        {"tashlhit": "shuṛṛu", "pos": "n.", "example": "ar ishuṛṛu uɣwyul"})


def test_el_mot_sol_a_lexemple_no_prova_res():
    #: Que el mot surti al seu exemple és normal i no diu de quina mena és.
    assert not morfologia._lexemple_el_conjuga(
        {"tashlhit": "argaz", "pos": "n.", "example": "argaz anna iga ibba"})


def test_no_es_busca_el_mot_a_dins_de_laltre():
    #: Buscant el mot sense vora de paraula, `kra tidrekt` casava amb la partícula `ra` i
    #: sortien 709 falsos positius en comptes de 128 troballes.
    assert not morfologia._lexemple_el_conjuga(
        {"tashlhit": "tidrekt", "pos": "n.", "example": "ur dar-s kra tidrekt!"})


def test_els_caps_massa_curts_o_amb_espai_no_compten():
    #: Amb dues lletres casa qualsevol cosa, i una entrada que és una frase sencera
    #: («igan uhum») no té prefix de persona que valgui.
    assert not morfologia._lexemple_el_conjuga(
        {"tashlhit": "id", "pos": "n.", "example": "tid nnes"})
    assert not morfologia._lexemple_el_conjuga(
        {"tashlhit": "igan uhum", "pos": "adj.", "example": "taɣawsa igan uhum ad iga"})


def test_sense_exemple_no_hi_ha_prova():
    assert not morfologia._lexemple_el_conjuga({"tashlhit": "sawal", "pos": "n."})


# ------------------------------ la taula escrita a mà i l'ortografia que el model escriu
def test_la_taula_casa_amb_lortografia_del_model():
    #: La taula ve del compendi (`acku`) i l'adaptador de l'ASR es va afinar amb `c→š`, o
    #: sigui que escriu `ašku`. És la quarta paraula més freqüent de la llista (52
    #: aparicions) i no hi casava: rebia «Because, because of, Since» del diccionari,
    #: marcat com a lectura SEGURA quan era sort.
    assert morfologia.clau_de_particula("ašku") == "acku"
    assert morfologia.clau_de_particula("maḫ") in ("maḫ", "max")
    assert glossa("ašku")[0].startswith("perquè")


def test_una_paraula_que_no_hi_es_no_sinventa_una_clau():
    assert morfologia.clau_de_particula("tamaziġt") is None
    assert morfologia.clau_de_particula("ššššš") is None


def test_les_paraules_de_funcio_que_el_diccionari_glossava_malament():
    #: `ġir` («només») sortia «Run, Caper, Hurry» i marcat com a SEGUR: la mena d'error
    #: pitjor, confiat i fals.
    for mot, tros in (("ġir", "només"), ("akkw", "tot"), ("mad", "què"),
                      ("man", "quin"), ("waḫḫa", "tot i que")):
        diu, _ = glossa(mot)
        assert tros in diu, (mot, diu)


def test_nnig_diu_les_dues_lectures():
    #: Conjunció «o» i «vaig dir» del verb `ini`: totes dues corrents, i no es pot triar
    #: sense context.
    #: La taula ve escrita a mà, i per tant la FONT és fiable; el que no es pot decidir és
    #: quina de les dues lectures toca. Per això les diu totes dues al text en comptes de
    #: triar-ne una, i qui munti la frase ho veu.
    diu, _ = glossa("nniġ")
    assert "o, o bé" in diu and "vaig dir" in diu
