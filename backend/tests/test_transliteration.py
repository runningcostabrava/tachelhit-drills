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
