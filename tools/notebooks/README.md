# Quaderns: la feina que no cap en aquesta màquina

Aquí hi ha el que s'ha de córrer **fora**, i el perquè de cada cas. No hi ha res aquí que es
pugui fer a casa: si es pot fer a casa, es fa a casa.

## Per què calen

L'ordinador del projecte té **1 GB de RAM lliure i cap targeta NVIDIA**. El model que tenim
corrent al Docker fa 51 MB i va a CPU; amb l'amazic estàndard llegit se'n surt (CER 0,134) i
amb les nostres veus de Beni Mellal i d'Aït Mraw, no. Els models que podrien fer-ho millor
—l'omniASR de 7B, el MMS, el wav2vec2-berber— **volen GPU**.

## On córrer cada cosa

| | què dona | per a què el fem servir |
|---|---|---|
| **Kaggle** | ~30 h de GPU **cada setmana**; «Save & Run All» corre sol 12 h encara que tanquis el navegador | **entrenar i provar**, setmana rere setmana |
| **ModelScope** | 8 nuclis i 32 GB de RAM **sense comptador**, i 36 h de GPU de 24 GB | la feina llarga de CPU, i l'únic que demana 24 GB |
| **Colab** | una T4 **quan n'hi ha**; la quota no es publica i a les hores puntes et deixa sense | comprovar que una idea funciona **abans** de muntar-hi res |

La diferència que mana: **Kaggle corre desatès**; ModelScope i Colab són sessions obertes. Per a
un bloc gros que ha d'acabar, Kaggle.

## El que hi ha

### `prova_models.py` — quin model llegeix millor les nostres veus

Passa diversos models pel mateix material i amb la mateixa vara, de manera que els números es
puguin comparar entre ells i amb el que ja tenim.

**Dues vares, i el segon número és el que mana:**

- **la de fora** (TOSD, amazic estàndard llegit): diu si el model sap llegir la llengua;
- **la nostra** (Beni Mellal, Aït Mraw): diu si sap llegir **el que nosaltres gravem**.

Un model pot ser bo a la primera i inútil a la segona. Ens ha passat amb el que tenim, i per
això es miren totes dues.

### Com es corre

**Kaggle.** `kaggle kernels push` des d'aquí, o pujar-lo a mà. Cal Accelerator = GPU i el token
de HuggingFace a **Add-ons → Secrets** amb el nom `HF_TOKEN`.

**Colab.** Obre'l, tria entorn amb GPU, i posa el token al pany de l'esquerra (Secrets), amb el
mateix nom. No cal cap altra credencial.

El corpus se'l baixa sol del dataset privat `josepabloucr/tamazight-corpus`, que porta el
manifest, el repartiment i la fitxa que diu d'on surt cada tall i amb quin permís.

## La regla que no canvia quan la feina surt de casa

**Res del que surti d'aquí entra a la biblioteca pel seu compte.** Els quaderns escriuen un
fitxer de resultats; el que arribi a l'app passa per la porta de sempre —`*_suggested`— i ho
confirma una persona.

I una cosa que hem après avui i que val la pena no tornar a aprendre: **abans de creure's un
número, comprova que les dues bandes parlen el mateix idioma.** Avui una mesura va dir que el
model era inservible amb les nostres veus, i el que passava és que comparava tifinag contra
llatí.
