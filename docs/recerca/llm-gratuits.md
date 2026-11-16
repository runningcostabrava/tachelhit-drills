# Models de text gratuïts: què hi ha, què ens serveix i com s'endollen (16-11-2026)

En Pablo demana «com puc fer servir molts altres models gratuïts amb llmfree». Això és el mapa, mirat
el 16-11-2026 a partir dels tres directoris que es mantenen al dia a GitHub (`mnfst/awesome-free-llm-apis`,
13.400 estrelles, actualitzat avui; `open-free-llm-api/awesome-freellm-apis`; i el paquet
`MoonLite-Br/llmfree`), més les nostres pròpies mesures. Còpies dels tres LLEGEIX-ME a
`Veus-tachelhit\_escoltats\models\llmfree\`.

## 1. Què és «llmfree» i per què no és el nostre camí

`llmf` (paquet PyPI `llmf`, repositori `MoonLite-Br/llmfree`) és una llibreria Python sense dependències
que fa `llmf.chat("…")` contra una llista de **punts d'accés públics i no oficials, sense clau**, amb
alternança automàtica quan un cau: `ch-at` (un `gpt-4o` sense autenticació), `rewind-ai`, `ovh`,
`kilo`, `freeai`, `llm7`, `pollinations`, `chatjimmy`, `blockrun`, `chatai` (un `claude-haiku-5.5` i un
`gemini-2.5-flash-lite` a 3-5 crides per IP i dia)… El seu propi LLEGEIX-ME ho diu: «els vostres
prompts van a tercers anònims; canvien, s'estrenyen o desapareixen sense avís; no hi envieu secrets».

Per a nosaltres té dos problemes que el descarten com a peça del sistema: (1) la majoria d'aquests
punts són **la porta del darrere de webs de xat d'altri**, no una oferta del proveïdor: fer-los
servir en un projecte que demana permís per cada vídeo seria incoherent; (2) la qualitat i la
disponibilitat canvien cada dia, i nosaltres mesurem i tornem a mesurar sobre la mateixa mostra: un
model que avui és un i demà un altre no es pot mesurar. **Dos dels seus proveïdors, però, són oferta
oficial i sense clau**: OVHcloud AI Endpoints i Kilo Code. Aquests sí (secció 3).

## 2. Capes gratuïtes oficials que valen la pena (clau gratuïta, sense targeta)

| proveïdor | models que ens interessen | límit gratuït | privadesa | endoll |
|---|---|---|---|---|
| **Google AI Studio (Gemini)** | Gemini 3.8 Flash, 3.5 Flash-Lite, Gemma 4 31B | capa gratuïta per clau d'AI Studio (no és la clau de pagament que tenim, que és a 402) | **les peticions gratuïtes poden servir per entrenar** | el nostre `gemini_client.py` tal qual, amb la clau nova |
| **Groq** | `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` | 30 crides/min, 1.000/dia, 200.000 fitxes/dia | capa gratuïta: no entrena amb les dades segons els seus termes (comprovar) | OpenAI-compatible, `https://api.groq.com/openai/v1` |
| **OpenRouter** | 17 models `:free` (Gemma 4 31B, Nemotron 3 Ultra 550B, Nemotron nano omni amb àudio) | 20 crides/min, **50/dia** (1.000/dia si un dia hi poses 10 $) | els `:free` poden enviar-se a proveïdors que entrenen | OpenAI-compatible, `https://openrouter.ai/api/v1` |
| **Cloudflare Workers AI** | Llama 3.3 70B, gpt-oss-120b, Gemma 4 26B, Whisper | 10.000 «neurones»/dia (unes desenes de milers de fitxes) | compte de Cloudflare (ja en tenim un per R2) | OpenAI-compatible per compte |
| **Mistral La Plateforme** | Mistral Small, Codestral, 10 models | capa «experiment» amb límit mensual, cal acceptar que les dades s'usin per millorar | **entrena amb les dades** a la capa gratuïta | OpenAI-compatible |
| **Cohere** | Command A, **Command A Translate**, Aya Expanse 32B, Command R7B Arabic | 1.000 crides/mes, només ús no comercial | clau «trial» | OpenAI-compatible `https://api.cohere.ai/compatibility/v1` |
| **NVIDIA NIM** | 100+ models (Nemotron, gpt-oss, Llama, Qwen) | sense taula pública; verificació per telèfon | compte de desenvolupador | OpenAI-compatible |
| **Z AI (Zhipu)** | GLM-4.7-Flash, GLM-4.6V-Flash | 1 petició concurrent, permanent | compte xinès amb telèfon estranger acceptat | OpenAI-compatible |
| **Model Studio (Alibaba)** — ja el tenim | Qwen 3.8 Max, Qwen4 Max, qwen-image, qwen3-vl, omni, DeepSeek servit | 1 M fitxes per model durant 91 dies | ja està mesurat i endollat | `qwen_client.py` |

Capes **sense ni clau ni compte**: OVHcloud AI Endpoints (2 crides/min per model i IP; Qwen3.5-397B,
gpt-oss-120b, Qwen3.8-27B, Llama 3.3 70B, Mistral Small, Whisper large v3, servidors a la UE) i Kilo
Code (`kilo-auto/free`, Nemotron 3 Ultra 550B, uns 200 crides/hora). LLM7 també, però gira el catàleg
cada setmana.

No val la pena: Aion Labs (joc de rol), Gonka (telèfon, 1 M/mes), SiliconFlow (identitat xinesa),
ModelScope API (compte xinès; a més ja tenim Model Studio), Chutes, Glhf.

## 3. Què ens serveix de debò, per feina

El que hem après aquests dos dies mana sobre la llista: **cap model entén l'amazic** (chrF 0,3-0,5
contra el parlant; `models-de-text.md`), i els models sí que saben català, àrab, francès i anglès.
Per tant un model gratuït nou no és un traductor d'amazic nou; és un **auditor** o un **redactor** més.

| feina | què demana | candidats gratuïts | com |
|---|---|---|---|
| auditor de traduccions (regla «dos de tres») | català bo, obeir el format, temperatura 0, barat | Qwen 3.8 Max (ja), DeepSeek Chat (0,75 $/1.600), **Groq gpt-oss-120b** (gratis, ràpid), Gemma 4 31B a OpenRouter (50/dia: poc) | `audita.py` ja accepta qualsevol OpenAI-compatible: afegir una entrada a `AUDITORS` |
| àrab → català (Baba Ali, subtítols en dàrija de TFA) | àrab bo | Qwen, DeepSeek, **Cohere Command R7B Arabic / Command A Translate** (1.000/mes), gpt-oss-120b | el mateix client |
| esborrany català d'una frase amaziga | el millor possible, i que no s'inventi | Qwen 3.8 Max (0,47), **Google Translate `ber`** (0,43, sense clau), deepseek-v4-pro quan contesta (0,58) | `compara_models*.py` |
| escena per a un dibuix, resum, redacció de lliçó en català | català natural | Gemini Flash gratuït, gpt-oss-120b, Qwen | `serveis.py` |
| transcriure dàrija o àrab d'àudio | ASR àrab | Whisper large v3 a OVH (sense clau) o Cloudflare; `qwen3.8-omni` a Model Studio | nou client d'àudio |
| OCR de tifinag / àrab | visió | `qwen3-vl-plus`, `qwen-vl-ocr` (Model Studio), Gemma 4 amb imatge (OpenRouter) | el lector de plantilles segueix sent millor per a aslmdtv |

El que **no** s'ha de fer amb cap capa gratuïta que entreni amb les dades (Gemini gratuït, Mistral
experiment, OpenRouter `:free`): enviar-hi text de parlants que no sigui ja públic a la biblioteca,
ni res del material de tercers que tenim amb permís d'ús però no de redistribució. El text del
Mètode, els subtítols de Zouhir o els guions de StoryChannel no hi van. Les frases de la biblioteca
pública i el català de la màquina sí.

## 4. Com s'endollen (una tarda de feina, no més)

El backend ja parla amb tres cases amb la mateixa forma (`gemini_client`, `deepseek_client`,
`qwen_client`: `*_generate(system, contents, model=…)` i `*_available()`), i `serveis.py` tria per
feina. El pas natural és **un client OpenAI-compatible genèric** parametritzat per proveïdor:

```
PROVEIDORS = {
  "groq":       ("https://api.groq.com/openai/v1",          "GROQ_API_KEY",       "openai/gpt-oss-120b"),
  "openrouter": ("https://openrouter.ai/api/v1",            "OPENROUTER_API_KEY", "google/gemma-4-31b-it:free"),
  "cohere":     ("https://api.cohere.ai/compatibility/v1",  "COHERE_API_KEY",     "command-a-translate"),
  "ovh":        ("https://oai.endpoints.kepler.ai.cloud.ovh.net/v1", None,         "gpt-oss-120b"),
}
```

amb el comptador de `ai_budget` per proveïdor i la regla de `QUOTA_SIGNS` que ja hi ha (davant d'un
402/429 es canvia de casa; davant d'un altre error, no). Les claus les crea en Pablo als taulers de
cada casa i les enganxa a `backend/.env` (mai al xat). Abans d'endollar-ne cap es mesura sobre les 60
frases i els 40 parells d'auditoria de sempre, i només entra el que millora o abarateix sense
empitjorar.

## 5. Mesura dels que van sense clau (OVH i Kilo), sobre les 60 frases de sempre

Amazic → català, mateix encàrrec i mateixa chrF que `compara.py`; 93 minuts per a 300 crides, perquè
OVH deixa 2 per minut i model. Crus a `Veus-tachelhit\_escoltats\models\llmfree\sense_clau_resultat.json`.

| proveïdor | model | buits o errors | chrF (60, buit = 0) | chrF contestades | latència mediana |
|---|---|---|---|---|---|
| OVH | `Qwen3.5-397B-A17B` | **54** | 0,071 | 0,710 (6 frases) | 58 s |
| OVH | `gpt-oss-120b` | 0 | 0,156 | 0,156 | 4 s |
| OVH | `Qwen3.8-27B` | 0 | 0,216 | 0,216 | 17 s |
| Kilo | `nvidia/nemotron-3-ultra-550b-a55b:free` | 11 | 0,279 | 0,342 | 23 s |
| Kilo | `kilo-auto/free` | **52** | 0,027 | 0,206 | 30 s |
| *ref.* `deepseek-chat` / Google `ber` / `qwen3.8-max` / NLLB afinat + pont | | 0 | 0,303 / 0,428 / 0,471 / **0,521** | | 1-3 s |

El que se'n treu: **cap dels que van sense clau serveix per a l'amazic, i la meitat ni contesta.** El
Qwen 397B es menja el sostre raonant (54 buits) i, quan contesta, és el millor de tots (0,71 sobre 6
frases: massa poques per creure-s'ho); el gpt-oss-120b contesta sempre i malament (0,16); el Nemotron
550B, 0,34 quan contesta. Per a feines en català, anglès o àrab aquests punts d'accés poden valer com
a reserva; per a l'amazic, no, i amb 2 crides per minut no valen per a cap lot.

## 6. El que se'n treu

1. **No cal cap compte nou per fer el que fem**: Model Studio (gratis 91 dies) + DeepSeek (cèntims)
   + Google Translate (sense clau) cobreixen auditors, esborranys i àrab. El que afegiria valor de
   debò és **Groq** (gpt-oss-120b com a tercer auditor ràpid i gratuït) i, per a l'àrab, **Cohere
   Command A Translate**: dues claus que en Pablo pot crear en cinc minuts.
2. `llmfree` és per a jugar, no per a un projecte que demana permisos: els seus punts d'accés són
   webs d'altri usades per la porta del darrere.
3. Cap d'aquests models tradueix amazic; més models no és més amazic. L'amazic entra per la veritat
   humana i el lector, no pel traductor.
