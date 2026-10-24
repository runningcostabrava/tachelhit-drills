# -*- coding: utf-8 -*-
from transliteration import to_forms, phonemic_key


def test_basic_word_azul():
    f = to_forms("azul")
    assert f["tifinagh"] == "ⴰⵣⵓⵍ"
    assert f["clean_latin"] == "azul"
    assert f["key"] == "azul"


def test_common_words_to_tifinagh():
    assert to_forms("aman")["tifinagh"] == "ⴰⵎⴰⵏ"      # water
    assert to_forms("argaz")["tifinagh"] == "ⴰⵔⴳⴰⵣ"     # man


def test_tifinagh_spells_itself():
    # gh -> ɣ ; the word "tifinagh" is ⵜⵉⴼⵉⵏⴰⵖ
    f = to_forms("tifinagh")
    assert f["tifinagh"] == "ⵜⵉⴼⵉⵏⴰⵖ"
    assert f["clean_latin"] == "tifinaɣ"


def test_digraph_gh():
    f = to_forms("aghrum")  # bread
    assert f["clean_latin"] == "aɣrum"
    assert f["tifinagh"] == "ⴰⵖⵔⵓⵎ"


def test_chat_numeral_7_is_haa():
    f = to_forms("ta7anut")  # shop
    assert f["clean_latin"] == "taḥanut"
    assert "ⵃ" in f["tifinagh"]


def test_chat_numeral_3_is_ayin():
    f = to_forms("3")
    assert f["clean_latin"] == "ɛ"
    assert f["tifinagh"] == "ⵄ"


def test_chat_numeral_9_is_qaf():
    assert to_forms("9")["tifinagh"] == "ⵇ"


def test_key_collapses_gemination_and_matches_variant():
    # doubled consonant differs in spelling but must share a phonemic key
    assert phonemic_key("azzul") == phonemic_key("azul") == "azul"


def test_key_is_script_independent():
    # the whole point: three spellings of "bread" share ONE phonemic key,
    # so search / dedup / pronunciation-scoring match across scripts.
    k = phonemic_key("aghrum")            # phone-Latin
    assert phonemic_key("aɣrum") == k     # academic Latin
    assert phonemic_key("ⴰⵖⵔⵓⵎ") == k     # Tifinagh
    assert k == "aɣrum"


def test_labialization_roundtrips_via_ascii_w():
    # labialized k (Tifinagh ⴽⵯ) renders as ASCII "kw" so it re-parses to the
    # same phonemic key — search/dedup stay consistent across scripts.
    f = to_forms("ⴽⵯ")
    assert f["clean_latin"] == "kw"
    assert phonemic_key(f["clean_latin"]) == phonemic_key("ⴽⵯ")


def test_tifinagh_input_roundtrips():
    f = to_forms("ⵜⵉⴼⵉⵏⴰⵖ")
    assert f["clean_latin"] == "tifinaɣ"
    assert f["key"] == "tifinaɣ"


def test_academic_input_is_idempotent():
    # feeding the clean Latin back in reproduces the same Tifinagh
    once = to_forms("aghrum")
    twice = to_forms(once["clean_latin"])
    assert twice["tifinagh"] == once["tifinagh"]
    assert twice["key"] == once["key"]


def test_c_is_sh_and_ou_is_u():
    # Berber-Latin: c = š ; demotic: ou = u
    assert to_forms("acou")["tifinagh"] == "ⴰⵛⵓ"


def test_multiword_keeps_spaces_and_normalizes():
    f = to_forms("azul fellawen")  # "hello to you (pl.)"
    assert " " in f["tifinagh"]
    # key drops schwa and collapses the geminate ll -> l
    assert f["key"] == "azul flawn"


def test_th_is_two_letters_not_a_digraph():
    """«th» és t + h, i a la nostra llengua és freqüentíssim.

    El prefix de 3a persona femenina és «t-» i hi ha arrels que comencen per h-: «thnna» («va
    bé»), «thlla», «thanut» («la botiga»). Mentre «th» va ser un dígraf, el mapa se'n menjava la
    h a les tres cares alhora —tifinagh, clau de cerca i `clean_latin`, que és la que el mòdul
    promet com a citable— i produïa «tnna», que no és cap paraula.

    Comptat al corpus: 75 aparicions de «th» i cap no és el dígraf cabilenc.
    """
    f = to_forms("thnna")
    assert f["clean_latin"] == "thnna"
    assert f["tifinagh"] == "ⵜⵀⵏⵏⴰ"
    assert f["key"] == "thna", "la clau col·lapsa la geminada, però no es menja la h"

    assert to_forms("thanut")["tifinagh"] == "ⵜⵀⴰⵏⵓⵜ"
    assert to_forms("thlla")["clean_latin"] == "thlla"
    # i la h que no va darrere d'una t ja anava bé: que segueixi igual
    assert to_forms("ihnna")["clean_latin"] == "ihnna"


def test_the_other_digraphs_stay():
    """Els que sí que són com la gent escriu: gh 936 aparicions, sh 569, ch 174, kh 141, ou 21."""
    assert to_forms("aghrum")["clean_latin"] == "aɣrum"
    assert to_forms("akhir")["clean_latin"] == "axir"
    assert to_forms("ashku")["clean_latin"] == "ašku"
    assert to_forms("achku")["clean_latin"] == "ašku"
    assert to_forms("souq")["clean_latin"] == "suq"


def test_una_lletra_descomposta_dona_la_mateixa_tifinag_que_una_dajuntada():
    """La biblioteca guarda 283 frases amb les lletres descompostes: «sġix» amb la g i el punt a
    sobre a part, «3afaš» amb la s i el capelló a part. Sense ajuntar-les, el transliterador no
    veia ni la ġ ni la š i servia una ALTRA lletra: «sġix» sortia ⵙⴳⵉⵅ (una g) i «3afaš»,
    ⵄⴰⴼⴰⵙ (una s). Qui aprenia llegia una tifinag equivocada."""
    import unicodedata
    import transliteration
    for word, tifinagh in (("sġix", "ⵙⵖⵉⵅ"), ("3afaš", "ⵄⴰⴼⴰⵛ"), ("awraɣ", "ⴰⵡⵔⴰⵖ")):
        trencada = unicodedata.normalize("NFD", word)
        sencera = unicodedata.normalize("NFC", word)
        assert transliteration.to_forms(sencera)["tifinagh"] == tifinagh
        assert transliteration.to_forms(trencada)["tifinagh"] == tifinagh, f"«{word}» descomposta"


def test_la_mateixa_paraula_escrita_de_dues_maneres_te_una_sola_clau():
    """I per això una frase gravada es troba: si la clau depengués de com estigui ajuntat el
    text, la mateixa paraula tindria dues claus i el capítol no trobaria mai la seva veu."""
    import unicodedata
    import practice
    for word in ("3afaš", "sġix", "aḍar", "tiṭṭ"):
        assert (practice.sound_key(unicodedata.normalize("NFD", word))
                == practice.sound_key(unicodedata.normalize("NFC", word))), word
