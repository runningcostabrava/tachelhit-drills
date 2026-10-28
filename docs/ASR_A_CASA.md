# Sentir amazic sense dependre de ningú (#445)

La feina de **transcriure** —sentir una gravació i escriure el que diu— és l'única del projecte
que fa setmanes que no té cap servei viu: el nostre Space s'adorm, el cron que el mantenia
despert el va desactivar GitHub, i el segon model ni tan sols està configurat.

No cal. **El model, el codi i el `Dockerfile` ja són dins del repositori**, i el model fa 51 MB i
va a CPU. Es pot engegar a la màquina de casa en dues ordres.

```bash
docker build -t asr-amazic:local huggingface-asr-space
docker run -d --name asr-amazic -p 7861:7860 asr-amazic:local
curl http://127.0.0.1:7861/health
# {"status":"ok","model":"ayymen/stt_zgh_fastconformer_ctc_small","routes":["/transcribe","/align"]}
```

La primera vegada triga: compila les dependències i es baixa el model. Després l'arrencada és
d'un minut llarg, el que el NeMo tarda a carregar.

Per transcriure un tall:

```bash
curl -F "audio_file=@frase.m4a" http://127.0.0.1:7861/transcribe
# {"text":"ⵉⵙ ⴽⴰ … ⵔⵉⵖ ⴰⴷ …","confidence":0.78, …}
```

El camp es diu **`audio_file`**; amb qualsevol altre nom el servidor contesta 422.

## Que l'app el faci servir

Sense tocar codi. `_space_host()` (`backend/dialect.py`) es queda l'adreça tal com ve quan no és
un Space de HuggingFace, de manera que n'hi ha prou amb:

```
HUGGINGFACE_ASR_SPACE_URL=http://127.0.0.1:7861
```

## Per què el model és aquest i no un de millor

La taula de models que vam mesurar posa l'`omniASR-LLM-7B-v2` al davant (CER 0,27), però **vol
GPU i està tancat darrere d'un permís**. En aquesta màquina la targeta és una **Radeon integrada
de 2 GB** —la RTX és a l'ordinador del vídeo—, així que aquí es va a CPU i els models grossos
queden fora.

Aquesta taula, a més, **no s'ha de prendre com a veritat**: surt d'un banc de proves amb sortides
de només **deu talls**. Hi ha el conjunt de 1.801 frases per fer-ho de debò, i fins que no es
faci, l'ordre dels models és una pista i prou.

El que sí que està mesurat és el que fa falta saber: el model d'abans
(`SoufianeDahimi` whisper, CER 0,68) estava entrenat per **traduir a l'àrab** i s'inventava
llengües; aquest dona tifinag de debò.

## El que això desencalla: dues lectures que no poden compartir un error

Les frases del conte del lleó i el ratolí (`wcUZI6__nk4`), **llegides dels píxels** amb
[`tools/text_de_video/signes.py`](../tools/text_de_video/signes.py) i **sentides de l'àudio** per
aquest model, diuen el mateix:

| frase | llegint la imatge | sentint la veu |
|---|---|---|
| 8 | `išša` · `kra` · `ittmus` · `tiqqrt` | ⵉⵛⵛⴰ · ⴽⵔⴰ · ⵉⵜⵜⵎⵡⵓⵙⵙⵓ · ⵜⵉⵇⵔⵜ |
| 15 | `is ka` · `laẓ` · `riɣ` | ⵉⵙ ⴽⴰ · ⵍⴰⵥ · ⵔⵉⵖ |
| 27 | `wass` · `tifawt` · `uɣrda` | ⵡⴰⵙⵙ · ⵜⵉⴼⴼⵖⵜ · ⵓⵖⵔⴷⴰ |

Un camí mira la **forma de les lletres** cremades a la imatge; l'altre **sent la veu**. No
comparteixen ni el model ni l'entrada, de manera que no poden compartir un error. La regla de la
casa diu que dos models que coincideixen valen més que un de segur; dos models **amb entrades
diferents** valen encara més.

De passada, va corroborar sol el [#364](https://github.com/runningcostabrava/tachelhit-drills/issues/364):
el parlant escriu `rix` i aquest model, entrenat amb l'estàndard, escriu **ⵔⵉⵖ**. És la mateixa
paraula amb la ɣ final ensordida.

## El que segueix igual

Una transcripció d'aquest model **no és el text de cap parlant**. Va a `*_suggested` i la
confirma una persona, com tota sortida de màquina. El que ha canviat no és la confiança: és que
ara tenim una **segona lectura independent** per contrastar, i una casella només es dona per
bona quan les dues coincideixen.
