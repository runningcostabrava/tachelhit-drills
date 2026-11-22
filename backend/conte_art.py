"""Dibuixar un conte sencer perquè sigui el mateix conte (#390).

El dibuixant de targetes (`illustrate.py`) fa **una escena per frase, cadascuna pel seu compte**:
és el que ha de fer una targeta solta, i és exactament el que no ha de fer un conte. Trenta-set
dibuixos independents del mateix conte donen trenta-set llops diferents en trenta-set rius
diferents, i llavors la imatge deixa d'ajudar a seguir la història: la distreu.

Aquí hi ha el que fa que siguin un de sol, i el que es va haver d'aprendre dibuixant-lo.

## Quatre coses, i les quatre calen

1. **El repartiment s'escriu sempre igual** i es repeteix a cada crida.
2. **La geografia no es mou.** Al conte del llop i el xai, el llop és sempre riu amunt i a
   l'esquerra, i el xai riu avall i a la dreta. Si això balla, la línia «vosaltres esteu a dalt,
   jo estic a baix» deixa de voler dir res.
3. **Cada línia porta la seva escena escrita.** N'hi ha que no en són cap —«Aquell matí,», «El
   llop li va dir:»— i, deixades soles, tornen un dibuix genèric que no diu res del conte.
4. **La llavor, per línia.** `LLAVOR + número`: així cada dibuix es pot tornar a fer igual quan
   calgui refer-ne un de sol.

## Tres coses que es van aprendre equivocant-se

**El model no llegeix negacions.** Demanar «el xai sol, cap llop enlloc» va dibuixar el llop ben
gros i al mig. El que buida una escena no és la paraula «cap»: és el pla. De prop i ben ple, no
hi cap ningú més.

**El repartiment convoca.** Encara amb l'escena escrita en positiu, el llop seguia sortint:
estava descrit al text de cada crida. Un personatge només entra al dibuix si se'l descriu, de
manera que cada escena diu **qui hi surt** i la descripció dels altres no s'envia.

**La llavor fixa la composició, no el personatge.** Amb una de sola per a tot el conte, totes les
imatges volien ser la mateixa —dos animals, el gros a l'esquerra i el petit a la dreta— i una
escena del xai tot sol tornava una ovella gran i un xai, per omplir els dos llocs. Qui fa que el
llop sigui el mateix llop és el text que el descriu.

**I una escena s'ha de dir pel dret.** «Una vista de perfil que ensenyi el pendent» va tornar
dues ovelles i cap llop. «El llop és dalt a l'esquerra d'on ve l'aigua; a baix a la dreta hi ha
el xai» ja ensenya qui és a dalt i qui a baix, que és tot el que la línia diu.

## Què ha de dir un dibuix

Petició del propietari (27-10-2026): «les imatges han de mostrar el que el llop o el xai estan
dient, potser un núvol de pensament mostrant el que diu el llop… al final és un tema de
mnemotècnia».

Té raó, i canvia el criteri de totes les escenes. Un conte en una llengua que no saps no
s'aguanta amb un dibuix **de la situació**: vint línies seguides al mateix riu amb els mateixos
dos animals són vint dibuixos iguals, i llavors la imatge no ajuda a recordar res. El que recorda
és **el que es diu**: el llop acusa el xai d'embrutar-li l'aigua, i el xai respon que l'any passat
encara no havia nascut. Això es pot ensenyar, i és el que fa que la frase s'enganxi.

Per això les línies de diàleg porten una **bafarada** —rodona per al que es diu, de núvol per al
que es pensa— i **a dins hi ha un dibuix, no lletres**: aigua marró per «me l'has embrutat», un
xai acabat de néixer per «encara no havia nascut», dos xais iguals per «doncs va ser el teu
germà». Lletres no, i no perquè no agradin: el model no sap escriure amazic ni català, i el que
hi posa són gargots que semblen paraules. Un gargot al costat d'una frase que s'està aprenent
ensenya a llegir el que no és.

## El final d'un conte violent

El llop se'l menja. El dibuix ho ha d'explicar **sense ensenyar-ho**: el salt, no la ferida. I,
com que el model no llegeix negacions, tampoc no se li diu «sense sang»: se li demana un salt, i
el que ve després es diu amb el llop tip i la vall en calma.
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

#: D'on surt cada dibuix: aquesta més el número de línia.
LLAVOR = 20261027

ESTIL = (
    "Flat vector storybook illustration, warm earthy palette (sand, terracotta, indigo, olive), "
    "clean simple shapes, soft rounded forms, gentle shadows. "
    "The only words anywhere are none: no letters, no numbers, no captions, no labels, no "
    "signs. A speech balloon, when the scene asks for one, holds a small drawing instead."
)


class Conte:
    """Un conte amb el seu repartiment, el seu lloc i una escena per línia."""

    def __init__(self, slug: str, lloc: str, personatges: Dict[str, str],
                 escenes: Dict[int, Tuple[Iterable[str], str]]):
        self.slug = slug
        self.lloc = lloc
        self.personatges = personatges
        self.escenes = escenes

    def prompt(self, n: int, frase: str) -> str:
        qui, escena = self.escenes[n]
        parts = [self.lloc] + [self.personatges[q] for q in qui]
        return (
            "%s\n\n%s\n\nThis is picture %d of %d of one single picture book, so the place and "
            "the characters must look identical to every other picture.\n\nThe scene: %s\n\n"
            "What the line of the story says, for the mood only, never written anywhere: «%s»"
            % (ESTIL, "\n".join(parts), n, len(self.escenes), escena,
               " ".join((frase or "").split()))
        )

    def llavor(self, n: int) -> int:
        return LLAVOR + n


LLOP_I_XAI = Conte(
    slug="the-wolf-and-the-lamb-ⵓⵛⵛⵏ-ⴷ-ⵉⴽⵔⵓ-the-sop-for-children",
    lloc=(
        "THE PLACE, identical in every picture: one shallow rocky stream running through a "
        "Moroccan Atlas valley, red earth banks, round pale stones, olive and argan trees, a low "
        "dry-stone wall far on the left, bare ochre hills behind, clear morning sky. The stream "
        "always runs from the HIGHER ground on the LEFT down to the LOWER ground on the RIGHT."
    ),
    personatges={
        "llop": ("THE WOLF: a lean grey wolf, dark grey back, pale cream muzzle and chest, amber "
                 "eyes, a clear notch missing from his LEFT ear, long thin legs, ribs faintly "
                 "showing. He is always on the higher ground upstream, on the LEFT."),
        "xai": ("THE LAMB: a small cream-white lamb, woolly curly fleece, dark grey face and "
                "ears, one black front hoof, big dark eyes, half the size of a wolf. He is "
                "always on the lower ground downstream, on the RIGHT."),
    },
    escenes={
        1: (("llop", "xai"), "Wide establishing view of the whole valley: the wolf standing on "
                             "the high left bank, the lamb drinking far down on the right bank, "
                             "the stream between them."),
        2: (("xai",), "One single lamb alone in the whole picture, grazing calmly on the green "
                      "grass of the right bank, filling most of the frame, quiet hills behind."),
        3: (("xai",), "Close view of the lamb at the water's edge in morning light, head lowered "
                      "to drink, its reflection in the water, filling most of the picture."),
        4: ((), "The valley at early morning, long shadows, mist lying over the stream, only "
                "stones, trees and water in the whole picture."),
        5: (("llop",), "Close view of the wolf prowling along the high left bank, head low, "
                       "tongue out, gaunt and thirsty, filling most of the picture."),
        6: (("llop",), "The wolf lapping water at the left bank edge, one ear turned, eyes "
                       "searching the valley for something to eat."),
        7: (("llop", "xai"), "The wolf freezes mid-step on the left bank, head turned sharply, "
                             "amber eyes fixed on the small lamb far downstream on the right."),
        8: (("llop", "xai"), "Close view of the wolf on the left bank licking his chops and staring downstream. A "
                     "soft white thought cloud with three little bubbles rises above the wolf's head. Inside "
                     "the cloud, drawn small and simple in the same flat style, there is a picture of the "
                     "little lamb standing alone. The cloud holds only that little picture."),
        9: (("llop", "xai"), "The wolf crouched low behind a big pale stone on the left bank, watching. A soft white "
                     "thought cloud with three little bubbles rises above the wolf's head. Inside the cloud, "
                     "drawn small and simple in the same flat style, there is a picture of the little lamb "
                     "with the long shadow of a wolf falling across it. The cloud holds only that little "
                     "picture."),
        10: (("llop",), "The wolf sitting on his haunches on the left bank, head tilted, one front paw lifted "
                     "as he thinks up a plan. A soft white thought cloud with three little bubbles rises "
                     "above the wolf's head. Inside the cloud, drawn small and simple in the same flat "
                     "style, there is a picture of a little lamb standing in thick brown muddy water. The "
                     "cloud holds only that little picture."),
        11: (("xai",), "The small lamb drinking peacefully on the right bank, calm and innocent, "
                       "while a long dark animal shadow stretches across the water towards it "
                       "from off-picture."),
        12: (("llop", "xai"), "The wolf steps up onto a flat rock on the left bank, chest out, "
                              "mouth opening to speak across the stream towards the lamb."),
        13: (("llop", "xai"), "The wolf barks across the water at the lamb, muzzle thrust forward, one front paw "
                     "pointing down at the stream. A big white rounded comic speech balloon with a smooth "
                     "outline rises from the wolf's open mouth. Inside the balloon, drawn small and simple "
                     "in the same flat style, there is a picture of the little lamb standing in the stream "
                     "with thick brown muddy water swirling around its hooves. The balloon holds only that "
                     "little picture."),
        14: (("llop", "xai"), "The wolf leans down from the higher left bank, teeth bared, looming over the small "
                     "lamb. A big white rounded comic speech balloon with a smooth outline rises from the "
                     "wolf's open mouth. Inside the balloon, drawn small and simple in the same flat style, "
                     "there is a picture of a wolf's wide open jaws above a tiny lamb. The balloon holds "
                     "only that little picture."),
        15: (("xai",), "Close view of the lamb on the right bank, legs trembling, ears flattened "
                       "back, looking up with wide frightened eyes."),
        16: (("xai",), "The lamb raises one front hoof, head bowed low, pleading towards the left. A big white "
                     "rounded comic speech balloon with a smooth outline rises from the lamb's open mouth. "
                     "Inside the balloon, drawn small and simple in the same flat style, there is a picture "
                     "of a small calm wolf with smooth flat fur and its mouth shut. The balloon holds only "
                     "that little picture."),
        17: (("xai",), "The lamb turns its head towards the water flowing away downstream on its own side. A "
                     "big white rounded comic speech balloon with a smooth outline rises from the lamb's "
                     "open mouth. Inside the balloon, drawn small and simple in the same flat style, there "
                     "is a picture of clear blue water running clean over pale stones. The balloon holds "
                     "only that little picture."),
        18: (("xai",), "Close view of the lamb with ears spread wide and head tilted, an innocent puzzled "
                     "look. A big white rounded comic speech balloon with a smooth outline rises from the "
                     "lamb's open mouth. Inside the balloon, drawn small and simple in the same flat style, "
                     "there is a picture of a tiny lamb with its two front hooves turned out wide. The "
                     "balloon holds only that little picture."),
        19: (("llop", "xai"), "The grey wolf stands high up on the left bank where the water comes from; far below "
                     "him on the right bank the small lamb stands at the water's edge. A big white rounded "
                     "comic speech balloon with a smooth outline rises from the lamb's open mouth. Inside "
                     "the balloon, drawn small and simple in the same flat style, there is a picture of a "
                     "side view of a stream running steeply downhill, with a tiny wolf up at the top end and "
                     "a tiny lamb down at the bottom end. The balloon holds only that little picture."),
        20: (("llop",), "The wolf roaring with his mouth wide open, head thrown forward, fur "
                        "bristling, front paws planted on the left bank."),
        21: (("llop",), "The wolf stamps a front paw down into the shallow water, shouting downstream. A big "
                     "white rounded comic speech balloon with a smooth outline rises from the wolf's open "
                     "mouth. Inside the balloon, drawn small and simple in the same flat style, there is a "
                     "picture of thick brown muddy water swirling in a stream. The balloon holds only that "
                     "little picture."),
        22: (("llop", "xai"), "The wolf glares with narrowed eyes, one front paw raised and pointed across the "
                     "stream. A big white rounded comic speech balloon with a smooth outline rises from the "
                     "wolf's open mouth. Inside the balloon, drawn small and simple in the same flat style, "
                     "there is a picture of a tiny lamb with its mouth open bleating at a tiny wolf. The "
                     "balloon holds only that little picture."),
        23: (("llop", "xai"), "The wolf leans right out over the water, teeth bared, demanding an answer. A big white "
                     "rounded comic speech balloon with a smooth outline rises from the wolf's open mouth. "
                     "Inside the balloon, drawn small and simple in the same flat style, there is a picture "
                     "of a tiny lamb bleating while a tiny wolf turns its head away. The balloon holds only "
                     "that little picture."),
        24: (("xai",), "The lamb standing very small on the right bank, head lowered, answering "
                       "quietly."),
        25: (("xai",), "The lamb looks tiny and very young beside a patch of fresh spring flowers. A big white "
                     "rounded comic speech balloon with a smooth outline rises from the lamb's open mouth. "
                     "Inside the balloon, drawn small and simple in the same flat style, there is a picture "
                     "of a newborn lamb lying curled up in the grass. The balloon holds only that little "
                     "picture."),
        26: (("llop",), "The wolf turning his head away dismissively on the left bank, "
                        "unconvinced, one ear flicked back."),
        27: (("llop",), "The wolf points his muzzle far away downstream, blaming somebody out of sight. A big "
                     "white rounded comic speech balloon with a smooth outline rises from the wolf's open "
                     "mouth. Inside the balloon, drawn small and simple in the same flat style, there is a "
                     "picture of two identical little lambs standing side by side. The balloon holds only "
                     "that little picture."),
        28: (("xai",), "Close view of the lamb shaking its head slowly, ears swinging, "
                       "answering."),
        29: (("xai",), "Wide view of the right bank with one single small lamb standing by itself on open "
                     "empty ground. A big white rounded comic speech balloon with a smooth outline rises "
                     "from the lamb's open mouth. Inside the balloon, drawn small and simple in the same "
                     "flat style, there is a picture of one single little lamb alone on an empty patch of "
                     "grass. The balloon holds only that little picture."),
        30: (("llop", "xai"), "The wolf stepping down off the left bank with one front paw in "
                              "the shallow water, coming closer to the lamb."),
        31: (("llop",), "The wolf sweeps a front paw towards the far ochre hills. A big white rounded comic "
                     "speech balloon with a smooth outline rises from the wolf's open mouth. Inside the "
                     "balloon, drawn small and simple in the same flat style, there is a picture of a small "
                     "flock of several sheep standing close together. The balloon holds only that little "
                     "picture."),
        32: (("xai",), "The lamb backs up against a big pale stone on the right bank, both front hooves "
                     "raised, pleading. A big white rounded comic speech balloon with a smooth outline rises "
                     "from the lamb's open mouth. Inside the balloon, drawn small and simple in the same "
                     "flat style, there is a picture of a little lamb standing perfectly still with its four "
                     "hooves together. The balloon holds only that little picture."),
        33: (("xai",), "Close view of the lamb turning its face away from a tuft of green grass at its feet. A "
                     "big white rounded comic speech balloon with a smooth outline rises from the lamb's "
                     "open mouth. Inside the balloon, drawn small and simple in the same flat style, there "
                     "is a picture of a tuft of green grass with a little lamb's head turned away from it. "
                     "The balloon holds only that little picture."),
        34: (("llop", "xai"), "The wolf leaping across the shallow stream towards the lamb, "
                              "water splashing up under him, seen from behind, the lamb "
                              "springing aside with its ears flying."),
        35: (("llop",), "The wolf lying full and satisfied on the left bank, head resting on his "
                        "front paws, eyes half closed, the calm green right bank beyond him."),
        36: ((), "An old Amazigh storyteller in a brown djellaba and a white turban sitting on a "
                 "stone beside the same stream, hands open, telling a story to the quiet "
                 "valley."),
        37: (("llop",), "The wolf's dark silhouette standing on the ridge high above the valley "
                        "at dusk, looking down at the empty stream below."),
    },
)

CONTES = {LLOP_I_XAI.slug: LLOP_I_XAI}
