# ADR 0009: El MMS s'entrena amb les lletres riques

- **Estat:** acceptada
- **Data:** 2026-10-30
- **Decideix:** Pablo (propietari)
- **Issue:** #511

## El problema

En 4.561 segments, el MMS afinat no ha escrit cap ɣ, ɛ, ḥ ni emfàtica. La causa és nostra: abans
d'entrenar plegàvem el text a 26 lletres, també el tifinag (ⵖ→g, ⵄ→a, ⵃ→h). El model base sí que
les escriu: a 300 frases de MTNRA encerta 171 de 184 ɣ.

## Què s'ha provat

Dues passades amb l'objectiu ric, mesurades sense plegar. La taula diu el CER:

| prova | base | tot el corpus | només fonts riques |
|---|---|---|---|
| test-fora (veus que no entrenen) | 0,339 | 0,291 | 0,287 |
| cv-zgh-test (test net) | 0,217 | 0,144 | 0,141 |
| test-mtnra | 0,194 | 0,098 | 0,094 |
| test-dins (Beni Mellal) | 0,277 | 0,198 | 0,222 |

Totes dues mantenen les lletres riques i inventen menys que el base. test-mtnra no decideix: el
MTNRA no diu qui parla. El text d'or de test-dins va gairebé pla, i això penalitza qui escriu ric.

## La decisió

1. L'objectiu d'entrenament és ric: `tools/notebooks/afina_mms_lletres_riques.py`. El CER que tria
   el millor model tampoc no plega, i cada mesura diu l'encert per lletra.
2. Al Space hi va l'adaptador de **tot el corpus**: als tests externs la diferència és petita, i
   conserva millor la parla més propera a la ruta.
3. La sortida continua a `*_suggested`. Una ɣ escrita pel model no és cap prova d'ortografia.
4. Baba Ali i els canals es tornen a transcriure amb aquest model, només als camps suggerits.

## Què en ve al darrere

- ṛ no és a l'alfabet `shi` i continua sortint com a r.
- ɛ, ḥ i ṣ tenen pocs exemples als tests: el seu encert és orientatiu.
- Falta mesurar-ho amb l'Atles central de debò: cal text d'or ric de Halima i Driss.
- `gh`, `kh`, `sh`, `ch` i els números de l'arabizi es llegeixen com la lletra que representen,
  encara que de vegades puguin ser dues lletres.
- El model no s'ha mesurat amb cançons: als vídeos de música la sortida és molt pitjor.
