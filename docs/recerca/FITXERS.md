# Què és cada fitxer del magatzem

*20-11-2026. Si un fitxer no és aquí, és que no s'ha de fer servir.*

## Llegir primer

| | |
|---|---|
| [`LA_NIT_DEL_20.md`](LA_NIT_DEL_20.md) | el resum d'una pàgina |
| [`METODE.md`](METODE.md) | com es treballa i per què; les regles |
| [`DESXIFRAT.md`](DESXIFRAT.md) | el diari de tot, amb els números i les desdites |

## El corpus, per ordre de com es fa

| fitxer | línies | què és |
|---|---|---|
| `text_triat.jsonl` | 15.365 | **el text bo de cada rèplica**: per cada capítol, el que més s'acorda amb l'orella entre el de la fàbrica (720p) i la relectura (1080p). Porta tifinag, àrab, català, temps i d'on surt |
| `acord_triat.jsonl` | 14.426 | una línia per rèplica amb el seu grau (A/B/C) i el CER |
| `ocurrencies_triat.jsonl` | 75.747 | **una línia per paraula sentida**, amb confiança, grau, i la paraula escrita que li correspon per alineació d'ordre |
| `parelles_alineades.jsonl` | 74.761 | l'alineació global paraula a paraula (Needleman-Wunsch) |
| `corpus_grau_a_triat.jsonl` | 2.190 | **el corpus utilitzable**: so + tifinag + significat, les dues lectures d'acord. 2,14 h |
| `corpus_grau_a_{tachelhit,atles,tarifit}.jsonl` | 1.738 / 354 / 98 | el mateix, partit per varietat |

## La varietat de cada episodi

| fitxer | què és |
|---|---|
| `varietats.tsv`, `varietats.json` | **de quina varietat és cada un dels 25 episodis**, amb com s'ha decidit, la part de mencions de la zona, l'acord i les dues marques fonètiques |
| `lexic_diferencial.tsv` (157) | les formes que separen el tachelhit del tarifit, amb el seu pes. *bahra* contra *aṭṭas* |

## Les paraules

| fitxer | línies | què és |
|---|---|---|
| `index_paraules_tachelhit.tsv` | 18.872 | **l'índex per paraula**: vegades, vegades amb acord de l'ull, boques i confiança. 490 formes al nucli |
| `index_paraules_atles.tsv` | 5.303 | el mateix per a l'Atles central (80 al nucli) |
| `index_paraules_tarifit.tsv` | 17.573 | el mateix per al tarifit (91 al nucli, i es sap per què són pocs) |
| `index_paraules.tsv` | 39.274 | el de tots barrejats. **No el feu servir**: barreja tres llengües |
| `variants.tsv` (97) | | paraules escrites amb dues formes sentides, cada una acordada |
| `variacio.tsv` (187) | | les anteriors amb l'escapçament separat de la variació, i el canvi de consonant |
| `lexic_ircam_gramatical.tsv` (732) | | el lèxic de l'IRCAM amb les seves formes |

## Fitxers vells, que es guarden però no es fan servir

| fitxer | per què no |
|---|---|
| `acord_26.jsonl`, `ocurrencies_26.jsonl` | fets amb el text de la fàbrica (720p) i amb l'aparellament per veïnatge, que és cec a l'ordre |
| `corpus_grau_a.jsonl` (1.560) | el substitueix `corpus_grau_a_triat.jsonl` (2.190) |
| `estandard_dialecte.jsonl` (181) | **artefactes d'alineació.** Vegeu `DESXIFRAT.md` §12.7 |
| `norma_parla.tsv`, `norma_parla_ancorada.tsv` | el mateix: les 8 que sobrevivien eren la frase *tutlayt tamaziġt* desplaçada un lloc |
| `acord.jsonl`, `ocurrencies.jsonl` | de la primera prova, de només un capítol |
| `rellegit.json` | buit |

## Les carpetes

| | |
|---|---|
| `rellegit_bo/` | la relectura de 1080p de cada capítol, una per fitxer |
| `prova_adaptadors/` | els 639 talls i el que hi senten `shi`, `kab`, `taq`, `ara`, el rifeny i el Whisper |
| `prova_kab/` | els 3.515 talls dels episodis bons: `kab` contra `shi` |
| `prova_dolents/` | els 3.517 talls dels episodis rifenys, pujats i sense córrer |
| `prova_rif/` | la passada del model rifeny a Kaggle (idèntica a la local) |
| `ronda/` | la ronda d'entrenament: `dades/rows.json` i els talls |
| `vrif/` | l'entorn de Python amb numpy 2 per als models nous (el del backend porta numpy 1.26 perquè és el que desplega a Render) |

## Del matí del 20 (validació fora del SNRT)

| fitxer | què fa |
|---|---|
| `valida_contra_veritat.py` | l'acord d'esquelet contra veritat humana a les quatre proves que en tenen |
| `que_compra_el_grau_a.py` | precisió i record del filtre **per paraula**, contra veritat humana |
| `el_llindar_per_frase.py` | el mateix **per frase**, que és com es tria el train (§20.4) |
| `el_lexic_fora_del_snrt.py` | el lèxic de varietats aplicat al manifest de la biblioteca |
| `el_lexic_contra_latzar.py` | la prova nul·la del lèxic: 200 repartiments a l'atzar |
| `consens_de_tres_orelles.py` | el pseudo-transcrit rifeny de consens → `corpus_consens_rifeny.jsonl` |
| `EL_MATI_DEL_20.md` | el resum d'una pàgina |

**Vell des del matí del 20:** el número de «4.492 rèpliques (5,2 h)» de `LA_NIT_DEL_20.md` és una
extrapolació de dues orelles; el bo és 2.824 rèpliques i 3,56 h (§20.5).
