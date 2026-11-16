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

## Resultats sobre tot el corpus (16-11; nucli `zouhir-lector-contra-pista-humana`, CPU, 2 h)

El mateix lector de sempre (`mms-1b-all` + `adaptador_shi_ric.pt`, el que serveix al Space) sobre
els **2.164 rètols** dels 50 vídeos, tallats del so a ±0,1 s, descodificat de quatre maneres
(`tools/lm/kaggle/zouhir_lector_contra_pista.py`); el CER/WER a casa amb `h3_puntua` via
`zouhir_de_kaggle.py` + `zouhir_resum.py` → `resum.md`. S'exclouen 50 rètols de pantalla, 144 en
lletres àrabs i 43 en altra grafia (vegeu més avall): queden **1.927 rètols parlats**.

**Zouhir Amazigh (33 vídeos, 1.128 rètols, 68 min):**

| lector | CER | WER | CER plegat |
|---|---|---|---|
| greedy | 0,297 | 0,842 | 0,272 |
| feix sol (64) | **0,293** | **0,823** | 0,269 |
| feix + bigrames biblioteca α 0,1 | 0,294 | 0,833 | 0,270 |
| feix + bigrames α 0,15 (el del Space) | 0,295 | 0,826 | 0,271 |

Greedy → feix: −0,004 [−0,005, −0,003] (bootstrap 1114, 329 milloren / 192 empitjoren): real
i petit. Greedy → feix amb lèxic: −0,003 [−0,006, +0,001]: **el model de llengua de la
biblioteca no fa res aquí**, ni a α 0,1 ni a 0,15. És el que s'esperava: els bigrames són del
taixelhit dels contes i Zouhir parla d'ADN, bitcoin i ozó en amazic estàndard. El pes del Space
(α 0,15) es queda com és: a TFA ajuda el WER i aquí no fa mal. Millors vídeos (feix): El Niño
0,215, agricultura 0,223, Alzheimer 0,224, cabilencs 0,228; pitjors: les «meva ciutat» (Fes 0,37,
Rabat 0,41, Laayoune 0,44: noms propis i música), patrimoni 0,43 i el cantat 0,50. El Space
(`transcribe_mms`, 690 rètols de 18 vídeos) dóna 0,308: el mateix model, dins del soroll.

**BerberFreeQuranEducation (17 vídeos, 799 rètols nets, 34 min): CER 0,57, WER 0,97.** Molt
pitjor, i no només per l'oïda. Mirat rètol a rètol, la pista «af» d'aquest canal és tres coses
alhora:

| què hi ha a la pista | rètols | exemple |
|---|---|---|
| amazic en tifinag estàndard, ben alineat (ROl7INibBdg, G_VEuI0veIk, f3bUnaPrGYY…) | ~600 | `ar tlmadm attirim ingratun` → lector `ar ttlmad mad tirin ingratun` |
| **amazic en lletres àrabs** (tot C6IB4oLQRt8, 80; trossos a 4SwUf6I419o, G_VEuI0veIk) + versos de l'Alcorà en àrab | 144 | `أدور إغال كرا` → lector `adur iġal krag`: la veu és taixelhit i el lector l'encerta; la veritat no es pot comparar |
| cabilenc o rifeny amb lletres fora de l'IRCAM (ⵝ ⴺ ⵒ: UdGldeTMLSc, part d'1NypFO7bIvA) | 43 | `axxam`, `ulaš` |
| **temps desplaçats** un o dos rètols respecte del so (DPJrHx2meXE 88, QiR0qrnYV0g, stQPF2-LrB4) | ~190 | el lector diu al rètol 11,2 s el text del rètol 6,8 s |

Sense els desplaçats i el cabilenc, els 613 rètols que queden donen CER 0,477: predicació amb
diversos parlants, cites en àrab enmig de la frase i ritme de sermó. Aquest canal val com a
veritat **només després de netejar-lo**: fora l'àrab (el transliterador no llegeix grafia àrab;
`to_forms` deixa l'àrab tal qual, i per això el CER d'aquells rètols passava d'1), fora les
altres varietats, i cada vídeo amb els temps comprovats.

**Conseqüència per a H4.** El nucli del 15-11 va entrenar amb tot el canal menys 3 vídeos: entre
els seus 1.563 rètols hi havia **~120 amb veritat en lletres àrabs, ~33 en grafia cabilenca i ~86
desplaçats** (DPJrHx2meXE), un 15 % de brossa. Dos dels tres vídeos «fora» de l'Alcorà
(1NypFO7bIvA, 4SwUf6I419o) són dels contaminats, així que el 0,510 → 0,473 d'«Alcorà fora» no
vol dir gaire. La millora de TFA-226 (0,187 → 0,171) i de Zouhir fora (0,268 → 0,197) es van
mesurar sobre veritat neta i es mantenen. **H4b**: el mateix nucli amb `mena == "parlat"` i sense
DPJrHx2meXE/QiR0qrnYV0g/stQPF2-LrB4: menys rètols i probablement més guany. `zouhir_resum.py`
ja marca la mena a `veritat_zouhir.json`; el nucli l'ha de llegir.

**El corpus:** `veritat_zouhir.json` (2.164 rètols: so, temps, tifinag, llatí, en/ar/fr, mena,
canal); 947 amb les tres traduccions. És l'entrada d'`induccio.py` amb `[en|ar|fr]` i d'H4b.
