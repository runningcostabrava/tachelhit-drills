# -*- coding: utf-8 -*-
"""El filtre dels fets: res que no tingui un token darrere no es desa.

Les dues trampes que el va fer néixer (14-11-2026): una frase pot OMETRE un token (`islman` =
«peix» glossat bé, i la frase parla d'una altra cosa) i pot ESCRIURE UNA RELACIÓ («és diferent
de» amb la glossa dient «lligat»). La interlineal no pot ometre; el marc no pot relacionar.

I els dos forats que l'auditor va demostrar amb codi a la primera versió, que ara tenen prova:
el suport es comprova contra la interlineal (no contra un `soste` només mirat en rang), i la
llargada d'una paraula no l'eximeix de tenir token.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fets  # noqa: E402

TROS = "tagurin islman tga tamaziġt"          # 4 tokens
VERBS = {"tga", "ttinin", "nssn", "sawalḫ", "tgit"}


def es_verb(f):
    return f in VERBS


def resposta(**k):
    base = {
        "interlineal": ["paraules", "peix", "és", "amazic"],
        "tema": "les paraules del peix",
        "cita": None,
        "frase": "Les paraules del peix són amazigues.",
        "soste": {"amazigues": [3]},
    }
    base.update(k)
    return json.dumps(base, ensure_ascii=False)


def test_una_resposta_ben_sostinguda_passa_sencera():
    f, motius = fets.comprova(resposta(), TROS)
    assert f and not motius
    assert f["interlineal"] == ["paraules", "peix", "és", "amazic"]
    assert f["frase"] == "Les paraules del peix són amazigues."
    assert f["marc"]["tema"] == "les paraules del peix"


def test_la_interlineal_ha_de_fer_la_llargada_dels_tokens():
    #: Si pot saltar-se'n un, el filtre no serveix: es rebutja TOT, no es poda.
    f, motius = fets.comprova(resposta(interlineal=["paraules", "peix", "és"]), TROS)
    assert f is None and "interlineal de 3" in motius[0]


def test_una_frase_amb_una_paraula_sense_token_cau():
    #: «poques» no surt de cap casella: és la invenció del #9.
    f, motius = fets.comprova(resposta(frase="Les paraules amazigues són poques.",
                                       soste={"amazigues": [3]}), TROS)
    assert f["frase"] is None
    assert any("poques" in m for m in motius)
    assert f["interlineal"][1] == "peix"      # la interlineal i el tema sobreviuen


def test_el_suport_es_la_interlineal_no_un_soste_apuntat_al_token_zero():
    #: El forat demostrat per l'auditor: apuntant TOT al token 0, la frase falsa del #17
    #: («el meu pare») passava neta. Ara el que compta és què diu la casella.
    f, motius = fets.comprova(resposta(
        interlineal=["?", "?", "?", "?"],
        frase="Per què el meu pare em fa pujar?",
        soste={"pare": [0], "pujar": [0]}), TROS)
    assert f["frase"] is None and any("pare" in m for m in motius)


def test_una_paraula_que_es_un_token_es_sosté_sola():
    #: El #30: la frase citava «imikk», que ÉS un token, i el filtre vell la podava.
    tros = "darayt iffus da ttinin imikk"
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["?", "sud", "partícula", "diuen", "«imikk»"],
        "tema": "?", "cita": "imikk", "frase": "Al sud diuen «imikk».", "soste": {}},
        ensure_ascii=False), tros)
    assert f["frase"] == "Al sud diuen «imikk»."
    assert f["cita"] == "imikk"
    assert not any("imikk" in m for m in motius)


def test_una_paraula_de_tres_lletres_tambe_necessita_token():
    #: «gos», «pou», «nen» passaven per ser curtes. La llargada no eximeix res.
    f, motius = fets.comprova(resposta(frase="El gos va al pou.", soste={}), TROS)
    assert f["frase"] is None and any("gos" in m for m in motius)


def test_el_tema_sense_token_cau_a_interrogant():
    f, motius = fets.comprova(resposta(tema="la lingüística comparada"), TROS)
    assert f["marc"]["tema"] == "?"
    assert any("tema sense token" in m for m in motius)


# ----------------------------------------------- el que no es pregunta: es calcula en codi
def test_la_polaritat_surt_de_les_particules():
    assert fets.polaritat("ur tgi ġar iwaliwn".split()) == "restrictiu"
    assert fets.polaritat("ur illi waman".split()) == "negatiu"
    assert fets.polaritat("illa waman".split()) == "afirmatiu"


def test_la_mena_surt_de_les_particules_i_dels_verbs_de_dir():
    assert fets.mena("is tlla tmaziġt".split()) == "pregunta"
    assert fets.mena("ma igan tutlayt".split()) == "pregunta"
    assert fets.mena("darayt iffus da ttinin imikk".split()) == "citació"
    assert fets.mena("illa waman".split()) == "afirmació"


def test_les_persones_surten_dels_pronoms_i_de_les_formes_de_la_taula():
    #: Només pronoms explícits i formes verbals de la taula a mà. Endevinar per afix va donar
    #: 8 falsos de 18 a la v6 («tu» en un tros sense verb, «nosaltres» per la preposició n).
    assert fets.qui_hi_surt("nkkin sawalḫ".split()) == ["jo"]
    assert fets.qui_hi_surt("da ttinin imaziġn".split()) == ["ells/elles"]
    assert fets.qui_hi_surt("ng tamaziġt".split()) == ["nosaltres"]
    #: cap afix: `nssufuġ` no és a la taula, `imaziġn` acaba en -n, `ntguriwin` comença per n-
    assert fets.qui_hi_surt("nssufuġ imaziġn ntguriwin".split()) == []


def test_es_verb_i_es_particula_sacepten_i_signoren():
    #: els qui criden passen aquests arguments; el camp ja no se'n fia
    assert fets.qui_hi_surt(["iffġ"], lambda f: True) == []
    assert fets.qui_hi_surt(["taguriġ"], lambda f: True, lambda f: False) == []


# ---------------------------------------------------------------------------- la cita
def test_la_cita_nomes_pot_ser_un_candidat_marcat_a_la_interlineal():
    tros = "darayt iffus da ttinin imikk"
    base = {"interlineal": ["?", "sud", "?", "diuen", "«imikk»"], "tema": "?", "frase": None}
    f, _ = fets.comprova(json.dumps(dict(base, cita="imikk")), tros)
    assert f["cita"] == "imikk"
    #: no segueix cap verb de dir
    f, motius = fets.comprova(json.dumps(dict(base, cita="iffus")), tros)
    assert f["cita"] is None and any("verb de dir" in m for m in motius)
    #: candidat però traduït a la casella, no marcat: el model no l'ha donat per anomenat
    f, motius = fets.comprova(json.dumps(dict(base, interlineal=["?", "sud", "?", "diuen", "una mica"],
                                              cita="imikk")), tros)
    assert f["cita"] is None and any("no marcada" in m for m in motius)


def test_una_cita_que_designa_gent_no_es_cap_cita():
    #: El #9: «da ttinin imaziġn» — `imaziġn` és el subjecte de «diuen», no la paraula anomenada.
    tros = "da ttinin imaziġn isrman drusn"
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["?", "diuen", "«imaziġn»", "peixos", "pocs"], "tema": "?",
        "cita": "imaziġn", "frase": None}), tros, es_gent=lambda w: w == "imaziġn")
    assert f["cita"] is None and any("gent" in m for m in motius)


def test_el_json_pot_venir_entre_cometes_de_bloc():
    f, motius = fets.comprova("```json\n" + resposta() + "\n```", TROS)
    assert f and not motius


def test_el_que_no_es_json_es_rebutja_i_es_diu():
    f, motius = fets.comprova("CATALA: Les paraules del peix.\nCERTESA: probable", TROS)
    assert f is None and motius == ["la resposta no és JSON"]


# ------------------------------------------------ els quatre pedaços del judici de la v3
def test_el_suport_compara_per_arrel():
    #: «amaziga» contra la casella «amazic»; «escriptura» contra «escriure»: 4 de les 5 podes
    #: del tema a la v3 eren això.
    f, motius = fets.comprova(resposta(tema="la llengua amaziga",
                                       interlineal=["paraules", "peix", "és", "amazic"],
                                       soste={}), "tagurin islman tga tamaziġt")
    assert f["marc"]["tema"] == "?" and any("llengua" in m for m in motius)   # «llengua» no hi és
    f, motius = fets.comprova(resposta(tema="paraules amazigues", soste={}), TROS)
    assert f["marc"]["tema"] == "paraules amazigues" and not motius


def test_una_casella_amb_el_token_copiat_es_un_interrogant():
    #: El #10 de la v3: cinc caselles de cinc eren el token copiat i comptaven com a plenes.
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["is", "da", "gis", "ittara", "kra"], "tema": "?", "frase": None}),
        "is da gis ittara kra")
    assert f["interlineal"] == ["?"] * 5
    assert any("copiat" in m for m in motius)


def test_les_cometes_nomes_valen_per_a_un_candidat_a_cita():
    #: `tamaziġt` entre cometes quan és l'objecte («fer amazic») i no s'anomena: també «?».
    f, _ = fets.comprova(json.dumps({"interlineal": ["fer", "«tamaziġt»"], "tema": "?",
                                     "frase": None}), "skr tamaziġt")
    assert f["interlineal"][1] == "?"
    #: però «imikk» darrere d'un verb de dir es queda
    f, _ = fets.comprova(json.dumps({"interlineal": ["diuen", "«imikk»"], "tema": "?",
                                     "cita": "imikk", "frase": None}), "ttinin imikk")
    assert f["interlineal"][1] == "«imikk»" and f["cita"] == "imikk"


def test_el_tema_ha_de_ser_un_grup_nominal():
    for tema, tros in (("què entrar a ?", "tema amb un «?»"), ("afegir el nostre", "infinitiu")):
        ok, motiu = fets.tema_es_grup_nominal(tema)
        assert not ok and tros.split()[0] in motiu
    assert fets.tema_es_grup_nominal("la conjugació dels verbs")[0]
    assert fets.tema_es_grup_nominal("el paper del professor")[0]     # -er no és infinitiu aquí


def test_una_frase_que_passa_porta_la_nota_de_procedencia():
    f, _ = fets.comprova(resposta(), TROS)
    assert f["frase_nota"] == "muntada a partir de glosses, no traducció"
    f, _ = fets.comprova(resposta(frase=None), TROS)
    assert "frase_nota" not in f


# ------------------------------------------------------- la còpula, l'única relació possible
def test_una_copula_a_la_frase_val_nomes_si_una_casella_la_porta():
    #: #3 de la v4: «No és només paraules» amb la casella `tgi→no és` → passa
    tros = "ur tgi ġar iwaliwn"
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["no", "no és", "només", "paraules"], "tema": "?",
        "frase": "No és només paraules."}), tros)
    assert f["frase"] == "No és només paraules." and not motius
    #: #19: «és la nostra llengua» sense cap casella de còpula → cau, i es diu
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["?", "llengua", "amaziga", "nostra"], "tema": "?",
        "frase": "És la nostra llengua amaziga."}), "x tutlayt tamaziġt nnġ")
    assert f["frase"] is None and any("còpula" in m for m in motius)


def test_el_forat_dins_la_frase_es_marca_com_a_buit():
    tros = "ur tgi ġar iwaliwn ur tgi ġar tguriwin"
    f, _ = fets.comprova(json.dumps({
        "interlineal": ["no", "no és", "només", "paraules", "no", "?", "només", "?"],
        "tema": "?", "frase": "No és només paraules, no ? només ?"}), tros)
    assert f["frase"] == "No és només paraules, no [?] només [?]"


def test_larrel_casa_singular_i_plural_de_quatre_lletres():
    #: «verbs» contra la casella «verb» (#36 de la v6): tallar sempre a cinc els separava.
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["?", "verb", "amazic"], "tema": "els verbs amazics", "frase": None}),
        "n imyagn tmaziġt")
    assert f["marc"]["tema"] == "els verbs amazics" and not motius
    #: i l'alternança vocàlica NO casa: «surt» contra «sortir» és una pèrdua acceptada
    assert not fets._mateixa_arrel("surt", "sortir")
    assert fets._mateixa_arrel("escriptura", "escriure")


def test_una_casella_entre_cometes_que_no_es_la_cita_es_un_interrogant():
    #: Contra la veritat humana en van sortir quatre («suššn», «maksmman»…) comptades com a
    #: plenes: eren el token copiat amb cometes, no cap glossa.
    f, motius = fets.comprova(json.dumps({
        "interlineal": ["?", "«suššn»", "diuen", "«imikk»"], "tema": "?",
        "cita": "imikk", "frase": None}), "yan suššn ttinin imikk")
    assert f["interlineal"][1] == "?" and f["interlineal"][3] == "«imikk»"
    #: cau per la regla del token copiat (les cometes es treuen en comparar) o per la de les
    #: cometes que no són la cita: el que compta és que no quedi com a casella plena
    assert any(("cometes" in m) or ("copiat" in m) for m in motius)


def test_les_formes_ambigues_no_donen_persona():
    #: `nniġ` és «o» o «vaig dir»; `inna` és «va dir» o «mare»: cap persona.
    assert fets.qui_hi_surt("nniġ inna".split()) == []
