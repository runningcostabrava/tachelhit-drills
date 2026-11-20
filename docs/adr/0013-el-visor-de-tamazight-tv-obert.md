# 0013 · El visor de Tamazight TV, obert; el vídeo, no

**Data:** 20-11-2026 · **Estat:** acceptat (decisió d'en Pablo) · **Substitueix:** [0012](0012-visor-privat-de-tamazight-tv.md)

## Problema

L'ADR 0012 va posar el visor darrere `require_admin` (després, també convidats de la SNRT). El
20-11-2026 en Pablo el va obrir i va veure el vídeo negre i el missatge «aquesta pàgina és només
per a administradors». Ho va llegir com una porta que li barrava el pas i va demanar treure-la.

**No era la porta.** Mesurat aquell matí: el servidor de producció es moria de memòria cada ~70
minuts i entre un terç i un 40 % de les peticions tornaven 502; la pàgina feia passar aquell
silenci per un «no hi entres» (arreglat a part, PR #701). En Pablo ja era administrador.

Dit això, va mantenir la decisió amb un argument propi: **el vídeo no el serveix ningú**. El
visor demana el fitxer al disc de qui mira, i això vol dir que, a la pràctica, només el pot
fer servir qui té els vídeos — ell. La porta d'administrador no protegia el vídeo: protegia el
text.

## Opcions

1. Deixar la porta i arreglar només el missatge.
2. Obrir-ho a qualsevol que tingui compte.
3. **Obrir-ho a tothom, sense comptes (triada per en Pablo).**

## Decisió

`GET /snrt-privat/` i `GET /snrt-privat/{slug}` no demanen qui ets. Segueixen tancats:

- `GET /snrt-privat/{slug}/video`, que dóna una adreça signada del vídeo que tenim allotjat
  (administradors i convidats de la SNRT). Obrir això sí que seria repartir el vídeo, i és just
  el contrari de l'argument amb què s'obre la resta.
- `POST /snrt-privat/{slug}/importa`, que escriu (administradors).

I el que no canvia de l'ADR 0012: les taules no surten a cap exportació, corpus ni ruta pública
de la biblioteca (`test_snrt_visor_privat.py`), i la pàgina no passa pel cau fora de línia.

## Conseqüències

- **El text de la SNRT (tifinag, àrab i el català de màquina) queda públic.** Li vaig dir abans
  de fer-ho, amb aquestes paraules, que el permís que tenim apuntat és de recerca i que
  `docs/PERMISOS.md` encara espera el correu de la SNRT per a aquest ús. Va decidir obrir-ho
  igualment, i això és seu de decidir: hi consta aquí perquè quedi escrit qui ho va decidir i
  sabent què.
- Si la SNRT demana que es tanqui o s'esborri: tornar les dues dependències a les dues rutes és
  una línia cadascuna, i esborrar-ho és un `DELETE` de les dues taules.
- El text segueix **sense revisar** i la pàgina ho diu a dalt de tot: el tifinag i l'àrab els va
  llegir una màquina de la imatge i el català el va traduir una altra.
