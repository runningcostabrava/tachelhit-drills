import { useState, useEffect, useRef } from 'react';
import {
  FaTimes,
  FaSave,
  FaCamera,
  FaVideo,
  FaMicrophone,
  FaKeyboard,
  FaFolderOpen,
  FaVolumeUp,
  FaFileAlt,
  FaMicroscope,
  FaClipboardCheck,
  FaComments,
  FaCheck,
  FaRegSquare,
  FaLanguage,
  FaChevronLeft,
  FaChevronRight,
  FaCut as FaScissors,
  FaMagic
} from 'react-icons/fa';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import TransliterationPreview from './TransliterationPreview';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { API_BASE, getMediaUrl, isNativeApp } from '../config';
import { fileNameFor, kindOf, type MediaKind } from '../utils/media';
import { syncManager, type Drill } from '../services/OfflineSyncManager';
import { api } from '../api';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import AiAssistant from './AiAssistant';

interface MobileDrillEditorProps {
  drill: Drill;
  onClose: () => void;
  onUpdate: () => void;
  onNavigate: (direction: 'next' | 'prev') => void;
}

export default function MobileDrillEditor({ drill, onClose, onUpdate, onNavigate }: MobileDrillEditorProps) {
  const [localDrill, setLocalDrill] = useState<Drill>({ ...drill });
  // The last version the SERVER gave us. What we send is the difference against this, so that
  // changing a tag cannot rewrite the speaker's text with whatever was on screen when it opened.
  const serverCopy = useRef<Drill>({ ...drill });
  // A save that did not land: the work and the reason, kept until it does.
  const [unsaved, setUnsaved] = useState<string | null>(null);
  // A sentence belongs to whoever made it, and the library's own to whoever administers it
  // (`owner_or_admin` on the server). Knowing it here means saying so BEFORE the work, and
  // offering the thing that is actually open to you: saying it your way, as a variant.
  const [me, setMe] = useState<{ id: number; is_admin: boolean } | null>(null);
  const [myVersion, setMyVersion] = useState<string | null>(null);
  const [sendingVariant, setSendingVariant] = useState(false);
  useEffect(() => { api.me().then((m) => setMe(m ? { id: m.id, is_admin: !!m.is_admin } : null)).catch(() => {}); }, []);
  const mayChange = !me ? false : me.is_admin || (!!drill.created_by_user_id && drill.created_by_user_id === me.id);

  const sendVariant = async () => {
    const said = (myVersion || '').trim();
    if (!said) return;
    setSendingVariant(true);
    try {
      await api.addVariant(drill.id, said);
      setMyVersion(null);
      toast.success('Desada com una altra manera de dir-ho. Gr\u00e0cies!');
      onUpdate();
    } catch (e) { toast.error(whyItFailed(e, 'No s\u2019ha pogut desar')); }
    finally { setSendingVariant(false); }
  };
  const [isRecording, setIsRecording] = useState(false);
  const [aiLoadingKey, setAiLoadingKey] = useState<string | null>(null);
  const [showAi, setShowAi] = useState(false);
  const [aiAction, setAiAction] = useState<'analyze' | 'review'>('analyze');
  const [suggesting, setSuggesting] = useState(false);

  // AI draft translation → goes to the *_suggested column, never the gold field
  const handleSuggest = async () => {
    setSuggesting(true);
    try {
      const r = await api.aiSuggestTranslation(localDrill.id);
      setLocalDrill(prev => ({ ...prev, [r.field]: r.suggestion }));
      toast.success('Suggeriment d\'IA generat (esborrany)');
    } catch (e: any) {
      toast.error(e.message || 'No s\'ha pogut generar el suggeriment');
    } finally {
      setSuggesting(false);
    }
  };
    const [trimTimes, setTrimTimes] = useState({ start: 0, end: 10 });
    const [videoDuration, setVideoDuration] = useState(60);
    const [audioDuration, setAudioDuration] = useState(60);
    const videoRef = useRef<HTMLVideoElement>(null);

  const addLog = (msg: string) => {
    console.log(`[MobileDrillEditor] ${msg}`);
  };

  useEffect(() => {
    setLocalDrill({ ...drill });
    serverCopy.current = { ...drill };
    setUnsaved(null);
  }, [drill]);

  useEffect(() => {
    if (isNativeApp()) {
      VoiceRecorder.requestAudioRecordingPermission().catch(e => console.warn('VoiceRecorder permissions not available', e));
      SpeechRecognition.requestPermissions().catch(e => console.warn('SpeechRecognition permissions not available', e));
    }
  }, [drill]);

  // blob:/data:/file:/capacitor: URLs are previews that only exist on this
  // device; they must never be persisted as the drill's media URL.
  const isLocalUrl = (u?: string) => !!u && /^(blob:|data:|file:|capacitor:|https?:\/\/localhost\/_capacitor)/i.test(u);
  const stripLocalUrls = (d: Drill): Drill => {
    const out = { ...d };
    (['audio_url', 'video_url', 'image_url'] as const).forEach(k => { if (isLocalUrl(out[k])) delete (out as any)[k]; });
    return out;
  };

  /** What this edit actually changes, against the last version the server gave us. */
  const whatChanged = (next: Drill): Partial<Drill> => {
    const base = serverCopy.current || ({} as Drill);
    const out: Record<string, unknown> = {};
    (Object.keys(next) as (keyof Drill)[]).forEach((k) => {
      if (k === 'id' || k === 'date_created' || k === 'updated_at') return;
      const a = (next as any)[k], b = (base as any)[k];
      if ((a ?? null) !== (b ?? null)) out[k as string] = a;
    });
    return out as Partial<Drill>;
  };

  const triggerSave = async (updatedDrill: Drill) => {
    const clean = stripLocalUrls(updatedDrill);
    // Only what you touched. The whole row used to go up, so a new tag carried a stale copy of
    // every other field with it — including the speaker's own words.
    const patch = whatChanged(clean);
    if (Object.keys(patch).length === 0) { toast.info('No hi ha res de nou per desar'); return; }
    try {
      const status = await Network.getStatus();
      if (status.connected && !clean.is_local) {
        const res = await axios.put(`${API_BASE}/drills/${clean.id}`, patch);
        serverCopy.current = { ...(res.data as Drill) };
        setUnsaved(null);
        onUpdate();
        toast.success('Desat');
      } else {
        await syncManager.queueAction({
          type: clean.is_local ? 'CREATE' : 'UPDATE',
          drillId: clean.id,
          payload: clean
        });
        setUnsaved(null);
        onUpdate();
        toast.info('Desat sense connexió — es sincronitzarà');
      }
    } catch (err) {
      // It is NOT queued: saying so in the log while losing the work is how this hid itself.
      const why = whyItFailed(err, 'No s\u2019ha pogut desar');
      addLog(`Save failed: ${why}`);
      setUnsaved(why);
      toast.error(why);
    }
  };

  const captureVideo = async () => {
    try {
        document.getElementById('native-video-input')?.click();
    } catch (err: any) {
        addLog(`Video error: ${err.message}`);
    }
  };

  const handleFieldChange = (field: keyof Drill, value: string) => {
    addLog(`Field change: ${field} -> ${value?.substring(0, 20)}...`);
    const updated = { ...localDrill, [field]: value };
    setLocalDrill(updated);
  };

  const [drawHint, setDrawHint] = useState('');
  /** Ask the server to draw the sentence (Gemini, flashcard style). Replaces the current picture. */
  const illustrate = async () => {
    setAiLoadingKey('illustrate');
    try {
      const r = await api.illustrateDrill(localDrill.id, drawHint);
      setLocalDrill(prev => ({ ...prev, image_url: r.image_url }));
      setLocalMediaUrls(prev => { const n = { ...prev }; delete n.image; return n; });
      toast.success('Dibuix fet');
      onUpdate();
    } catch (err: any) {
      toast.error(`No s'ha pogut dibuixar: ${err?.message || 'error'}`);
    } finally {
      setAiLoadingKey(null);
    }
  };

  /** Upload a blob for this drill (online) or queue it (native, offline).
   *  The server URL goes into the drill; the blob URL is only the preview. */
  const attachMedia = async (blob: Blob, kind: MediaKind, prefix?: string) => {
    const fileName = fileNameFor(blob, kind, `${prefix || kind}_${localDrill.id}`);
    const previewUrl = URL.createObjectURL(blob);
    setLocalMediaUrls(prev => ({ ...prev, [kind]: previewUrl }));
    setAiLoadingKey(`upload-${kind}`);
    try {
      const status = await Network.getStatus();
      if (status.connected && !localDrill.is_local) {
        const fd = new FormData();
        fd.append('file', blob, fileName);
        const res = await axios.post(`${API_BASE}/upload-media/${localDrill.id}/${kind}`, fd);
        const url: string | undefined = res.data?.url;
        if (!url) throw new Error('El servidor no ha retornat cap URL');
        setLocalDrill(prev => ({ ...prev, [`${kind}_url`]: url }));
        toast.success(kind === 'image' ? 'Foto pujada' : kind === 'video' ? 'Vídeo pujat' : 'Àudio pujat');
        onUpdate();
      } else if (isNativeApp()) {
        await syncManager.saveMediaLocally(blob, fileName);
        await syncManager.queueAction({ type: 'UPLOAD_MEDIA', drillId: localDrill.id, mediaType: kind, localPath: fileName, fileName });
        toast.info('Sense connexió: es pujarà quan tornis a estar en línia');
      } else {
        throw new Error('Sense connexió: no es pot pujar des del navegador.');
      }
    } catch (err: any) {
      toast.error(`No s'ha pogut pujar: ${err?.response?.data?.detail || err?.message || 'error'}`);
    } finally {
      setAiLoadingKey(null);
    }
  };

  const capturePhoto = async () => {
    try {
      addLog('Triggering native photo camera...');
      const status = await Camera.requestPermissions();
      if (status.camera !== 'granted' && status.photos !== 'granted') {
        addLog(`Permissions status: ${JSON.stringify(status)}`);
      }

      addLog('Opening camera...');
      const image = await Camera.getPhoto({
        quality: 50, // Reduced quality for smaller size
        width: 640,  // Optimized resolution for drill area
        height: 480,
        allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Camera, // Direct camera access
        saveToGallery: false,
        correctOrientation: true,
        presentationStyle: 'fullscreen',
        webUseInput: false
      });

      if (image && image.base64String) {
        const blob = await (await fetch(`data:image/${image.format};base64,${image.base64String}`)).blob();
        await attachMedia(blob, 'image', 'photo');
      }
    } catch (err: any) {
      if (!/cancel/i.test(err?.message || '')) toast.error(`Foto: ${err?.message || 'error'}`);
    }
  };

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
      toast.error(`Micròfon: ${err?.message || 'no disponible'}`);
    }
  };

  const handleTrimAudio = async () => {
    if (!localDrill.audio_url) return;
    setAiLoadingKey('trim-audio');
    addLog(`Trimming audio: ${trimTimes.start}s to ${trimTimes.end}s`);
    try {
        const res = await axios.post(`${API_BASE}/drills/${localDrill.id}/trim-audio`, {
            start_time: trimTimes.start,
            end_time: trimTimes.end
        });
        if (res.data.url) {
            const updated = { ...localDrill, audio_url: res.data.url };
            setLocalDrill(updated);
            triggerSave(updated);
            addLog('Audio trimmed successfully');
        }
    } catch (err: any) {
        toast.error(`Retallar ha fallat: ${err?.response?.data?.detail || err?.message || 'error'}`);
    } finally {
        setAiLoadingKey(null);
    }
  };

  const stopVoiceRecording = async () => {
    try {
      const result = await VoiceRecorder.stopRecording();
      setIsRecording(false);
      if (result.value && result.value.recordDataBase64) {
        const mime = result.value.mimeType || 'audio/aac';
        const blob = await (await fetch(`data:${mime};base64,${result.value.recordDataBase64}`)).blob();
        await attachMedia(blob, 'audio', 'rec');
      }
    } catch (err: any) {
      setIsRecording(false);
      toast.error(`Micròfon: ${err?.message || 'error en aturar'}`);
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

      addLog('Starting dictation...');
      await SpeechRecognition.removeAllListeners();

      await SpeechRecognition.start({
        language: 'ca-ES',
        partialResults: true,
        popup: false
      });

      SpeechRecognition.addListener('partialResults', (data: any) => {
          if (data.matches && data.matches.length > 0) {
              const transcript = data.matches[0];
              setLocalDrill(prev => ({ ...prev, text_catalan: transcript }));
          }
      });
    } catch (err: any) {
      toast.error(`Dictat: ${err?.code || err?.message || 'error'}`);
    }
  };

      const handleAutoTranscribe = async (sourceType?: 'audio' | 'video') => {
        let mediaSource = '';
        if (sourceType === 'audio') mediaSource = localDrill.audio_url || '';
        else if (sourceType === 'video') mediaSource = localDrill.video_url || '';
        else mediaSource = localDrill.audio_url || localDrill.video_url || '';

        if (!mediaSource) return toast.error('Primer enregistra o puja àudio/vídeo.');

        const status = await Network.getStatus();
        if (!status.connected) return toast.error('La transcripció requereix connexió a internet.');

        setAiLoadingKey('transcribe-voice');
        addLog(`Transcribing ${sourceType || 'media'}...`);
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource, drill_id: localDrill.id });
            const safeText = (res.data.corrected_transcription || '').trim();
            if (!safeText) return toast.error('La transcripció ha retornat un text buit.');

            const updated = { ...localDrill, text_tachelhit: safeText };
            setLocalDrill(updated);
            triggerSave(updated);
            addLog('Transcription success');
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message;
            toast.error(`La transcripció ha fallat: ${msg}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

  const handleTachelhitTTS = async () => {
    const text = localDrill.text_tachelhit;
    if (!text) return toast.error('El camp de tachelhit és buit.');

    const status = await Network.getStatus();
    if (!status.connected) return toast.error('El TTS requereix connexió a internet.');

    setAiLoadingKey('tts-shi');
    addLog('Generating Tachelhit TTS...');
    try {
        const res = await axios.post(`${API_BASE}/tts/tachelhit`, { text, drill_id: localDrill.id });
        if (res.data.url) {
            addLog('TTS ready, playing...');
            new Audio(getMediaUrl(res.data.url)).play();
        }
    } catch (err: any) {
        const msg = err.response?.data?.detail || err.message;
        toast.error(`El TTS ha fallat: ${msg}`);
    } finally {
        setAiLoadingKey(null);
    }
  };

  const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
    const status = await Network.getStatus();
    if (!status.connected) return toast.error('La traducció requereix internet.');

    const sourceText = source === 'ca' ? localDrill.text_catalan : localDrill.text_tachelhit;
    if (!sourceText) return toast.error("El camp d'origen és buit.");

    const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
    setAiLoadingKey(`trans-${targetField}`);
    try {
      const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
      const safeText = (res.data.translated_text || '').trim();
      if (!safeText) return toast.error('La traducció ha retornat un text buit.');

      const updated = { ...localDrill, [targetField]: safeText };
      setLocalDrill(updated);
      triggerSave(updated);
    } catch (err: any) {
      toast.error(`La traducció ha fallat: ${err?.response?.data?.detail || err?.message || ''}`);
    } finally {
      setAiLoadingKey(null);
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    await attachMedia(file, kindOf(file, 'audio'));
  };

  const handleTrimVideo = async (mode: 'video' | 'audio') => {
    if (!localDrill.video_url) return toast.error('No hi ha cap vídeo pujat per retallar.');
    setAiLoadingKey(`trim-${mode}`);
    addLog(`API Call: Trimming ${mode} (${trimTimes.start}s - ${trimTimes.end}s) via ${API_BASE}`);
    try {
        const endpoint = mode === 'video' ? 'trim-video' : 'trim-audio';
        const res = await axios.post(`${API_BASE}/drills/${localDrill.id}/${endpoint}`, {
            start_time: trimTimes.start,
            end_time: trimTimes.end
        });
        addLog(`API Response: ${JSON.stringify(res.data).substring(0, 100)}...`);
        if (res.data.url) {
            const updated = mode === 'video'
                ? { ...localDrill, video_url: res.data.url }
                : { ...localDrill, audio_url: res.data.url };

            setLocalDrill(updated);
            triggerSave(updated);
            addLog(`${mode === 'video' ? 'Video' : 'Audio'} trim applied successfully`);
        } else {
            addLog('Warning: Trim API returned success but no URL');
        }
    } catch (err: any) {
        toast.error(`Retallar ha fallat: ${err?.response?.data?.detail || err?.message || 'error'}`);
    } finally {
        setAiLoadingKey(null);
    }
  };

  const [localMediaUrls, setLocalMediaUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    const resolveLocalUrls = async () => {
      const urls: Record<string, string> = { ...localMediaUrls };
      let changed = false;

      if (localDrill.audio_url && !localDrill.audio_url.startsWith('blob:') && !localDrill.audio_url.startsWith('data:')) {
        const resolved = await syncManager.getLocalMediaUrl(localDrill.audio_url);
        if (resolved !== urls.audio) { urls.audio = resolved; changed = true; }
      }
      if (localDrill.video_url && !localDrill.video_url.startsWith('blob:') && !localDrill.video_url.startsWith('data:')) {
        const resolved = await syncManager.getLocalMediaUrl(localDrill.video_url);
        if (resolved !== urls.video) { urls.video = resolved; changed = true; }
      }
      if (localDrill.image_url && !localDrill.image_url.startsWith('blob:') && !localDrill.image_url.startsWith('data:')) {
        const resolved = await syncManager.getLocalMediaUrl(localDrill.image_url);
        if (resolved !== urls.image) { urls.image = resolved; changed = true; }
      }

      if (changed) setLocalMediaUrls(urls);
    };
    resolveLocalUrls();
  }, [localDrill.audio_url, localDrill.video_url, localDrill.image_url]);

  const getSourceUrl = (url: string | undefined, type: 'audio'|'video'|'image') => {
    if (!url) return '';
    if (url.startsWith('blob:') || url.startsWith('data:')) return url;

    const local = localMediaUrls[type];
    if (local) return local;

    return getMediaUrl(url);
  };

  // Guard against discarding unsaved edits when closing or navigating away.
  const isDirty = JSON.stringify(localDrill) !== JSON.stringify(drill);
  const confirmDiscard = () =>
    !isDirty || window.confirm('Tens canvis sense desar. Vols sortir igualment?');

  const handleClose = () => {
    if (!confirmDiscard()) return;
    onClose();
  };

  const handleNavigate = (dir: 'next' | 'prev') => {
    if (!confirmDiscard()) return;
    onNavigate(dir);
  };

  // Escape-to-close (goes through the same dirty-check guard).
  const handleCloseRef = useRef(handleClose);
  handleCloseRef.current = handleClose;
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleCloseRef.current();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="editor-title" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--bg)', zIndex: 11000, display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
            <div style={{ background: 'var(--surface)', padding: 'calc(12px + env(safe-area-inset-top, 0px)) 18px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
                <button onClick={handleClose} aria-label="Tanca" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-soft)', borderRadius: 'var(--r-pill)', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><FaTimes size={18} /></button>
                <div id="editor-title" style={{ color: 'var(--text)', fontSize: '18px', fontWeight: 700, letterSpacing: '-0.01em', fontFamily: 'var(--font-display)' }}>Edita</div>
                <button onClick={() => triggerSave(localDrill)} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', padding: '10px 18px', fontWeight: 700, fontSize: '14px', cursor: 'pointer' }}><FaSave /> Desa</button>
            </div>

      <div style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px', paddingBottom: 'calc(120px + env(safe-area-inset-bottom, 0px))' }}>

        {/* A failed save used to vanish with its toast, leaving the work alone in the text box. */}
        {unsaved && (
          <div role="alert" style={{ padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--rose)', background: 'var(--rose-soft)', fontSize: '13.5px', lineHeight: 1.5, color: 'var(--text)' }}>
            <strong>No s\u2019ha desat.</strong> {unsaved}
            <div style={{ marginTop: 8 }}>
              <button onClick={() => triggerSave(localDrill)} style={{ padding: '6px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--rose)', background: 'var(--surface)', color: 'var(--rose)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit' }}>Torna-ho a provar</button>
            </div>
          </div>
        )}

        {/* Not yours to change: say it here, and offer what IS open. */}
        {me && !mayChange && (
          <div style={{ padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface-2)', fontSize: '13.5px', lineHeight: 1.5 }}>
            <strong>Aquesta frase no \u00e9s teva.</strong>{' '}
            {drill.created_by_user_id ? '\u00c9s d\u2019alg\u00fa altre, i els seus mots s\u00f3n seus.' : '\u00c9s de la biblioteca: demana-ho a qui l\u2019administra.'}{' '}
            Si tu ho dius d\u2019una altra manera, apunta-la: queda lligada a aquesta, amb el mateix catal\u00e0.
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
              <input
                value={myVersion || ''}
                onChange={(e) => setMyVersion(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendVariant(); }}
                placeholder="Com ho dius tu"
                aria-label="Com ho dius tu"
                style={{ flex: 1, minWidth: 180, padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit' }}
              />
              <button onClick={sendVariant} disabled={sendingVariant || !(myVersion || '').trim()} style={{ padding: '10px 16px', borderRadius: 'var(--r-md)', border: 'none', background: 'var(--brand-1)', color: '#fff', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit', opacity: sendingVariant || !(myVersion || '').trim() ? 0.5 : 1 }}>
                {sendingVariant ? 'Desant\u2026' : 'Apunta-la'}
              </button>
            </div>
          </div>
        )}

        <div style={{ background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
              <button onClick={capturePhoto} aria-label="Fes una foto" style={{ height: '56px', background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Càmera"><FaCamera size={22} /></button>
              <button onClick={captureVideo} aria-label="Enregistra vídeo" style={{ height: '56px', background: 'var(--brand-gradient-soft)', color: 'var(--brand-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Vídeo"><FaVideo size={22} /></button>
              <button onClick={isRecording ? stopVoiceRecording : startVoiceRecording} aria-label={isRecording ? 'Atura l\'enregistrament' : 'Enregistra veu'} style={{ height: '56px', background: isRecording ? 'var(--rose-soft)' : 'var(--rose)', color: isRecording ? 'var(--rose)' : 'white', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Enregistra veu"><FaMicrophone size={22} /></button>
              <button onClick={startDictation} aria-label="Dictat de veu" style={{ height: '56px', background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Dictat"><FaKeyboard size={22} /></button>
              <button onClick={() => document.getElementById('gallery-upload')?.click()} aria-label="Tria de la galeria" style={{ height: '56px', background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Galeria"><FaFolderOpen size={22} /></button>
            </div>
            <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-input" style={{ display: 'none' }} onChange={handleFileChange} />
            <input type="file" accept="image/*,audio/*,video/*" id="gallery-upload" style={{ display: 'none' }} onChange={handleFileChange} />
        </div>

        {localDrill.image_url && (
          <img src={getSourceUrl(localDrill.image_url, 'image')} alt="Recurs del drill" onError={(e) => { e.currentTarget.style.display = 'none'; }} style={{ width: '100%', height: '180px', borderRadius: 'var(--r-lg)', objectFit: 'contain', background: 'var(--surface-2)', border: '1px solid var(--border)' }} />
        )}

        {/* Draw the sentence: one illustration in the deck's style, replacing whatever picture is there */}
        {!localDrill.is_local && (localDrill.text_catalan || '').trim() && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <input value={drawHint} onChange={e => setDrawHint(e.target.value)} placeholder="Què s'ha de dibuixar? (opcional)" aria-label="Indicació per al dibuix"
                   style={{ flex: 1, minWidth: 0, padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: '14px' }} />
            <button onClick={illustrate} disabled={aiLoadingKey === 'illustrate'} aria-label="Dibuixa la frase" title="Dibuixa la frase (IA)"
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', borderRadius: 'var(--r-md)', border: 'none', background: 'var(--saffron)', color: '#fff', fontWeight: 700, fontSize: '14px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              <FaMagic /> {aiLoadingKey === 'illustrate' ? 'Dibuixant…' : localDrill.image_url ? 'Torna a dibuixar' : 'Dibuixa'}
            </button>
          </div>
        )}

        {localDrill.video_url && (
          <div style={{ background: '#000', borderRadius: 'var(--r-xl)', overflow: 'hidden', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', boxShadow: 'var(--shadow-lg)', marginBottom: '0', border: '1px solid var(--border-strong)' }}>
            <video
                ref={videoRef}
                key={getSourceUrl(localDrill.video_url, 'video')}
                id="editor-video-preview"
                src={getSourceUrl(localDrill.video_url, 'video')}
                controls
                playsInline
                preload="auto"
                crossOrigin="anonymous"
                onPlay={() => addLog('Video: Play event triggered')}
                onError={(e) => addLog(`Video: Playback error: ${(e.target as any).error?.message || 'unknown'}`)}
                style={{ width: '100%', minHeight: '150px', maxHeight: '300px', display: 'block', backgroundColor: '#333' }}
                onLoadedMetadata={(e) => {
                  const dur = (e.target as HTMLVideoElement).duration;
                  if (dur) {
                      setVideoDuration(dur);
                      setTrimTimes(prev => ({ ...prev, end: Math.min(prev.end, dur) }));
                  }
                }}
            />
            <div style={{ width: '100%', padding: '14px 16px', background: '#0f172a', color: 'white' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '12px', fontWeight: 700 }}>
                    <button
                        onClick={() => {
                            if (videoRef.current) setTrimTimes(prev => ({ ...prev, start: videoRef.current!.currentTime }));
                        }}
                        style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--emerald)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}
                    >INICI</button>
                    <span style={{ color: 'var(--text-muted)' }}>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                    <button
                        onClick={() => {
                            if (videoRef.current) setTrimTimes(prev => ({ ...prev, end: videoRef.current!.currentTime }));
                        }}
                        style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--rose)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}
                    >FINAL</button>
                </div>
                <input
                    type="range"
                    aria-label="Temps d'inici"
                    min="0"
                    max={videoDuration}
                    step="0.1"
                    value={trimTimes.start}
                    onChange={e => setTrimTimes(prev => ({ ...prev, start: Math.min(parseFloat(e.target.value), prev.end - 0.1) }))}
                    style={{ width: '100%', marginBottom: '10px', accentColor: 'var(--brand-1)' }}
                />
                <input
                    type="range"
                    aria-label="Temps final"
                    min="0"
                    max={videoDuration}
                    step="0.1"
                    value={trimTimes.end}
                    onChange={e => setTrimTimes(prev => ({ ...prev, end: Math.max(parseFloat(e.target.value), prev.start + 0.1) }))}
                    style={{ width: '100%', marginBottom: '15px', accentColor: 'var(--brand-1)' }}
                />
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                      onClick={() => handleTrimVideo('video')}
                      disabled={aiLoadingKey !== null}
                      style={{ flex: 1, padding: '12px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)' }}
                  >
                      <FaScissors /> {aiLoadingKey === 'trim-video' ? '…' : 'Retallar Vídeo'}
                  </button>
                  <button
                      onClick={() => handleTrimVideo('audio')}
                      disabled={aiLoadingKey !== null}
                      style={{ flex: 1, padding: '12px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'pointer' }}
                  >
                      <FaScissors /> {aiLoadingKey === 'trim-audio' ? '…' : 'Extreure Àudio'}
                  </button>
                </div>
            </div>
          </div>
        )}

        {localDrill.audio_url && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
            <audio
                id="editor-audio-preview"
                src={getSourceUrl(localDrill.audio_url, 'audio')}
                onLoadedMetadata={(e) => {
                    const dur = (e.target as HTMLAudioElement).duration;
                    addLog(`Audio: Metadata loaded. Duration: ${dur}`);
                    setAudioDuration(dur || 60);
                }}
                onPlay={() => addLog('Audio: Play event triggered')}
                onError={(e) => addLog(`Audio: Playback error: ${(e.target as any).error?.message || 'unknown'}`)}
                style={{ display: 'block', width: '100%', marginBottom: '10px' }}
                controls
                preload="auto"
            />
            <button
                onClick={() => {
                    const a = document.getElementById('editor-audio-preview') as HTMLAudioElement;
                    if (a) a.play();
                }}
                style={{ width: '100%', padding: '14px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', color: 'var(--text)', cursor: 'pointer' }}
            >
              Reprodueix l'àudio
            </button>
            <div style={{ padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-soft)' }}>
                    <button
                        onClick={() => {
                            const a = document.getElementById('editor-audio-preview') as HTMLAudioElement;
                            if (a) setTrimTimes(prev => ({ ...prev, start: a.currentTime }));
                        }}
                        style={{ background: 'var(--surface)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}
                    >INICI</button>
                    <span>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                    <button
                        onClick={() => {
                            const a = document.getElementById('editor-audio-preview') as HTMLAudioElement;
                            if (a) setTrimTimes(prev => ({ ...prev, end: a.currentTime }));
                        }}
                        style={{ background: 'var(--surface)', color: 'var(--rose)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 14px', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}
                    >FINAL</button>
                </div>
                <input type="range" aria-label="Temps d'inici" min="0" max={audioDuration} step="0.1" value={trimTimes.start} onChange={e => setTrimTimes(p => ({...p, start: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '8px', accentColor: 'var(--brand-1)' }} />
                <input type="range" aria-label="Temps final" min="0" max={audioDuration} step="0.1" value={trimTimes.end} onChange={e => setTrimTimes(p => ({...p, end: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '12px', accentColor: 'var(--brand-1)' }} />
                <button onClick={handleTrimAudio} disabled={aiLoadingKey !== null} style={{ width: '100%', padding: '11px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)' }}>
                    <FaScissors /> {aiLoadingKey === 'trim-audio' ? '…' : 'Retallar Àudio'}
                </button>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
          <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaLanguage size={18} /> {aiLoadingKey === 'trans-text_tachelhit' ? '…' : 'CA➔SH'}</button>
          <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaLanguage size={18} /> {aiLoadingKey === 'trans-text_catalan' ? '…' : 'SH➔CA'}</button>
          <button onClick={handleTachelhitTTS} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaVolumeUp size={18} /> {aiLoadingKey === 'tts-shi' ? '…' : 'TTS'}</button>
          <button
                onClick={() => {
                    const hasAudio = localDrill.audio_url;
                    const hasVideo = localDrill.video_url;

                    if (hasAudio && hasVideo) {
                        if (confirm('Transcriure des del VÍDEO? (Cancel·la per a l\'ÀUDIO)')) {
                            handleAutoTranscribe('video');
                        } else {
                            handleAutoTranscribe('audio');
                        }
                    } else if (hasVideo) {
                        handleAutoTranscribe('video');
                    } else if (hasAudio) {
                        handleAutoTranscribe('audio');
                    } else {
                        toast.error('Primer enregistra o puja contingut.');
                    }
                }}
                disabled={!(localDrill.audio_url || localDrill.video_url) || aiLoadingKey !== null}
                aria-label="Transcriu automàticament"
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', opacity: (localDrill.audio_url || localDrill.video_url) ? 1 : 0.5 }}
            ><FaFileAlt size={18} /> {aiLoadingKey === 'transcribe-voice' ? '…' : 'Transcriu'}</button>
        </div>

                <div style={{ background: 'var(--surface)', padding: '20px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div><label htmlFor="fld-catalan" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Català</label><textarea id="fld-catalan" lang="ca" value={localDrill.text_catalan || ''} onChange={(e) => handleFieldChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  <div><label htmlFor="fld-tachelhit" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea id="fld-tachelhit" lang="shi" autoCapitalize="off" autoCorrect="off" spellCheck={false} value={localDrill.text_tachelhit || ''} onChange={(e) => handleFieldChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--brand-1)', fontWeight: 700, background: 'var(--surface-2)', fontFamily: 'var(--font-tifinagh)' }} /></div>
                  <div><label htmlFor="fld-arabic" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Àrab (العربية)</label><textarea id="fld-arabic" lang="ar" dir="rtl" value={localDrill.text_arabic || ''} onChange={(e) => handleFieldChange('text_arabic', e.target.value)} rows={2} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  <div>
                    <label htmlFor="fld-tachelhit-latin" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tachelhit (llatí)</label>
                    <input id="fld-tachelhit-latin" type="text" value={localDrill.text_tachelhit_latin || ''} onChange={(e) => handleFieldChange('text_tachelhit_latin', e.target.value)} placeholder="Escriu com al mòbil: aghrum, ta7anut, 3ad…" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} />
                    <TransliterationPreview
                      text={localDrill.text_tachelhit_latin || localDrill.text_tachelhit || ''}
                      onUseTifinagh={(tif) => handleFieldChange('text_tachelhit', tif)}
                      onUseLatin={(clean) => handleFieldChange('text_tachelhit_latin', clean)}
                    />
                  </div>

                  {/* AI tools: analyse the attested form + generate a draft suggestion (never overwrites gold) */}
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => { setAiAction('analyze'); setShowAi(true); }}
                      disabled={!localDrill.text_tachelhit}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: localDrill.text_tachelhit ? 'pointer' : 'not-allowed', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--brand-1)', opacity: localDrill.text_tachelhit ? 1 : 0.5 }}
                    >
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaMicroscope /> Analitza</span>
                    </button>
                    <button
                      onClick={() => { setAiAction('review'); setShowAi(true); }}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--amber)' }}
                    >
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaClipboardCheck /> Revisa</span>
                    </button>
                    <button
                      onClick={handleSuggest}
                      disabled={suggesting}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: suggesting ? 'wait' : 'pointer', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)' }}
                    >
                      {suggesting ? '…' : <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaComments /> Suggeriment</span>}
                    </button>
                  </div>

                  {/* Draft suggestion column — kept separate from the gold field */}
                  {localDrill.text_tachelhit_suggested && localDrill.text_tachelhit_suggested !== localDrill.text_tachelhit && (
                    <div style={{ padding: '12px 14px', background: 'var(--sky-soft)', border: '1px dashed var(--sky)', borderRadius: 'var(--r-md)' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--sky)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}><FaComments /> ESBORRANY D'IA (no és la forma recollida)</div>
                      <div style={{ fontFamily: 'var(--font-tifinagh)', fontSize: '16px', color: 'var(--text)', marginBottom: '8px' }}>{localDrill.text_tachelhit_suggested}</div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => { handleFieldChange('text_tachelhit', localDrill.text_tachelhit_suggested || ''); setLocalDrill(p => ({ ...p, text_tachelhit_suggested: '' })); }}
                          style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '12px', cursor: 'pointer', background: 'var(--emerald)', color: '#fff', border: 'none' }}
                        >
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaCheck /> Accepta com a forma</span>
                        </button>
                        <button
                          onClick={() => setLocalDrill(p => ({ ...p, text_tachelhit_suggested: '' }))}
                          style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '12px', cursor: 'pointer', background: 'var(--surface)', color: 'var(--text-soft)', border: '1px solid var(--border)' }}
                        >
                          Descarta
                        </button>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <div style={{ flex: 1 }}><label htmlFor="fld-variety" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Varietat</label><input id="fld-variety" type="text" value={localDrill.variety || ''} onChange={(e) => handleFieldChange('variety', e.target.value)} placeholder="tashelhit" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                    <div style={{ flex: 1 }}><label htmlFor="fld-region" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Regió</label><input id="fld-region" type="text" value={localDrill.region || ''} onChange={(e) => handleFieldChange('region', e.target.value)} placeholder="Souss" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  </div>
                  <div><label htmlFor="fld-tag" style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tag</label><input id="fld-tag" type="text" value={localDrill.tag || ''} onChange={(e) => handleFieldChange('tag', e.target.value)} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  <button
                    onClick={async () => {
                      try {
                        const res = await api.verifyDrill(localDrill.id, !localDrill.verified);
                        setLocalDrill(prev => ({ ...prev, verified: res.verified }));
                        toast.success(res.verified ? '✓ Verificat' : 'Verificació retirada');
                      } catch (e: any) {
                        toast.error(e.message || 'Cal un compte per verificar (👤 Perfil)');
                      }
                    }}
                    style={{
                      padding: '12px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '14px', cursor: 'pointer',
                      background: localDrill.verified ? 'var(--emerald-soft)' : 'var(--surface-2)',
                      color: localDrill.verified ? 'var(--emerald)' : 'var(--text-soft)',
                      border: localDrill.verified ? '1px solid var(--emerald)' : '1px solid var(--border)'
                    }}
                  >
                    {localDrill.verified
                      ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaCheck /> Verificat — toca per desverificar</span>
                      : <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaRegSquare /> Marca com a verificat (revisió humana)</span>}
                  </button>
                </div>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', padding: '12px 20px calc(12px + env(safe-area-inset-bottom, 0px))', background: 'var(--surface)', justifyContent: 'space-between', borderTop: '1px solid var(--border)', gap: '15px' }}>
        <button onClick={() => handleNavigate('prev')} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '14px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 600, fontSize: '15px', cursor: 'pointer' }}><FaChevronLeft /> Anterior</button>
        <button onClick={() => handleNavigate('next')} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '14px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 600, fontSize: '15px', cursor: 'pointer' }}>Següent <FaChevronRight /></button>
      </div>
      {showAi && (
        <AiAssistant
          drillId={localDrill.id}
          drillLabel={localDrill.text_catalan || localDrill.text_tachelhit || `Drill #${localDrill.id}`}
          autoAction={aiAction}
          onClose={() => setShowAi(false)}
        />
      )}
    </div>
  );
}
