---
name: Pantalla o disposició
about: Una pantalla que es trenca, se superposa o no aguanta un contingut llarg
labels: bug
---

## Què es veu

Què passa, on, i a quina amplada de pantalla. Captura si en tens.

## Què ha de passar

## Criteris d'acceptació

Escriu-los de manera que es puguin comprovar mirant, no raonant sobre el CSS.

- [ ] **Què aguanta la secció:** flex o graella, i què no la pot canviar
- [ ] **Què no es pot tapar mai:** (capçalera sobre targetes, botó de so sobre el text…)
- [ ] **Amplades que ha de sobreviure:** 360 · 768 · 1280 · 1920 px
- [ ] **Contingut llarg:** una frase de 90 caràcters, una paraula sense espais, una imatge que
      no carrega, tifinag i llatí a la mateixa línia
- [ ] Provat a les quatre amplades abans del PR
