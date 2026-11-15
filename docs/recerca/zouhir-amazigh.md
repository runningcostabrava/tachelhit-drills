# Canal «Zouhir Amazigh» (i BerberFreeQuranEducation): pista amaziga humana alineada amb tres traduccions

Issue: #620. Enllaços d'en Pablo (15-11-2026): «this are some translated videos with
transcriptions, they might be really useful». Material de tercers: es cataloga i es mesura; **res
no entra a la biblioteca ni al model servit sense permís escrit de l'autor** (regla de
`tamazight-for-all.md`). Dades: `C:\Users\josep\Veus-tachelhit\_escoltats\zouhir\` (wav 16 kHz
mono, vtt de cada pista, `mesura/<id>.json`, `veritat_zouhir.json`).

## El truc que amaga la pista

YouTube no té codi de llengua per a l'amazic. Els autors pengen la pista en tifinag sota el
primer codi que troben: Zouhir sota **«ak»** (àkan), BerberFreeQuranEducation sota **«af»**
(afrikaans) i en un vídeo **«wo»** (wòlof). Cap cerca per llengua la troba; s'ha de llistar
`subtitles` vídeo a vídeo (`yt-dlp -j`) i mirar-se la pista. Les quatre pistes (amazic, en, ar,
fr) tenen **els mateixos temps**: corpus paral·lel rètol a rètol.

## El catàleg (15-11, `yt-dlp`, pista a pista)

**Zouhir Amazigh** (`UChhn0zW3qcFcly8ViWTt6MA`): 105 vídeos, 380 min, 13 llistes temàtiques
(història, economia, salut, aprenentatge, la meva ciutat, cultura, contes, felicitacions,
religió, ciència i tecnologia, el temps, espai). Amazic estàndard (grafia IRCAM), veu narrada
d'un sol parlant, registre culte (ciència, història).

| pistes humanes | vídeos | minuts |
|---|---|---|
| amazic + en + ar + fr | 25 | 92,7 |
| amazic + en + ar | 8 | 19,9 |
| només ar, o cap | 72 | 268 |

**BerberFreeQuranEducation** (`UCmlGmHeQOUL7AhYFmGHu8kw`): 35 vídeos, 82 min; 16 amb pista
amaziga («af», 40 min), 1 més sota «wo»; només 2 porten àrab. Predicació en amazic, diversos
parlants (ⴰⵙⵍⵎⴰⴷ ⵄⴰⵍⵉ ⵀⵉⴷⴰⵢⴰⵜ, ⵢⵓⵛⴰⵄ ⵉⵠⴰⵏⵥ): veritat de transcripció sense traducció.

`5YGZ_OGmcGA` (Zouhir, lliçó de les lletres tifinag): només subtítol anglès.

## La primera mesura (RzG-vYOY2L8, «Imazighen i l'agricultura», 40 rètols)

`tools/lm/zouhir_mesura.py`: cada rètol tallat del so (±0,1 s), passat pel lector del Space i
comparat amb la pista humana transliterada (`transliteration.to_forms`), amb el mateix codi de
puntuació que H3 (`h3_puntua`).

| lector | CER | WER | WER només de frontera |
|---|---|---|---|
| greedy `/transcribe_mms` | 0,229 | 0,781 | 0,035 |
| feix + lèxic `/transcribe_mms_lm` | **0,217** | **0,711** | 0,035 |

Mateix nivell que sobre els contes de Tamazight For All (CER 0,207 greedy / 0,198 feix): la
varietat estàndard narrada la llegim igual que el taixelhit dels contes, i el feix amb el lèxic
hi guanya el mateix. Errors: ɣ→ġ (plec de sempre), talls de paraula (`gumzw arus` per
`g umzwaru s`), lèxic culte fora del diccionari (`tettawẓlay`, `ajɣrafi`, `tsqqnt`).

## Què en fem (per ordre)

1. **Test net gran.** ~1.000 rètols amb veritat humana (fins ara 226) per jutjar qualsevol
   canvi del lector: model de llengua, pesos, plec.
2. **H4 amb transcripció humana.** 112 min de so transcrit per afinar l'adaptador `shi`. Varietat
   estàndard: l'afinament es mesura **també** sobre els 226 versos de TFA perquè no empitjori
   el taixelhit.
3. **Inducció de glosses amb tres llengües** (en + ar + fr del mateix rètol: dues fonts de franc
   per la regla del creuament) i **lèxic culte** cap a `LEXIC_VALIDAT` amb procedència.

## Resultats sobre tot el corpus

*(s'omple quan acaba la mesura dels 33 vídeos; `tools/lm/zouhir_resum.py` → `resum.md`)*
