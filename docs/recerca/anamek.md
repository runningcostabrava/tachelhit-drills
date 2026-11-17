# Anamek, el diccionari col·laboratiu amazic–francès (mirat el 17-11-2026)

Font passada per en Pablo: `github.com/AnamekOrganisation/Anamek-Dictionary` i el web `anamek.org`.
Catalogada, no incorporada (regla de les fonts noves: només catalogar fins que hi hagi permís).

## Què és

Un diccionari web amazic → francès, col·laboratiu, viu (el web diu **26.188 mots i 299 proverbis**;
entrades noves del 8 i 9 de novembre de 2026). El repositori de GitHub (gener 2026, PHP + MySQL,
3 estrelles, darrer canvi 3-4-2026) només conté el **codi** sota GPL-3: l'esquema de la base de dades
ho diu explícitament, «sense cap dada inicial». Les dades viuen només al web.

## Les dades

- **Esquema ric, entrades pobres.** La taula `words` preveu tifinag, llatí, francès, definició,
  categoria gramatical, plural, femení, estat d'annexió, arrel i exemple, i hi ha taules de sinònims,
  antònims, exemples, etimologies i conjugacions verbals (importades d'un SQLite `conjugations.db`
  que no és al repositori). Però les entrades mirades (`aman` → «eau», `iẓli` → «être séparé»,
  `Amenkay` → «Doyen») tenen **tots els camps buits llevat de la paraula i el francès**. És una
  llista de mot → glossa francesa, no un diccionari amb gramàtica.
- **Varietat.** Tamazight estàndard marroquí amb neologismes de l'IRCAM (`tarselt tadidaktit`
  «unitat didàctica», `asngḍ`, `isngadda`): el món de l'escola i de l'estàndard, no la parla
  d'Aït Mraw. Cap marca de varietat per entrada. La base de dades es diu `Amawal`.
- **Accés.** Cap bolcat ni exportació (l'exportació CSV/JSON és a la llista de «previst»). Hi ha
  una API pública de cerca per prefix, `/api/search?q=<prefix>&lang=ber`, que torna JSON amb tots
  els camps, i pàgines `/word/<slug>-<id>` amb ids correlatius fins a ~26.217. Es podria recórrer,
  però seria raspar 26.000 pàgines d'un web petit sense demanar-ho.
- **Condicions d'ús** (`/terms-of-use`): ús personal, educatiu i no comercial; «la reproducció o
  redistribució del contingut és autoritzada només amb finalitat educativa, citant clarament la font
  “Anamek”»; qualsevol ús comercial demana autorització escrita. El peu diu «Tous droits réservés».
  La nostra biblioteca és educativa i sense ànim de lucre: hi cabria, amb crèdit, però la manera
  neta és demanar-los el bolcat (tenen formulari de contacte i GitHub obert a contribucions).

## Què ens aportaria

El mateix que el Viccionari zgh i amazic.cat: un **lèxic de validació** (la forma estàndard en
tifinag i llatí d'una paraula, i la seva glossa), 25 vegades més gran que ⵡⵉⴽⵉⵎⴰⵡⴰⵍ (1.033 entrades).
Serviria per: (1) comprovar l'ortografia tifinag de les formes que surten de l'OCR i de l'ASR;
(2) donar glossa a les paraules del dàrija del professor que no tenim (169 formes «no la tenim» a
`tamazight-for-all-darija-confirmat-vs-lexic.md`); (3) alimentar el diccionari que posem al prompt
dels models que no saben la llengua. **No** aportaria: frases (no n'hi ha), veu, varietat ni català
(el francès → català el fa qualsevol model, però la glossa segueix sent la d'un redactor, no la d'un
parlant). Ja sabem (v3 del NLLB, 16-11) que el vocabulari solt no ajuda el traductor: no és per
entrenar-hi.

## Dues notes per a ells

El guió `import_sqlite_verbs.php` del repositori públic porta una contrasenya de base de dades
escrita al codi (apunta a `localhost`, però és una mala pràctica que convindria dir-los). I l'API
de cerca no té límit de resultats per pàgina documentat: si volen que algú els faci servir les dades
sense raspar, l'exportació prevista és el camí.

## Decisió

Catalogada. Si en Pablo vol les dades: escriure'ls pel formulari de contacte demanant el bolcat
(CSV/JSON) amb crèdit «Anamek» a l'app, i mentrestant res. Relacionat: `tamazight-for-all.md`
(amazic.cat i el Viccionari zgh), `models-de-text.md` (tamazightdev, el mateix dia).
