import { useState, useEffect } from 'react';
import { FaCamera, FaVideo, FaMicrophone, FaKeyboard, FaFolderOpen, FaRobot, FaLanguage, FaSave, FaTimes, FaCut as FaScissors } from 'react-icons/fa';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { VoiceRecorder } from 'capacitor-voice-recorder';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { API_BASE, getMediaUrl } from '../config';
import { syncManager, type Drill } from '../services/OfflineSyncManager';

interface MobileDrillCreatorProps {
    onClose: () => void;
    onDrillCreated: () => void;
}

export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    const [drill, setDrill] = useState<Drill>({
        id: Date.now(),
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        tag: '',
        author: '',
        date_created: new Date().toISOString(),
        is_local: true
    });

    const [isRecording, setIsRecording] = useState(false);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [capturedAudio, setCapturedAudio] = useState<string | null>(null);
    const [aiLoadingKey, setAiLoadingKey] = useState<string | null>(null);
    const [debugLogs, setDebugLogs] = useState<string[]>(['[System] Native Creator Initialized']);
    const [trimTimes, setTrimTimes] = useState({ start: 0, end: 10 });
    const [videoDuration, setVideoDuration] = useState(60);

    const addLog = (msg: string) => {
        console.log(`[MobileDrillCreator] ${msg}`);
        setDebugLogs(prev => [`[${new Date().toLocaleTimeString().split(' ')[0]}] ${msg}`, ...prev].slice(0, 20));
    };

    useEffect(() => {
        if ((window as any).Capacitor?.isNative) {
            VoiceRecorder.requestAudioRecordingPermission().catch(e => console.warn('VoiceRecorder permissions not available', e));
            SpeechRecognition.requestPermissions().catch(e => console.warn('SpeechRecognition permissions not available', e));
        }
    }, []);

    const triggerSave = async (updatedDrill: Partial<Drill>) => {
        try {
            await syncManager.queueAction({
                type: updatedDrill.is_local ? 'CREATE' : 'UPDATE',
                drillId: updatedDrill.id!,
                payload: updatedDrill
            });
            syncManager.sync();
        } catch (err) {
            addLog('Save queued offline');
        }
    };

    const handleTextChange = (field: keyof Drill, value: string) => {
        const updated = { ...drill, [field]: value };
        setDrill(updated);
    };

    const capturePhoto = async () => {
        try {
            const status = await Camera.requestPermissions();
            if (status.camera !== 'granted' && status.photos !== 'granted') {
                addLog(`Permissions status: ${JSON.stringify(status)}`);
            }

            const image = await Camera.getPhoto({
                quality: 50,
                width: 640,
                height: 480,
                allowEditing: false,
                resultType: CameraResultType.Base64,
                source: CameraSource.Camera,
                saveToGallery: false,
                correctOrientation: true,
                presentationStyle: 'fullscreen',
                webUseInput: false
            });

            if (image && image.base64String) {
                const base64Data = `data:image/${image.format};base64,${image.base64String}`;
                setCapturedImage(base64Data);
                
                const response = await fetch(base64Data);
                const blob = await response.blob();
                const fileName = `photo_${Date.now()}.jpg`;
                
                await syncManager.saveMediaLocally(blob, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id!,
                    mediaType: 'image',
                    localPath: fileName,
                    fileName: fileName
                });
                addLog('Photo captured & queued');
            }
        } catch (err: any) {
            addLog(`Photo error: ${err.message}`);
        }
    };

    const captureVideo = async () => {
        try {
            document.getElementById('native-video-input')?.click();
        } catch (err: any) {
            addLog(`Video trigger error: ${err.message}`);
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

    const stopVoiceRecording = async () => {
        try {
            const result = await VoiceRecorder.stopRecording();
            setIsRecording(false);
            if (result.value && result.value.recordDataBase64) {
                const base64Response = await fetch(`data:${result.value.mimeType};base64,${result.value.recordDataBase64}`);
                const blob = await base64Response.blob();
                const fileName = `audio_${Date.now()}.m4a`;
                
                setCapturedAudio(URL.createObjectURL(blob));
                await syncManager.saveMediaLocally(blob, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id!,
                    mediaType: 'audio',
                    localPath: fileName,
                    fileName: fileName
                });
                addLog('Audio recorded & queued');
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
                    setDrill(prev => ({ ...prev, text_catalan: transcript }));
                }
            });
        } catch (err: any) {
            addLog(`Dictation error: ${err.code || err.message || JSON.stringify(err)}`);
        }
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }

        addLog(`File selected: ${file.name} (${file.type})`);
        const type = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
        const fileName = `${type}_${Date.now()}_${file.name}`;
        
        try {
            const blobUrl = URL.createObjectURL(file);
            if (type === 'image') setCapturedImage(blobUrl);
            if (type === 'video') setCapturedVideo(blobUrl);
            if (type === 'audio') setCapturedAudio(blobUrl);

            if ((window as any).Capacitor?.isNative) {
                await syncManager.saveMediaLocally(file, fileName);
            }
            if ((window as any).Capacitor?.isNative) {
                await syncManager.saveMediaLocally(file, fileName);
                await syncManager.queueAction({
                    type: 'UPLOAD_MEDIA',
                    drillId: drill.id!,
                    mediaType: type as any,
                    localPath: fileName,
                    fileName: fileName
                });
                addLog(`${type} successfully queued`);
            } else {
                // Web-based direct upload
                const formData = new FormData();
                formData.append('file', file, fileName);
                addLog(`Uploading ${type} to ${API_BASE}...`);
                const res = await axios.post(`${API_BASE}/upload-media/${drill.id}/${type}`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                if (res.data.url) {
                    addLog(`${type} uploaded: ${res.data.url.substring(0, 30)}...`);
                }
            }
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.message || 'Unknown error';
            addLog(`ERROR: ${type} upload: ${errorMsg}`);
            console.error('Upload error details:', err);
        }
    };

    const handleAutoTranscribe = async (sourceType?: 'audio' | 'video') => {
        let mediaSource = '';
        if (sourceType === 'audio') mediaSource = drill.audio_url || capturedAudio || '';
        else if (sourceType === 'video') mediaSource = drill.video_url || capturedVideo || '';
        else mediaSource = drill.audio_url || drill.video_url || capturedAudio || capturedVideo || '';

        if (!mediaSource) {
            return alert('Please record and save media first.');
        }
        
        const status = await Network.getStatus();
        if (!status.connected) {
            return alert('Transcription requires internet connection.');
        }

        setAiLoadingKey('transcribe-voice');
        try {
            const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const currentContent = drill.text_tachelhit || '';
            const safeText = currentContent.trim() ? `${currentContent} (${res.data.corrected_transcription})` : res.data.corrected_transcription;
            
            const updated = { ...drill, text_tachelhit: safeText };
            setDrill(updated);
            triggerSave(updated);
            addLog('Transcription success');
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message;
            alert(`Transcription failed: ${msg}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

    const handleTachelhitTTS = async () => {
        const text = drill.text_tachelhit;
        if (!text) return alert('Tachelhit field is empty.');
        
        const status = await Network.getStatus();
        if (!status.connected) return alert('TTS requires internet connection.');

        setAiLoadingKey('tts-shi');
        try {
            const res = await axios.post(`${API_BASE}/tts/tachelhit`, { text, drill_id: drill.id });
            if (res.data.url) {
                new Audio(getMediaUrl(res.data.url)).play();
            }
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message;
            alert(`TTS failed: ${msg}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

    const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        const status = await Network.getStatus();
        if (!status.connected) {
            return alert('Translation requires internet connection.');
        }

        const sourceText = source === 'ca' ? drill.text_catalan : drill.text_tachelhit;
        if (!sourceText) {
            return alert('Source field is empty.');
        }
        
        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        setAiLoadingKey(`trans-${targetField}`);

        try {
            const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
            const currentContent = (drill as any)[targetField] || '';
            const safeText = currentContent.trim() ? `${currentContent} (${res.data.translated_text})` : res.data.translated_text;

            const updated = { ...drill, [targetField]: safeText };
            setDrill(updated);
            triggerSave(updated);
            addLog('Translation success');
        } catch (err: any) {
            alert('Translation failed.');
        } finally {
            setAiLoadingKey(null);
        }
    };

    const handleTrimVideo = async (mode: 'video' | 'audio') => {
        setAiLoadingKey(`trim-${mode}`);
        try {
            const endpoint = mode === 'video' ? 'trim-video' : 'trim-audio';
            const res = await axios.post(`${API_BASE}/drills/${drill.id}/${endpoint}`, {
                start_time: trimTimes.start,
                end_time: trimTimes.end
            });
            if (res.data.url) {
                if (mode === 'video') {
                    setCapturedVideo(getMediaUrl(res.data.url));
                    addLog('Video trimmed successfully');
                } else {
                    setCapturedAudio(getMediaUrl(res.data.url));
                    addLog('Trimmed audio extracted');
                }
            }
        } catch (err: any) {
            addLog(`Trim error: ${err.message}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: '#F3F4F6', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaTimes size={20} /></button>
                <div style={{ color: 'yellow', fontSize: '24px', fontWeight: 900, letterSpacing: '1px', textShadow: '2px 2px 4px rgba(0,0,0,0.5)' }}>NEW DRILL p2</div>
                <button onClick={() => { triggerSave(drill); onDrillCreated(); }} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#10B981', color: 'white', border: 'none', borderRadius: '12px', padding: '10px 18px', fontWeight: 'bold' }}><FaSave /> Save</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '120px' }}>
                <div style={{ background: 'white', padding: '15px', borderRadius: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', border: '1px solid #E5E7EB' }}>
                    <div style={{ gridTemplateColumns: 'repeat(5, 1fr)', display: 'grid', gap: '10px' }}>
                        <button onClick={capturePhoto} style={{ height: '55px', background: '#EBFBEE', color: '#166534', border: '1px solid #D1FAE5', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Camera"><FaCamera size={22} /></button>
                        <button onClick={captureVideo} style={{ height: '55px', background: '#F3E8FF', color: '#7E22CE', border: '1px solid #E9D5FF', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Video"><FaVideo size={22} /></button>
                        <button onClick={isRecording ? stopVoiceRecording : startVoiceRecording} style={{ height: '55px', background: isRecording ? '#FFE4E6' : '#E11D48', color: isRecording ? '#E11D48' : 'white', border: `1px solid ${isRecording ? '#FECDD3' : '#E11D48'}`, borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Voice Record"><FaMicrophone size={22} /></button>
                        <button onClick={startDictation} style={{ height: '55px', background: '#FFF7ED', color: '#9A3412', border: '1px solid #FFEDD5', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Dictation"><FaKeyboard size={22} /></button>
                        <button onClick={() => document.getElementById('gallery-upload')?.click()} style={{ height: '55px', background: '#F1F5F9', color: '#334155', border: '1px solid #E2E8F0', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Gallery"><FaFolderOpen size={22} /></button>
                    </div>
                    <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-input" style={{ display: 'none' }} onChange={handleFileChange} />
                    <input type="file" id="gallery-upload" style={{ display: 'none' }} onChange={handleFileChange} />
                </div>

                {capturedImage && <img src={capturedImage} alt="Preview" style={{ width: '100%', height: '150px', borderRadius: '12px', objectFit: 'cover' }} />}
                {capturedVideo && (
                    <div style={{ background: '#000', borderRadius: '16px', overflow: 'hidden', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.3)', marginBottom: '15px', border: '1px solid #333' }}>
                        <video 
                            id="creator-video-preview"
                            key={capturedVideo}
                            src={capturedVideo} 
                            controls 
                            playsInline 
                            preload="auto"
                            onPlay={() => addLog('Video Playback started')}
                            onError={(e) => addLog(`Video Load Error: ${(e.target as any).error?.message || 'Check format'}`)}
                            onLoadedMetadata={(e) => {
                                const dur = (e.target as HTMLVideoElement).duration;
                                if (dur) {
                                    addLog(`Video loaded: ${dur.toFixed(1)}s`);
                                    setVideoDuration(dur);
                                    setTrimTimes(prev => ({ ...prev, end: dur }));
                                }
                            }}
                            style={{ width: '100%', maxHeight: '40vh', display: 'block', backgroundColor: '#000', objectFit: 'contain' }} 
                        />
                        <div style={{ width: '100%', padding: '15px', background: '#111' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '12px', fontWeight: 'bold' }}>
                                <button 
                                    onClick={() => {
                                        const v = document.getElementById('creator-video-preview') as HTMLVideoElement;
                                        if (v) setTrimTimes(prev => ({ ...prev, start: v.currentTime }));
                                    }}
                                    style={{ background: '#333', color: '#10B981', border: '1px solid #444', borderRadius: '4px', padding: '2px 6px', fontSize: '10px' }}
                                >INICI</button>
                                <span style={{ color: '#9CA3AF' }}>{trimTimes.start.toFixed(1)}s - {trimTimes.end.toFixed(1)}s</span>
                                <button 
                                    onClick={() => {
                                        const v = document.getElementById('creator-video-preview') as HTMLVideoElement;
                                        if (v) setTrimTimes(prev => ({ ...prev, end: v.currentTime }));
                                    }}
                                    style={{ background: '#333', color: '#EF4444', border: '1px solid #444', borderRadius: '4px', padding: '2px 6px', fontSize: '10px' }}
                                >FINAL</button>
                            </div>
                            <input 
                                type="range" 
                                min="0" 
                                max={videoDuration} 
                                step="0.1" 
                                value={trimTimes.start} 
                                onChange={e => setTrimTimes(p => ({...p, start: Math.min(parseFloat(e.target.value), p.end - 0.1)}))} 
                                style={{ width: '100%', marginBottom: '10px' }} 
                            />
                            <input 
                                type="range" 
                                min="0" 
                                max={videoDuration} 
                                step="0.1" 
                                value={trimTimes.end} 
                                onChange={e => setTrimTimes(p => ({...p, end: Math.max(parseFloat(e.target.value), p.start + 0.1)}))} 
                                style={{ width: '100%', marginBottom: '15px' }} 
                            />
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button 
                                    onClick={() => handleTrimVideo('video')} 
                                    disabled={aiLoadingKey !== null} 
                                    style={{ flex: 1, padding: '12px', background: '#4F46E5', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                                >
                                    <FaScissors /> Retallar Vídeo
                                </button>
                                <button 
                                    onClick={() => handleTrimVideo('audio')} 
                                    disabled={aiLoadingKey !== null} 
                                    style={{ flex: 1, padding: '12px', background: '#E11D48', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                                >
                                    <FaScissors /> Extreure Àudio
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {capturedAudio && (
                    <div style={{ background: 'white', padding: '15px', borderRadius: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', border: '1px solid #E5E7EB', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <audio 
                            id="creator-audio-preview"
                            src={capturedAudio}
                            style={{ width: '100%', marginBottom: '8px' }}
                            controls
                            preload="auto"
                            onPlay={() => addLog('Creator Audio: Play event')}
                            onError={(e) => addLog(`Creator Audio: Error: ${(e.target as any).error?.message}`)}
                        />
                        <button 
                            onClick={() => {
                                const a = document.getElementById('creator-audio-preview') as HTMLAudioElement;
                                if (a) a.play().catch(e => addLog(`Play error: ${e.message}`));
                            }} 
                            style={{ width: '100%', padding: '14px', background: '#f3f4f6', border: 'none', borderRadius: '12px', fontWeight: 700, fontSize: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}
                        >
                            🔊 Escolta la gravació
                        </button>
                        <div style={{ padding: '10px', background: '#F9FAFB', borderRadius: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '11px', fontWeight: 'bold', color: '#6B7280' }}>
                                <span>INICI ÀUDIO: {trimTimes.start.toFixed(1)}s</span>
                                <span>FINAL: {trimTimes.end.toFixed(1)}s</span>
                            </div>
                            <input type="range" min="0" max="60" step="0.1" value={trimTimes.start} onChange={e => setTrimTimes(p => ({...p, start: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '8px' }} />
                            <input type="range" min="0" max="60" step="0.1" value={trimTimes.end} onChange={e => setTrimTimes(p => ({...p, end: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '12px' }} />
                            <button onClick={() => handleTrimVideo('audio')} disabled={aiLoadingKey !== null} style={{ width: '100%', padding: '10px', background: '#4F46E5', color: 'white', border: 'none', borderRadius: '10px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '13px' }}>
                                <FaScissors /> Retallar Àudio
                            </button>
                        </div>
                    </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'white', padding: '15px', borderRadius: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', border: '1px solid #E5E7EB' }}>
                    <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '8px 4px', fontSize: '9px', fontWeight: 700, background: '#EEF2FF', color: '#4338CA', border: 'none', borderRadius: '12px' }}><FaLanguage size={18} /> CA➔SH</button>
                    <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '8px 4px', fontSize: '9px', fontWeight: 700, background: '#ECFDF5', color: '#059669', border: 'none', borderRadius: '12px' }}><FaLanguage size={18} /> SH➔CA</button>
                    <button onClick={handleTachelhitTTS} disabled={aiLoadingKey !== null} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', padding: '8px 4px', fontSize: '9px', fontWeight: 700, background: '#FEF3C7', color: '#B45309', border: 'none', borderRadius: '12px' }}><FaRobot size={18} /> TTS</button>
                    <button 
                        onClick={() => {
                            const hasAudio = drill.audio_url || capturedAudio;
                            const hasVideo = drill.video_url || capturedVideo;

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
                                alert('Please record or pick media first.');
                            }
                        }} 
                        disabled={!(drill.audio_url || drill.video_url || capturedAudio || capturedVideo) || aiLoadingKey !== null} 
                        style={{ padding: '12px 4px', background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '10px', opacity: (drill.audio_url || drill.video_url || capturedAudio || capturedVideo) ? 1 : 0.5 }}
                    >🪄 Trans</button>
                </div>

                <div style={{ background: 'white', padding: '20px', borderRadius: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', border: '1px solid #E5E7EB', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <div><label style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>Català</label><textarea value={drill.text_catalan || ''} onChange={(e) => handleTextChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid #D1D5DB', borderRadius: '14px', fontSize: '16px', color: '#1F2937', outline: 'none', background: '#F9FAFB' }} /></div>
                    <div><label style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea value={drill.text_tachelhit || ''} onChange={(e) => handleTextChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '14px', border: '1px solid #D1D5DB', borderRadius: '14px', fontSize: '16px', color: '#4F46E5', fontWeight: 700, outline: 'none', background: '#F9FAFB' }} /></div>
                    <div><label style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>Tag</label><input type="text" value={drill.tag || ''} onChange={(e) => handleTextChange('tag', e.target.value)} style={{ width: '100%', padding: '14px', border: '1px solid #D1D5DB', borderRadius: '14px', fontSize: '16px', color: '#1F2937', outline: 'none', background: '#F9FAFB' }} /></div>
                </div>

                <div style={{ background: '#111', color: '#0f0', padding: '10px', borderRadius: '8px', fontSize: '10px', fontFamily: 'monospace', height: '100px', overflowY: 'auto' }}>
                    <div style={{ color: '#fff', borderBottom: '1px solid #333', paddingBottom: '4px', marginBottom: '4px' }}>DEBUG LOGS</div>
                    {debugLogs.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </div>
        </div>
    );
}
