# L'estandardització del tifinag de la SNRT: pla d'anàlisi amb IA forta (17-11-2026)

Complement de `tifinag-estandard-i-dialecte.md` (hipòtesi, dades, mètode). Aquí es fixa **qui fa què**, perquè aquesta
feina no és de peó: una taula de correspondències equivocada contamina el traductor i el transcriptor, i és fàcil
d'equivocar-se (cada «regla» que s'hi infereix pot ser un error del transcriptor, un subtítol que resumeix, una
variant de parlant o una errada de l'OCR). Per això hi apliquem els models més forts que tenim, amb control humà.

## 1. Què cal decidir amb cura (i per això requereix IA forta)

| decisió | risc si es fa malament |
|---|---|
| Si una diferència entre el que es diu i el que s'escriu és **sistemàtica** o accidental | una regla falsa entra al traductor |
| Quina part és **ortografia** (convenció de la norma) i quina és **fonètica** (dialecte de debò) | es confon escriptura amb varietat |
| Quina part és **lèxic estàndard** (neologisme de l'IRCAM, sinònim literari) i quina és **morfologia** | es perd el que el parlant diu de veritat |
| Si el subtítol és **transcripció** o **resum/paràfrasi** de la rèplica | es conclou «correspondència» on no n'hi ha |
| Quina varietat parla cada parlant i capítol | es barregen dialectes en una mateixa taula |

## 2. Qui fa què

1. **Producció de les dades** (guions, sense IA): fàbrica a l'ECS → so ↔ tifinag per rèplica; transcriptor (MMS) → tifinag
   «sentit». Alineació a nivell de paraula i caràcter amb pesos (determinista).
2. **Anàlisi lingüística: models forts, dues passades independents.** Per a cada lot de parelles (estàndard, sentit):
   - Passada A: `qwen3.8-max` (i `qwen4-max` com a tercer): classifica cada diferència en `ortografia`, `fonètica regular`,
     `morfologia`, `lèxic`, `resum del subtítol`, `error del transcriptor`, `no ho sé`, i proposa la regla en forma
     `estàndard → dialecte` amb context (paraula anterior/posterior).
   - Passada B: `deepseek-chat` amb el mateix prompt, sense veure la resposta d'A.
   - Una diferència entra a la taula **només si les dues passades coincideixen en la classe i en la regla**.
   - Els casos de desacord i els `no ho sé` van a una llista de **revisió humana**.
3. **Jutge del director (Claude).** Llegeix **una mostra** de cada classe (50 entrades) i les 30 correspondències més freqüents
   abans que entrin a la taula; si en troba una falsa, el prompt s'arregla i es repeteix tot el lot. És l'únic pas on usem el
   model més potent disponible: poc text, molt criteri.
4. **Validació humana (en Pablo, o un parlant).** Una mostra de 20 correspondències per varietat, en un full curt (estàndard,
   dialecte, exemple amb enllaç al segon del vídeo, casella «és així / no / no sé»). Cap regla no és «confirmada» sense això.
5. **Control de varietat:** la mateixa anàlisi sobre parlants amb varietat coneguda (Aït Mraw, Beni Mellal, Souss); la taula
   ha de **discriminar**, si no, el mètode no és vàlid.

## 3. Sortides

- `TD_TV/_varietat/correspondencies.jsonl`: una fila per correspondència amb classe, regla, comptes, parlants i capítols
  on apareix, exemples (id de rèplica + segon), acord entre passades i estat de validació.
- `CORRESPONDENCIES.md`: les cent més freqüents, llegible.
- `revisio_humana.html`: el full per a en Pablo.
- Cap sortida va a producció ni es publica (permís SNRT: recerca sí, republicar no).

## 4. Portes (números, no opinions)

- **Entra a la taula** una correspondència amb: ≥ 8 aparicions en ≥ 3 capítols i ≥ 2 parlants diferents; acord de les dues
  passades; no explicada per un error del transcriptor (la mateixa paraula llegida bé en un altre lloc).
- **Confirmada** només després de la validació humana de la mostra (≥ 80 % «és així»).
- **El control de varietat passa** si les correspondències difereixen entre varietats de referència (p. ex. Jaccard < 0,7
  de les 50 més freqüents) i no entre mostres de la mateixa varietat.

## 5. Quan s'activa

Necessita (a) el transcriptor millor (pas 6 del pla), (b) tifinag de la cadena a escala (fàbrica en curs), (c) un parell de
parlants de referència. Fins llavors: una **passada de prova sobre 20 rèpliques** per afinar el prompt i veure si hi ha
senyal. Tota la feina de la fase 2 usa quota de text de Qwen (gratuïta) i DeepSeek (límit 4 €); res de visió, res de Gemini.

## 6. Riscos

Hipòtesi no provada; el transcriptor imperfecte (CER 0,15) fa passar soroll per «dialecte»; el subtítol resumeix; els
parlants són pocs. Per això la validació humana és obligatòria i la taula es versiona (cada canvi, amb els números).
