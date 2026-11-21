# Tamazight TV (SNRT, canal 8): sèries amb subtítols cremats en tifinag i àrab (mirat el 17-11-2026)

En Pablo va passar l'Instagram `tamazight.officiel` (32.400 seguidors, 820 publicacions): és el compte
oficial de **Tamazight TV**, la cadena generalista amaziga de la SNRT (televisió pública marroquina).
L'Instagram en si són extractes d'un minut; el que importa és el canal de YouTube de la cadena,
`youtube.com/channel/UCZ97maPQK1vncXInrHeTEAg` (@TamazightTV.Officiel), que penja la programació
sencera. Llista plana del 17-11 a `Veus-tachelhit\_escoltats\tamazight_tv_videos.txt`.

## Què hi ha

| | vídeos | hores |
|---|---|---|
| tot el canal | 3781 | 1,575 |
| capítols de sèrie (títol amb ⵜⴰⵅⵔⵙⵜ / épisode / الحلقة) | 954 | 284 |
| telenotícies («JT TAMAZIGHT», diaris) | 662 | 335 |

3366 dels 3781 títols porten tifinag. Les sèries més llargues:

| sèrie | capítols | hores |
|---|---|---|
| ANMMAL N TMAZIGHT | 132 | 21.5 |
| ILLIS N WOUCHEN | 60 | 17.0 |
| BOUYDOUNAN | 60 | 16.7 |
| ILLY | 59 | 16.3 |
| MAKH A WINOU | 30 | 16.1 |
| KARIMA D ISTIS | 31 | 14.6 |
| SIDI MOHA | 29 | 14.6 |
| TIBRATINE N MARZOUK | 27 | 14.2 |
| AGHBALOU | 28 | 14.0 |
| AATTAR | 21 | 12.0 |
| أفاذار | 23 | 11.9 |
| IMTAWN ZWANIN | 17 | 8.7 |
| مسلسل أفاذار | 16 | 8.5 |
| AVAZAR | 14 | 7.3 |
| HMOU BOUTMOUKRISSIN | 16 | 6.9 |
| إمطاون زوانين | 12 | 6.1 |

## El que fa que valgui la pena

- **Subtítols cremats en dues línies, tifinag a dalt i àrab a sota**, comprovats en un extracte
  d'Instagram i al capítol 1 d'«Illy» a YouTube (`q8rMnmWpMkI`, minut 10). Cap pista de subtítols
  pròpia a YouTube (`--list-subs`: «has no subtitles»), només les automàtiques en llengües alienes:
  per això l'enquesta dels 531 canals (que buscava pistes manuals) no ho va veure.
- **La varietat va escrita a les etiquetes:** «Illy» és «#مسلسلات_الأطلس #اللهجة_الأطلسية» (sèries de
  l'Atles, dialecte atlàsic); «Akabar n izli d wawal» té versió «ⴰⵟⵍⴰⵚ ⴰⵏⴰⵎⵎⴰⵙ» (Atles Mitjà).
  Cal mirar sèrie per sèrie: Tamazight TV emet en les tres varietats.
- **Ja tenim la cadena sencera per a aquest material:** el lector d'àrab cremat (Baba Ali, que és una
  sèrie d'aquesta mateixa cadena: 3.621 rèpliques llegides), el lector de tifinag per plantilles
  (aslmdtv), i els dos auditors àrab → català. Un capítol d'«Illy» (30 min) és la prova de foc:
  quantes rèpliques, quin CER del tifinag contra l'àrab traduït, quantes entren.
- **És so real de parlants en context**, no lectura: diàleg, famílies, carrer. Per a l'escolta de
  la biblioteca, el complement natural de TutlAit (frases llegides) i de les faules de TFA.

## El que ho frena

- **Drets:** SNRT, «Tous droits réservés». Televisió pública: es pot demanar (servei públic, ús
  educatiu i sense ànim de lucre, crèdit a la cadena), però fins que no hi hagi un sí escrit, la
  regla de les fonts noves: **catalogar, no incorporar**. El web de la SNRT (`snrt.ma`,
  `snrtlive.ma`) té formulari de contacte i «Médiateur».
- **Volum:** 284 hores de sèrie són més que tot el que hem processat fins ara junt. Si s'hi entra,
  per sèrie i varietat, començant per l'Atles, i amb la lliçó de TutlAit al davant (ids únics,
  so comprovat abans de cap cadena).
> **Això es va corregir a `ocr-tifinag-snrt.md` (vegeu `AUDITORIA-2026-11-21.md`, troballa 3):** el
> tifinag cremat de la SNRT es llegeix amb **CER 0,0009** sobre 100 línies no vistes, i aslmdtv amb
> ≥ 99,5 % dels glifs. El 0,29 és d'un lector de veu sobre rètols d'un altre canal, no d'un OCR:
> aquesta línia es va escriure sis hores abans que hi hagués la mesura. **I amb això cau la
> conclusió que hi penja:** amb un 0,09 % d'error, el tifinag no és un esborrany que només l'àrab
> pugui avalar. El que hi ha aquí sota és el que es va creure.

- **El tifinag cremat** es llegeix amb CER 0,29 al millor cas (aslmdtv): la línia àrab és la que
  dona el significat segur; el tifinag és esborrany a `text_tachelhit_suggested` fins que algú el
  confirmi.

## Decisió

~~Catalogada. Si en Pablo vol tirar endavant: (1) demanar permís a la SNRT; (2) mentrestant, una
prova sobre UN capítol d'«Illy» amb la cadena que ja tenim, només per mesurar, sense carregar res.~~

**17-11-2026, resposta de la SNRT** (vegeu `docs/PERMISOS.md`): endavant amb els canals de YouTube
i `snrtlive.ma/fr/tamazight` **com a font de recerca**, per millorar el diccionari-traductor i el
transcriptor de veu; **no republicar el contingut**; de moment no poden passar els subtítols en SRT.
El que això canvia: les rèpliques de Tamazight TV **no entren a la biblioteca pública** (ni so ni
text: seria republicar), però **sí al train** del traductor (tifinag/àrab → català) i de l'ASR (so +
text), i als tests. El material es guarda a `Veus-tachelhit\_escoltats\tamazight_tv\`, fora de l'app,
i cap `audio_url` ni frase seva es puja a producció. El crèdit a la SNRT va als informes i als models
que en surtin.
Relacionat: `tamazight-for-all.md`, `models-de-text.md` (Baba Ali), memòria «YouTube no té més
veritat humana amaziga» (que cal matisar: pistes no, text cremat sí).

## Per a la trucada amb la SNRT (17-11)

En Pablo parlarà amb el director lingüístic de la SNRT perquè ho passi al cap de la secció
amaziga. El que es demana, per ordre de valor, i el que s'ofereix:

**Demanar.** (1) **Els fitxers de subtítols originals** (SRT o semblant) de les sèries: la línia en
tifinag i la línia en àrab amb els temps. És la petició clau: l'OCR del tifinag cremat costa un
29 % d'error; el fitxer original dona el text exacte i a ells no els costa res. Si tenen guió o
versió llatina, millor. (2) **Permís per fer servir rèpliques curtes de so** dels capítols amb el seu
text i la traducció al català, en una biblioteca educativa sense ànim de lucre, amb crèdit a
Tamazight TV i a la SNRT a cada rèplica i enllaç al capítol sencer a YouTube. (3) **La varietat de
cada sèrie** (Atles Central, Souss, Rif) i, si pot ser, la zona dels actors: només ho saben ells.
(4) Que **ho revisin** si volen: ensenyar-los com queda abans de publicar res seu i retirar el que
demanin.

**Oferir.** Crèdit visible a cada rèplica («Tamazight TV, SNRT, sèrie Illy, capítol 1»), mai
l'estat del permís a l'app; ús només educatiu i sense ànim de lucre; cap redistribució de capítols
ni d'àudio llarg; la traducció catalana marcada com a nostra; les frases alineades i traduïdes a la
seva disposició (tindrien les sèries traduïdes al català i un corpus de l'Atles alineat); enllaç a
cada capítol.

**Què cal per escrit.** Un correu d'un paràgraf: qui autoritza, què (sèries i canal de YouTube), per
a què (biblioteca educativa) i com s'ha de citar. Es desa a `docs/PERMISOS.md`.

**La prova de mesura** (capítol 1 d'«Illy», `q8rMnmWpMkI`, autoritzada per en Pablo el 17-11 només
per baixar i mesurar) és a `Veus-tachelhit\_escoltats\tamazight_tv\illy_01\INFORME.md` quan acabi.
