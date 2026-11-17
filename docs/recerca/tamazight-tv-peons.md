# Encàrrecs tipus per als peons de la fàbrica de Tamazight TV (17-11-2026)

Text per copiar a l'encàrrec d'un peó (un model més senzill). Cada encàrrec porta el preàmbul i un
sol bloc de feina. El peó no decideix res de §5 ni §8 de l'especificació: ho apunta i pregunta.

## Preàmbul (sempre)

> Ets un peó del projecte tachelhit-drills (repositori `C:\Users\josep\app2\tachelhit-drills.worktrees\mirar`,
> branca `feat/ecs` = `origin/main`; dades a `C:\Users\josep\Veus-tachelhit\`). Tot en català. Regles:
> python només el del venv del backend (`C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe -X utf8`),
> mai el global; els guions s'escriuen amb l'eina Write; `sleep` està bloquejat (fes
> `ping -n N 127.0.0.1 >nul`); res a producció; cap secret al xat ni al repositori (claus al `.env`
> del backend, carregat amb `override=True`); no obris PR si no t'ho demano; «acabat» no és «bo»:
> cada resultat porta una mostra a ull. Llegeix primer `docs/recerca/tamazight-tv-fabrica-especificacio.md`
> i segueix-la al peu de la lletra; si una cosa no quadra, apunta-la a l'informe i continua amb la
> resta. Quan acabis, envia'm deu línies amb els comptes i les rutes.

## Bloc A: processar una llista de capítols

> Carpeta `TD_TV` = `…\tamazight_tv\`. A `cataleg\capitols.jsonl` hi ha N capítols amb `estat = pendent`
> i `prioritat ≤ 2`. Per a cada un, en ordre de prioritat i amb les entrevistes abans que les sèries:
> `nit.py` (etapes 01 → 05 de `tools/snrt/fabrica/`). Comprova la geometria de les franges al primer
> capítol de cada programa nou (10 fotogrames mirats amb Read) abans de llançar la lectura. Quan un
> capítol surti `error`, no el repeteixis més de dues vegades: apunta el motiu i passa al següent.
> Informa'm amb l'informe de la nit (`_informes\`): capítols fets, rèpliques aptes per al traductor i
> per a l'ASR, fitxes de visió gastades (la quota gratuïta és d'1 M per model), portes tancades.

## Bloc B: catalogar un programa i les seves persones

> Programa `<nom>` del replay de snrt.ma (pàgina `<url>`) o del canal de YouTube. Omple
> `cataleg\capitols.jsonl` (esquema §3.1) amb tots els capítols i `cataleg\persones.jsonl` (§3.2) amb
> cada convidat i presentador: lloc i regió d'origen amb la font (Viquipèdia, premsa, editorials,
> webs d'autor); «no trobat» si no hi és; mai inventat. Marca `prioritat = 1` si la persona és de la
> zona Boumalne Dadès – Kalaat M'Gouna o Azilal – Aït Bougmez (Boutharar, Aït Mraw, Demnat,
> Ouaouizeght) o a prop; 2 si és de l'Alt Atles o Beni Mellal; 3 la resta. Taula `PERSONES.md`
> ordenada per proximitat a Aït Bougmez.

## Bloc C: mesurar la varietat d'un capítol

> Capítol `<slug>` amb `subtitols.jsonl` fet. Aplica §6.1 i §6.2 sencers: tres proporcions (totes
> les formes i només gramaticals), el control entre referències, i les 30 rèpliques passades per
> l'ASR actual amb els parells de correspondència a `_varietat\<slug>.jsonl`. No posis
> `varietat_capitol` tu: dona els números i 10 parells a ull, i el director decideix.

## Bloc D: lector sintètic nou (tifinag o àrab)

> Segueix §6.3. Entrega: la tipografia amb la prova visual i numèrica; el generador de línies
> sintètiques; el nucli de Kaggle; el model; l'avaluació sobre les 200 franges amb veritat humana
> (CER global i per parella de confusió, 20 errors a ull); i la funció `llegeix_<escriptura>()`
> llesta per endollar a l'etapa 02 sense canviar-ne res més. No la substitueixis tu: el director
> aplica §5.

## Bloc E: experiment del traductor

> Segueix §6.4 exactament (partició per capítol, fuita per text normalitzat, els candidats indicats,
> mateix nucli i llavor, bootstrap aparellat). Entrega: `resum_dataset.json` (comptes de train / dev /
> test i fuites tretes), les taules de chrF amb IC per a cada candidat i grup, 20 frases a ull de la
> mostra de 60 amb els candidats costat per costat, i una secció de dues línies «què recomano i per
> què». No despleguis res al Space.

## Bloc F: experiment del transcriptor

> Segueix §6.5. Entrega: comptes de rèpliques aptes per a l'ASR per capítol i varietat, el nucli de
> Kaggle, CER amb IC sobre CV zgh net, test-fora i capítols retinguts, 20 talls a ull (so, tifinag,
> transcripció), i la recomanació en dues línies. No despleguis res al Space.

## Bloc G: informe per al director

> A partir de `_informes\` dels últims 7 dies i dels `INFORME.md` dels capítols: una pàgina amb els
> acumulats (capítols, rèpliques aptes per traductor i ASR, hores de so, cost), les portes tancades
> amb motiu, els capítols amb varietat per decidir (amb els seus tres números i les persones), i la
> llista de decisions pendents, cadascuna amb les dues opcions i el que costa cada una. Sense
> recomanar: el director tria.
