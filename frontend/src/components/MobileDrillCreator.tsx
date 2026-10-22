import { useState, useEffect, useRef } from 'react';
import { FaCamera, FaVideo, FaMicrophone, FaKeyboard, FaFolderOpen, FaVolumeUp, FaFileAlt, FaLanguage, FaSave, FaTimes, FaCut as FaScissors } from 'react-icons/fa';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { API_BASE, getMediaUrl, isNativeApp } from '../config';
import { syncManager, type Drill } from '../services/OfflineSyncManager';
import { toast } from '../toast';
import { fileNameFor, kindOf, type MediaKind } from '../utils/media';

interface MobileDrillCreatorProps {
    onClose: () => void;
    // The id of what was made, when there is one: the practice workshop needs to know which
    // sentence to put in the sequence. Offline the drill has no real id yet, so it is omitted.
    onDrillCreated: (drillId?: number) => void;
}

const errMsg = (err: any, fallback: string) =>
    err?.response?.data?.detail || err?.message || fallback;

const isOnline = async () => (await Network.getStatus()).connected;

/**
 * "Nou drill" sheet.
 *
 * Lifecycle (fixes the three web bugs of the old sheet):
 *  1. The drill is created on the server ONCE, lazily, the first time anything
 *     needs an id (a media upload, an AI action, or Desa). Its real id is kept
 *     in `serverId`; every later action is a PUT / upload against that id.
 *  2. Media is uploaded first and the Cloudinary URL goes into the drill; the
 *     `blob:` object URL is only ever used for the local <audio>/<video> preview
 *     and is never sent to the server.
 *  3. Desa awaits the save before closing, so nothing is lost.
 * Offline (native only) the old queue path is used with a temporary id; the
 * sync manager remaps it when the CREATE is pushed.
 */
export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    const tempId = useRef(Date.now());
    const [serverId, setServerId] = useState<number | null>(null);
    const serverIdRef = useRef<number | null>(null);
    const creating = useRef<Promise<number> | null>(null);

    const [drill, setDrill] = useState<Partial<Drill>>({
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        tag: '',
    });
    // Always read the latest fields from a ref: async handlers (AI calls,
    // uploads) must not save a stale closure of `drill`.
    const drillRef = useRef(drill);
    drillRef.current = drill;

    const [isRecording, setIsRecording] = useState(false);
    const [corpusConsent, setCorpusConsent] = useState(true);
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [previewVideo, setPreviewVideo] = useState<string | null>(null);
    const [previewAudio, setPreviewAudio] = useState<string | null>(null);
    const [busy, setBusy] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [trimTimes, setTrimTimes] = useState({ start: 0, end: 10 });
    const [videoDuration, setVideoDuration] = useState(60);
    const [audioDuration, setAudioDuration] = useState(60);

    useEffect(() => {
        if (isNativeApp()) {
            VoiceRecorder.requestAudioRecordingPermission().catch(e => console.warn('VoiceRecorder permissions not available', e));
            SpeechRecognition.requestPermissions().catch(e => console.warn('SpeechRecognition permissions not available', e));
        }
    }, []);

    // Revoke object URLs when the sheet unmounts.
    useEffect(() => () => {
        [previewImage, previewVideo, previewAudio].forEach(u => { if (u?.startsWith('blob:')) URL.revokeObjectURL(u); });
    }, [previewImage, previewVideo, previewAudio]);

    const licenseFor = () => (corpusConsent ? 'CC-BY-SA' : 'private');

    const hasText = (d: Partial<Drill>) => !!(d.text_catalan?.trim() || d.text_tachelhit?.trim() || d.text_arabic?.trim());
    const hasMedia = (d: Partial<Drill>) => !!(d.audio_url || d.video_url || d.image_url);

    /** Create the server drill once and return its id (serialised). */
    const ensureServerDrill = async (): Promise<number> => {
        if (serverIdRef.current) return serverIdRef.current;
        if (creating.current) return creating.current;
        creating.current = (async () => {
            const res = await axios.post(`${API_BASE}/drills/`, { ...drillRef.current, license: licenseFor() });
            const id: number = res.data.id;
            serverIdRef.current = id;
            setServerId(id);
            // Keep server-generated fields (audio_tts_url, text_arabic...) but
            // never let the response overwrite what the user is typing.
            setDrill(prev => ({ ...res.data, ...prev, id }));
            return id;
        })().finally(() => { creating.current = null; });
        return creating.current;
    };

    /** Persist the given fields (PUT when online, offline queue on native). */
    const saveFields = async (fields: Partial<Drill>): Promise<void> => {
        const payload = { ...fields, license: licenseFor() };
        if (await isOnline()) {
            const id = await ensureServerDrill();
            const res = await axios.put(`${API_BASE}/drills/${id}`, payload);
            setDrill(prev => ({ ...prev, ...res.data, ...fields }));
            return;
        }
        if (!isNativeApp()) throw new Error('Sense connexió: no es pot desar des del navegador.');
        await syncManager.queueAction({
            type: serverIdRef.current ? 'UPDATE' : 'CREATE',
            drillId: serverIdRef.current ?? tempId.current,
            payload: { ...drillRef.current, ...payload, id: serverIdRef.current ?? tempId.current, is_local: !serverIdRef.current, date_created: new Date().toISOString() },
        });
    };

    const setField = (field: keyof Drill, value: string) => setDrill(prev => ({ ...prev, [field]: value }));

    /** Upload a blob and attach its server URL to the drill. */
    const attachMedia = async (blob: Blob, kind: MediaKind, prefix?: string) => {
        const fileName = fileNameFor(blob, kind, prefix);
        const previewUrl = URL.createObjectURL(blob);
        if (kind === 'image') setPreviewImage(previewUrl);
        if (kind === 'video') setPreviewVideo(previewUrl);
        if (kind === 'audio') setPreviewAudio(previewUrl);

        setBusy(`upload-${kind}`);
        try {
            if (await isOnline()) {
                const id = await ensureServerDrill();
                const fd = new FormData();
                fd.append('file', blob, fileName);
                const res = await axios.post(`${API_BASE}/upload-media/${id}/${kind}`, fd);
                const url: string | undefined = res.data?.url;
                if (!url) throw new Error('El servidor no ha retornat cap URL');
                setDrill(prev => ({ ...prev, [`${kind}_url`]: url }));
                toast.success(kind === 'image' ? 'Foto pujada' : kind === 'video' ? 'Vídeo pujat' : 'Àudio pujat');
            } else if (isNativeApp()) {
                await syncManager.saveMediaLocally(blob, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: serverIdRef.current ?? tempId.current,
                    mediaType: kind,
                    localPath: fileName,
                    fileName,
                });
                toast.info('Sense connexió: es pujarà quan tornis a estar en línia');
            } else {
                throw new Error('Sense connexió: no es pot pujar des del navegador.');
            }
        } catch (err: any) {
            toast.error(`No s'ha pogut pujar: ${errMsg(err, 'error desconegut')}`);
        } finally {
            setBusy(null);
        }
    };

    const capturePhoto = async () => {
        try {
            const status = await Camera.requestPermissions();
            if (status.camera !== 'granted' && status.photos !== 'granted') {
                toast.error('Cal permís de càmera');
                return;
            }
            const image = await Camera.getPhoto({
                quality: 50, width: 640, height: 480, allowEditing: false,
                resultType: CameraResultType.Base64, source: CameraSource.Camera,
                saveToGallery: false, correctOrientation: true, presentationStyle: 'fullscreen', webUseInput: false,
            });
            if (image?.base64String) {
                const blob = await (await fetch(`data:image/${image.format};base64,${image.base64String}`)).blob();
                await attachMedia(blob, 'image', 'photo');
            }
        } catch (err: any) {
            if (!/cancel/i.test(err?.message || '')) toast.error(`Foto: ${errMsg(err, 'error')}`);
        }
    };

    const captureVideo = () => document.getElementById('native-video-input')?.click();

    const startVoiceRecording = async () => {
        try {
            if (isNativeApp()) {
                const perm = await VoiceRecorder.hasAudioRecordingPermission();
                if (!perm.value) {
                    const req = await VoiceRecorder.requestAudioRecordingPermission();
                    if (!req.value) return toast.error('Cal permís de micròfon');
                }
            }
            const result = await VoiceRecorder.startRecording();
            if (result.value) setIsRecording(true);
        } catch (err: any) {
            toast.error(`Micròfon: ${errMsg(err, 'no disponible')}`);
        }
    };

    const stopVoiceRecording = async () => {
        try {
            const result = await VoiceRecorder.stopRecording();
            setIsRecording(false);
            if (result.value?.recordDataBase64) {
                const mime = result.value.mimeType || 'audio/aac';
                const blob = await (await fetch(`data:${mime};base64,${result.value.recordDataBase64}`)).blob();
                await attachMedia(blob, 'audio', 'rec');
            }
        } catch (err: any) {
            setIsRecording(false);
            toast.error(`Micròfon: ${errMsg(err, 'error en aturar')}`);
        }
    };

    const startDictation = async () => {
        try {
            if (isNativeApp()) {
                const perm = await SpeechRecognition.checkPermissions();
                if (perm.speechRecognition !== 'granted') {
                    const req = await SpeechRecognition.requestPermissions();
                    if (req.speechRecognition !== 'granted') return toast.error('Cal permís de reconeixement de veu');
                }
            }
            const supported = await SpeechRecognition.available();
            if (!supported) return toast.error('El dictat no està disponible en aquest dispositiu');
            await SpeechRecognition.removeAllListeners();
            await SpeechRecognition.start({ language: 'ca-ES', partialResults: true, popup: false });
            SpeechRecognition.addListener('partialResults', (data: any) => {
                if (data.matches?.length) setField('text_catalan', data.matches[0]);
            });
        } catch (err: any) {
            toast.error(`Dictat: ${err?.code || errMsg(err, 'error')}`);
        }
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        await attachMedia(file, kindOf(file, 'audio'));
    };

    const requireOnline = async (what: string) => {
        if (await isOnline()) return true;
        toast.error(`${what} requereix connexió a internet.`);
        return false;
    };

    const mediaSourceFor = (sourceType?: 'audio' | 'video') => {
        const d = drillRef.current;
        if (sourceType === 'audio') return d.audio_url || '';
        if (sourceType === 'video') return d.video_url || '';
        return d.audio_url || d.video_url || '';
    };

    const handleAutoTranscribe = async (sourceType?: 'audio' | 'video') => {
        const mediaSource = mediaSourceFor(sourceType);
        if (!mediaSource) return toast.error('Primer enregistra o puja àudio/vídeo.');
        if (!(await requireOnline('La transcripció'))) return;
        setBusy('transcribe');
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const text = (res.data.corrected_transcription || '').trim();
            if (!text) return toast.error('La transcripció ha retornat un text buit.');
            setField('text_tachelhit', text);
            await saveFields({ text_tachelhit: text });
            toast.success('Transcripció feta');
        } catch (err: any) {
            toast.error(`La transcripció ha fallat: ${errMsg(err, 'error')}`);
        } finally {
            setBusy(null);
        }
    };

    const handleTachelhitTTS = async () => {
        const text = drillRef.current.text_tachelhit?.trim();
        if (!text) return toast.error('El camp de tachelhit és buit.');
        if (!(await requireOnline('El TTS'))) return;
        setBusy('tts');
        try {
            const id = await ensureServerDrill();
            const res = await axios.post(`${API_BASE}/tts/tachelhit`, { text, drill_id: id });
            if (res.data.url) {
                setDrill(prev => ({ ...prev, audio_tts_shi_url: res.data.url }));
                new Audio(getMediaUrl(res.data.url)).play().catch(() => {});
            }
        } catch (err: any) {
            toast.error(`El TTS ha fallat: ${errMsg(err, 'error')}`);
        } finally {
            setBusy(null);
        }
    };

    const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        const d = drillRef.current;
        const sourceText = (source === 'ca' ? d.text_catalan : d.text_tachelhit)?.trim();
        if (!sourceText) return toast.error("El camp d'origen és buit.");
        if (!(await requireOnline('La traducció'))) return;
        const targetField: keyof Drill = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        setBusy(`trans-${targetField}`);
        try {
            const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
            const translated = (res.data.translated_text || '').trim();
            if (!translated) return toast.error('La traducció ha retornat un text buit.');
            // Replace the target field (the old sheet appended "(…)" copies).
            setField(targetField, translated);
            await saveFields({ [targetField]: translated });
            toast.success('Traducció feta');
        } catch (err: any) {
            toast.error(`La traducció ha fallat: ${errMsg(err, 'error')}`);
        } finally {
            setBusy(null);
        }
    };

    // One-tap pipeline: transcribe the recording to Tachelhit, translate it to
    // Catalan, fill both fields in one save. Uses the API responses directly.
    const handleVoiceToDrill = async () => {
        const mediaSource = mediaSourceFor();
        if (!mediaSource) return toast.error('Primer enregistra o puja àudio/vídeo.');
        if (!(await requireOnline('Veu → Drill'))) return;
        setBusy('voice-to-drill');
        try {
            const tRes = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const tachelhit = (tRes.data.corrected_transcription || '').trim();
            if (!tachelhit) return toast.error('La transcripció ha retornat un text buit.');
            let catalan = '';
            try {
                const trRes = await axios.post(`${API_BASE}/translate`, { text: tachelhit, source_lang: 'shi', target_lang: 'ca' });
                catalan = (trRes.data.translated_text || '').trim();
            } catch {
                toast.info('Transcrit; la traducció ha fallat, omple el català a mà.');
            }
            const fields: Partial<Drill> = { text_tachelhit: tachelhit, ...(catalan ? { text_catalan: catalan } : {}) };
            setDrill(prev => ({ ...prev, ...fields }));
            await saveFields(fields);
            toast.success('Veu → Drill fet');
        } catch (err: any) {
            toast.error(`Veu → Drill ha fallat: ${errMsg(err, 'error')}`);
        } finally {
            setBusy(null);
        }
    };

    const handleTrim = async (mode: 'video' | 'audio') => {
        const d = drillRef.current;
        if (!(mode === 'video' ? d.video_url : d.audio_url || d.video_url)) return toast.error('No hi ha cap fitxer pujat per retallar.');
        if (!(await requireOnline('Retallar'))) return;
        setBusy(`trim-${mode}`);
        try {
            const id = await ensureServerDrill();
            const endpoint = mode === 'video' ? 'trim-video' : 'trim-audio';
            const res = await axios.post(`${API_BASE}/drills/${id}/${endpoint}`, { start_time: trimTimes.start, end_time: trimTimes.end });
            if (res.data.url) {
                const full = getMediaUrl(res.data.url);
                if (mode === 'video') { setDrill(prev => ({ ...prev, video_url: res.data.url })); setPreviewVideo(full); }
                else { setDrill(prev => ({ ...prev, audio_url: res.data.url })); setPreviewAudio(full); }
                toast.success(mode === 'video' ? 'Vídeo retallat' : 'Àudio extret');
            }
        } catch (err: any) {
            toast.error(`Retallar ha fallat: ${errMsg(err, 'error')}`);
        } finally {
            setBusy(null);
        }
    };

    const handleSave = async () => {
        const d = drillRef.current;
        if (!hasText(d) && !hasMedia(d)) {
            toast.error('Escriu almenys el català o el tachelhit, o afegeix una gravació.');
            return;
        }
        setSaving(true);
        try {
            await saveFields({
                text_catalan: d.text_catalan, text_tachelhit: d.text_tachelhit,
                text_arabic: d.text_arabic, tag: d.tag,
            });
            toast.success('Drill desat');
            onDrillCreated(serverIdRef.current ?? undefined);
        } catch (err: any) {
            toast.error(`No s'ha pogut desar: ${errMsg(err, 'error')}`);
        } finally {
            setSaving(false);
        }
    };

    // Closing without Desa: a drill auto-created for an upload/AI call but
    // with no text and no media would be an empty row, so remove it.
    const handleClose = async () => {
        const d = drillRef.current;
        const id = serverIdRef.current;
        if (id && !hasText(d) && !hasMedia(d)) {
            axios.delete(`${API_BASE}/drills/${id}`).catch(() => {});
        } else if (id && (hasText(d) || hasMedia(d))) {
            if (!window.confirm('Tens canvis sense desar. Vols sortir igualment?')) return;
        }
        onClose();
    };

    const anyMedia = !!(drill.audio_url || drill.video_url || previewAudio || previewVideo);
    const disabled = busy !== null || saving;

    const tileStyle = (bg: string, color: string, border = 'var(--border)'): React.CSSProperties => ({
        minHeight: '64px', background: bg, color, border: `1px solid ${border}`, borderRadius: 'var(--r-md)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '4px',
        cursor: 'pointer', fontSize: '11px', fontWeight: 700, padding: '6px 2px',
    });
    const aiTileStyle = (bg: string, color: string): React.CSSProperties => ({
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '5px', padding: '10px 4px',
        fontSize: '11px', fontWeight: 700, background: bg, color, border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', minHeight: '56px',
    });
    const inputStyle: React.CSSProperties = { width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)', boxSizing: 'border-box' };
    const labelStyle: React.CSSProperties = { display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' };

    return (
        <div role="dialog" aria-modal="true" aria-labelledby="creator-title" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--bg)', zIndex: 10000, display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
            <div style={{ background: 'var(--brand-gradient)', padding: 'calc(16px + env(safe-area-inset-top, 0px)) 20px 22px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottomLeftRadius: 'var(--r-2xl)', borderBottomRightRadius: 'var(--r-2xl)', boxShadow: 'var(--shadow-brand)' }}>
                <button onClick={handleClose} aria-label="Tanca" style={{ background: 'rgba(255,255,255,0.18)', color: 'white', border: 'none', borderRadius: 'var(--r-pill)', width: '44px', height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><FaTimes size={20} /></button>
                <div id="creator-title" style={{ color: 'white', fontSize: '20px', fontWeight: 800, letterSpacing: '-0.01em' }}>Nou drill</div>
                <button onClick={handleSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.95)', color: 'var(--brand-1)', border: 'none', borderRadius: 'var(--r-md)', padding: '11px 18px', fontWeight: 700, fontSize: '14px', cursor: 'pointer', boxShadow: 'var(--shadow-sm)', minHeight: '44px' }}>
                    <FaSave /> {saving ? 'Desant…' : 'Desa'}
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px', paddingBottom: 'calc(120px + env(safe-area-inset-bottom, 0px))' }}>
                <div style={{ background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
                    <div style={{ gridTemplateColumns: 'repeat(5, 1fr)', display: 'grid', gap: '8px' }}>
                        <button onClick={capturePhoto} disabled={disabled} aria-label="Fes una foto" style={tileStyle('var(--emerald-soft)', 'var(--emerald)')}><FaCamera size={20} />Foto</button>
                        <button onClick={captureVideo} disabled={disabled} aria-label="Enregistra vídeo" style={tileStyle('var(--brand-gradient-soft)', 'var(--brand-2)')}><FaVideo size={20} />Vídeo</button>
                        <button onClick={isRecording ? stopVoiceRecording : startVoiceRecording} disabled={disabled && !isRecording} aria-label={isRecording ? "Atura l'enregistrament" : 'Enregistra veu'} style={tileStyle(isRecording ? 'var(--rose-soft)' : 'var(--rose)', isRecording ? 'var(--rose)' : 'white', 'var(--rose)')}><FaMicrophone size={20} />{isRecording ? 'Atura' : 'Veu'}</button>
                        <button onClick={startDictation} disabled={disabled} aria-label="Dictat en català" style={tileStyle('var(--amber-soft)', 'var(--amber-strong)')}><FaKeyboard size={20} />Dictat</button>
                        <button onClick={() => document.getElementById('gallery-upload')?.click()} disabled={disabled} aria-label="Tria de la galeria" style={tileStyle('var(--sky-soft)', 'var(--sky)')}><FaFolderOpen size={20} />Galeria</button>
                    </div>
                    <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-input" style={{ display: 'none' }} onChange={handleFileChange} />
                    <input type="file" accept="image/*,audio/*,video/*" id="gallery-upload" style={{ display: 'none' }} onChange={handleFileChange} />
                    {busy?.startsWith('upload-') && <div style={{ marginTop: '10px', fontSize: '13px', color: 'var(--text-soft)', fontWeight: 600 }}>Pujant…</div>}
                </div>

                {previewImage && <img src={previewImage} alt="Vista prèvia" style={{ width: '100%', height: '150px', borderRadius: 'var(--r-lg)', objectFit: 'cover', border: '1px solid var(--border)' }} />}

                {previewVideo && (
                    <div style={{ background: '#000', borderRadius: 'var(--r-xl)', overflow: 'hidden', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border-strong)' }}>
                        <div style={{ width: '100%', position: 'relative', paddingTop: '56.25%', background: '#000' }}>
                            <video
                                id="creator-video-preview"
                                key={previewVideo}
                                src={previewVideo}
                                controls
                                playsInline
                                preload="metadata"
                                onError={() => toast.error('No es pot reproduir aquest vídeo en aquest dispositiu')}
                                onLoadedMetadata={(e) => {
                                    const dur = (e.target as HTMLVideoElement).duration;
                                    if (dur && isFinite(dur)) { setVideoDuration(dur); setTrimTimes(prev => ({ ...prev, end: dur })); }
                                }}
                                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: '#000', objectFit: 'contain' }}
                            />
                        </div>
                        <div style={{ width: '100%', padding: '14px 16px', background: '#0f172a', boxSizing: 'border-box' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '12px', fontWeight: 700 }}>
                                <button onClick={() => { const v = document.getElementById('creator-video-preview') as HTMLVideoElement; if (v) setTrimTimes(prev => ({ ...prev, start: v.currentTime })); }} style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--emerald)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>INICI</button>
                                <span style={{ color: 'var(--text-muted)' }}>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                                <button onClick={() => { const v = document.getElementById('creator-video-preview') as HTMLVideoElement; if (v) setTrimTimes(prev => ({ ...prev, end: v.currentTime })); }} style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--rose)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>FINAL</button>
                            </div>
                            <input type="range" aria-label="Temps d'inici" min="0" max={videoDuration} step="0.1" value={trimTimes.start} onChange={e => setTrimTimes(p => ({ ...p, start: Math.min(parseFloat(e.target.value), p.end - 0.1) }))} style={{ width: '100%', marginBottom: '10px' }} />
                            <input type="range" aria-label="Temps final" min="0" max={videoDuration} step="0.1" value={trimTimes.end} onChange={e => setTrimTimes(p => ({ ...p, end: Math.max(parseFloat(e.target.value), p.start + 0.1) }))} style={{ width: '100%', marginBottom: '15px' }} />
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button onClick={() => handleTrim('video')} disabled={disabled || !drill.video_url} style={{ flex: 1, padding: '12px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)', minHeight: '44px' }}>
                                    <FaScissors /> {busy === 'trim-video' ? '…' : 'Retallar vídeo'}
                                </button>
                                <button onClick={() => handleTrim('audio')} disabled={disabled || !drill.video_url} style={{ flex: 1, padding: '12px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', minHeight: '44px' }}>
                                    <FaScissors /> {busy === 'trim-audio' ? '…' : 'Extreure àudio'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {previewAudio && (
                    <div style={{ background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <audio
                            id="creator-audio-preview"
                            key={previewAudio}
                            src={previewAudio}
                            style={{ width: '100%' }}
                            controls
                            preload="metadata"
                            onLoadedMetadata={(e) => {
                                const dur = (e.target as HTMLAudioElement).duration;
                                if (dur && isFinite(dur)) { setAudioDuration(dur); setTrimTimes(prev => ({ ...prev, end: Math.min(prev.end, dur) || dur })); }
                            }}
                            onError={() => toast.error('No es pot reproduir aquest àudio en aquest dispositiu')}
                        />
                        <div style={{ padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-soft)' }}>
                                <span>INICI: {trimTimes.start.toFixed(1)}s</span>
                                <span>FINAL: {trimTimes.end.toFixed(1)}s</span>
                            </div>
                            <input type="range" aria-label="Temps d'inici" min="0" max={audioDuration} step="0.1" value={trimTimes.start} onChange={e => setTrimTimes(p => ({ ...p, start: Math.min(parseFloat(e.target.value), p.end - 0.1) }))} style={{ width: '100%', marginBottom: '8px', accentColor: 'var(--brand-1)' }} />
                            <input type="range" aria-label="Temps final" min="0" max={audioDuration} step="0.1" value={trimTimes.end} onChange={e => setTrimTimes(p => ({ ...p, end: Math.max(parseFloat(e.target.value), p.start + 0.1) }))} style={{ width: '100%', marginBottom: '12px', accentColor: 'var(--brand-1)' }} />
                            <button onClick={() => handleTrim('audio')} disabled={disabled || !drill.audio_url} style={{ width: '100%', padding: '12px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)', minHeight: '44px' }}>
                                <FaScissors /> {busy === 'trim-audio' ? '…' : 'Retallar àudio'}
                            </button>
                        </div>
                    </div>
                )}

                <button
                    onClick={handleVoiceToDrill}
                    disabled={!anyMedia || disabled}
                    style={{ width: '100%', padding: '16px', background: busy === 'voice-to-drill' ? 'var(--text-muted)' : 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-lg)', fontWeight: 800, fontSize: '15px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', cursor: 'pointer', opacity: anyMedia ? 1 : 0.5, boxShadow: 'var(--shadow-brand)' }}
                    title="Transcriu la gravació a tachelhit i tradueix-la al català amb un sol toc"
                >
                    <FaMicrophone size={18} /> {busy === 'voice-to-drill' ? 'Treballant…' : 'Veu → Drill (auto)'}
                </button>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
                    <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={disabled} aria-label="Tradueix del català al tachelhit" style={aiTileStyle('var(--brand-gradient-soft)', 'var(--brand-1)')}><FaLanguage size={18} /> {busy === 'trans-text_tachelhit' ? '…' : 'CA➔SH'}</button>
                    <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={disabled} aria-label="Tradueix del tachelhit al català" style={aiTileStyle('var(--emerald-soft)', 'var(--emerald)')}><FaLanguage size={18} /> {busy === 'trans-text_catalan' ? '…' : 'SH➔CA'}</button>
                    <button onClick={handleTachelhitTTS} disabled={disabled} aria-label="Veu sintètica en tachelhit" style={aiTileStyle('var(--amber-soft)', 'var(--amber-strong)')}><FaVolumeUp size={18} /> {busy === 'tts' ? '…' : 'TTS'}</button>
                    <button
                        onClick={() => {
                            const hasAudio = !!drill.audio_url, hasVideo = !!drill.video_url;
                            if (hasAudio && hasVideo) handleAutoTranscribe(window.confirm("Transcriure des del VÍDEO? (Cancel·la per a l'ÀUDIO)") ? 'video' : 'audio');
                            else if (hasVideo) handleAutoTranscribe('video');
                            else if (hasAudio) handleAutoTranscribe('audio');
                            else toast.error('Primer enregistra o puja contingut.');
                        }}
                        disabled={!anyMedia || disabled}
                        aria-label="Transcriu automàticament"
                        style={{ ...aiTileStyle('var(--sky-soft)', 'var(--sky)'), opacity: anyMedia ? 1 : 0.5 }}
                    ><FaFileAlt size={18} /> {busy === 'transcribe' ? '…' : 'Transcriu'}</button>
                </div>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px', color: 'var(--text-soft)', padding: '0 4px', cursor: 'pointer' }}>
                    <input type="checkbox" checked={corpusConsent} onChange={(e) => setCorpusConsent(e.target.checked)} style={{ marginTop: '2px' }} />
                    <span>Consento que aquesta gravació s'afegeixi al corpus per documentar la llengua (CC BY-SA). Desmarca-ho per mantenir-la privada.</span>
                </label>

                <div style={{ background: 'var(--surface)', padding: '20px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div><label htmlFor="new-catalan" style={labelStyle}>Català</label><textarea id="new-catalan" lang="ca" value={drill.text_catalan || ''} onChange={(e) => setField('text_catalan', e.target.value)} rows={3} style={inputStyle} /></div>
                    <div><label htmlFor="new-tachelhit" style={labelStyle}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea id="new-tachelhit" lang="shi" autoCapitalize="off" autoCorrect="off" spellCheck={false} value={drill.text_tachelhit || ''} onChange={(e) => setField('text_tachelhit', e.target.value)} rows={3} style={{ ...inputStyle, color: 'var(--brand-1)', fontWeight: 700, fontFamily: 'var(--font-tifinagh)' }} /></div>
                    <div><label htmlFor="new-arabic" style={labelStyle}>Àrab (العربية)</label><textarea id="new-arabic" lang="ar" dir="rtl" value={drill.text_arabic || ''} onChange={(e) => setField('text_arabic', e.target.value)} rows={2} style={inputStyle} /></div>
                    <div><label htmlFor="new-tag" style={labelStyle}>Tag</label><input id="new-tag" type="text" value={drill.tag || ''} onChange={(e) => setField('tag', e.target.value)} style={inputStyle} /></div>
                    {serverId && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Drill #{serverId}</div>}
                </div>
            </div>
        </div>
    );
}
