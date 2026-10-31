import { useCallback, useEffect, useRef, useState } from 'react';
import {
    FaCamera, FaCheck, FaChevronDown, FaChevronLeft, FaChevronRight, FaKeyboard,
    FaMicrophone, FaPlay, FaPlus, FaRedo, FaTimes, FaVideo,
} from 'react-icons/fa';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { API_BASE, getMediaUrl, isNativeApp } from '../config';
import { syncManager, type Drill } from '../services/OfflineSyncManager';
import { toast } from '../toast';
import { fileNameFor, kindOf, type MediaKind } from '../utils/media';
import { whyItFailed } from '../utils/errors';

interface MobileDrillCreatorProps {
    onClose: () => void;
    /** L'id del que s'ha fet, quan n'hi ha: el taller de pràctica vol saber quina frase posar a la
     *  seqüència. Sense connexió encara no hi ha id de debò i no se'n diu cap. */
    onDrillCreated: (drillId?: number) => void;
}

/**
 * Fer una frase nova al telèfon: prémer i parlar (#450).
 *
 * En Pablo, mirant la pantalla vella: «això s'ha de millorar moltíssim». El que hi havia era un
 * formulari —quatre camps per escriure i, al peu, cinc icones petites—, o sigui que el primer que
 * es demanava era ESCRIURE. Qui té al davant algú que parla la llengua no té temps d'escriure
 * res: el que ha de poder fer és prémer i que quedi gravat.
 *
 * El que mana aquí:
 *  · **Dos micròfons, no un**, i a dalt de tot: un per a l'amazic i un per al català. Un de sol
 *    no deia mai de quina llengua era el que s'hi deia.
 *  · **Es grava mentre es té premut.** Deixar anar acaba. Res de prémer per començar i tornar a
 *    prémer per acabar: amb algú al davant, el segon toc no arriba.
 *  · **Es desa tot sol**, al telèfon, de seguida. Sense connexió també: la frase surt i puja quan
 *    hi hagi senyal. Res no espera un botó «Desa».
 *  · **El text ve després.** El català es dicta amb el reconeixedor del mateix telèfon, que va
 *    sense connexió; l'amazic es transcriu quan es pugui, i va a `text_tachelhit_suggested`
 *    —mai al camp del parlant, que no és d'una màquina (ADR 0003).
 *  · **La màquina sempre diu la seva**, i es veu al costat: la transcripció es demana a cada
 *    gravació, encara que la frase ja porti text escrit, i del que la màquina ha sentit se'n
 *    demana el significat en català, que es mostra entre parèntesis darrere el teu. Serveix per
 *    veure de seguida si la màquina ha entès el mateix que tu —sovint no— i va a
 *    `text_catalan_suggested`, no al camp del significat.
 *  · **El «+» fa la següent** sense sortir de la pantalla: tres toc i ja ets a la frase de
 *    després, que és el que decideix si se'n capturen tres o trenta en una tarda.
 *  · **I s'hi pot tornar.** Les frases d'aquesta estona queden en una tira: amb les fletxes
 *    s'hi va endavant i enrere, s'escolten i es corregeixen sense sortir de la pantalla.
 */

const errMsg = (err: any, fallback: string) =>
    err?.response?.data?.detail || err?.message || fallback;

const isOnline = async () => (await Network.getStatus()).connected;

/** On es guarda el que s'escriu mentre la frase no és desada. */
const ESBORRANY = 'td_esborrany_frase';

const hasText = (d: Partial<Drill>) => !!(d.text_catalan?.trim() || d.text_tachelhit?.trim() || d.text_arabic?.trim());
const hasMedia = (d: Partial<Drill>) => !!(d.audio_url || d.video_url || d.image_url);

type Gravant = null | 'shi' | 'ca';

/**
 * L'identificador provisional d'una frase feta sense connexió.
 *
 * `Date.now()` sol no bastava: fent-ne una darrere l'altra, dues poden caure al mateix
 * mil·lisegon i llavors la segona s'hi enganxaria a sobre —la cua busca el CREATE «d'aquest
 * drill» pel número. El comptador ho impedeix, i el número segueix sent prou gran per no topar
 * mai amb cap id del servidor.
 */
let seguitProvisional = 0;
const idProvisional = () => Date.now() * 1000 + (seguitProvisional++ % 1000);

/**
 * Una frase de l'estona: la seva, amb el seu id i les seves gravacions.
 *
 * Abans la pantalla només tenia la d'ara, i en prémer «+» l'anterior desapareixia de la vista.
 * Qui grava deu frases seguides amb algú al davant necessita poder tornar enrere a escoltar la
 * que acaba de fer —i corregir-ne el text— sense anar a buscar-la a la biblioteca. Els camps es
 * canvien a dins de l'objecte perquè una pujada que torna mig segon després trobi la seva frase
 * i no la que ara es té a la pantalla.
 */
type Entrada = {
    tempId: number;
    serverId: number | null;
    creant: Promise<number> | null;
    d: Partial<Drill>;
    /** Les adreces `blob:` del que s'acaba de gravar: deixen escoltar-ho també sense senyal. */
    pAudio: string | null;
    pImg: string | null;
    pVid: string | null;
};

const novaEntrada = (): Entrada => ({
    tempId: idProvisional(), serverId: null, creant: null,
    d: { text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '' },
    pAudio: null, pImg: null, pVid: null,
});

export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    // `entradesRef` és qui manda: les crides que tornen d'una pujada o d'una transcripció hi
    // escriuen de seguida, i `setEntrades` només serveix per tornar a pintar.
    const [entrades, setEntrades] = useState<Entrada[]>(() => [novaEntrada()]);
    const entradesRef = useRef(entrades);
    const [i, setI] = useState(0);
    const iRef = useRef(0);

    const refresca = useCallback(() => setEntrades([...entradesRef.current]), []);
    /** L'entrada que es té a la pantalla ara mateix. */
    const act = useCallback(() => entradesRef.current[iRef.current], []);
    const posaD = useCallback((e: Entrada, canvis: Partial<Drill>) => {
        e.d = { ...e.d, ...canvis };
        refresca();
    }, [refresca]);

    const [gravant, setGravant] = useState<Gravant>(null);
    const gravantRef = useRef<Gravant>(null);
    const [busy, setBusy] = useState<string | null>(null);
    const [estat, setEstat] = useState<string>('');
    const [obertText, setObertText] = useState(false);
    const [corpusConsent, setCorpusConsent] = useState(true);
    /** Quantes coses esperen senyal. Una cua silenciosa és una cua que algú es pensa que ha perdut. */
    const [pendents, setPendents] = useState(0);
    const compta = useCallback(() => {
        syncManager.getQueue().then(q => setPendents(q.length)).catch(() => {});
    }, []);
    useEffect(() => {
        compta();
        const t = window.setInterval(compta, 4000);
        return () => window.clearInterval(t);
    }, [compta]);

    useEffect(() => {
        if (!isNativeApp()) return;
        // Un cop, en obrir: així el primer «mantén premut» ja grava en comptes de demanar permís.
        VoiceRecorder.requestAudioRecordingPermission().catch(() => {});
        SpeechRecognition.requestPermissions().catch(() => {});
        Camera.requestPermissions().catch(() => {});
    }, []);

    const drill = entrades[i]?.d ?? {};

    // L'esborrany: el que s'ha escrit no es perd si entra una trucada o es tanca sense voler (#372).
    const [recuperat, setRecuperat] = useState(false);
    useEffect(() => {
        try {
            const cru = localStorage.getItem(ESBORRANY);
            if (!cru) return;
            const d = JSON.parse(cru) as Partial<Drill>;
            if (!hasText(d)) return;
            posaD(entradesRef.current[0], d);
            setRecuperat(true);
        } catch { /* sense magatzem no hi ha esborrany, i prou */ }
    }, [posaD]);
    useEffect(() => {
        try {
            if (hasText(drill)) localStorage.setItem(ESBORRANY, JSON.stringify({
                text_catalan: drill.text_catalan, text_tachelhit: drill.text_tachelhit,
                text_tachelhit_suggested: drill.text_tachelhit_suggested,
                text_catalan_suggested: drill.text_catalan_suggested, tag: drill.tag,
            }));
            else localStorage.removeItem(ESBORRANY);
        } catch { /* ídem */ }
    }, [drill.text_catalan, drill.text_tachelhit, drill.text_tachelhit_suggested, drill.text_catalan_suggested, drill.tag, drill]);

    useEffect(() => () => {
        entradesRef.current.forEach(e => {
            [e.pAudio, e.pImg, e.pVid].forEach(u => { if (u?.startsWith('blob:')) URL.revokeObjectURL(u); });
        });
    }, []);

    const licenseFor = () => (corpusConsent ? 'CC-BY-SA' : 'private');

    /**
     * Es crea la frase al servidor una sola vegada, el primer cop que fa falta un id.
     *
     * `capturing` diu que la gravació ja és a la mà: amb els micròfons, el primer que es fa és
     * gravar i encara no hi ha cap text, i el servidor no deixa crear files en blanc. Qui ho
     * demana explícitament sí que pot, perquè el fitxer hi arriba tot seguit (#450).
     */
    const ensureServerDrill = useCallback(async (e: Entrada, capturant = false): Promise<number> => {
        if (e.serverId) return e.serverId;
        if (e.creant) return e.creant;
        e.creant = (async () => {
            const res = await axios.post(`${API_BASE}/drills/`, {
                ...e.d, license: licenseFor(), ...(capturant ? { capturing: true } : {}),
            });
            const id: number = res.data.id;
            e.serverId = id;
            e.d = { ...res.data, ...e.d, id };
            refresca();
            return id;
        })().finally(() => { e.creant = null; });
        return e.creant;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [corpusConsent, refresca]);

    /** Desa (PUT amb xarxa, cua al telèfon sense). Tot passa per aquí: no hi ha botó «Desa». */
    const desa = useCallback(async (e: Entrada, fields: Partial<Drill>): Promise<void> => {
        const payload = { ...fields, license: licenseFor() };
        if (await isOnline()) {
            const id = await ensureServerDrill(e);
            const res = await axios.put(`${API_BASE}/drills/${id}`, payload);
            e.d = { ...e.d, ...res.data, ...fields };
            refresca();
            setEstat('desat');
            return;
        }
        if (!isNativeApp()) throw new Error('Sense connexió: no es pot desar des del navegador.');
        await syncManager.queueAction({
            type: e.serverId ? 'UPDATE' : 'CREATE',
            drillId: e.serverId ?? e.tempId,
            payload: {
                ...e.d, ...payload,
                id: e.serverId ?? e.tempId,
                is_local: !e.serverId, date_created: new Date().toISOString(),
            } as Drill,
        });
        setEstat('al telèfon');
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [corpusConsent, ensureServerDrill, refresca]);

    /** El que es desa d'una frase: els textos i l'etiqueta. Els fitxers van pel seu compte. */
    const textos = (d: Partial<Drill>): Partial<Drill> => ({
        text_catalan: d.text_catalan, text_tachelhit: d.text_tachelhit,
        text_tachelhit_suggested: d.text_tachelhit_suggested,
        text_catalan_suggested: d.text_catalan_suggested, tag: d.tag,
    });

    /**
     * Desa sol, sense que ningú premi res.
     *
     * Espera un segon i mig des de l'últim canvi: amb algú al davant dictant, desar a cada lletra
     * ompliria la cua de versions a mig fer. Només desa quan hi ha alguna cosa que valgui la pena.
     *
     * Canviar de frase amb les fletxes no és un canvi a desar: el que entra a la pantalla ja és
     * desat, i tornar-lo a enviar ompliria la cua de còpies. Per això se salta la passada que ve
     * just després d'un salt.
     */
    const primer = useRef(true);
    const darrerI = useRef(0);
    useEffect(() => {
        if (primer.current) { primer.current = false; darrerI.current = i; return; }
        if (darrerI.current !== i) { darrerI.current = i; return; }
        if (!hasText(drill) && !hasMedia(drill)) return;
        const e = entradesRef.current[i];
        if (!e) return;
        setEstat('desant…');
        const t = window.setTimeout(() => {
            desa(e, textos(e.d)).catch(() => setEstat('no s’ha pogut desar'));
        }, 1500);
        return () => window.clearTimeout(t);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [drill.text_catalan, drill.text_tachelhit, drill.text_tachelhit_suggested, drill.text_catalan_suggested, drill.tag, i, desa]);

    const posa = (field: keyof Drill, value: string) => posaD(act(), { [field]: value } as Partial<Drill>);

    /** Puja un fitxer i enganxa la seva adreça a la frase. Sense xarxa, es queda a la cua. */
    const enganxa = async (e: Entrada, blob: Blob, kind: MediaKind, prefix?: string) => {
        const fileName = fileNameFor(blob, kind, prefix);
        const previewUrl = URL.createObjectURL(blob);
        if (kind === 'image') e.pImg = previewUrl;
        if (kind === 'video') e.pVid = previewUrl;
        if (kind === 'audio') e.pAudio = previewUrl;
        refresca();

        setBusy(kind);
        try {
            if (await isOnline()) {
                const id = await ensureServerDrill(e, true);
                const fd = new FormData();
                fd.append('file', blob, fileName);
                const res = await axios.post(`${API_BASE}/upload-media/${id}/${kind}`, fd);
                const url: string | undefined = res.data?.url;
                if (!url) throw new Error('El servidor no ha retornat cap URL');
                posaD(e, { [`${kind}_url`]: url } as Partial<Drill>);
                setEstat('desat');
                return url;
            }
            if (!isNativeApp()) throw new Error('Sense connexió: no es pot pujar des del navegador.');
            // Primer que existeixi la frase, i després el fitxer.
            //
            // Sense això, gravar sense connexió deixava a la cua una pujada per a una frase que
            // no s'havia demanat mai: quan tornava el senyal, el fitxer no tenia on anar. La
            // cua ja ajunta els CREATE d'una mateixa frase, de manera que fer-ho a cada fitxer
            // no en crea dos (#450).
            if (!e.serverId) {
                await syncManager.queueAction({
                    type: 'CREATE', drillId: e.tempId,
                    payload: {
                        ...e.d, id: e.tempId, is_local: true,
                        license: licenseFor(), capturing: true,
                        date_created: new Date().toISOString(),
                    } as unknown as Drill,
                });
            }
            await syncManager.saveMediaLocally(blob, fileName);
            await syncManager.queueAction({
                type: 'UPLOAD_MEDIA', drillId: e.serverId ?? e.tempId,
                mediaType: kind, localPath: fileName, fileName,
            });
            setEstat('al telèfon, pujarà sol');
            return null;
        } catch (err: any) {
            toast.error(`No s'ha pogut desar: ${errMsg(err, 'error')}`);
            return null;
        } finally {
            setBusy(null);
        }
    };

    // ── Els dos micròfons ────────────────────────────────────────────────────────────────────

    /** La veu en amazic: la gravació és el que val, i el text ve després si es pot. */
    const comencaAmazic = async () => {
        if (gravantRef.current) return;
        try {
            if (isNativeApp()) {
                const perm = await VoiceRecorder.hasAudioRecordingPermission();
                if (!perm.value && !(await VoiceRecorder.requestAudioRecordingPermission()).value) {
                    return toast.error('Cal permís de micròfon');
                }
            }
            const r = await VoiceRecorder.startRecording();
            if (r.value) { gravantRef.current = 'shi'; setGravant('shi'); }
        } catch (err: any) {
            toast.error(whyItFailed(err, `Micròfon: ${errMsg(err, 'no disponible')}`));
        }
    };

    const acabaAmazic = async () => {
        if (gravantRef.current !== 'shi') return;
        gravantRef.current = null; setGravant(null);
        // La frase d'ara, agafada abans de cap espera: el que torni després és SEU, encara que
        // entretant s'hagi passat a una altra amb les fletxes o amb el «+».
        const e = act();
        try {
            const r = await VoiceRecorder.stopRecording();
            const b64 = r.value?.recordDataBase64;
            if (!b64) return;
            const mime = r.value.mimeType || 'audio/aac';
            const blob = await (await fetch(`data:${mime};base64,${b64}`)).blob();
            const url = await enganxa(e, blob, 'audio', 'rec');
            if (url) void transcriuAmazic(e, url);
        } catch (err: any) {
            toast.error(`Micròfon: ${errMsg(err, 'error en aturar')}`);
        }
    };

    /**
     * El que diu la gravació en amazic, i què en vol dir la màquina.
     *
     * Es demana **sempre** que hi hagi senyal, encara que la frase ja porti text escrit o una
     * transcripció d'abans: en Pablo ho va demanar així, i té sentit —el que val d'això no és
     * omplir un buit sinó poder comparar. La transcripció va a `text_tachelhit_suggested` i el
     * seu significat a `text_catalan_suggested`: mai als camps del parlant, que no són d'una
     * màquina (ADR 0003). Si no hi ha xarxa no passa res: la gravació ja és desada i això es
     * podrà fer un altre dia des de la fitxa.
     */
    const transcriuAmazic = async (e: Entrada, audioUrl: string) => {
        if (!(await isOnline())) return;
        setBusy('transcriu');
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: audioUrl });
            const text = (res.data?.corrected_transcription || '').trim();
            if (!text) return;
            posaD(e, { text_tachelhit_suggested: text });
            toast.info('Transcrit: mira-ho abans de donar-ho per bo');
            try {
                const tr = await axios.post(`${API_BASE}/translate`, {
                    text, source_lang: 'shi', target_lang: 'ca',
                });
                const ca = (tr.data?.translated_text || '').trim();
                if (ca) posaD(e, { text_catalan_suggested: ca });
            } catch { /* sense significat, la transcripció ja val per ella mateixa */ }
        } catch { /* la gravació ja hi és: una transcripció que falla no és una frase perduda */ }
        finally { setBusy(null); }
    };

    /** La veu en català (o en la llengua que parlis): el reconeixedor del telèfon, que va sense xarxa. */
    const comencaCatala = async () => {
        if (gravantRef.current) return;
        try {
            if (isNativeApp()) {
                const perm = await SpeechRecognition.checkPermissions();
                if (perm.speechRecognition !== 'granted'
                    && (await SpeechRecognition.requestPermissions()).speechRecognition !== 'granted') {
                    return toast.error('Cal permís de reconeixement de veu');
                }
            }
            if (!(await SpeechRecognition.available())) {
                toast.error('Aquest telèfon no sap dictar: grava l’amazic i escriu el significat');
                return;
            }
            const e = act();
            await SpeechRecognition.removeAllListeners();
            SpeechRecognition.addListener('partialResults', (data: any) => {
                if (data.matches?.length) posaD(e, { text_catalan: data.matches[0] });
            });
            gravantRef.current = 'ca'; setGravant('ca');
            await SpeechRecognition.start({ language: 'ca-ES', partialResults: true, popup: false });
        } catch (err: any) {
            gravantRef.current = null; setGravant(null);
            toast.error(`Dictat: ${err?.code || errMsg(err, 'error')}`);
        }
    };

    const acabaCatala = async () => {
        if (gravantRef.current !== 'ca') return;
        gravantRef.current = null; setGravant(null);
        try { await SpeechRecognition.stop(); } catch { /* ja s'ha aturat sol */ }
    };

    // ── Foto i vídeo ─────────────────────────────────────────────────────────────────────────

    const fesFoto = async () => {
        const e = act();
        try {
            const status = await Camera.requestPermissions();
            if (status.camera !== 'granted' && status.photos !== 'granted') return toast.error('Cal permís de càmera');
            const image = await Camera.getPhoto({
                quality: 80, allowEditing: false, resultType: CameraResultType.Base64,
                source: CameraSource.Camera, correctOrientation: true, width: 1600,
            });
            if (!image.base64String) return;
            const mime = `image/${image.format || 'jpeg'}`;
            const blob = await (await fetch(`data:${mime};base64,${image.base64String}`)).blob();
            await enganxa(e, blob, 'image', 'foto');
        } catch (err: any) {
            const m = String(err?.message || '');
            if (/cancel/i.test(m)) return;            // tancar la càmera no és cap error
            toast.error(whyItFailed(err, `Càmera: ${errMsg(err, 'no disponible')}`));
        }
    };

    const fesVideo = () => document.getElementById('native-video-input')?.click();

    const deFitxer = async (ev: React.ChangeEvent<HTMLInputElement>) => {
        const e = act();
        const file = ev.target.files?.[0];
        ev.target.value = '';
        if (file) await enganxa(e, file, kindOf(file, 'video'));
    };

    // ── Anar d'una a l'altra ─────────────────────────────────────────────────────────────────

    const vesA = useCallback((idx: number) => {
        if (idx < 0 || idx >= entradesRef.current.length) return;
        iRef.current = idx;
        setI(idx);
        setEstat('');
        setRecuperat(false);
    }, []);

    /** Desa el que hi ha i deixa la pantalla a punt per a la frase següent, sense sortir-ne. */
    const seguent = async () => {
        const e = act();
        if (hasText(e.d) || hasMedia(e.d)) {
            try { await desa(e, textos(e.d)); } catch { /* el que no s'ha pogut desar ja ho diu l'estat */ }
            onDrillCreated(e.serverId ?? undefined);
        }
        try { localStorage.removeItem(ESBORRANY); } catch { /* ídem */ }
        // Si l'última de la tira encara és en blanc, no en cal una altra: s'hi va.
        const ultima = entradesRef.current[entradesRef.current.length - 1];
        if (ultima && !hasText(ultima.d) && !hasMedia(ultima.d)) {
            return vesA(entradesRef.current.length - 1);
        }
        entradesRef.current = [...entradesRef.current, novaEntrada()];
        setEntrades(entradesRef.current);
        vesA(entradesRef.current.length - 1);
    };

    const tanca = async () => {
        const e = act();
        if (hasText(e.d) || hasMedia(e.d)) {
            try {
                await desa(e, textos(e.d));
                try { localStorage.removeItem(ESBORRANY); } catch { /* ídem */ }
            } catch { /* ídem */ }
            onDrillCreated(e.serverId ?? undefined);
        }
        onClose();
    };

    const sona = (url: string | null) => { if (url) new Audio(url).play().catch(() => {}); };
    const veuDe = (e: Entrada) => e.pAudio || (e.d.audio_url ? getMediaUrl(e.d.audio_url) : null);
    const entrada = entrades[i];
    const audioPreview = entrada ? veuDe(entrada) : null;
    const imatgePreview = entrada?.pImg || (drill.image_url ? getMediaUrl(drill.image_url) : null);
    const videoPreview = entrada?.pVid || (drill.video_url ? getMediaUrl(drill.video_url) : null);
    const fetes = entrades.filter(e => hasText(e.d) || hasMedia(e.d)).length;

    return (
        <div style={full}>
            <header style={cap}>
                <button onClick={tanca} aria-label="Tanca" style={icona}><FaTimes size={18} /></button>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <strong style={{ fontSize: 16 }}>Frase nova</strong>
                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                        {estat || (fetes ? `${fetes} ${fetes === 1 ? 'feta' : 'fetes'} en aquesta estona` : 'Prem i parla; es desa sol')}
                        {pendents > 0 && <> · <span style={{ color: 'var(--amber-strong, var(--text-soft))' }}>{pendents} esperen senyal</span></>}
                    </div>
                </div>
                <button onClick={seguent} aria-label="Desa i fes-ne una altra" style={mes}><FaPlus size={20} /></button>
            </header>

            <div style={cos}>
                {/* La tira de l'estona: endavant, enrere, i escoltar la que es té al davant. */}
                {entrades.length > 1 && (
                    <div style={tira}>
                        <button onClick={() => vesA(i - 1)} disabled={i === 0} style={{ ...fletxa, opacity: i === 0 ? 0.35 : 1 }}
                                aria-label="La frase d'abans">
                            <FaChevronLeft size={16} />
                        </button>
                        <button onClick={() => sona(audioPreview)} disabled={!audioPreview}
                                style={{ ...rodo, opacity: audioPreview ? 1 : 0.35 }} aria-label="Escolta aquesta">
                            <FaPlay size={13} />
                        </button>
                        <div style={{ flex: 1, minWidth: 0, textAlign: 'center' }}>
                            <div style={{ fontSize: 13, fontWeight: 700 }}>{i + 1} de {entrades.length}</div>
                            <div style={{ fontSize: 11.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {drill.text_catalan?.trim() || drill.text_tachelhit?.trim() || 'encara sense text'}
                            </div>
                        </div>
                        <button onClick={() => vesA(i + 1)} disabled={i >= entrades.length - 1}
                                style={{ ...fletxa, opacity: i >= entrades.length - 1 ? 0.35 : 1 }} aria-label="La frase de després">
                            <FaChevronRight size={16} />
                        </button>
                    </div>
                )}

                {recuperat && (
                    <p style={avis}>Hi havia una frase a mig fer i l’hem recuperada.</p>
                )}

                {/* ELS DOS MICRÒFONS, a dalt de tot i grans: és el que es fa servir sempre. */}
                <button
                    onPointerDown={comencaAmazic} onPointerUp={acabaAmazic} onPointerCancel={acabaAmazic}
                    onContextMenu={(e) => e.preventDefault()}
                    style={{ ...micro, background: gravant === 'shi' ? 'var(--rose)' : 'var(--brand-1)' }}
                    aria-label="Mantén premut i parla en amazic"
                >
                    <FaMicrophone size={30} />
                    <span style={microText}>{gravant === 'shi' ? 'Parla… deixa anar per acabar' : 'Amazic'}</span>
                    <span style={microPeu}>mantén premut i parla</span>
                </button>

                <button
                    onPointerDown={comencaCatala} onPointerUp={acabaCatala} onPointerCancel={acabaCatala}
                    onContextMenu={(e) => e.preventDefault()}
                    style={{ ...micro, background: gravant === 'ca' ? 'var(--rose)' : 'var(--emerald, #2f7d53)' }}
                    aria-label="Mantén premut i digues què vol dir"
                >
                    <FaMicrophone size={30} />
                    <span style={microText}>{gravant === 'ca' ? 'Parla… deixa anar per acabar' : 'Què vol dir'}</span>
                    <span style={microPeu}>en català, i s’escriu sol</span>
                </button>

                <div style={{ display: 'flex', gap: 10 }}>
                    <button onClick={fesFoto} disabled={busy === 'image'} style={{ ...gran, flex: 1 }} aria-label="Fes una foto">
                        <FaCamera size={24} /><span>{busy === 'image' ? 'Pujant…' : 'Foto'}</span>
                    </button>
                    <button onClick={fesVideo} disabled={busy === 'video'} style={{ ...gran, flex: 1 }} aria-label="Fes un vídeo">
                        <FaVideo size={24} /><span>{busy === 'video' ? 'Pujant…' : 'Vídeo'}</span>
                    </button>
                </div>

                {/* El que s'ha capturat. Res d'això no és un formulari: és el que ja tens. */}
                {(audioPreview || imatgePreview || videoPreview || busy === 'transcriu') && (
                    <div style={fitxa}>
                        {audioPreview && (
                            <div style={fila}>
                                <button onClick={() => sona(audioPreview)} style={rodo} aria-label="Escolta la gravació"><FaPlay size={13} /></button>
                                <span style={{ flex: 1, fontSize: 13 }}>La veu en amazic</span>
                                <button onPointerDown={comencaAmazic} onPointerUp={acabaAmazic} style={petit} aria-label="Torna-la a gravar">
                                    <FaRedo size={12} /> Torna-hi
                                </button>
                            </div>
                        )}
                        {busy === 'transcriu' && <p style={{ ...avis, margin: 0 }}>Escoltant el que has gravat…</p>}
                        {imatgePreview && <img src={imatgePreview} alt="" style={{ width: '100%', borderRadius: 'var(--r-md)', maxHeight: 220, objectFit: 'cover' }} />}
                        {videoPreview && <video src={videoPreview} controls playsInline style={{ width: '100%', borderRadius: 'var(--r-md)', maxHeight: 220 }} />}
                    </div>
                )}

                {(drill.text_catalan || drill.text_tachelhit || drill.text_tachelhit_suggested || drill.text_catalan_suggested) && (
                    <div style={fitxa}>
                        {(drill.text_catalan || drill.text_catalan_suggested) && (
                            <p style={{ margin: 0, fontSize: 16 }}>
                                {drill.text_catalan}
                                {drill.text_catalan_suggested && (
                                    <span style={maquina} title="El que la màquina ha entès de la gravació">
                                        {drill.text_catalan ? ' ' : ''}({drill.text_catalan_suggested})
                                    </span>
                                )}
                            </p>
                        )}
                        {drill.text_tachelhit && <p style={{ margin: 0, fontSize: 16, fontWeight: 700 }} lang="shi">{drill.text_tachelhit}</p>}
                        {/* La transcripció es veu SEMPRE, també quan el text ja és escrit: és el que
                            deixa comparar el que has escrit amb el que la màquina ha sentit. */}
                        {drill.text_tachelhit_suggested && (
                            <p style={{ margin: 0, fontSize: 15, fontStyle: 'italic', color: 'var(--text-soft)' }} lang="shi">
                                {drill.text_tachelhit_suggested}
                                <span style={{ fontSize: 11, marginLeft: 6, color: 'var(--text-muted)' }}>(ho ha escrit la màquina)</span>
                            </p>
                        )}
                    </div>
                )}

                {/* Escriure encara es pot, però ha deixat de ser el primer que es demana. */}
                <button onClick={() => setObertText(v => !v)} style={desplega} aria-expanded={obertText}>
                    <FaKeyboard size={13} /> Escriure-ho a mà <FaChevronDown size={11} style={{ transform: obertText ? 'rotate(180deg)' : 'none' }} />
                </button>
                {obertText && (
                    <div style={fitxa}>
                        <label style={etiqueta}>Amazic (el que diu qui parla)
                            <textarea value={drill.text_tachelhit || ''} onChange={e => posa('text_tachelhit', e.target.value)} rows={2} style={camp} lang="shi" />
                        </label>
                        <label style={etiqueta}>Què vol dir, en català
                            <textarea value={drill.text_catalan || ''} onChange={e => posa('text_catalan', e.target.value)} rows={2} style={camp} />
                        </label>
                        <label style={etiqueta}>Etiqueta
                            <input value={drill.tag || ''} onChange={e => posa('tag', e.target.value)} style={{ ...camp, minHeight: 0 }} />
                        </label>
                        <label style={{ ...etiqueta, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                            <input type="checkbox" checked={corpusConsent} onChange={e => setCorpusConsent(e.target.checked)} />
                            <span style={{ fontSize: 12.5, color: 'var(--text-soft)' }}>Que pugui entrar al corpus obert</span>
                        </label>
                    </div>
                )}

                <button onClick={tanca} style={acabar}><FaCheck size={14} /> Ja està</button>
                <input id="native-video-input" type="file" accept="video/*" capture="environment" onChange={deFitxer} style={{ display: 'none' }} />
            </div>
        </div>
    );
}

const full: React.CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 1000, background: 'var(--bg)', display: 'flex', flexDirection: 'column',
};
const cap: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 10, padding: 'calc(10px + env(safe-area-inset-top, 0px)) 12px 10px',
    borderBottom: '1px solid var(--border)', background: 'var(--surface)',
};
const cos: React.CSSProperties = {
    flex: 1, overflowY: 'auto', padding: '14px 12px calc(20px + env(safe-area-inset-bottom, 0px))',
    display: 'flex', flexDirection: 'column', gap: 12,
};
const icona: React.CSSProperties = {
    width: 42, height: 42, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)',
    background: 'var(--surface-2)', color: 'var(--text)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
};
const mes: React.CSSProperties = { ...icona, width: 52, height: 52, background: 'var(--brand-1)', color: '#fff', border: 'none' };
const micro: React.CSSProperties = {
    width: '100%', minHeight: 104, borderRadius: 'var(--r-lg, 16px)', border: 'none', color: '#fff',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4,
    touchAction: 'none', userSelect: 'none', WebkitUserSelect: 'none', cursor: 'pointer',
};
const microText: React.CSSProperties = { fontSize: 18, fontWeight: 800 };
const microPeu: React.CSSProperties = { fontSize: 12, opacity: 0.85 };
const gran: React.CSSProperties = {
    minHeight: 76, borderRadius: 'var(--r-lg, 16px)', border: '1px solid var(--border)', background: 'var(--surface)',
    color: 'var(--text)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6,
    fontSize: 14, fontWeight: 700, cursor: 'pointer',
};
const fitxa: React.CSSProperties = {
    background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
    padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
};
const fila: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 10 };
const tira: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-2)',
    border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', padding: '6px 8px',
};
const fletxa: React.CSSProperties = {
    width: 42, height: 42, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)',
    background: 'var(--surface)', color: 'var(--text)', display: 'inline-flex', alignItems: 'center',
    justifyContent: 'center', flexShrink: 0, cursor: 'pointer',
};
const rodo: React.CSSProperties = {
    width: 38, height: 38, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-1)', color: '#fff',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, cursor: 'pointer',
};
const petit: React.CSSProperties = {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 'var(--r-pill)',
    border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text-soft)', fontSize: 12.5, cursor: 'pointer',
};
const desplega: React.CSSProperties = { ...petit, justifyContent: 'center', padding: '10px 14px' };
const acabar: React.CSSProperties = {
    minHeight: 50, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)',
    color: 'var(--text)', fontSize: 15, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, cursor: 'pointer',
};
const etiqueta: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: 5, fontSize: 12.5, color: 'var(--text-soft)' };
const camp: React.CSSProperties = {
    width: '100%', boxSizing: 'border-box', font: 'inherit', fontSize: 15, padding: '10px 12px',
    borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', minHeight: 44,
};
const avis: React.CSSProperties = { fontSize: 12.5, color: 'var(--text-soft)', margin: 0 };
const maquina: React.CSSProperties = { fontSize: 14, fontStyle: 'italic', color: 'var(--text-muted)' };
