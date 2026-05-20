import { useState, useEffect } from 'react';
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

    const addLog = (msg: string) => {
        setDebugLogs(prev => [`[${new Date().toLocaleTimeString().split(' ')[0]}] ${msg}`, ...prev].slice(0, 12));
    };

    useEffect(() => {
        VoiceRecorder.requestAudioRecordingPermission();
        SpeechRecognition.requestPermissions();
    }, []);

    const triggerSave = async (updatedDrill: Partial<Drill>) => {
        try {
            const status = await Network.getStatus();
            if (status.connected && !updatedDrill.is_local) {
                await axios.put(`${API_BASE}/drills/${updatedDrill.id}`, updatedDrill);
            } else {
                await syncManager.queueAction({
                    type: updatedDrill.is_local ? 'CREATE' : 'UPDATE',
                    drillId: updatedDrill.id!,
                    payload: updatedDrill
                });
            }
        } catch (err) {
            addLog('Save queued offline');
        }
    };

    const handleTextChange = (field: keyof Drill, value: string) => {
        const updated = { ...drill, [field]: value };
        setDrill(updated);
        // Auto-save disabled
    };

    const capturePhoto = async () => {
        try {
            const status = await Camera.requestPermissions();
            if (status.camera !== 'granted') {
                return alert('Camera permission required.');
            }

            addLog('Opening camera...');
            const image = await Camera.getPhoto({
                quality: 80,
                allowEditing: false,
                resultType: CameraResultType.Base64,
                source: CameraSource.Camera,
                saveToGallery: false,
                correctOrientation: true,
                presentationStyle: 'fullscreen'
            });

            if (image && image.base64String) {
                addLog('Photo data received');
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
            alert(`Photo error: ${err.message}`);
        }
    };

    const captureVideo = async () => {
        try {
            // Capacitor Camera doesn't support video recording directly in all versions easily via getPhoto
            // We use the native capture fallback or a dedicated plugin if needed, 
            // but many people use captureVideo from @capacitor/camera if available or native input.
            // For now, let's use native input for video as it's more reliable for video than getUserMedia.
            document.getElementById('native-video-input')?.click();
        } catch (err: any) {
            addLog(`Video error: ${err.message}`);
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
            const perm = await SpeechRecognition.checkPermissions();
            if (perm.speechRecognition !== 'granted') {
                const req = await SpeechRecognition.requestPermissions();
                if (req.speechRecognition !== 'granted') return addLog('Mic permission denied');
            }

            const supported = await SpeechRecognition.available();
            if (!supported) return addLog('Speech not supported');

            addLog('Starting dictation...');
            await SpeechRecognition.start({
                language: 'ca-ES',
                partialResults: false,
                popup: true
            });

            SpeechRecognition.addListener('partialResults', (data: any) => {
                if (data.matches && data.matches.length > 0) {
                    const transcript = data.matches[0];
                    addLog(`Dictated: ${transcript}`);
                    setDrill(prev => ({ ...prev, text_catalan: transcript }));
                }
            });
        } catch (err: any) {
            addLog(`Dictation error: ${err.code || err.message || JSON.stringify(err)}`);
        }
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const type = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
        const fileName = `${type}_${Date.now()}_${file.name}`;
        
        if (type === 'image') setCapturedImage(URL.createObjectURL(file));
        if (type === 'video') setCapturedVideo(URL.createObjectURL(file));
        if (type === 'audio') setCapturedAudio(URL.createObjectURL(file));

        await syncManager.saveMediaLocally(file, fileName);
        await syncManager.queueAction({
            type: 'UPLOAD_MEDIA',
            drillId: drill.id!,
            mediaType: type as any,
            localPath: fileName,
            fileName: fileName
        });
        addLog(`${type} queued from file`);
    };

    const handleAutoTranscribe = async () => {
        const mediaSource = drill.audio_url || drill.video_url;
        if (!mediaSource) return alert('Please record and save media first.');
        
        const status = await Network.getStatus();
        if (!status.connected) return alert('Transcription requires internet connection.');

        setAiLoadingKey('transcribe-voice');
        addLog('Transcribing media...');
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
            addLog(`ASR Error: ${msg}`);
        } finally {
            setAiLoadingKey(null);
        }
    };

    const handleImportLink = async () => {
        const url = prompt('Paste video or audio link (YouTube, Instagram, etc.):');
        if (!url) return;

        const status = await Network.getStatus();
        if (!status.connected) return alert('Importing via link requires internet.');

        setAiLoadingKey('import-link');
        addLog('Importing link...');
        try {
            const res = await axios.post(`${API_BASE}/import-link`, { url, drill_id: drill.id });
            if (res.data.url) {
                const updated = { ...drill, video_url: res.data.url };
                setDrill(updated);
                setCapturedVideo(res.data.url);
                triggerSave(updated);
                addLog('Import success');
            }
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message;
            alert(`Import failed: ${msg}`);
            addLog(`Import Error: ${msg}`);
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
        addLog('Generating Tachelhit TTS...');
        try {
            const res = await axios.post(`${API_BASE}/tts/tachelhit`, { text, drill_id: drill.id });
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
        if (!status.connected) return alert('Translation requires internet connection.');

        const sourceText = source === 'ca' ? drill.text_catalan : drill.text_tachelhit;
        if (!sourceText) return alert('Source field is empty.');
        
        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        setAiLoadingKey(`trans-${targetField}`);

        try {
            const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
            const currentContent = (drill as any)[targetField] || '';
            const safeText = currentContent.trim() ? `${currentContent} (${res.data.translated_text})` : res.data.translated_text;

            const updated = { ...drill, [targetField]: safeText };
            setDrill(updated);
            triggerSave(updated);
        } catch (err) {
            alert('Translation failed.');
        } finally {
            setAiLoadingKey(null);
        }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none', borderRadius: '50%', width: '40px', height: '40px' }}>✕</button>
                <div style={{ color: 'white', fontSize: '18px', fontWeight: 700 }}>Native Creator</div>
                <button onClick={() => { triggerSave(drill); onDrillCreated(); }} style={{ background: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px' }}>💾 Save & Close</button>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '16px', border: '1px solid #e0e0e0' }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#666', textAlign: 'center', fontWeight: 'bold' }}>NATIVE MEDIA CONTROLS</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '12px' }}>
                        <button onClick={capturePhoto} style={{ height: '70px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>📷 Take Photo</button>
                        <button onClick={captureVideo} style={{ height: '70px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>🎬 Record Video</button>
                        <button onClick={isRecording ? stopVoiceRecording : startVoiceRecording} style={{ height: '70px', background: isRecording ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>
                            {isRecording ? '⏹️ Stop Mic' : '🎙️ Record Audio'}
                        </button>
                        <button onClick={startDictation} style={{ height: '70px', background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>🗣️ Speak (Català)</button>
                    </div>
                    <button onClick={handleImportLink} disabled={aiLoadingKey !== null} style={{ width: '100%', height: '50px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>🔗 Import via Link (YouTube/Insta)</button>
                    <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-input" style={{ display: 'none' }} onChange={handleFileChange} />
                </div>

                {capturedImage && <img src={capturedImage} alt="Preview" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover' }} />}
                {capturedVideo && (
                    <div style={{ background: '#000', borderRadius: '12px', overflow: 'hidden', width: '100%', minHeight: '200px', display: 'flex', alignItems: 'center' }}>
                        <video src={capturedVideo} controls playsInline preload="metadata" style={{ width: '100%', borderRadius: '12px' }} />
                    </div>
                )}
                {capturedAudio && <button onClick={() => new Audio(capturedAudio).play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: '1px solid #e0e0e0', borderRadius: '10px', fontWeight: 600 }}>🔊 Play Audio Asset</button>}

                <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tag</label><input type="text" value={drill.tag || ''} onChange={(e) => handleTextChange('tag', e.target.value)} style={{ width: '100%', padding: '10px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '8px' }}>
                    <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ padding: '12px', background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '11px' }}>🤖 CA➔SHI</button>
                    <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ padding: '12px', background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '11px' }}>🤖 SHI➔CA</button>
                    <button onClick={handleTachelhitTTS} disabled={aiLoadingKey !== null} style={{ padding: '12px', background: '#fef3c7', color: '#92400e', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '11px' }}>🔊 TTS SHI</button>
                    <button 
                        onClick={() => {
                            if (drill.audio_url || drill.video_url) {
                                // If already saved and has URL, it will work
                                handleAutoTranscribe(); // Need to call the actual transcribe function if it exists or define it
                            } else {
                                alert('Please finish/save drill to enable transcription.');
                            }
                        }} 
                        disabled={!(drill.audio_url || drill.video_url || capturedAudio || capturedVideo) || aiLoadingKey !== null} 
                        style={{ padding: '12px', background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '11px', opacity: (drill.audio_url || drill.video_url || capturedAudio || capturedVideo) ? 1 : 0.5 }}
                    >🪄 Transcribe</button>
                </div>

                <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Català</label><textarea value={drill.text_catalan || ''} onChange={(e) => handleTextChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>
                <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea value={drill.text_tachelhit || ''} onChange={(e) => handleTextChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>

                <div style={{ background: '#111', color: '#0f0', padding: '10px', borderRadius: '8px', fontSize: '10px', fontFamily: 'monospace', height: '100px', overflowY: 'auto' }}>
                    <div style={{ color: '#fff', borderBottom: '1px solid #333', paddingBottom: '4px', marginBottom: '4px' }}>DEBUG LOGS</div>
                    {debugLogs.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </div>
        </div>
    );
}
