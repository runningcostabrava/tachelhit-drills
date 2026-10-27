"""El compendi s'ha d'anar a buscar, no carregar (#374).

Anava sencer al prompt de cada pregunta: 549.650 caràcters, uns 137.000 tokens, es preguntés el
que es preguntés. Una pregunta al copilot costava 0,065 € —seixanta vegades una crida del
pipeline— i portava dos-cents mil tokens de llibre i cap frase de la biblioteca.

Les proves van sobre un compendi de mentida, petit i escrit aquí: el de debò no viu al
repositori (és material d'altri, es baixa a la primera) i una prova que depengui d'una descàrrega
no és una prova.
"""
import compendi

LLIBRE = """# Compendi de prova

## 1. Fonologia i grafemàtica

1.1 Les lletres
Aquest apartat parla de l'escriptura i de com es fan servir les lletres en general, amb molts
exemples i molta palla perquè tingui la llargada d'una secció de debò i no la descarti el tall
de les seccions massa curtes. Les lletres, les lletres i les lletres.

1.2.1 Vocals
Les vocals de l'amazic son tres: a, i, u. Aquesta seccio parla de les vocals i de res mes, i te
prou text per no ser descartada: vocals, vocals, vocals, obertura, timbre i quantitat vocalica.

## 5. Morfosintaxi verbal

5.1.3 Sufixos de l'imperatiu
L'imperatiu es forma amb uns sufixos propis segons la persona i el nombre. Aquesta seccio parla
de l'imperatiu i dels seus sufixos, amb exemples llargs perque la seccio tingui cos suficient.

5.2 L'aorist
L'aorist es un altre tema ben diferent, i aquesta seccio no parla ni de vocals ni d'imperatiu;
parla de l'aorist i prou, amb text abundant per arribar a la llargada minima d'una seccio.
"""


def _net():
    compendi.oblida()


def test_el_tros_que_torna_es_molt_mes_petit_que_el_llibre():
    _net()
    tros, _noms = compendi.per("com es fa l'imperatiu?", LLIBRE)
    assert tros and len(tros) < len(LLIBRE), "ha de tornar un tros, no el llibre"


def test_tria_la_seccio_que_es_diu_com_la_pregunta():
    _net()
    _tros, noms = compendi.per("com es fa l'imperatiu?", LLIBRE)
    assert noms, "no ha trobat res"
    assert "imperatiu" in noms[0].lower(), \
        "la primera hauria de ser la secció de l'imperatiu, i és %r" % noms[0]


def test_una_paraula_que_surt_a_tot_arreu_no_mana():
    """«les vocals» tornava el capítol de les conjuncions: «les» s'emportava el compte.

    Cada paraula pesa segons a quantes seccions surt, de manera que «vocals» mana sobre «les»
    sense cap llista de paraules buides escrita a mà.
    """
    _net()
    _tros, noms = compendi.per("les les les vocals", LLIBRE)
    assert noms and "vocals" in noms[0].lower(), \
        "la primera hauria de ser la de les vocals, i és %r" % noms[0]
    # I la prova de debò: repetir la paraula buida no mou qui guanya.
    _net()
    _t2, n2 = compendi.per("les vocals", LLIBRE)
    assert n2[0] == noms[0], "una paraula que surt a tot arreu no pot moure el primer lloc"


def test_sense_pregunta_nomes_torna_lindex():
    _net()
    tros, noms = compendi.per("", LLIBRE)
    assert not noms
    assert "capítols" in tros and len(tros) < 400, "sense pregunta no es tria res"
    assert "Fonologia" in tros, "l'índex ha de dir de què parla el llibre"


def test_mai_mes_del_que_se_li_diu():
    _net()
    tros, _noms = compendi.per("lletres vocals imperatiu aorist", LLIBRE, max_caracters=400)
    assert len(tros) <= 400 + len(compendi.index(LLIBRE)) + 4, len(tros)
