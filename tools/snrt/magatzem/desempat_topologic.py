"""Desempat per topologia: quan la forma global no sap triar, decideix la de dins.

El problema, mesurat: sis lletres són una anella amb una marca diferent a dins i se solapen
entre 0,74 i 0,88. L'anella és la major part dels píxels i la comparteixen totes, o sigui que
l'IoU no pot separar-les: a `tskla` el lector tria ⵀ sobre ⵙ per 0,03 i encerta nou de cada deu
vegades, no deu.

La topologia sí que les separa, i surt de les plantilles mateixes:

    trossos de tinta | forats |  signes
          2          |   1    |  ⵙ        <- única
          1          |   2    |  ⴱ ⵀ ⵛ
          1          |   1    |  ⴰ ⴳ ⴽ ⵇ ⵔ ⵕ ⵚ
          1          |   0    |  la resta

La regla: dels candidats que la plantilla posa a dalt, es queden els que tenen la MATEIXA
topologia que el signe de la pantalla; si en queda algun, mana el millor d'aquells. Si no en
queda cap, no es toca res — val més deixar-ho com estava que forçar una resposta.

Això NO toca el codi del lector: s'aplica a sobre, per poder mesurar si val abans de proposar-ho.
"""
import sys

import numpy as np
from scipy import ndimage

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
if FAB not in sys.path:
    sys.path.insert(0, FAB)
import tifinag_plantilles as PL  # noqa: E402

VUIT = np.ones((3, 3), bool)
CREU = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
#: per sota d'això un forat és soroll de binarització, no un forat de debò
FORAT_MIN = 8


def topologia(m):
    """La firma d'una mascara: (trossos de tinta, forats, com estan posats).

    El tercer element nomes val quan hi ha DOS forats, i separa tres lletres que la resta de la
    firma no distingeix (mesurat sobre les plantilles):

        ⴱ  barra horitzontal -> els dos forats, un SOBRE l'altre (dy 10,1 / dx 0,1)
        ⵀ  barra vertical    -> un AL COSTAT de l'altre          (dy 0,0 / dx 10,2)
        ⵛ  dos punts         -> forats minusculs (11 i 10 px)

    Els forats petits no compten com a forats: a aquesta mida son soroll de binaritzacio.
    """
    m = np.asarray(m) > 0
    if m.size == 0 or not m.any():
        return (0, 0, "")
    _, n_tinta = ndimage.label(m, structure=VUIT)
    lab, n = ndimage.label(~m, structure=CREU)
    if n == 0:
        return (n_tinta, 0, "")
    vora = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    forats = []
    for i in range(1, n + 1):
        if i in vora:
            continue
        ys, xs = np.nonzero(lab == i)
        if len(ys) < FORAT_MIN:
            continue
        forats.append((len(ys), ys.mean(), xs.mean()))
    if len(forats) != 2:
        return (n_tinta, len(forats), "")
    forats.sort(key=lambda t: -t[0])
    (na, ya, xa), (nb, yb, xb) = forats[:2]
    #: en proporcio a la mida del signe, que les plantilles i els glifs de pantalla no fan igual
    petits = max(na, nb) < 0.08 * m.size
    com = "petits" if petits else ("apilats" if abs(ya - yb) > abs(xa - xb) else "costat")
    return (n_tinta, 2, com)


def taula_plantilles():
    z = np.load(PL.NPZ, allow_pickle=True)
    return {str(s): topologia(np.asarray(m) > 0)
            for s, m in zip(z["signes"], z["mascares"])}


TOPO = taula_plantilles()


def desempata(mask, notes, marge=0.08, mira=4):
    """`notes` és [(iou, signe), ...] ordenat. Torna la llista reordenada.

    Només actua quan els primers candidats estan JUNTS (dins de `marge`): si el primer guanya
    de molt, la forma global ja ho té clar i no s'hi ha de ficar ningú.
    """
    if len(notes) < 2:
        return notes
    if notes[0][0] - notes[1][0] > marge:
        return notes
    t = topologia(mask)
    caps = notes[:mira]
    casen = [n for n in caps if TOPO.get(n[1]) == t]
    if not casen or casen[0][1] == notes[0][1]:
        return notes
    #: el millor dels que casen passa davant; la resta es queda com estava
    resta = [n for n in notes if n is not casen[0]]
    return [casen[0]] + resta


def posa_el_desempat():
    """Embolcalla `PL.classifica` perquè torni les notes ja desempatades."""
    original = PL.classifica

    def classifica(mask, y_rel, *a, **k):
        return desempata(mask, original(mask, y_rel, *a, **k))

    PL.classifica = classifica
    return original
