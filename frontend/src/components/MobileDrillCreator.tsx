import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE, getMediaUrl } from '../config';

interface MobileDrillCreatorProps {
    onClose: () => void;
    onDrillCreated: () => void;
}

interface Drill {
    id?: number;
    text_catalan?: string;
    text_tachelhit?: string;
    text_arabic?: string;
    audio_url?: string;
    video_url?: string;
    image_url?: string;
    tag?: string;
    author?: string;
    date_created?: string;
}

export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    const [drill, setDrill] = useState<Drill>({ text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '', author: '' });

    const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
    const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [capturedAudio, setCapturedAudio] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [aiLoadingKey, setAiLoadingKey] = useState<string | null>(null);
    const [lastSaved, setLastSaved] = useState<string | null>(null);

    // 🐛 LIVE DEBUG LOGGER
    const [debugLogs, setDebugLogs] = useState<string[]>(['[System] Creator Initialized']);
    const addLog = (msg: string) => {
        setDebugLogs(prev => [`[${new Date().toLocaleTimeString().split(' ')[0]}] ${msg}`, ...prev].slice(0, 12));
    };

    const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const isCreatingRef = useRef(false);
    const pendingSaveRef = useRef<Drill | null>(null);
    const drillRef = useRef<Drill>(drill);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const recognitionRef = useRef<any>(null);

    useEffect(() => { drillRef.current = drill; }, [drill]);

    useEffect(() => {
        return () => {
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
            stopCamera();
        };
    }, []);

    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'ca-ES';
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;
            recognitionRef.current.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                addLog(`Dictation heard: ${transcript}`);
                setDrill(prev => {
                    const fresh = { ...prev, text_catalan: transcript };
                    triggerDirectSave(fresh);
                    return fresh;
                });
            };
        }
    }, []);

    useEffect(() => {
        if (cameraMode && previewRef.current && streamRef.current) {
            addLog(`Binding stream to <video> for ${cameraMode}`);
            previewRef.current.srcObject = streamRef.current;
            previewRef.current.play()
                .then(() => addLog('Video playback started'))
                .catch(e => addLog(`Video autoplay error: ${e.message}`));
        }
    }, [cameraMode]);

    const getSupportedMimeType = (type: 'audio' | 'video') => {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        if (isIOS) return type === 'audio' ? { mime: 'audio/mp4', ext: 'm4a' } : { mime: 'video/mp4', ext: 'mp4' };
        return type === 'audio' ? { mime: 'audio/webm', ext: 'webm' } : { mime: 'video/webm', ext: 'webm' };
    };

    const triggerDirectSave = async (freshDrill: Drill) => {
        const status = await Network.getStatus();
        const cleanPayload = { ...freshDrill };

        if (status.connected) {
            try {
                if (freshDrill.id && freshDrill.id < 1000000) {
                    await axios.put(`${API_BASE}/drills/${freshDrill.id}`, cleanPayload);
                    setLastSaved(`Online: ${new Date().toLocaleTimeString()}`);
                } else {
                    if (isCreatingRef.current) { pendingSaveRef.current = cleanPayload; return; }
                    isCreatingRef.current = true;
                    const res = await axios.post(`${API_BASE}/drills/`, cleanPayload);
                    setDrill(prev => {
                        const updatedWithId = { ...prev, id: res.data.id };
                        if (pendingSaveRef.current) {
                            axios.put(`${API_BASE}/drills/${res.data.id}`, { ...pendingSaveRef.current, id: res.data.id });
                            pendingSaveRef.current = null;
                        }
                        return updatedWithId;
                    });
                    setLastSaved(`Online: ${new Date().toLocaleTimeString()}`);
                    isCreatingRef.current = false;
                }
            } catch (err) { isCreatingRef.current = false; saveOffline(freshDrill); }
        } else { saveOffline(freshDrill); }
    };

    const saveOffline = (drillToSave: any) => {
        let currentDrill = { ...drillToSave };
        if (!currentDrill.id) { currentDrill.id = Date.now(); setDrill(currentDrill); }
        const queue = JSON.parse(localStorage.getItem('sync_queue') || '[]');
        const filteredQueue = queue.filter((d: any) => d.id !== currentDrill.id);
        filteredQueue.push(currentDrill);
        localStorage.setItem('sync_queue', JSON.stringify(filteredQueue));
        setLastSaved(`Offline Cache: ${new Date().toLocaleTimeString()}`);
    };

    const handleSave = async () => {
        setSaving(true);
        await triggerDirectSave(drillRef.current);
        setSaving(false);
        onDrillCreated();
        alert('Drill saved successfully!');
    };

    const handleTextChange = (field: keyof Drill, value: string) => {
        setDrill(prev => ({ ...prev, [field]: value }));
        if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = setTimeout(() => triggerDirectSave(drillRef.current), 1500);
    };

    const uploadCapturedBlob = async (blob: Blob, type: 'audio' | 'video' | 'image', filename: string) => {
        addLog(`Uploading ${type} (${blob.size} bytes)...`);
        setSaving(true);
        const formData = new FormData();
        formData.append('file', blob, filename);
        try {
            let targetId = drillRef.current.id;
            if (!targetId || targetId >= 1000000) {
                const res = await axios.post(`${API_BASE}/drills/`, { text_catalan: drillRef.current.text_catalan || `New Drill` });
                targetId = res.data.id;
                setDrill({ ...drillRef.current, id: targetId });
                drillRef.current = { ...drillRef.current, id: targetId };
            }
            const uploadRes = await axios.post(`${API_BASE}/upload-media/${targetId}/${type}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
            if (uploadRes.data.url) {
                const updatedDrill = { ...drillRef.current, [`${type}_url`]: uploadRes.data.url };
                setDrill(updatedDrill); drillRef.current = updatedDrill;
                triggerDirectSave(updatedDrill);
                addLog(`Upload success: ${type}`);
            }
        } catch (err: any) { addLog(`Upload Failed: ${err.message}`); } finally { setSaving(false); }
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) { addLog('Native capture canceled.'); return; }

        addLog(`Native capture received: ${file.name} (${file.type})`);
        const fileType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
        if (fileType === 'image') setCapturedImage(URL.createObjectURL(file));
        if (fileType === 'video') setCapturedVideo(URL.createObjectURL(file));
        if (fileType === 'audio') setCapturedAudio(URL.createObjectURL(file));
        await uploadCapturedBlob(file, fileType, file.name);
    };

    const startVoiceRecording = () => {
        addLog('Starting Catalan Dictation...');
        if (!recognitionRef.current) return addLog('Speech-to-Text not supported');
        recognitionRef.current.start();
    };

    const stopCamera = () => {
        if (previewRef.current) previewRef.current.srcObject = null;
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
            addLog('Hardware tracks stopped.');
        }
        setCameraMode(null);
        setRecording(null);
    };

    const openVideoCamera = async () => {
        addLog('Init In-App Video Camera...');
        try {
            stopCamera();
            await new Promise(r => setTimeout(r, 150));
            addLog('Requesting video stream...');
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 640, height: 480 }, audio: true });
            streamRef.current = stream;
            addLog('Video Stream acquired!');
            setCameraMode('video');
        } catch (err: any) { addLog(`In-App Video Error: ${err.message}`); }
    };

    const startRecordingVideo = () => {
        if (!streamRef.current) return;
        addLog('Starting video record...');
        const format = getSupportedMimeType('video');
        mediaRecorderRef.current = new MediaRecorder(streamRef.current, { mimeType: format.mime });
        chunksRef.current = [];
        mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
        mediaRecorderRef.current.onstop = async () => {
            const blob = new Blob(chunksRef.current, { type: format.mime });
            addLog(`Video recorded: ${blob.size} bytes`);
            if (blob.size > 0) {
                setCapturedVideo(URL.createObjectURL(blob));
                await uploadCapturedBlob(blob, 'video', `video_${drillRef.current.id || Date.now()}.${format.ext}`);
            }
            stopCamera();
        };
        mediaRecorderRef.current.start();
        setRecording('video');
    };

    const startImageCapture = async () => {
        addLog('Init In-App Photo Camera...');
        try {
            stopCamera();
            await new Promise(r => setTimeout(r, 200));
            addLog('Requesting photo stream...');
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            streamRef.current = stream;
            addLog('Photo Stream acquired!');
            setCameraMode('photo');
        } catch (err: any) {
            addLog(`In-App Photo Error: ${err.name} - ${err.message}`);
            if (err.name === 'NotAllowedError') alert('Camera permission denied.');
        }
    };

    const startAudioRecording = async () => {


        addLog('Init In-App Audio...');
        try {
            stopCamera();
            await new Promise(r => setTimeout(r, 150));
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
            streamRef.current = stream;

            const format = getSupportedMimeType('audio');
            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: format.mime });
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: format.mime });
                addLog(`Audio recorded: ${blob.size} bytes`);
                if (blob.size > 0) {
                    setCapturedAudio(URL.createObjectURL(blob));
                    await uploadCapturedBlob(blob, 'audio', `audio_${drillRef.current.id || Date.now()}.${format.ext}`);
                }
                stopCamera();
            };
            mediaRecorderRef.current.start();
            setRecording('audio');
            addLog('Audio recording STARTED');
        } catch (err: any) { addLog(`In-App Audio Error: ${err.message}`); }
    };

    const takePicture = () => {
        addLog('Taking picture...');
        if (!previewRef.current || !canvasRef.current || !streamRef.current) { addLog('Missing ref for picture'); return; }
        const video = previewRef.current; const canvas = canvasRef.current;
        if (video.readyState !== video.HAVE_ENOUGH_DATA) { addLog('Video not ready, waiting...'); setTimeout(takePicture, 200); return; }
        const size = Math.min(video.videoWidth, video.videoHeight);
        canvas.width = size; canvas.height = size;
        const context = canvas.getContext('2d');
        if (context) {
            context.fillStyle = '#ffffff'; context.fillRect(0, 0, size, size);
            context.drawImage(video, (video.videoWidth - size) / 2, (video.videoHeight - size) / 2, size, size, 0, 0, size, size);
            canvas.toBlob(async (blob) => {
                addLog(`Picture snapped: ${blob?.size || 0} bytes`);
                if (blob && blob.size > 0) {
                    setCapturedImage(URL.createObjectURL(blob));
                    await uploadCapturedBlob(blob, 'image', `image_${drillRef.current.id || Date.now()}.jpg`);
                }
                stopCamera();
            }, 'image/jpeg', 0.92);
        }
    };

    const stopRecording = () => {
        addLog('Stopping recording...');
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try { mediaRecorderRef.current.requestData(); } catch (e) { }
            mediaRecorderRef.current.stop(); setRecording(null);
        } else { stopCamera(); }
    };

    const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        const sourceText = source === 'ca' ? drillRef.current.text_catalan : drillRef.current.text_tachelhit;
        if (!sourceText) return alert('Source translation field is empty.');
        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        setAiLoadingKey(`trans-${targetField}`);

        try {
            const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
            const currentContent = drillRef.current[targetField] || '';
            const safeAppendText = currentContent.trim() ? `${currentContent} (${res.data.translated_text})` : res.data.translated_text;

            const updated = { ...drillRef.current, [targetField]: safeAppendText };
            setDrill(updated);
            triggerDirectSave(updated);
        } catch (err) { alert('Translation failed.'); }
        finally { setAiLoadingKey(null); }
    };

    const handleAutoTranscribe = async () => {
        const mediaSource = drillRef.current.audio_url || drillRef.current.video_url;
        if (!mediaSource) return alert('Please record media first.');
        setAiLoadingKey('transcribe-voice');

        try {
            const response = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const { corrected_transcription } = response.data;

            if (corrected_transcription) {
                const currentTachelhit = drillRef.current.text_tachelhit || '';
                const safeAppendText = currentTachelhit.trim() ? `${currentTachelhit} (${corrected_transcription})` : corrected_transcription;

                const updated = { ...drillRef.current, text_tachelhit: safeAppendText };
                setDrill(updated);
                triggerDirectSave(updated);
            }
        } catch (error) { alert('Failed to transcribe audio.'); }
        finally { setAiLoadingKey(null); }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none', borderRadius: '50%', width: '40px', height: '40px' }}>✕</button>
                <div style={{ color: 'white', fontSize: '18px', fontWeight: 700 }}>
                    {drill.id && drill.id < 1000000 ? `Drill #${drill.id}` : 'New Drill'}
                    {lastSaved && <div style={{ fontSize: '10px', fontWeight: 400 }}>{lastSaved}</div>}
                </div>
                <button onClick={handleSave} disabled={saving} style={{ background: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px' }}>💾 Save</button>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column' }}>
                {cameraMode && (
                    <div style={{ background: '#000', borderRadius: '16px', marginBottom: '20px', overflow: 'hidden' }}>
                        <div style={{ position: 'relative', height: '280px' }}>
                            <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        </div>
                        <div style={{ padding: '16px', background: '#111', display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                            <button onClick={stopCamera} style={{ padding: '10px 20px', background: '#444', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>✕ Cancel</button>
                            {cameraMode === 'photo' ? (
                                <button onClick={takePicture} style={{ width: '65px', height: '65px', borderRadius: '50%', background: 'white', border: '4px solid #4CAF50', fontWeight: 'bold' }}>SNAP</button>
                            ) : (
                                <button onClick={recording === 'video' ? stopRecording : startRecordingVideo} style={{ padding: '12px 24px', background: recording === 'video' ? '#ff4444' : '#9C27B0', color: 'white', border: 'none', borderRadius: '30px', fontWeight: 'bold' }}>
                                    {recording === 'video' ? '⏹️ STOP' : '🎬 START'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {!cameraMode && (
                    <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '16px', marginBottom: '20px', border: '1px solid #e0e0e0' }}>
                        <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#666', textAlign: 'center' }}>IN-APP CAMERA</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' }}>
                            <button onClick={startImageCapture} disabled={saving} style={{ height: '70px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>📷 Photo</button>
                            <button onClick={openVideoCamera} disabled={saving} style={{ height: '70px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>🎬 Video</button>
                            <button onClick={recording === 'audio' ? stopRecording : startAudioRecording} disabled={saving} style={{ height: '70px', background: recording === 'audio' ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>{recording === 'audio' ? '⏹️ Stop Mic' : '🎙️ Record Audio'}</button>
                            <button onClick={startVoiceRecording} disabled={saving} style={{ height: '70px', background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>🗣️ Speak (Català)</button>
                        </div>

                        <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#666', textAlign: 'center' }}>NATIVE ANDROID CAPTURE (Backup)</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
                            {/* 🌟 FIX: Updated HTML5 capture hints to force native apps */}
                            <input type="file" accept="image/*" capture={"camera" as any} id="native-photo-c" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                            <button onClick={() => fileInputRef.current?.click()} disabled={saving} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Photo</button>

                            <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video-c" style={{ display: 'none' }} onChange={handleFileChange} />
                            <button onClick={() => document.getElementById('native-video-c')?.click()} disabled={saving} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Video</button>

                            <input type="file" accept="audio/*" capture={"microphone" as any} id="native-audio-c" style={{ display: 'none' }} onChange={handleFileChange} />
                            <button onClick={() => document.getElementById('native-audio-c')?.click()} disabled={saving} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Audio</button>
                        </div>
                    </div>
                )}

                {(drill.image_url || capturedImage) && <img src={drill.image_url ? getMediaUrl(drill.image_url) : capturedImage || ''} alt="Preview" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover', marginBottom: '20px' }} />}
                {(drill.video_url || capturedVideo) && <video src={drill.video_url ? getMediaUrl(drill.video_url) : capturedVideo || ''} controls playsInline style={{ width: '100%', borderRadius: '12px', background: '#000', marginBottom: '20px' }} />}
                {(drill.audio_url || capturedAudio) && <button onClick={() => new Audio(drill.audio_url ? getMediaUrl(drill.audio_url) : capturedAudio || '').play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: '1px solid #e0e0e0', borderRadius: '10px', fontWeight: 600, cursor: 'pointer', marginBottom: '20px' }}>🔊 Play Audio Asset</button>}

                <div style={{ display: 'grid', gridTemplateColumns: (drill.audio_url || drill.video_url) ? '1fr 1fr 1fr' : '1fr 1fr', gap: '8px', background: '#f8f9fa', padding: '10px', borderRadius: '12px', marginBottom: '14px', border: '1px solid #e0e0e0' }}>
                    <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>🤖 CA➔SHI</button>
                    <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>🤖 SHI➔CA</button>
                    {(drill.audio_url || drill.video_url) && (
                        <button onClick={handleAutoTranscribe} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>🪄 Transcribe</button>
                    )}
                </div>

                <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Català</label><textarea value={drill.text_catalan || ''} onChange={(e) => handleTextChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>
                <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea value={drill.text_tachelhit || ''} onChange={(e) => handleTextChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>

                {/* 🐛 LIVE DEBUG CONSOLE UI */}
                <div style={{ background: '#111', color: '#0f0', padding: '10px', borderRadius: '8px', fontSize: '10px', fontFamily: 'monospace', height: '120px', overflowY: 'auto', marginTop: '10px' }}>
                    <div style={{ color: '#fff', borderBottom: '1px solid #333', paddingBottom: '4px', marginBottom: '4px' }}>LIVE DEBUGGER</div>
                    {debugLogs.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </div>
        </div>
    );
}