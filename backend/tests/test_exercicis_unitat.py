"""Exercicis que ensenyen el punt de la unitat (#428).

El que es prova aquí és el que fa que un exercici valgui: que el buit caigui **a la peça de la
unitat** i no a una paraula qualsevol, que una frase amb dues peces no serveixi, que les
respostes falses siguin formes que la biblioteca fa servir de debò, i que es corregeixi **pel
so** —qui escriu `gh` on la resposta diu `ɣ` ha encertat (#364).
"""
import types

import exercicis


def fila(id, shi, ca, audio=None, speaker=None):
    return types.SimpleNamespace(id=id, text_tachelhit=shi, text_catalan=ca,
                                 audio_url=audio, speaker=speaker, region=None, author=None)


def test_el_buit_cau_a_la_peca_de_la_unitat_i_no_a_una_paraula_qualsevol():
    frases = [
        fila(1, "tigmmi-nns tmqqur", "la seva casa és gran"),
        fila(2, "ism-inu Driss", "em dic Driss"),
        fila(3, "tarbat nnm tella", "la teva filla hi és"),
        fila(4, "gma-s iffuɣ", "el seu germà ha sortit"),
        fila(5, "tigmmi nnɣ tmẓẓi", "la nostra casa és petita"),
    ]
    ex = exercicis.fes("possessius", frases, quants=3)
    assert ex, "cinc frases amb possessiu donen exercicis"
    for e in ex:
        assert "·" in e["shi"], e["shi"]
        # el que es tapa és el possessiu, i la resta de la frase es queda sencera
        tapat = e["shi"].split("·")[0], e["shi"].split("·")[-1]
        assert e["resposta"].lower() in ("nns", "inu", "nnm", "nnɣ"), e["resposta"]
        assert e["ca"] and e["drill_id"] and e["unit"] == "possessius"
        assert all(t in next(f.text_tachelhit for f in frases if f.id == e["drill_id"]) for t in tapat if t)


def test_una_frase_amb_dues_peces_no_serveix():
    """Tapar-ne una és demanar una cosa que qui respon no pot endevinar quina és."""
    dues = fila(9, "tigmmi-nns d tarbat-nns", "la seva casa i la seva filla")
    frases = [dues] + [fila(i, f"ism-inu {i}", "em dic") for i in range(10, 15)]
    ex = exercicis.fes("possessius", frases, quants=9)
    assert dues.id not in [e["drill_id"] for e in ex], "la frase amb dos possessius es deixa"


def test_les_respostes_falses_son_formes_que_la_biblioteca_fa_servir():
    frases = [
        fila(1, "tigmmi-nns tmqqur", "la seva casa és gran"),
        fila(2, "ism-inu Driss", "em dic Driss"),
        fila(3, "tarbat nnm tella", "la teva filla hi és"),
        fila(4, "tigmmi nnɣ tmẓẓi", "la nostra casa és petita"),
        fila(5, "gma nnk iffuɣ", "el teu germà ha sortit"),
    ]
    ex = exercicis.fes("possessius", frases, quants=3)
    formes = {"nns", "inu", "nnm", "nnɣ", "nnk"}
    for e in ex:
        assert len(e["opcions"]) == 4 and len(set(e["opcions"])) == 4, e["opcions"]
        assert set(e["opcions"]) <= formes, e["opcions"]
        assert any(exercicis.igual_de_so(o, e["resposta"]) for o in e["opcions"]), e


def test_es_corregeix_pel_so_i_no_lletra_per_lletra():
    """«gh» i «ɣ» són la mateixa lletra escrita per dues mans: dir que no seria ensenyar una
    falsedat."""
    e = {"resposta": "nnɣ"}
    assert exercicis.corregeix(e, "nnɣ")
    assert exercicis.corregeix(e, "nngh"), "la mateixa forma amb l'altra grafia val"
    assert not exercicis.corregeix(e, "nns")


def test_una_unitat_sense_prou_frases_no_fa_cap_exercici():
    """Val més cap exercici que un de dolent, com les seccions buides del Mètode."""
    assert exercicis.fes("possessius", [fila(1, "ism-inu Driss", "em dic Driss")]) == []
    assert exercicis.fes("aorist-ad", [fila(1, "ad dduɣ", "hi aniré")] * 6) == [], \
        "una unitat sense peça escrita no s'inventa cap exercici"


def test_lestat_dannexio_no_te_exercici_a_posta():
    """La seva peça són les primeres lletres del nom, i amb un patró no es pot distingir un nom
    que ha perdut la «a-» d'un que comença per «t-» de tota la vida: l'exercici ensenyaria una
    cosa falsa. Queda per fer amb la forma lliure del nom al davant."""
    assert "estat-annexio" not in exercicis.PECES
