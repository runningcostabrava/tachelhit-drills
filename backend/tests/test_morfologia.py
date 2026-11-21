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
    assert set(morfologia.SEGURES) == {"diccionari", "partícula", "forma gramatical",
                                      "preposició amb pronom", "lèxic validat"}
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
    #: i la tercera, la preposició `nnig` «damunt»: els subtítols humans del conte del vaixell
    #: escriuen «inin nnig turft» (dalt del vaixell), i 20 de les 21 `nniġ` de la llista van
    #: seguides d'un nom, no d'un pronom
    assert "damunt" in diu


def test_el_verb_anar_en_perfectiu_surt_de_la_taula():
    #: Validació del 15-11-2026: sense `ddu` en perfectiu a cap taula, el diccionari glossava
    #: `tddit` «sangonera» (tiddit) 16 vegades, `idda` «aquí» i `ddiġ` «encara». Les 16
    #: `tddit` anaven darrere de «mani s» («on»): és «vas».
    for forma, tros in (("tddit", "vas"), ("idda", "va anar"), ("ndda", "vam anar"),
                        ("ddan", "van anar")):
        diu, com = glossa(forma)
        assert tros in diu, (forma, diu)
        assert com.startswith("forma gramatical"), (forma, com)
    diu, _ = glossa("ddiġ")
    assert "vaig anar" in diu and "encara" in diu


def test_el_lexic_validat_pels_subtitols_guanya_al_diccionari_sense_alternativa():
    #: H9 (15-11-2026): als rètols humans dels 58 vídeos, `immut` coapareix amb «dead» (Dice
    #: 0,67, 7 rètols) i el diccionari deia «urge»; `irgzn` amb «men» (0,68, 22) i no hi era;
    #: `isġi` és l'heroi dels contes i el diccionari el traduïa («vautour»). El diccionari ha
    #: perdut: no se'l torna a oferir amb «o bé».
    for forma, tros in (("immut", "va morir"), ("irgzn", "homes"), ("wawal", "paraula"),
                        ("nnif", "més enllà"), ("isġi", "nom propi"),
                        #: doble evidència, anglès i àrab: «lord» i «الله», «أنتم» 0,86
                        ("rbbi", "Déu"), ("knnumi", "vosaltres"), ("umsfri", "intèrpret")):
        diu, com = glossa(forma)
        assert tros in diu and " — o bé: " not in diu, (forma, diu)
        assert com == "lèxic validat" and com in morfologia.SEGURES, (forma, com)
    #: `didak` = did + ak («amb tu»): als rètols àrabs, «al teu costat» (صفك, جانبك)
    assert "tu" in glossa("didak")[0]


def test_els_termes_linguistics_del_web_de_lautor_guanyen_al_diccionari():
    #: 15-11-2026: el glossari de tamazightforall.com (l'autor de les classes) dóna el
    #: metallenguatge que el diccionari general glossava amb mots de la vida corrent:
    #: `azɣr` «onguent» (és «arrel morfològica»), `aḍfiṛ` «roba vella» («sufix»),
    #: `asnaway` «li + proceed» («estandardització»); i en té que no teníem (`tasntalant`).
    for forma, tros in (("azɣr", "arrel"), ("aḍfiṛ", "sufix"), ("asnaway", "estandarditzaci"),
                        ("tasntalant", "dialectologia"), ("afrimsli", "fonema"), ("timsislit", "fonètica")):
        diu, com = glossa(forma)
        assert tros in diu and "terme lingüístic" in diu, (forma, diu)
        assert com == "lèxic validat", (forma, com)


def test_el_que_diuen_els_subtitols_humans_mana_sobre_el_diccionari():
    #: 15-11-2026: als contes amb subtítols humans en amazic i anglès, el diccionari deia
    #: `ġr` «appeler, chez» (el parlant: «only»), `ayda` «Land» («everything he owned»),
    #: `yufa` «valoir mieux» («he found»), `iffġ` «valoir mieux» («get out»), `mas` «Mister»
    #: («where to»), `tusi` «gémination» («was full of»), `ssinḫ` «de là» («I don't know»).
    for forma, tros in (("ġr", "només"), ("hat", "vet aquí"), ("ayda", "béns"), ("kiy", "tu"),
                        ("mas", "cap a on"), ("yufa", "va trobar"), ("iffġ", "surt"),
                        ("ssinḫ", "sé"), ("tusi", "porta"), ("ta", "encara")):
        diu, com = glossa(forma)
        assert tros in diu, (forma, diu)
        assert com.startswith(("partícula", "forma gramatical")), (forma, com)
    #: `didawn` = did + awn: «amb vosaltres», no «i, amb + Place»
    diu, com = glossa("didawn")
    assert "vosaltres" in diu, (diu, com)


# -------------------------------------- el verb «ser», que el diccionari serveix com a nom
def test_el_verb_ser_surt_de_la_taula_i_no_del_diccionari():
    #: 171 de les 220 aparicions de la còpula arribaven al traductor absents o com a nom:
    #: `tga` «Juniper» (40), `illa` «Obligation, Case» (23), `tlla` «action de pleurer» (22).
    #: Sense el verb, els noms arriben i el model s'inventa qui fa què.
    for forma, tros in (("iga", "és"), ("tga", "és"), ("illa", "hi ha"), ("tlla", "hi ha"),
                        ("llan", "hi ha"), ("igan", "que és"), ("illan", "que hi ha"),
                        ("ira", "vol"), ("tram", "voleu"), ("riġ", "vull")):
        diu, com = glossa(forma)
        assert tros in diu, (forma, diu)
        assert com.startswith("forma gramatical"), (forma, com)


def test_la_forma_gramatical_tambe_casa_amb_lortografia_de_lasr():
    #: `macc` («però») l'ASR l'escriu `mašš`; `giḫ` i `giġ` són la mateixa persona.
    assert "però" in glossa("mašš")[0]
    assert "però" in glossa("macc")[0]
    assert "sóc" in glossa("giġ")[0]


def test_una_forma_amb_dues_lectures_mai_no_es_segura():
    #: `inna` és «va dir» (ini) i també «mare»: la taula ho diu tot dos, i cap no és segura.
    diu, com = glossa("inna")
    assert "va dir" in diu and "mare" in diu
    assert com not in morfologia.SEGURES


def test_la_negacio_del_verb_ser():
    #: Darrere d'`ur` la `a` es torna `i`: `ur illi`, `ur tlli`, `ur llin`.
    assert "no hi ha" in glossa("illi")[0]
    assert "no hi ha" in glossa("llin")[0]


# ------------------------------------ els mots curts, que el guard vell no deixava partir
def test_un_mot_curt_es_parteix_si_la_resta_es_a_la_taula():
    #: `das` (16 aparicions), `dak` (6), `dag` (7) eren els mots sense glossa més freqüents
    #: del corpus: el guard de MIN_ARREL no deixava partir res de 2-3 lletres. Es parteixen
    #: bé perquè la resta és a la taula a mà, no al diccionari.
    #: `da`+`s` («habitual + amb») també és un tall vàlid; mana la resta més llarga.
    assert morfologia._particula_al_davant("das")[0] == ("d", "as")
    diu, com = glossa("das")
    assert com == "partícula enganxada" and "li" in diu


def test_un_mot_curt_no_es_parteix_cap_al_diccionari():
    #: Una resta de dues lletres casa amb qualsevol entrada del diccionari: només val la
    #: taula. `did` no és `d`+`id` («cadena»), per molt que `id` sigui al diccionari fals:
    #: des del 15-11-2026 és a la taula («amb»), i d'allà ha de sortir, no del diccionari.
    assert glossa("did") == ("amb", "partícula")


def test_la_labialitzada_de_lasr_casa_amb_la_taula():
    #: `akkw` («tot») l'ASR l'escriu `akku`; contra la veritat humana sortia «perroquet».
    assert morfologia.clau_de_particula("akku") == "akkw"
    assert glossa("akku")[0].startswith("tot")


def test_el_creuament_de_dues_fonts_independents_entra_al_lexic_validat():
    #: 15-11-2026 (vespre): `tools/lm/creuament.py` → `data/lexic_validat_creuament.json`. Una
    #: glossa hi entra quan dues fonts independents coincideixen (els subtítols en/ar del mateix
    #: subtitulador compten com UNA). La majoria confirmen el diccionari; tres el corregeixen:
    #: `tiġrmt` «forteresse» → ciutat (subtítols + amazic.cat), `izlan` «poem» → cançons
    #: (professor en dàrija + amazic.cat). I totes porten la mena «lèxic validat».
    for forma, tros in (("tiġrmt", "ciutat"), ("izlan", "cançons"), ("knni", "vosaltres"), ("mlmi", "quan")):
        diu, com = glossa(forma)
        assert tros in diu and " — o bé: " not in diu, (forma, diu)
        assert com == "lèxic validat", (forma, com)


def test_ax_es_un_dictic_rere_un_nom_i_ens_rere_un_verb():
    #: #398, 15-11-2026: 20 aparicions als contes de TFA amb pista humana i anglès humà, totes
    #: darrere d'un nom o d'un díctic i traduïdes com a determinant («ill ax» this sea, «dinn ax»
    #: there, «ikru ann ax» that lamb); «ens» només darrere d'un verb. La glossa ha de dir les dues
    #: lectures amb la seva condició, i no ha de dir mai «també».
    for forma in ("ax", "aġ", "aḫ"):
        diu, com = glossa(forma)
        assert "díctic" in diu and "ens" in diu and "també" not in diu, (forma, diu)
        assert com == "partícula", (forma, com)
