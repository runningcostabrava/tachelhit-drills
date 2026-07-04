import { useState, useEffect, useRef } from 'react';
import { 
  FaTimes, 
  FaSave, 
  FaCamera, 
  FaVideo, 
  FaMicrophone, 
  FaKeyboard, 
  FaFolderOpen, 
  FaRobot, 
  FaLanguage, 
  FaChevronLeft, 
  FaChevronRight,
  FaCut as FaScissors
} from 'react-icons/fa';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { API_BASE, getMediaUrl } from '../config';
import { syncManager, type Drill } from '../services/OfflineSyncManager';
import { api } from '../api';
import { toast } from '../toast';
import AiAssistant from './AiAssistant';

interface MobileDrillEditorProps {
  drill: Drill;
  onClose: () => void;
  onUpdate: () => void;
  onNavigate: (direction: 'next' | 'prev') => void;
}

export default function MobileDrillEditor({ drill, onClose, onUpdate, onNavigate }: MobileDrillEditorProps) {
  const [localDrill, setLocalDrill] = useState<Drill>({ ...drill });
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
  }, [drill]);

  useEffect(() => {
    if ((window as any).Capacitor?.isNative) {
      VoiceRecorder.requestAudioRecordingPermission().catch(e => console.warn('VoiceRecorder permissions not available', e));
      SpeechRecognition.requestPermissions().catch(e => console.warn('SpeechRecognition permissions not available', e));
    }
  }, [drill]);

  const triggerSave = async (updatedDrill: Drill) => {
    try {
      const status = await Network.getStatus();
      if (status.connected && !updatedDrill.is_local) {
        await axios.put(`${API_BASE}/drills/${updatedDrill.id}`, updatedDrill);
      } else {
        await syncManager.queueAction({
          type: updatedDrill.is_local ? 'CREATE' : 'UPDATE',
          drillId: updatedDrill.id,
          payload: updatedDrill
        });
      }
      onUpdate();
    } catch (err) {
      addLog('Save queued offline');
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
        addLog('Photo data received');
        const base64Data = `data:image/${image.format};base64,${image.base64String}`;
        const response = await fetch(base64Data);
        const blob = await response.blob();
        const fileName = `photo_${localDrill.id}_${Date.now()}.jpg`;
        
        await syncManager.saveMediaLocally(blob, fileName);
        await syncManager.queueAction({
          type: 'UPLOAD_MEDIA',
          drillId: localDrill.id,
          mediaType: 'image',
          localPath: fileName,
          fileName: fileName
        });
        addLog('Photo captured & queued');
        setLocalDrill(prev => ({ ...prev, image_url: image.webPath }));
      }
    } catch (err: any) {
      addLog(`Photo error: ${err.message}`);
    }
  };

  const startVoiceRecording = async () => {
    try {
      const result = await VoiceRecorder.startRecording();
      if (result.value) {
        setIsRecording(true);
        addLog('Recording started...');
      }
    } catch (err: any) {
      addLog(`Mic error: ${err.message}`);
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
        addLog(`Trim error: ${err.message}`);
    } finally {
        setAiLoadingKey(null);
    }
  };

  const stopVoiceRecording = async () => {
    try {
      const result = await VoiceRecorder.stopRecording();
      setIsRecording(false);
      if (result.value && result.value.recordDataBase64) {
        const base64Response = await fetch(`data:${result.value.mimeType};base64,${result.value.recordDataBase64}`);
        const blob = await base64Response.blob();
        const fileName = `audio_${localDrill.id}_${Date.now()}.m4a`;
        
        const localUri = await syncManager.saveMediaLocally(blob, fileName);
        await syncManager.queueAction({
          type: 'UPLOAD_MEDIA',
          drillId: localDrill.id,
          mediaType: 'audio',
          localPath: fileName,
          fileName: fileName
        });
        addLog('Audio recorded & queued');
        // Update local media URLs to use the new local file immediately
        const resolvedPath = (window as any).Capacitor.convertFileSrc(localUri);
        setLocalMediaUrls(prev => ({ ...prev, audio: resolvedPath }));
        setLocalDrill(prev => ({ ...prev, audio_url: resolvedPath }));
      }
    } catch (err: any) {
      addLog(`Mic stop error: ${err.message}`);
    }
  };

  const startDictation = async () => {
    try {
      if ((window as any).Capacitor?.isNative) {
        const perm = await SpeechRecognition.checkPermissions();
        if (perm.speechRecognition !== 'granted') {
            const req = await SpeechRecognition.requestPermissions();
            if (req.speechRecognition !== 'granted') return addLog('Mic permission denied');
        }
      }

      const supported = await SpeechRecognition.available();
      if (!supported) return addLog('Speech not supported');

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
      addLog(`Dictation error: ${err.code || err.message || JSON.stringify(err)}`);
    }
  };

      const handleAutoTranscribe = async (sourceType?: 'audio' | 'video') => {
        let mediaSource = '';
        if (sourceType === 'audio') mediaSource = localDrill.audio_url || '';
        else if (sourceType === 'video') mediaSource = localDrill.video_url || '';
        else mediaSource = localDrill.audio_url || localDrill.video_url || '';

        if (!mediaSource) return alert('Please record and save media first.');
        
        const status = await Network.getStatus();
        if (!status.connected) return alert('Transcription requires internet connection.');

        setAiLoadingKey('transcribe-voice');
        addLog(`Transcribing ${sourceType || 'media'}...`);
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const currentContent = localDrill.text_tachelhit || '';
            const safeText = currentContent.trim() ? `${currentContent} (${res.data.corrected_transcription})` : res.data.corrected_transcription;
            
            const updated = { ...localDrill, text_tachelhit: safeText };
            setLocalDrill(updated);
            triggerSave(updated);
            addLog('Transcription success');
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message;
            alert(`Transcription failed: ${msg}`);
            addLog(`ASR Error: ${msg}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

  const handleTachelhitTTS = async () => {
    const text = localDrill.text_tachelhit;
    if (!text) return alert('Tachelhit field is empty.');
    
    const status = await Network.getStatus();
    if (!status.connected) return alert('TTS requires internet connection.');

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
        alert(`TTS failed: ${msg}`);
        addLog(`TTS Error: ${msg}`);
    } finally {
        setAiLoadingKey(null);
    }
  };

  const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
    const status = await Network.getStatus();
    if (!status.connected) return alert('Translation requires internet.');

    const sourceText = source === 'ca' ? localDrill.text_catalan : localDrill.text_tachelhit;
    if (!sourceText) return alert('Field is empty.');
    
    const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
    setAiLoadingKey(`trans-${targetField}`);
    try {
      const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
      const currentContent = (localDrill as any)[targetField] || '';
      const safeText = currentContent.trim() ? `${currentContent} (${res.data.translated_text})` : res.data.translated_text;
      
      const updated = { ...localDrill, [targetField]: safeText };
      setLocalDrill(updated);
      triggerSave(updated);
    } catch (err) { 
      alert('Translation failed.'); 
    } finally { 
      setAiLoadingKey(null); 
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
        addLog('No file chosen in editor handleFileChange');
        return;
    }

    addLog(`Editor: File chosen ${file.name} (${file.type})`);
    const type = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
    const fileName = `${type}_${localDrill.id}_${Date.now()}_${file.name}`;
    
    try {
        // Create an object URL only for UI preview purposes
        // IMPORTANT: We must NOT use this URL for any state that triggers re-renders 
        // which might involve components that don't handle blobs well (like some native listeners)
        const blobUrl = URL.createObjectURL(file);
        addLog(`Editor: Mapping ${type} URL to ${blobUrl}`);
        
        // Use a functional update to ensure we're not closing over stale state
        // and to avoid immediate re-render issues in the main drill object
        setLocalMediaUrls(prev => {
          const newUrls = { ...prev };
          newUrls[type] = blobUrl;
          return newUrls;
        });

        setLocalDrill(prev => {
          const updated = { ...prev };
          (updated as any)[`${type}_url`] = blobUrl;
          return updated;
        });

        addLog(`Editor: Saving ${type} locally...`);
        await syncManager.saveMediaLocally(file, fileName);
        addLog('Editor: Local save complete. Queuing upload...');
        await syncManager.queueAction({
            type: 'UPLOAD_MEDIA',
            drillId: localDrill.id,
            mediaType: type as any,
            localPath: fileName,
            fileName: fileName
        });
        addLog(`Editor: ${type} upload action created`);
    } catch (err: any) {
        addLog(`Editor error: ${err.message}`);
    }
  };

  const handleTrimVideo = async (mode: 'video' | 'audio') => {
    if (!localDrill.video_url) {
        addLog('Error: No video URL available for trimming');
        return;
    }
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
        addLog(`Trim API Error: ${err.message}`);
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


  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--bg)', zIndex: 11000, display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
            <div style={{ background: 'var(--brand-gradient)', padding: '20px 20px 26px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'white', borderBottomLeftRadius: 'var(--r-2xl)', borderBottomRightRadius: 'var(--r-2xl)', boxShadow: 'var(--shadow-brand)' }}>
                <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.18)', border: 'none', color: 'white', borderRadius: 'var(--r-pill)', width: '42px', height: '42px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><FaTimes size={20} /></button>
                <div style={{ color: 'white', fontSize: '20px', fontWeight: 800, letterSpacing: '-0.01em' }}>Edit Card</div>
                <button onClick={() => triggerSave(localDrill)} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.95)', color: 'var(--brand-1)', border: 'none', borderRadius: 'var(--r-md)', padding: '11px 18px', fontWeight: 700, fontSize: '14px', cursor: 'pointer', boxShadow: 'var(--shadow-sm)' }}><FaSave /> Save</button>
            </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px', paddingBottom: '120px' }}>
        <div style={{ background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
              <button onClick={capturePhoto} style={{ height: '56px', background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Camera"><FaCamera size={22} /></button>
              <button onClick={captureVideo} style={{ height: '56px', background: 'var(--brand-gradient-soft)', color: 'var(--brand-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Video"><FaVideo size={22} /></button>
              <button onClick={isRecording ? stopVoiceRecording : startVoiceRecording} style={{ height: '56px', background: isRecording ? 'var(--rose-soft)' : 'var(--rose)', color: isRecording ? 'var(--rose)' : 'white', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Voice Record"><FaMicrophone size={22} /></button>
              <button onClick={startDictation} style={{ height: '56px', background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Dictation"><FaKeyboard size={22} /></button>
              <button onClick={() => document.getElementById('gallery-upload')?.click()} style={{ height: '56px', background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} title="Gallery"><FaFolderOpen size={22} /></button>
            </div>
            <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-input" style={{ display: 'none' }} onChange={handleFileChange} />
            <input type="file" id="gallery-upload" style={{ display: 'none' }} onChange={handleFileChange} />
        </div>

        {localDrill.image_url && (
          <img src={getSourceUrl(localDrill.image_url, 'image')} alt="Drill Asset" style={{ width: '100%', height: '150px', borderRadius: 'var(--r-lg)', objectFit: 'cover', border: '1px solid var(--border)' }} />
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
                        style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--emerald)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '4px 10px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                    >INICI</button>
                    <span style={{ color: 'var(--text-muted)' }}>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                    <button
                        onClick={() => {
                            if (videoRef.current) setTrimTimes(prev => ({ ...prev, end: videoRef.current!.currentTime }));
                        }}
                        style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--rose)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 'var(--r-sm)', padding: '4px 10px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                    >FINAL</button>
                </div>
                <input 
                    type="range" 
                    min="0" 
                    max={videoDuration} 
                    step="0.1" 
                    value={trimTimes.start} 
                    onChange={e => setTrimTimes(prev => ({ ...prev, start: Math.min(parseFloat(e.target.value), prev.end - 0.1) }))}
                    style={{ width: '100%', marginBottom: '10px', accentColor: 'var(--brand-1)' }}
                />
                <input
                    type="range"
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
                      <FaScissors /> Retallar Vídeo
                  </button>
                  <button
                      onClick={() => handleTrimVideo('audio')}
                      disabled={aiLoadingKey !== null}
                      style={{ flex: 1, padding: '12px', background: 'var(--rose)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'pointer' }}
                  >
                      <FaScissors /> Extreure Àudio
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
              Play Àudio
            </button>
            <div style={{ padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-soft)' }}>
                    <button
                        onClick={() => {
                            const a = document.getElementById('editor-audio-preview') as HTMLAudioElement;
                            if (a) setTrimTimes(prev => ({ ...prev, start: a.currentTime }));
                        }}
                        style={{ background: 'var(--surface)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '4px 10px', fontWeight: 700, cursor: 'pointer' }}
                    >INICI</button>
                    <span>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                    <button
                        onClick={() => {
                            const a = document.getElementById('editor-audio-preview') as HTMLAudioElement;
                            if (a) setTrimTimes(prev => ({ ...prev, end: a.currentTime }));
                        }}
                        style={{ background: 'var(--surface)', color: 'var(--rose)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '4px 10px', fontWeight: 700, cursor: 'pointer' }}
                    >FINAL</button>
                </div>
                <input type="range" min="0" max={audioDuration} step="0.1" value={trimTimes.start} onChange={e => setTrimTimes(p => ({...p, start: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '8px', accentColor: 'var(--brand-1)' }} />
                <input type="range" min="0" max={audioDuration} step="0.1" value={trimTimes.end} onChange={e => setTrimTimes(p => ({...p, end: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '12px', accentColor: 'var(--brand-1)' }} />
                <button onClick={handleTrimAudio} disabled={aiLoadingKey !== null} style={{ width: '100%', padding: '11px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)' }}>
                    <FaScissors /> Retallar Àudio
                </button>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'var(--surface)', padding: '16px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
          <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaLanguage size={18} /> CA➔SH</button>
          <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--emerald-soft)', color: 'var(--emerald)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaLanguage size={18} /> SH➔CA</button>
          <button onClick={handleTachelhitTTS} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer' }}><FaRobot size={18} /> TTS</button>
          <button 
                onClick={() => {
                    const hasAudio = localDrill.audio_url;
                    const hasVideo = localDrill.video_url;

                    if (hasAudio && hasVideo) {
                        if (confirm('Transcribe from VIDEO? (Cancel for AUDIO)')) {
                            handleAutoTranscribe('video');
                        } else {
                            handleAutoTranscribe('audio');
                        }
                    } else if (hasVideo) {
                        handleAutoTranscribe('video');
                    } else if (hasAudio) {
                        handleAutoTranscribe('audio');
                    } else {
                        alert('Please record and save media first.');
                    }
                }} 
                disabled={!(localDrill.audio_url || localDrill.video_url) || aiLoadingKey !== null} 
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '5px', padding: '10px 4px', fontSize: '10px', fontWeight: 700, background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', opacity: (localDrill.audio_url || localDrill.video_url) ? 1 : 0.5 }}
            >🪄 Trans</button>
        </div>

                <div style={{ background: 'var(--surface)', padding: '20px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Català</label><textarea value={localDrill.text_catalan || ''} onChange={(e) => handleFieldChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  <div><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea value={localDrill.text_tachelhit || ''} onChange={(e) => handleFieldChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--brand-1)', fontWeight: 700, outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-tifinagh)' }} /></div>
                  <div><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tachelhit (llatí)</label><input type="text" value={localDrill.text_tachelhit_latin || ''} onChange={(e) => handleFieldChange('text_tachelhit_latin', e.target.value)} placeholder="Romanització llatina" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>

                  {/* AI tools: analyse the attested form + generate a draft suggestion (never overwrites gold) */}
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => { setAiAction('analyze'); setShowAi(true); }}
                      disabled={!localDrill.text_tachelhit}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: localDrill.text_tachelhit ? 'pointer' : 'not-allowed', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', border: '1px solid var(--brand-1)', opacity: localDrill.text_tachelhit ? 1 : 0.5 }}
                    >
                      🔍 Analitza
                    </button>
                    <button
                      onClick={() => { setAiAction('review'); setShowAi(true); }}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', background: 'var(--amber-soft)', color: 'var(--amber-strong)', border: '1px solid var(--amber)' }}
                    >
                      🔎 Revisa
                    </button>
                    <button
                      onClick={handleSuggest}
                      disabled={suggesting}
                      style={{ flex: 1, minWidth: '120px', padding: '11px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '13px', cursor: suggesting ? 'wait' : 'pointer', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)' }}
                    >
                      {suggesting ? '…' : '🤖 Suggeriment'}
                    </button>
                  </div>

                  {/* Draft suggestion column — kept separate from the gold field */}
                  {localDrill.text_tachelhit_suggested && localDrill.text_tachelhit_suggested !== localDrill.text_tachelhit && (
                    <div style={{ padding: '12px 14px', background: 'var(--sky-soft)', border: '1px dashed var(--sky)', borderRadius: 'var(--r-md)' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--sky)', marginBottom: '6px' }}>🤖 ESBORRANY D'IA (no és la forma recollida)</div>
                      <div style={{ fontFamily: 'var(--font-tifinagh)', fontSize: '16px', color: 'var(--text)', marginBottom: '8px' }}>{localDrill.text_tachelhit_suggested}</div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => { handleFieldChange('text_tachelhit', localDrill.text_tachelhit_suggested || ''); setLocalDrill(p => ({ ...p, text_tachelhit_suggested: '' })); }}
                          style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '12px', cursor: 'pointer', background: 'var(--emerald)', color: '#fff', border: 'none' }}
                        >
                          ✓ Accepta com a forma
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
                    <div style={{ flex: 1 }}><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Varietat</label><input type="text" value={localDrill.variety || ''} onChange={(e) => handleFieldChange('variety', e.target.value)} placeholder="tashelhit" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                    <div style={{ flex: 1 }}><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Regió</label><input type="text" value={localDrill.region || ''} onChange={(e) => handleFieldChange('region', e.target.value)} placeholder="Souss" style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '15px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
                  </div>
                  <div><label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tag</label><input type="text" value={localDrill.tag || ''} onChange={(e) => handleFieldChange('tag', e.target.value)} style={{ width: '100%', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: '16px', color: 'var(--text)', outline: 'none', background: 'var(--surface-2)', fontFamily: 'var(--font-sans)' }} /></div>
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
                    {localDrill.verified ? '✓ Verificat — toca per desverificar' : '☐ Marca com a verificat (revisió humana)'}
                  </button>
                </div>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', padding: '16px 20px', background: 'var(--surface)', justifyContent: 'space-between', borderTop: '1px solid var(--border)', gap: '15px' }}>
        <button onClick={() => onNavigate('prev')} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '14px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 600, fontSize: '15px', cursor: 'pointer' }}><FaChevronLeft /> Previous</button>
        <button onClick={() => onNavigate('next')} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '14px', background: 'var(--brand-gradient)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 600, fontSize: '15px', cursor: 'pointer' }}>Next <FaChevronRight /></button>
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
