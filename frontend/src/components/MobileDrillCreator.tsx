import { useCallback, useEffect, useRef, useState } from 'react';
import {
    FaCamera, FaCheck, FaChevronDown, FaKeyboard, FaMicrophone, FaPlay,
    FaPlus, FaRedo, FaTimes, FaVideo,
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
 *  · **El «+» fa la següent** sense sortir de la pantalla: tres toc i ja ets a la frase de
 *    després, que és el que decideix si se'n capturen tres o trenta en una tarda.
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

export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    const tempId = useRef(idProvisional());
    const serverIdRef = useRef<number | null>(null);
    const creating = useRef<Promise<number> | null>(null);

    const [drill, setDrill] = useState<Partial<Drill>>({ text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '' });
    const drillRef = useRef(drill);
    drillRef.current = drill;

    const [gravant, setGravant] = useState<Gravant>(null);
    const gravantRef = useRef<Gravant>(null);
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [previewVideo, setPreviewVideo] = useState<string | null>(null);
    const [previewAudio, setPreviewAudio] = useState<string | null>(null);
    const [busy, setBusy] = useState<string | null>(null);
    const [estat, setEstat] = useState<string>('');
    const [obertText, setObertText] = useState(false);
    const [corpusConsent, setCorpusConsent] = useState(true);
    const [fetes, setFetes] = useState(0);
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

    // L'esborrany: el que s'ha escrit no es perd si entra una trucada o es tanca sense voler (#372).
    const [recuperat, setRecuperat] = useState(false);
    useEffect(() => {
        try {
            const cru = localStorage.getItem(ESBORRANY);
            if (!cru) return;
            const d = JSON.parse(cru) as Partial<Drill>;
            if (!hasText(d)) return;
            setDrill(prev => ({ ...prev, ...d }));
            setRecuperat(true);
        } catch { /* sense magatzem no hi ha esborrany, i prou */ }
    }, []);
    useEffect(() => {
        try {
            if (hasText(drill)) localStorage.setItem(ESBORRANY, JSON.stringify({
                text_catalan: drill.text_catalan, text_tachelhit: drill.text_tachelhit,
                text_tachelhit_suggested: drill.text_tachelhit_suggested, tag: drill.tag,
            }));
            else localStorage.removeItem(ESBORRANY);
        } catch { /* ídem */ }
    }, [drill.text_catalan, drill.text_tachelhit, drill.text_tachelhit_suggested, drill.tag]);

    useEffect(() => () => {
        [previewImage, previewVideo, previewAudio].forEach(u => { if (u?.startsWith('blob:')) URL.revokeObjectURL(u); });
    }, [previewImage, previewVideo, previewAudio]);

    const licenseFor = () => (corpusConsent ? 'CC-BY-SA' : 'private');

    /** Es crea la frase al servidor una sola vegada, el primer cop que fa falta un id. */
    const ensureServerDrill = async (): Promise<number> => {
        if (serverIdRef.current) return serverIdRef.current;
        if (creating.current) return creating.current;
        creating.current = (async () => {
            const res = await axios.post(`${API_BASE}/drills/`, { ...drillRef.current, license: licenseFor() });
            const id: number = res.data.id;
            serverIdRef.current = id;
            setDrill(prev => ({ ...res.data, ...prev, id }));
            return id;
        })().finally(() => { creating.current = null; });
        return creating.current;
    };

    /** Desa (PUT amb xarxa, cua al telèfon sense). Tot passa per aquí: no hi ha botó «Desa». */
    const desa = useCallback(async (fields: Partial<Drill>): Promise<void> => {
        const payload = { ...fields, license: licenseFor() };
        if (await isOnline()) {
            const id = await ensureServerDrill();
            const res = await axios.put(`${API_BASE}/drills/${id}`, payload);
            setDrill(prev => ({ ...prev, ...res.data, ...fields }));
            setEstat('desat');
            return;
        }
        if (!isNativeApp()) throw new Error('Sense connexió: no es pot desar des del navegador.');
        await syncManager.queueAction({
            type: serverIdRef.current ? 'UPDATE' : 'CREATE',
            drillId: serverIdRef.current ?? tempId.current,
            payload: {
                ...drillRef.current, ...payload,
                id: serverIdRef.current ?? tempId.current,
                is_local: !serverIdRef.current, date_created: new Date().toISOString(),
            } as Drill,
        });
        setEstat('al telèfon');
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [corpusConsent]);

    /**
     * Desa sol, sense que ningú premi res.
     *
     * Espera un segon i mig des de l'últim canvi: amb algú al davant dictant, desar a cada lletra
     * ompliria la cua de versions a mig fer. Només desa quan hi ha alguna cosa que valgui la pena.
     */
    const primer = useRef(true);
    useEffect(() => {
        if (primer.current) { primer.current = false; return; }
        if (!hasText(drill) && !hasMedia(drill)) return;
        setEstat('desant…');
        const t = window.setTimeout(() => {
            desa({
                text_catalan: drill.text_catalan, text_tachelhit: drill.text_tachelhit,
                text_tachelhit_suggested: drill.text_tachelhit_suggested, tag: drill.tag,
            }).catch(() => setEstat('no s’ha pogut desar'));
        }, 1500);
        return () => window.clearTimeout(t);
    }, [drill.text_catalan, drill.text_tachelhit, drill.text_tachelhit_suggested, drill.tag, desa]);

    const posa = (field: keyof Drill, value: string) => setDrill(prev => ({ ...prev, [field]: value }));

    /** Puja un fitxer i enganxa la seva adreça a la frase. Sense xarxa, es queda a la cua. */
    const enganxa = async (blob: Blob, kind: MediaKind, prefix?: string) => {
        const fileName = fileNameFor(blob, kind, prefix);
        const previewUrl = URL.createObjectURL(blob);
        if (kind === 'image') setPreviewImage(previewUrl);
        if (kind === 'video') setPreviewVideo(previewUrl);
        if (kind === 'audio') setPreviewAudio(previewUrl);

        setBusy(kind);
        try {
            if (await isOnline()) {
                const id = await ensureServerDrill();
                const fd = new FormData();
                fd.append('file', blob, fileName);
                const res = await axios.post(`${API_BASE}/upload-media/${id}/${kind}`, fd);
                const url: string | undefined = res.data?.url;
                if (!url) throw new Error('El servidor no ha retornat cap URL');
                setDrill(prev => ({ ...prev, [`${kind}_url`]: url }));
                setEstat('desat');
                return url;
            }
            if (!isNativeApp()) throw new Error('Sense connexió: no es pot pujar des del navegador.');
            await syncManager.saveMediaLocally(blob, fileName);
            await syncManager.queueAction({
                type: 'UPLOAD_MEDIA', drillId: serverIdRef.current ?? tempId.current,
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
        try {
            const r = await VoiceRecorder.stopRecording();
            const b64 = r.value?.recordDataBase64;
            if (!b64) return;
            const mime = r.value.mimeType || 'audio/aac';
            const blob = await (await fetch(`data:${mime};base64,${b64}`)).blob();
            const url = await enganxa(blob, 'audio', 'rec');
            if (url) void transcriuAmazic(url);
        } catch (err: any) {
            toast.error(`Micròfon: ${errMsg(err, 'error en aturar')}`);
        }
    };

    /**
     * El que diu la gravació en amazic, quan es pot.
     *
     * Va a `text_tachelhit_suggested` i mai al camp del parlant: ho ha escrit una màquina i ho ha
     * de confirmar una persona. Si no hi ha xarxa no passa res: la gravació ja és desada i això
     * es podrà fer un altre dia des de la fitxa.
     */
    const transcriuAmazic = async (audioUrl: string) => {
        if (!(await isOnline())) return;
        setBusy('transcriu');
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: audioUrl });
            const text = (res.data?.corrected_transcription || '').trim();
            if (text) {
                setDrill(prev => ({ ...prev, text_tachelhit_suggested: text }));
                toast.info('Transcrit: mira-ho abans de donar-ho per bo');
            }
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
            await SpeechRecognition.removeAllListeners();
            SpeechRecognition.addListener('partialResults', (data: any) => {
                if (data.matches?.length) posa('text_catalan', data.matches[0]);
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
            await enganxa(blob, 'image', 'foto');
        } catch (err: any) {
            const m = String(err?.message || '');
            if (/cancel/i.test(m)) return;            // tancar la càmera no és cap error
            toast.error(whyItFailed(err, `Càmera: ${errMsg(err, 'no disponible')}`));
        }
    };

    const fesVideo = () => document.getElementById('native-video-input')?.click();

    const deFitxer = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (file) await enganxa(file, kindOf(file, 'video'));
    };

    // ── La següent ───────────────────────────────────────────────────────────────────────────

    /** Desa el que hi ha i deixa la pantalla a punt per a la frase següent, sense sortir-ne. */
    const seguent = async () => {
        if (hasText(drillRef.current) || hasMedia(drillRef.current)) {
            try {
                await desa({
                    text_catalan: drill.text_catalan, text_tachelhit: drill.text_tachelhit,
                    text_tachelhit_suggested: drill.text_tachelhit_suggested, tag: drill.tag,
                });
            } catch { /* el que no s'ha pogut desar ja ho diu l'estat */ }
            onDrillCreated(serverIdRef.current ?? undefined);
            setFetes(n => n + 1);
        }
        tempId.current = idProvisional();
        serverIdRef.current = null;
        setDrill({ text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '' });
        setPreviewImage(null); setPreviewVideo(null); setPreviewAudio(null);
        setEstat(''); setRecuperat(false);
        try { localStorage.removeItem(ESBORRANY); } catch { /* ídem */ }
    };

    const tanca = async () => {
        if (hasText(drillRef.current) || hasMedia(drillRef.current)) {
            try {
                await desa({
                    text_catalan: drill.text_catalan, text_tachelhit: drill.text_tachelhit,
                    text_tachelhit_suggested: drill.text_tachelhit_suggested, tag: drill.tag,
                });
                try { localStorage.removeItem(ESBORRANY); } catch { /* ídem */ }
            } catch { /* ídem */ }
            onDrillCreated(serverIdRef.current ?? undefined);
        }
        onClose();
    };

    const sona = (url: string | null) => { if (url) new Audio(url).play().catch(() => {}); };
    const audioPreview = previewAudio || (drill.audio_url ? getMediaUrl(drill.audio_url) : null);
    const imatgePreview = previewImage || (drill.image_url ? getMediaUrl(drill.image_url) : null);
    const videoPreview = previewVideo || (drill.video_url ? getMediaUrl(drill.video_url) : null);

    return (
        <div style={full}>
            <header style={cap}>
                <button onClick={tanca} aria-label="Tanca" style={icona}><FaTimes size={18} /></button>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <strong style={{ fontSize: 16 }}>Frase nova</strong>
                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                        {estat || (fetes ? `${fetes} fetes en aquesta estona` : 'Prem i parla; es desa sol')}
                        {pendents > 0 && <> · <span style={{ color: 'var(--amber-strong, var(--text-soft))' }}>{pendents} esperen senyal</span></>}
                    </div>
                </div>
                <button onClick={seguent} aria-label="Desa i fes-ne una altra" style={mes}><FaPlus size={20} /></button>
            </header>

            <div style={cos}>
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

                {(drill.text_catalan || drill.text_tachelhit || drill.text_tachelhit_suggested) && (
                    <div style={fitxa}>
                        {drill.text_catalan && <p style={{ margin: 0, fontSize: 16 }}>{drill.text_catalan}</p>}
                        {drill.text_tachelhit && <p style={{ margin: 0, fontSize: 16, fontWeight: 700 }} lang="shi">{drill.text_tachelhit}</p>}
                        {!drill.text_tachelhit && drill.text_tachelhit_suggested && (
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
