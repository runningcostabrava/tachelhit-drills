"""Una mateixa lletra escrita de dues maneres, i qui aprèn ho ha de saber (#364).

Qui obre la biblioteca llegeix `rix` en una frase i `riɣ` en una altra, i es pensa que són dues
paraules. No ho són: és **la mateixa**, escrita per dues mans amb dues convencions. Qui ho sap no
hi ensopega; qui no ho sap aprèn una lletra que no hi és, perquè el transliterador escriu el que
té i pinta ⵅ on hi va ⵖ.

Això no és una opinió sobre com s'hauria d'escriure: és un fet mesurat a la nostra biblioteca, i
els números hi són perquè qualsevol els pugui tornar a comptar.

Es diu als dos llocs on algú pot topar-hi: la unitat dels sons de la Gramàtica i el capítol dels
sons del Mètode. No es diu a cada frase: seria soroll, i la frase ja està escrita com la va
escriure qui la va escriure.
"""
from __future__ import annotations

from typing import Dict

#: Les parelles que ho demostren: la mateixa paraula, escrita de les dues maneres, dins el nostre
#: propi corpus. Si algun dia els números canvien, es tornen a comptar; no s'arrodoneixen.
PARELLES = [
    {"x": "rix", "x_n": 23, "g": "riɣ", "g_n": 2, "ca": "vull"},
    {"x": "ssinx", "x_n": 2, "g": "ssinɣ", "g_n": 3, "ca": "sé"},
    {"x": "uznx", "x_n": 1, "g": "uznɣ", "g_n": 1, "ca": "vaig enviar"},
    {"x": "inna-yax", "x_n": 3, "g": "inna-yaɣ", "g_n": 1, "ca": "ens va dir"},
]

NOTA: Dict = {
    "titol": "La mateixa lletra, escrita de dues maneres",
    "cos": [
        "A la biblioteca trobaràs la mateixa paraula escrita de dues maneres: «rix» i «riɣ» "
        "són totes dues «vull». No són dues paraules; és una sola, escrita per dues mans.",

        "Qui va recollir les frases de Beni Mellal no fa servir mai la lletra ɣ: escriu una x "
        "allà on es diu ɣ. Ho sabem perquè en aquell recull hi ha 1.092 x i cap ɣ, i perquè "
        "quatre paraules surten escrites de les dues maneres segons qui les va escriure — i "
        "totes quatre són la primera persona («vull», «sé», «vaig enviar») o el «ens».",

        "La regla pràctica: quan un verb acaba en -x i vol dir «jo», aquella x es diu ɣ. Així "
        "«ddix» (vaig anar), «nnix» (vaig dir), «ssnx» (sé) i «gix» (sóc) sonen -ɣ, igual que "
        "«riɣ». També «llix» és «lliɣ» (quan) i «max» és «maɣ» (per què).",

        "No totes les x són ɣ. «ixf» (cap), «ixṣṣa» (cal) i «ixṛṛiḍn» porten una x de debò, que "
        "és un so diferent: la j castellana, o la ch alemanya de «Bach».",

        "Per què t'ho diem en comptes de corregir-ho: la frase està escrita com la va escriure "
        "qui la va escriure, i això no s'hi toca. El que podem fer és que no t'enganyi.",
    ],
    "parelles": PARELLES,
    "quantes": 635,
    "de_quantes": 3791,
}


def nota() -> Dict:
    """La nota, tal com la serveixen la Gramàtica i el Mètode."""
    return {**NOTA, "parelles": [dict(p) for p in PARELLES]}
