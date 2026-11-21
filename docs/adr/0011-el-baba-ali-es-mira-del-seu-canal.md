# ADR 0011: El Baba Ali es mira del seu canal, i el desplaçament es mesura

- **Estat:** acceptada
- **Data:** 2026-11-11
- **Decideix:** Pablo (propietari)
- **Issue:** #583

## El problema

Tenim 3.621 frases de tretze episodis del **Baba Ali** (del 2 al 15; l'1 i el 14 no hi són):
l'àrab llegit de la pantalla amb OCR, una traducció catalana de màquina, el tall de so i el
segon on surt cada frase. En Pablo demana un visor dins de l'app per **mirar la sèrie** amb
aquest text a sota.

Hi ha dos problemes, i el segon és el que costa.

**D'on surt el vídeo.** La sèrie és de la SNRT. Els `source_url` dels drills apunten a
forja.ma, que és on es van capturar, però tota la temporada 1 és pública al canal del Baba
Ali a YouTube, i el procés original del projecte ja hi anava
(`tools/notebooks/arab_easyocr.py`: `VIDEO_ID = "ihwiZk1WmJM"`).

**Quin vídeo és cada episodi, i a quin segon.** Les marques de temps les va escriure qui va
fer els talls i **no casen** amb la pujada: cada pujada comença amb uns dos minuts de resum i
de rètols, i algunes porten dos o tres episodis seguits. La numeració del canal tampoc no és
de fiar: la pujada que es diu «12 13 14» porta de fet els nostres 13, 14 i 15. Un visor fet
confiant en els títols ensenyaria el text desplaçat dos minuts, o d'un altre episodi.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| Servir una còpia nostra del vídeo | sincronia nostra, sense dependre de ningú | 1 GB per episodi i una còpia d'una obra que no és nostra |
| Encastar el canal i confiar en els títols de les pujades | immediat | fals: la pujada «12 13 14» no porta el 12, i les marques van dos minuts avançades |
| Encastar el canal i **mesurar** el desplaçament pel so | el vídeo no es copia i la sincronia es pot demostrar | la mesura s'ha de fer i algun episodi es queda sense |
| Sense vídeo: només els talls de so, frase a frase | ja ho tenim | no és mirar la sèrie |

## La decisió

**S'encasta el vídeo del canal públic i el desplaçament de cada episodi es mesura pel so.**

El tall de tres segons que tenim desat *és* un tros exacte de la banda sonora de la pujada, de
manera que trobar-hi on sona és un càlcul i no una endevinalla: es correlaciona l'envolvent
(l'energia cada 20 ms, que casa encara que les dues còpies estiguin codificades diferent) de
divuit talls repartits per l'episodi contra la banda sonora sencera de cada pujada del canal.

**El criteri no és «quants talls hi són d'acord» sinó quina probabilitat hi ha que hi siguin
per atzar.** Si la pujada no és la bona, els segons que torna cada tall són escampats; així
que es compta `C(n,k) · (finestra/durada)^(k-1)`, i s'accepta si almenys tres talls
coincideixen dins de mig segon, aquell número baixa de 1e-3, i cap altra pujada no s'hi
acosta. El primer llindar que vaig posar —cinc talls d'acord— descartava l'episodi 13, que hi
era amb tres talls clavats a −192,0 s; i n'hauria acceptat un amb cinc coincidències
casuals dins d'una pujada de 85 minuts.

El resultat, amb les proves, viu a `backend/data/baba_ali_pujades.json`: **deu episodis dels
tretze**, amb 10 a 16 talls d'acord a ±0,3 s i un número de falsos esperats entre 1e-27 i
1e-46. Els tres que falten hi surten dient per què: la pujada del 7 té el so **mut** a YouTube
(−91 dB baixada sencera), la del 9 no es deixa baixar (403), i del 12 **no hi ha pujada** al
canal.

## Què en ve al darrere

- Un episodi sense vídeo comprovat **surt igualment**, amb els seus talls de so i amb la raó
  escrita. No s'hi posa un vídeo «que probablement sigui aquell».
- Les esmenes del text trobades comprovant la imatge (el nom del mercader, que l'OCR va llegir
  «بلقاسم» les 42 vegades que surt quan la pantalla escriu «أبي القاسم»; i les fórmules
  islàmiques que la màquina convertia en advocacions marianes) **es fan en servir la línia i no
  a la biblioteca**: l'ADR 0003 continua valent, el text del parlant no es reescriu d'ofici, i
  la resposta diu quines línies porten esmena.
- La pantalla diu que el text va **sense revisar**, i mostra el català i l'àrab de costat, que
  és l'única manera que qui sàpiga àrab vegi si el que falla és la lectura o la traducció.
- Si algun dia la pujada del 9 es deixa baixar, o es mesura el 7 per la imatge en comptes del
  so, només canvia aquell fitxer de dades.
