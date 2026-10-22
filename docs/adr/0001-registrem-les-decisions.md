# ADR 0001: Registrem les decisions tècniques

- **Estat:** acceptat
- **Data:** 2026-10-22
- **Decideix:** el propietari del projecte
- **Issue:** #185

## El problema

Les decisions tècniques d'aquest projecte s'han pres al xat i han quedat al xat. Unes quantes de
la mateixa nit del 21 al 22 d'octubre de 2026, totes amb conseqüències que es noten:

- el so d'una frase és `audio_url` o `audio_tts_shi_url`, **mai** la lectura catalana del
  significat — abans el curs deia «jo» en català quan una paraula no tenia veu amazic;
- la nota de «per què és aquí» es guarda per **parella (frase, unitat)**, perquè una frase és a
  tres unitats i hi mostra coses diferents;
- qui pot canviar un drill: qui el va fer o qui administra;
- el correu surt per l'API HTTPS d'un proveïdor, no per SMTP, perquè Render bloqueja els ports de
  correu.

Cap d'aquestes decisions és al repositori. Qui hi arribi demà —una altra sessió, una altra
persona, tu mateix d'aquí a tres mesos— n'ha de deduir el perquè del codi, i el perquè no hi és.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| deixar-ho al xat | zero feina | es perd; es tornen a discutir les mateixes coses |
| explicar-ho als comentaris del codi | és allà on es llegeix | el comentari diu QUÈ fa, no què vam descartar |
| ADR numerats a `docs/adr/` | queda el perquè i les opcions mortes; es llegeix en ordre | cal escriure'ls |

## La decisió

Tota decisió tècnica que costi de desfer —esquema de dades, permisos, proveïdors de fora, format
d'una lliçó, què entra a la biblioteca— es documenta en un ADR numerat a `docs/adr/`, escrit amb
l'assistent (`.claude/skills/adr/`), que pregunta una cosa cada vegada i acaba obrint un PR.

Un ADR no es modifica un cop acceptat: si la decisió canvia, se n'escriu un de nou que digui que
substitueix l'anterior.

## Què en ve al darrere

- Escriure un ADR costa deu minuts i una conversa; es fa quan la decisió és d'aquelles que
  costaria desfer, no per a cada tria de nom de variable.
- Les quatre decisions de la llista de dalt queden pendents d'escriure com a ADR 0002 i següents.
- Qui revisi un PR pot demanar l'ADR si en troba a faltar el perquè.
