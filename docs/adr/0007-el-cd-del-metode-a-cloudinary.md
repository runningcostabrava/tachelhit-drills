# ADR 0007: Els talls del CD del Mètode viuen a Cloudinary

- **Estat:** acceptada
- **Data:** 2026-10-29
- **Decideix:** Pablo (propietari)
- **Issue:** #495

## El problema

En Pablo, el 29/10: «no veig les gravacions al Mètode». L'índex del CD (`backend/data/cd_metode.json`)
apuntava a `/method/cd/<pista>/<inici>/<fi>`, una ruta que talla el tros d'una carpeta d'aquesta
màquina (`CD_METODE_DIR`). A Render la carpeta no existeix, de manera que a la web el capítol
mostrava el botó i no sonava res. Es va fer així a posta, mentre esperàvem el permís de l'autor:
el CD no havia de sortir de la màquina. El permís és donat des del 26-10-2026 (`docs/PERMISOS.md`), i
l'autor vol veure el sistema funcionant.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| No fer res | cap cost | el Mètode no sona enlloc fora d'aquesta màquina |
| Pujar les pistes senceres a Render | la ruta actual funcionaria | 75 MB al disc efímer de Render, que es perd a cada desplegament; ffmpeg a cada clic |
| Fer sonar el vídeo de YouTube on viu el CD, del segon X al Y | no copiem res | un reproductor de YouTube per a mig segon de veu: lent, i no es pot tallar net |
| **Un mp3 per línia a Cloudinary** | és on viu tota la resta d'àudio; un clic, un fitxer petit | el CD surt de la màquina (amb permís); cada línia nova s'ha de pujar |

## La decisió

Cada línia que ha sentit una persona es talla en local i es puja a `tachelhit/cd_metode/` de
Cloudinary amb `tools/cd_metode_a_cloudinary.py`, i l'índex hi apunta amb l'adreça https. Una
prova impedeix que l'índex torni a portar una adreça que només sona en aquesta màquina.

## Què en ve al darrere

- Una línia nova del CD no sona fins que algú la sent, la posa a `capitols` i passa el guió.
- La ruta `/method/cd/...` queda per escoltar talls nous en local abans de pujar-los.
- Les pistes senceres no es pugen: només els talls que fan sonar una línia.
- El crèdit continua al costat de l'àudio (`CD_CREDIT`), no dins del fitxer.
