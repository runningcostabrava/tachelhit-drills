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


def test_lestat_dannexio_no_es_fa_amb_un_patro():
    """No hi és a `PECES`, i no hi ha de ser.

    La seva peça són les primeres lletres del nom, i amb un patró no es pot distingir un nom que
    ha perdut la «a-» d'un que comença per «t-» de tota la vida: l'exercici ensenyaria una cosa
    falsa. Es pregunta amb una taula de formes (`fes_annexio`), no buscant dins d'una frase."""
    assert "estat-annexio" not in exercicis.PECES


def test_lestat_dannexio_pregunta_amb_la_forma_lliure_al_davant():
    """L'exercici dona el nom sol i demana com queda darrere de la preposicio."""
    fets = exercicis.fes("estat-annexio", [])
    assert fets, "la unitat de l'annexio ha de tenir exercicis"
    e = fets[0]
    assert e["unit"] == "estat-annexio" and e["drill_id"] is None
    assert "«" in e["pregunta"], "la pregunta ha de dir QUIN nom es pregunta"
    assert e["resposta"] and e["resposta"] in e["opcions"]
    assert len(e["opcions"]) == 4, "quatre opcions: una de bona i tres de la mateixa regla"
    assert e["shi"].startswith("g ") and "·" in e["shi"], "el buit va dins d'una frase"
    assert e["tif"], "la tifinag la posa el servidor"


def test_lannexio_nomes_fa_servir_les_lectures_segures(monkeypatch):
    """El tifinag d'aquella classe es va llegir a ull, i hi ha signes que s'assemblen molt.

    Les parelles marcades `cert: false` hi son perque algu les confirmi; si sortissin com a
    exercici, l'app ensenyaria com a cert el que encara no ho es.

    La taula de debo es posa i es treu dubtes a mesura que es comproven, i per aixo aqui se'n
    fa una de falsa: el que s'ha de complir es **el filtre**, no que el fitxer d'avui tingui cap
    parella dubtosa.
    """
    taula = {"font": {"autor": "algu", "url": "http://exemple", "obra": "una classe"},
             "regles": [{"id": "prova", "nom": "prova", "diu": "prova", "segon": 1, "parelles": [
                 {"lliure": "argaz", "annexat": "urgaz", "ca": "home", "cert": True},
                 {"lliure": "adlis", "annexat": "udlis", "ca": "llibre", "cert": True},
                 {"lliure": "afus", "annexat": "ufus", "ca": "ma", "cert": True},
                 {"lliure": "amud", "annexat": "umud", "ca": "llavor", "cert": True},
                 {"lliure": "axxx", "annexat": "uxxx", "ca": None, "cert": False},
             ]}]}
    monkeypatch.setattr(exercicis, "_taula", lambda _fitxer: taula)
    fets = exercicis.fes("estat-annexio", [], quants=99)
    assert fets, "amb quatre parelles segures ja se'n pot fer"
    for e in fets:
        assert e["resposta"] != "uxxx"
        assert "uxxx" not in e["opcions"], "tampoc com a resposta falsa"


def test_lannexio_amb_poques_parelles_segures_no_fa_cap_exercici(monkeypatch):
    """Val mes cap exercici que un amb dues opcions: la bona es veuria de lluny."""
    taula = {"font": {}, "regles": [{"id": "curta", "diu": "", "segon": 1, "parelles": [
        {"lliure": "argaz", "annexat": "urgaz", "cert": True},
        {"lliure": "adlis", "annexat": "udlis", "cert": True},
        {"lliure": "afus", "annexat": "ufus", "cert": False},
    ]}]}
    monkeypatch.setattr(exercicis, "_taula", lambda _fitxer: taula)
    assert exercicis.fes("estat-annexio", []) == []


def test_el_buit_tambe_es_veu_a_la_ratlla_tifinag():
    """El transliterador només tradueix lletres, i els punts del buit se li perdien.

    A la pantalla, la ratlla tifinag sortia sencera i sense cap forat —i a l'exercici de
    l'annexió, que és «g» i prou més el buit, quedava una lletra solta que semblava una errada.
    Els espais de les puntes també es retallaven, i la frase quedava enganxada al buit.
    """
    assert exercicis.tif_amb_buit("g ···") == "ⴳ ···"

    enmig = exercicis.tif_amb_buit("is dar-k ···· ɣ wass")
    assert " ···· " in enmig, "el buit ha de quedar separat del que té al costat"
    assert enmig.startswith("ⵉⵙ "), "i el que hi ha abans del buit s'ha de traduir igual"

    e = exercicis.fes("estat-annexio", [])[0]
    assert "·" in e["tif"], "l'exercici que es serveix ha de portar el buit a la tifinag"


def test_lannexio_diu_d_on_surt():
    """Credit: cada exercici porta l'obra, qui la signa i el segon del video."""
    e = exercicis.fes("estat-annexio", [])[0]
    assert e["font"]["autor"] and e["font"]["url"] and e["font"]["segon"]


def test_el_plural_es_pregunta_amb_el_mot_sol_al_davant():
    """«N'hi ha un de sol. I quan n'hi ha molts?», amb el singular a la vista."""
    fets = exercicis.fes("noms-genere-nombre", [])
    assert fets, "la unitat del nom ha de tenir exercicis"
    e = fets[0]
    assert e["unit"] == "noms-genere-nombre" and e["drill_id"] is None
    assert e["resposta"] in e["opcions"] and len(e["opcions"]) == 4
    assert e["shi"] and "·" not in e["shi"], \
        "al plural no hi ha marc de frase: s'ensenya el mot sol, perquè no se'n pot inventar cap"
    assert e["tif"], "la tifinag la posa el servidor"
    assert e["font"]["autor"] and e["font"]["segon"]


def test_el_plural_no_barreja_les_dues_maneres_de_fer_lo():
    """Les respostes falses han de sortir de la MATEIXA regla.

    Si a un plural intern se li posen de fals tres plurals externs, la bona es veu de lluny i
    l'exercici deixa d'ensenyar res.
    """
    import json
    taula = json.loads(exercicis.PLURAL_FITXER.read_text(encoding="utf-8"))
    per_regla = {r["id"]: {p["molts"] for p in r["parelles"]} for r in taula["regles"]}
    for e in exercicis.fes("noms-genere-nombre", [], quants=99):
        quina = e["id"].split(":")[1]
        assert set(e["opcions"]) <= per_regla[quina], \
            "una opció surt d'una altra manera de fer el plural"


def test_les_dues_taules_no_es_trepitgen():
    """L'annexió i el plural fan servir el mateix constructor; els noms han de seguir sent únics."""
    tots = exercicis.fes("estat-annexio", [], quants=99) + \
        exercicis.fes("noms-genere-nombre", [], quants=99)
    noms = [e["id"] for e in tots]
    assert len(set(noms)) == len(noms)
    unitats = {e["unit"] for e in tots}
    assert unitats == {"estat-annexio", "noms-genere-nombre"}


def test_cada_exercici_porta_el_seu_nom():
    """La pantalla els posa un per un i necessita una clau; els d'annexio no tenen `drill_id`."""
    frases = [fila(i, "tigmmi-nns", "casa seva") for i in range(1, 7)]
    tots = exercicis.fes("possessius", frases) + exercicis.fes("estat-annexio", [])
    noms = [e["id"] for e in tots]
    assert all(noms) and len(set(noms)) == len(noms)
