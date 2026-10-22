# ADR 0002: Una pràctica és una seqüència de passos

- **Estat:** acceptat
- **Data:** 2026-10-22
- **Decideix:** el propietari del projecte
- **Issue:** #199

## El problema

Una pràctica, avui, és una fila a `tests`: títol, tipus de pregunta, percentatge de pistes, nota
per aprovar, i `drill_ids` — una cadena de números. Se'n fan de quatre llocs (una unitat de
gramàtica, una selecció a Drills, el formulari, i «del que has fallat») i, un cop feta, no se'n
pot canviar el contingut: el formulari edita el títol i les pistes, no les frases.

A producció n'hi ha **30**, amb 82 frases de mitjana i una de 511. Tenen títols de debò —les
preguntes amb «is, ma, mani…», les faules, les cançons—, o sigui que algú les ha pensades. I cap
no es pot tocar.

Hi ha dues coses més que xoquen:

- **Cap pràctica té amo.** No hi ha columna que digui qui l'ha feta, així que «les meves llistes»
  no es pot calcular. La pàgina de Pràctica obre amb els talls automàtics (per dia, per tema, per
  unitat) i les llistes fetes a mà no hi surten.
- **Hi ha dos reproductors que no es toquen**: `/tests/sessio` juga un *filtre* (escolta, parla,
  auto) i no desa res; `/tests/:id` passa un qüestionari. El que es fa servir cada dia —el
  primer— no és una pràctica.

I el material que tenim i no fem servir per practicar: les veus dels parlants, les imatges, el
tros marcat de cada lliçó, 13.000 glosses paraula per paraula, el tifinag, les versions d'una
mateixa frase, i la pronúncia puntuada.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| deixar-ho com és | zero feina | no es pot editar res; «les meves» impossible |
| passos en un JSON dins de `tests` | cap taula nova, com les lliçons de gramàtica | mal de comptar i de mesurar pas a pas; tot o res en cada desament |
| **taula `practice_steps`** | es reordena, es compta, es pot saber què s'ha respost a cada pas | cal migrar les 30 d'ara |

## La decisió

Una pràctica passa a ser una **seqüència ordenada de passos**, un pas per fila a `practice_steps`,
i cada pas porta la seva pròpia eina: escoltar i triar, escriure el que sents, dir-ho (puntuat),
mirar i dir-ho, omplir el buit, paraula per paraula, tifinag o llatí, triar la versió bona, una
**nota** que ensenya, i **gravar** la frase per a la biblioteca.

La fila de `tests` es queda com a capçalera de la pràctica (títol, descripció, qui l'ha feta, si
és compartida) i guanya `created_by_user_id`. Les **30 pràctiques d'ara es converteixen totes**:
cada frase es torna un pas, i l'eina surt del tipus que tenien (`text_input` → escriure-ho,
`audio` → escoltar i triar).

Que un pas pugui ser **gravar** és el que canvia per a què serveix l'eina: la mateixa pràctica que
ensenya pot ser la sessió de veu que se li passa a l'Halima o en Driss.

## Què en ve al darrere

- Una pràctica de 511 frases passa a ser 511 files. No és cap problema per a Postgres, però vol
  dir que l'editor ha de carregar i desar per trossos si algun dia n'hi ha de molt grosses.
- `question_type`, `hint_level` i companyia deixen de manar sobre tota la llista: passen a ser el
  valor per defecte de cada pas nou. No s'esborren, per no trencar el que juga avui.
- La conversió s'ha de poder tornar a executar sense duplicar res: es fa només per a les
  pràctiques que encara no tenen passos.
- Els permisos del #184 valen aquí: una pràctica la canvia qui la va fer, o qui administra.
- `/tests/sessio` (jugar un filtre) es queda com està: serveix per escoltar un tall sense desar
  res. El que es desa, ara, són els passos.
- Les estadístiques per pas obren la porta a saber **quina eina** costa més, no només quina frase.
