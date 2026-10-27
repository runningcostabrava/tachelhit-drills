"""Que un conte dibuixat segueixi essent el mateix conte (#390).

Tres coses que, si es trenquen, no es veurien fins que algú obrís la història i trobés un llop
diferent a cada pàgina —i llavors ja s'hauria gastat la quota de GPU del dia dibuixant-ho.
"""
import conte_art


def test_cada_linia_del_conte_te_la_seva_escena():
    """Una línia sense escena torna un dibuix genèric que no diu res de la història."""
    c = conte_art.LLOP_I_XAI
    assert len(c.escenes) == 37
    assert sorted(c.escenes) == list(range(1, 38)), "hi ha un forat o un número repetit"
    for n, (qui, escena) in c.escenes.items():
        assert escena.strip(), "la línia %d no diu què s'hi dibuixa" % n
        for q in qui:
            assert q in c.personatges, "la línia %d crida un personatge que no existeix: %s" % (n, q)


def test_nomes_es_descriu_qui_surt_a_lescena():
    """El repartiment convoca: un personatge descrit al text, el model el dibuixa.

    Per això l'escena del xai tot sol no pot portar la descripció del llop; si la porta, el llop
    hi surt encara que l'escena digui que no.
    """
    c = conte_art.LLOP_I_XAI
    sol = c.prompt(2, "Hi havia una vegada un xai que pasturava.")
    assert "THE LAMB" in sol
    assert "THE WOLF" not in sol, "una escena del xai sol no pot descriure el llop"
    tots_dos = c.prompt(19, "Vosaltres esteu a dalt, jo estic a baix.")
    assert "THE WOLF" in tots_dos and "THE LAMB" in tots_dos
    # El lloc hi és sempre: és el que fa que totes les imatges siguin la mateixa vall.
    assert "THE PLACE" in sol and "THE PLACE" in tots_dos


def test_cap_escena_no_demana_una_cosa_dient_que_no_hi_sigui():
    """El model no llegeix negacions: «cap llop enlloc» li va dibuixar el llop ben gros.

    El que buida una escena és el pla, no la paraula «cap». Si algú torna a escriure una escena
    en negatiu, això ho diu abans de gastar-hi la quota del dia.
    """
    c = conte_art.LLOP_I_XAI
    prohibits = (" no wolf", " no lamb", " no other", " nobody", " nothing ", " without any",
                 " no blood", " not in this picture")
    for n, (_, escena) in c.escenes.items():
        baix = " " + escena.lower()
        for p in prohibits:
            assert p not in baix, "la línia %d demana una cosa en negatiu: «%s»" % (n, p.strip())


def test_cada_linia_te_la_seva_llavor():
    """Una llavor per línia: un dibuix es pot refer igual sense refer tot el conte."""
    c = conte_art.LLOP_I_XAI
    assert c.llavor(1) != c.llavor(2)
    assert c.llavor(7) == conte_art.LLAVOR + 7


def test_lestil_no_prohibeix_el_que_les_escenes_demanen():
    """L'estil deia «cap bafarada enlloc» mentre divuit escenes en demanaven una.

    Es va veure abans de dibuixar res, de pura sort. Això ho diu sense gastar-hi cap quota: si
    una escena demana una cosa que l'estil prohibeix, el model obeirà l'un o l'altre i no sabrem
    quin fins que ens arribin trenta-set dibuixos per llençar.
    """
    import conte_art
    estil = conte_art.ESTIL.lower()
    demanen = [n for n, (_, e) in conte_art.LLOP_I_XAI.escenes.items()
               if "balloon" in e.lower() or "thought cloud" in e.lower()]
    assert len(demanen) >= 15, "les línies de diàleg han de portar la seva bafarada"
    assert "no speech bubbles" not in estil and "speech bubbles or" not in estil, \
        "l'estil prohibeix la bafarada que les escenes demanen"
    # El que sí que s'ha de prohibir sempre: lletres a dins del dibuix.
    assert "no letters" in estil and "no captions" in estil
