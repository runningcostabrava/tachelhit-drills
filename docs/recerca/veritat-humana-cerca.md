# Hi ha més veritat humana en amazic a YouTube? (16-11-2026)

L'única millora mesurada del lector (H4/H4b) ha vingut de rètols transcrits a mà (Zouhir Amazigh,
BerberFreeQuranEducation). Un peó ha buscat si n'hi ha més: 43 cerques de YouTube amb `yt-dlp`
(termes en tifinag, llatí, àrab i francès), 1.159 vídeos i 531 canals trobats, 92 canals plausibles
mirats vídeo a vídeo (148 vídeos, només metadades, cap descàrrega llevat de dues mostres VTT), més
Wikitongues, Amara, Jesus Film, Internet Archive, Vimeo, Hugging Face, YODAS i CoTaSS pel web.
Informe sencer i catàleg: `Veus-tachelhit\_escoltats\veritat\cerca_nova\`.

**Resultat: cap canal nou de parla amaziga marroquina té pista de subtítols humana en amazic.** L'únic
amb pista «Tamazight» (DJ. Billy, 104 vídeos) és cabilenc amb música generada per màquina.

El que sí que hi ha:

| què | on | quant | com | llicència |
|---|---|---|---|---|
| parla taixelhit llegida (salms, evangeli) amb el text cremat a la imatge | StoryChannel | 64 min | OCR o demanar els guions | Standard YouTube |
| lletres de cançons en taixelhit llatí cremades, amb en/fr/ar | Amarg Translation (32 cançons), TranslatedAmazighSongs, Amazigh land, AMAZIGH lyrics, Tyope | ≈ 3,5 h | demanar els fitxers de lletres | Standard YouTube |
| lectures escolars en tifinag cremat | 5 canals | ≈ 30 min | OCR | Standard YouTube |
| parla taixelhit espontània amb subtítols anglesos humans | Wikitongues (Jamal, Abderrahman, Lahoucine) | ≈ 7 min, ≈ 100 rètols | ja usable amb atribució; demanar transcripció via Amara | CC BY-SA 4.0 |
| pel·lícules taixelhit amb àrab cremat | Ayouz Vision i d'altres | hores | ja ho fa el dataset de sota | Standard YouTube |
| 15,5 h de pel·lícules taixelhit, 20.344 talls, text àrab per OCR | HF `SoufianeDahimi/Tamazight-ASR-Dataset-v2` | 15,5 h | parells veu amaziga + àrab, sense transcripció amaziga | Apache-2.0 el text; l'àudio és de les pel·lícules |
| corpus de parla semiespontània taixelhit transcrit, traduït i glossat (Agadir) | CoTaSS, Universitat de Colònia | no publicat | **demanar accés**: és veritat humana acadèmica | no declarada |
| 190 vídeos doblats al taixelhit, «JESUS» amb 64 pistes de subtítols | Jesus Film Project | hores | comprovar si alguna pista és taixelhit | pròpia del projecte |

Filtre negatiu útil: a gairebé tots els vídeos amazics YouTube genera automàtiques «ar-orig» (pren
l'amazic per àrab); on hi ha `ar-orig` no hi ha mai pista amaziga. Descartats: rifeny, cabilenc i
libi (Ilaria, Awal Lyrics, Likoul, Lmed, Chawiland, Madghis Madi), 64 canals sense cap pista, música
sense lletra.

El que se'n treu: (1) el filó de YouTube amb pista humana és el que ja tenim; més veritat vindrà de
**demanar-la** (CoTaSS, els guions de StoryChannel, les lletres d'Amarg Translation, la transcripció
de Wikitongues) o d'**OCR del text cremat** (2.000-3.000 línies possibles, cantades o llegides, no
espontànies). (2) Els autors que ja col·laboren (Zouhir, TFA, aslmdtv) poden exportar més `.srt`:
cada 1.000 rètols nets val més que qualsevol model nou. Tot és material de tercers: catalogat, res a
la biblioteca ni al model sense permís.

## CoTaSS: l'extracte públic contra el nostre lector (16-11, nit)

El CoTaSS (Corpus of Tashlhiyt Semi-spontaneous Speech, Universitat de Colònia; Bruggeman i Roettger
2017, grup de Martine Grice) són 10 converses de «tasca del mapa» entre parlants d'Agadir, 39 minuts,
transcrites, glossades i traduïdes a l'anglès línia a línia. Les transcripcions (TextGrids i text) es
baixen lliurement; el so es demana per correu amb un acord d'ús signat. L'adreça del web
(`cotasscorpus@gmail.com`) rebota: s'ha escrit als autors (Roettger, avui a Oslo; Grice, a Colònia).
Fitxers a `Veus-tachelhit\_escoltats\cotass\`.

L'extracte públic (29 s de la conversa 1m_2m, estèreo, 18 frases del TextGrid) passat pel Space amb
H4b, canal a canal i quedant-se el millor: **CER 0,80** (`cotass_mostra.json`). Res a veure amb el
0,17 de TFA ni el 0,20 de Zouhir. Les frases són curtes («iyyih», «aẓlmaḍ», «tama n»), amb
encavalcaments, vacil·lacions («[eeh]»), i el lector hi treu brossa o res. El que diu: **el nostre
lector sap parla llegida i subtitulada, no conversa espontània**; el CoTaSS és just la prova que no
teníem, i quan arribin els 39 minuts és el primer test net de parla espontània. Nota: la referència
porta guions de clític (`t-ggiz-t`) i anotacions entre claudàtors que es treuen abans de comparar.
