# El tifinag estàndard i la parla dialectal: què hi podem aprendre (17-11-2026)

Idea d'en Pablo, 17-11-2026: els subtítols de Tamazight TV s'escriuen en una **norma** (la de l'IRCAM) i
la veu dels actors és **dialectal**. Si l'estandardització és un fenomen sistemàtic, el nostre transcriptor,
que sent el dialecte, i el text de la cadena, que el diu en estàndard, **s'expliquen mútuament**: de la seva
comparació surten els patrons. Aquest document fixa la hipòtesi, les dades, el mètode i els riscos, perquè
un peó el pugui executar sense decidir res de fons.

## 1. La hipòtesi, dita amb precisió

- **H-E1.** El text tifinag de la SNRT està regularitzat a la norma de l'IRCAM: ortografia, formes verbals i
  pronoms normalitzats, i vocabulari **«estàndard»**, més literari que el de la parla. Indicis ja vistos:
  a «Illy» (sèrie marcada «Atles» per la cadena) el text és taixelhit estàndard (`rad`, `iɣ`, `ɣas`, cap
  `da`/`mš`); al control, Beni Mellal i el Souss només comparteixen un 14 % de formes, la distància és en
  bona part ortogràfica (`illy_01/INFORME.md`, `docs/recerca/tamazight-tv.md`).
- **H-E2.** La diferència entre el que es diu i el que s'escriu **té estructura**: no és soroll, són
  correspondències regulars (futur `rad` escrit i `ad`/`da` dit; condicional `iɣ` escrit i `mš` dit;
  assimilacions, caiguda de vocals, pronoms enclítics). Cada correspondència es pot comptar.
- **H-E3.** Si es té una taula estàndard ↔ dialecte, es poden fer tres coses que avui no existeixen:
  (a) un **traductor** que entén les dues formes; (b) un **transcriptor** que escrigui en norma a partir
  de la veu dialectal; (c) una **mesura de varietat** d'un vídeo sense preguntar a ningú (quina proporció de
  correspondències són les de la teva zona).

## 2. Les dades que ja tenim

| | què és | quant |
|---|---|---|
| Text tifinag de la cadena | forma **estàndard**, ja llegit amb el lector propi (CER ≈ 0,1–0,2 %) | 1.000 rèpliques de l'entrevista de Tadfi n Tskla, 306 d'Illy; 31 capítols de Tadfi en curs a l'ECS |
| So de cada rèplica | forma **dialectal/parlada** (talls wav 16 kHz alineats amb el text) | els mateixos |
| Transcriptor | MMS amb l'adaptador shi (CER 0,15 a CV zgh net; `docs/recerca/`) | el que hi ha |
| Parlants de referència | Aït Mraw, Beni Mellal, Souss (biblioteca, `cataleg_prod.json`) | milers de frases |
| Lèxics | amazic.cat, Viccionari zgh, Oulhaj, Anamek (catalogat) | per validar formes |

## 3. El mètode

1. **Parelles.** Per a cada rèplica apta (§5 de l'especificació), `tifinag` (norma) i `so`.
2. **Transcripció.** El transcriptor escriu el que sent en tifinag (o en llatí i es converteix amb
   `backend/transliteration.py`), sense plegar lletres (regla `tachelhit-asr-plegat-esborrava-lletres`).
3. **Alineació.** Alineació de les dues cadenes a nivell de paraula i després de caràcter (distància
   d'edició amb pesos per classes de lletres); es queden només les parelles de paraules **emparellades amb
   seguretat** (mateixa posició, context compartit de ≥ 2 paraules iguals).
4. **Taula de correspondències.** Per a cada parell (forma estàndard, forma dita) un recompte, i la regla
   que se'n dedueix (per paraules gramaticals primer: partícules, pronoms, formes de verb freqüents).
5. **Control.** El mateix pas amb **parlants dels quals sabem la varietat** (Aït Mraw / Beni Mellal): ha de
   donar correspondències diferents a les del Souss; si no, el mètode no discrimina.
6. **Sortida.** `TD_TV/_varietat/correspondencies.jsonl` i una taula llegible `CORRESPONDENCIES.md` amb les
   cent correspondències més freqüents, cada una amb exemples i enllaç al segon del vídeo.

## 4. Riscos i què no s'ha de conclure

- El **subtítol no sempre és transcripció literal** (a «Illy» les dues línies no es corresponen paraula per
  paraula). Només s'usen parelles amb alineació segura.
- El **transcriptor és imperfecte** (CER 0,15): una correspondència només es dona per bona si es repeteix en
  molts capítols i parlants diferents, no per una sola aparició.
- Aquesta hipòtesi **no està provada**: és una proposta. Es dona per confirmada quan (a) el control del punt 5
  discrimina i (b) un parlant de referència confirma una mostra de 20 correspondències.
- Res d'això es publica ni va a l'app: la taula és un instrument de recerca (permís SNRT del 17-11-2026:
  recerca sí, republicar no).

## 5. Prerequisits i ordre

1. Tifinag de la cadena a escala (fàbrica sense àrab a l'ECS: **en curs**, 31 capítols de Tadfi n Tskla).
2. Transcriptor millor (afinar MMS amb so ↔ tifinag, **pas 6 del pla**); amb el que hi ha ja es pot fer una
   primera passada de prova sobre 20 rèpliques.
3. Taula de correspondències (aquest document).
4. Traductor i transcriptor que l'usen.

Relacionat: `tamazight-tv-pla.md`, `tamazight-tv-fabrica-especificacio.md` (§6.1, §6.2), `ocr-tifinag-snrt.md`.
