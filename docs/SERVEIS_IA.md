# Quin servei fa cada feina, i per què

Aquest projecte fa servir cinc o sis serveis d'intel·ligència artificial i cap d'ells no serveix
per a tot. Aquesta pàgina diu **quin es fa servir per a què, en quin ordre, i què passa quan un
no contesta** — perquè això últim passa cada setmana: el 24-10-2026, en una sola jornada, Gemini
es va quedar sense crèdit (`402`), la quota de FLUX es va esgotar i el traductor gratuït de
Google ens va tallar per excés de peticions.

La regla que mana per sobre de totes: **el que surt d'una màquina no és mai el text d'un
parlant.** Va als camps `*_suggested` i ho decideix una persona. Això no és prudència: és el
projecte. Una biblioteca de llengua que es deixi omplir per una màquina no documenta res.

---

## 1. Transcriure veu → text amazic

**Només el pot fer un model de veu.** DeepSeek, Gemini i Claude són models de text: no senten
res. Això no és una qüestió de qualitat sinó de què entra per l'entrada.

| ordre | qui | notes |
|---|---|---|
| 1r | **el nostre Space** (`ayymen/stt_zgh_fastconformer_ctc_small`, NeMo CTC) | escriu tifinagh; 40-100 s per gravació en una CPU gratuïta; torna `confidence` |
| 2n | `TutlaytAI/wav2vec2-berber` | **no per substituir-lo, per contrastar-lo**: que dos models independents coincideixin val més que la certesa d'un de sol |

El resultat va a `text_tachelhit_suggested` amb la seva certesa, i es confirma primer el que té
més números de ser bo (`/asr/night/run`).

---

## 2. Traduir

| feina | qui | per què |
|---|---|---|
| **àrab → català**, a milers | **DeepSeek** (`deepseek-flash`) | ràpid i barat; una crida per lot. El traductor gratuït de Google talla a la tercera petició |
| **amazic → català** | **DeepSeek** (`deepseek-v4-pro`) **amb les fonts al davant** | vegeu més avall |
| **català/anglès → amazic** | **ningú automàticament** | és escriure la llengua, i això no ho fa una màquina sola |

### Les fonts no són un extra: són la diferència

Mesurat el 24-10-2026 amb cinc frases nostres de significat conegut:

- **sense fonts**, `deepseek-flash` n'encerta 4 de 5 i falla la subtil: tradueix
  `mnckk a tskar zzit?` per «com fas oli?» quan vol dir «quant val l'oli?» (el verb `skr` vol
  dir «fer», i amb `mnckk` al davant vol dir «valer» — pàgina 51 del manual);
- **amb el diccionari de l'IRCAM i les frases de la nostra biblioteca al davant**, encerta
  «manimsh tjit» → «Com et trobes?» exacte **i avisa del que no sap**: «*tudit* no apareix a les
  fonts».

Aquell avís és la raó per fer-ho així. Un model que diu què no sap es pot posar en una cua de
confirmació; un que ho dissimula, no.

Les fonts que es donen, per frase: les entrades del **DGLAI** de les seves paraules i les frases
**de la nostra biblioteca** que porten aquelles paraules amb el significat que hi va posar qui
les va dir.

---

## 3. Escriure text (lliçons, explicacions, glosses)

| ordre | qui |
|---|---|
| 1r | **DeepSeek** (`v4-pro` per a text llarg, `flash` per a lots) |
| 2n | **Gemini** — avui sense crèdit (`402`) |

**El que mai no fa una màquina sola:** escriure amazic. Pot proposar la traducció al català d'un
text que té al davant (el manual és en italià), i això és feina de traductor, no d'inventor.

---

## 4. Dibuixar

| ordre | qui | estat 24-10-2026 |
|---|---|---|
| 1r | **Gemini** (`gemini-2.5-flash-image`) | sense crèdit |
| 2n | **Spaces públics de FLUX** amb el nostre token | quota de ZeroGPU esgotada |
| 3r | *(per fer, #285)* Inference Providers, Pollinations, Together, Replicate | — |

I la regla que ja regeix: **una paraula només s'il·lustra amb un dibuix nostre**. Una foto
buscada a la xarxa il·lustra una paraula per casualitat o no la il·lustra gens.

---

## 5. Auditar

Els tres auditors del Mètode (amazigòleg, dialectòleg, pedagog) són avui **el mateix model que
escriu els capítols**. Això té un problema que ja ens ha costat una errada: el 23-10 van
concloure que unes formes del capítol 4 eren invencions meves, i eren del llibre.

**Fer-los córrer a DeepSeek els fa independents.** No és una millora de qualitat sinó de
naturalesa: una auditoria feta pel mateix model que ha escrit comparteix els seus punts cecs.

---

## Les regles, totes juntes

1. **El que surt d'una màquina va a `*_suggested`.** Sempre. Ho confirma una persona.
2. **Les fonts guanyen la memòria del model.** Si tenim el diccionari, el llibre o una frase
   nostra que ho digui, se li dona; i el que digui sense fonts és sospitós.
3. **Que digui què no sap.** Un model que avisa es pot fer servir; un que dissimula, no.
4. **Dos models que coincideixen valen més que un de segur.**
5. **Cap servei és l'únic.** Tots cauen: crèdit, quota, límit de peticions. Cada feina ha de
   tenir un segon i, si no en té, ha de dir clarament que està aturada en comptes de callar.
6. **Una certesa alta no vol dir correcte.** Ordena la cua; no decideix res.

---

## Què falta per muntar-ho

- `DEEPSEEK_API_KEY` a l'entorn del backend (avui la clau viu al projecte de SEO).
- El rellotge nocturn a cron-job.org que cridi `/asr/night/run`.
- Els proveïdors de dibuix de la fila 3r (#285).
