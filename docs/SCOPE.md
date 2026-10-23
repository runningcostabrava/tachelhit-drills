# Abast de Tamazight Drills

Aprovat el 22-10-2026. Qualsevol issue o PR que surti d'aquí ha de poder-se llegir contra aquest
document: si no hi cau a dins, primer es canvia l'abast.

## Què és

Una biblioteca viva d'amazic de l'Atles central (i tachelhit) per a catalanoparlants: frases dites
per parlants de debò, amb la seva veu, la seva escriptura i el seu poble, i un curs de gramàtica
fet **només** amb aquestes frases i amb el compendi d'amazic.cat.

No és un diccionari, ni un traductor automàtic, ni un curs genèric d'«amazic» sense procedència.

## Per a qui

| | |
|---|---|
| qui aprèn | adult catalanoparlant, no lingüista: un viatger encuriosit, la parella d'algú que el parla |
| qui el parla | Halima i Driss (Aït Mraw, Boutharar, Azilal), els reculls de Beni Mellal i d'Azilal, i qualsevol parlant que hi vulgui posar la veu |
| qui administra | manté la biblioteca, decideix què hi entra i corregeix el que cal |

## Què ha de fer

1. **Guardar** frases amb el seu significat en català, la veu, la imatge, la varietat i el lloc.
2. **Recollir veus**: demanar-ne, gravar-ne, i dir sempre si qui parla ho fa de tota la vida o
   l'està aprenent.
3. **Ensenyar**: 23 unitats de gramàtica fetes amb exemples de la biblioteca, cada frase amb el
   tros ensenyat marcat, la lectura paraula per paraula i el «per què és aquí», i un nivell «a
   fons» per unitat.
4. **Practicar**: tests per unitat i repàs espaiat.
5. **Capturar** material nou (vídeos, cançons, classes) i convertir-lo en frases revisades per una
   persona.
6. **Funcionar** al web i al mòbil, i també sense connexió.

## On s'atura

- **El text d'un parlant és seu.** Cap màquina el reescriu: la sortida automàtica va als camps
  `*_suggested` i la decideix una persona.
- **Res de veus sintètiques en amazic al curs.** I el so sintètic en català no es fa passar mai
  per amazic: si una frase no té veu amazic, no sona.
- **La varietat importa.** Cada frase porta d'on és; no es barregen varietats sense dir-ho.
- **Una línia cantada surt del vídeo.** La lletra es pren del text sobreimprès o dels subtítols, i
  d'enlloc més: el transcriptor no sap cantar, i quan s'hi posa torna frases que semblen frases i
  no ho són (decisió de l'amo, 23-10-2026). Una cançó sense lletra al vídeo es queda sense text
  fins que algú la hi posi a mà. `POST /drills/{id}/retranscribe` ho refusa.
- **Una veu diu qui és.** Una gravació de qui aprèn hi té lloc, però queda marcada: no pot passar
  per model de pronúncia.
- **Material exclòs**: res gravat en càmera de «Tamazight For All»; cap drill etiquetat irlandès
  entra al curs.
- **El recull de Beni Mellal s'ensenya, però no es publica.** Va etiquetat «private», i això vol
  dir que **no es redistribueix** — no surt en cap exportació ni corpus. Sí que es pot fer servir
  com a exemple dins de l'app: l'amo en té permís (decisió de 23-10-2026). Són dos terços de la
  biblioteca, i la regla d'abans es llegia com si fossin material exclòs del curs, que no ho són.
- **Les nostres veus van davant.** Quan hi ha més d'una frase que serveix, s'ensenya primer la
  que diu la Halima o en Driss: porten una persona que el projecte coneix, amb el seu poble i la
  seva varietat. Són 69 frases de 3.390, i sense aquesta regla no es veurien mai.
- **El curs cita només** la nostra biblioteca i el compendi d'amazic.cat.
- **El Mètode segueix el manual d'El Mountassir tan a prop com calgui**: explicacions,
  estructura, diàlegs i lèxic. El que es canvia és el que la **nostra varietat** diu d'una altra
  manera — el manual és del Souss i nosaltres ensenyem Atles central, i una forma correcta allà
  pot ser falsa aquí. Això es mira frase per frase; la resta es queda com és
  ([ADR 0004](adr/0004-el-metode-parteix-del-llibre.md), que substitueix
  l'[ADR 0003](adr/0003-el-metode-pren-el-pla-mai-les-paraules.md)).
- **La veu és sempre nostra.** El llibre pot donar el text; qui el diu és sempre una persona que
  el projecte coneix. Cap veu sintètica es fa passar per amazic.
- **Això no es ven mai.** L'app no tindrà ús comercial (decisió de l'amo, 22-10-2026). No és una
  conseqüència de les llicències: és el projecte. De retruc, el material CC BY-NC —el lèxic
  d'IRCAM— hi pot ser; vegeu [CREDITS.md](CREDITS.md).

## Com se sap que va bé

- cada frase que una lliçó mostra té el tros marcat **o** una nota que diu què hi fa;
- cap unitat es queda sense citar els tres reculls;
- el so d'una frase és sempre amazic, o no n'hi ha;
- les proves passen **a GitHub** abans de fusionar res;
- el que està bloquejat per qui administra es veu: etiqueta `blocked-on-owner`.
