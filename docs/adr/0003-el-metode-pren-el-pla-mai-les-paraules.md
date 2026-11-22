# ADR 0003: El Mètode pren el pla, mai les paraules

- **Estat:** acceptada
- **Data:** 2026-10-23
- **Decideix:** l'amo del projecte
- **Issue:** —

## El problema

Volem una àrea nova, **El Mètode**: un curs que porti algú de zero a poder dir alguna cosa al
mercat, amb el recorregut provat que té un bon manual. El recorregut el tenim davant:

> Abdallah El Mountassir, *Metodo di tachelhit. Lingua amazigh (berbera) del sud del Marocco*,
> Università degli Studi di Napoli «L'Orientale», 2017 — traducció italiana de *Méthode de
> Tachelhit. Langue amazighe (berbère) du sud du Maroc*, L'Asiathèque, Collection Langues &
> Mondes, París, **2009**.

Deu lliçons, cadascuna amb una situació (la botiga, el metge, el viatge), els punts de gramàtica
que aquella situació demana, i el vocabulari del camp. És un bon pla i és feina d'algú.

Dues coses ens obliguen a decidir abans de tocar res:

1. **És obra protegida.** La pàgina 3 de l'edició italiana diu que la traducció es va fer *«per
   gentile concessione dell'autore e di L'Asiathèque»*: fins i tot una edició acadèmica derivada
   va demanar permís a l'autor i a l'editorial.
2. **Ja tenim una regla que hi xoca de ple.** [SCOPE.md](../SCOPE.md) diu que *el curs cita només
   la nostra biblioteca i el compendi d'amazic.cat*. Si el Mètode comença a portar frases d'una
   altra banda, aquella regla deixa de voler dir res.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| Traduir-lo al català | ràpid; el curs queda fet de seguida | és una traducció d'obra protegida sense permís. I no serveix: el llibre és tachelhit del Souss i les nostres veus són de l'Atles central, així que les frases traduïdes no les diria cap dels nostres parlants |
| Demanar permís i després traduir | queda tot clar; és el camí que va fer la italiana | depèn d'una resposta que pot trigar o no arribar; i segueix sense resoldre que les frases no són de ningú que coneguem |
| **Prendre'n el pla i escriure-ho tot nosaltres** | el pla d'un curs —quina situació va abans de quina, quina gramàtica demana cadascuna— són fets sobre com s'ensenya una llengua, i no són de ningú. I obliga a omplir cada capítol amb frases **nostres**, que és el que volem de totes passades | més feina; i un capítol pot quedar curt fins que no hàgim recollit el que li falta |
| No fer-ho | cap risc | perdem el recorregut, que és justament el que no sabem fabricar de zero |

## La decisió

**El Mètode pren el pla del llibre i no en pren ni una paraula.**

Concretament, el que es pren de cada lliçó és una fitxa de quatre caselles, escrita per nosaltres
llegint-la: quines **funcions** comunicatives ensenya, quina **gramàtica** demana, de quins
**camps** de vocabulari va, i quins **papers** hi parlen.

I no s'hi pren: cap frase seva, cap diàleg seu, cap explicació seva ni traduïda, cap entrada del
seu lèxic. Ni a la base de dades, ni com a esborrany, ni «de moment».

Tot el text del Mètode —explicacions, exemples, diàlegs, vocabulari— surt de la nostra biblioteca
i del compendi d'amazic.cat, exactament com el curs de gramàtica. El que una fitxa demana i la
biblioteca no té **no es copia**: es converteix en una frase catalana sense amazic que va a la cua
de Posa-hi veu, perquè algú ens digui com ho diu ell.

Això queda escrit a SCOPE.md, i cada capítol porta la citació del llibre al peu.

## Què en ve al darrere

- **Els capítols neixen incomplets, i es veu.** La barra de cada capítol a l'índex no és el teu
  progrés: és quant d'aquell capítol tenim recollit. El capítol 10 (la cuina) començarà gairebé
  buit. Això no és un defecte de la implementació; és la veritat sobre la biblioteca, i és
  l'argument per anar a gravar.
- **Dues varietats conviuran a la mateixa targeta.** El llibre és del Souss i les nostres veus són
  de l'Atles central. Quan tinguem les dues maneres de dir una cosa, s'ensenyen de costat amb
  l'etiqueta de cadascuna, perquè SCOPE.md diu que no es barregen sense dir-ho. Una targeta amb
  només la columna de l'Atles és correcta; una targeta que no digui de quina varietat és, no.
- **Escriure a l'autor segueix sent bona idea**, i no ho impedeix res d'això. Amb permís explícit
  l'àrea pot ser molt més rica; sense, el Mètode funciona igual. El que no farem és començar
  copiant i demanar perdó després.
- **Costa més.** Un capítol no es pot escriure en una tarda copiant: s'ha de triar entre el que
  tenim, escriure l'explicació, i deixar apuntat el que falta.
