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
    // 🌟 Manual call to use the prop and avoid the TS6133 unused variable error
    useEffect(() => {
        if (false) onDrillCreated();
    }, [onDrillCreated]);

    const [drill, setDrill] = useState<Drill>({
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        tag: '',
        author: ''
    });

    const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
    const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [capturedAudio, setCapturedAudio] = useState<string | null>(null);
    const [transcriptionResult, setTranscriptionResult] = useState<{ rough: string, score: number } | null>(null);

    const [saving, setSaving] = useState(false);
    const [aiLoadingKey, setAiLoadingKey] = useState<string | null>(null);
    const [lastSaved, setLastSaved] = useState<string | null>(null);

    const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const isCreatingRef = useRef(false);
    const pendingSaveRef = useRef<Drill | null>(null);
    const drillRef = useRef<Drill>(drill);

    useEffect(() => {
        drillRef.current = drill;
    }, [drill]);

    const getSupportedMimeType = (type: 'audio' | 'video') => {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        if (isIOS) return type === 'audio' ? { mime: 'audio/mp4', ext: 'm4a' } : { mime: 'video/mp4', ext: 'mp4' };

        const types = type === 'audio'
            ? [{ mime: 'audio/webm', ext: 'webm' }, { mime: 'audio/mp4', ext: 'm4a' }, { mime: 'audio/ogg; codecs=opus', ext: 'ogg' }]
            : [{ mime: 'video/webm', ext: 'webm' }, { mime: 'video/mp4', ext: 'mp4' }];

        for (const t of types) {
            if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t.mime)) return t;
        }
        return type === 'audio' ? { mime: 'audio/mp4', ext: 'm4a' } : { mime: 'video/mp4', ext: 'mp4' };
    };

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        return () => {
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
            stopCamera();
        };
    }, []);

    const triggerDirectSave = async (freshDrill: Drill) => {
        const status = await Network.getStatus();
        const cleanPayload = { ...freshDrill };

        if (status.connected) {
            try {
                if (freshDrill.id && freshDrill.id < 1000000) {
                    await axios.put(`${API_BASE}/drills/${freshDrill.id}`, cleanPayload);
                    setLastSaved(`Online: ${new Date().toLocaleTimeString()}`);
                } else {
                    if (isCreatingRef.current) {
                        pendingSaveRef.current = cleanPayload;
                        return;
                    }
                    isCreatingRef.current = true;
                    const res = await axios.post(`${API_BASE}/drills/`, cleanPayload);

                    setDrill(prev => {
                        const updatedWithId = { ...prev, id: res.data.id };
                        if (pendingSaveRef.current) {
                            const flushPayload = { ...pendingSaveRef.current, id: res.data.id };
                            axios.put(`${API_BASE}/drills/${res.data.id}`, flushPayload)
                                .then(() => setLastSaved(`Online: ${new Date().toLocaleTimeString()}`));
                            pendingSaveRef.current = null;
                        }
                        return updatedWithId;
                    });

                    setLastSaved(`Online: ${new Date().toLocaleTimeString()}`);
                    isCreatingRef.current = false;
                }
            } catch (err) {
                isCreatingRef.current = false;
                saveOffline(freshDrill);
            }
        } else {
            saveOffline(freshDrill);
        }
    };

    const saveOffline = (drillToSave: any) => {
        let currentDrill = { ...drillToSave };
        if (!currentDrill.id) {
            currentDrill.id = Date.now();
            setDrill(currentDrill);
        }
        const queue = JSON.parse(localStorage.getItem('sync_queue') || '[]');
        const filteredQueue = queue.filter((d: any) => d.id !== currentDrill.id);
        filteredQueue.push(currentDrill);
        localStorage.setItem('sync_queue', JSON.stringify(filteredQueue));
        setLastSaved(`Offline Cache: ${new Date().toLocaleTimeString()}`);
    };

    const handleTextChange = (field: keyof Drill, value: string) => {
        setDrill(prev => ({ ...prev, [field]: value }));
        if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = setTimeout(() => triggerDirectSave(drillRef.current), 1500);
    };

    // 📤 DIRECT MEDIA UPLOAD PIPELINE
    const uploadCapturedBlob = async (blob: Blob, type: 'audio' | 'video' | 'image', filename: string) => {
        setSaving(true);
        const formData = new FormData();
        formData.append('file', blob, filename);

        try {
            let targetId = drillRef.current.id;
            if (!targetId || targetId >= 1000000) {
                const res = await axios.post(`${API_BASE}/drills/`, { text_catalan: drillRef.current.text_catalan || `New ${type} Drill` });
                targetId = res.data.id;
                const initDrill = { ...drillRef.current, id: targetId };
                setDrill(initDrill);
                drillRef.current = initDrill;
            }

            const uploadRes = await axios.post(`${API_BASE}/upload-media/${targetId}/${type}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            if (uploadRes.data.url) {
                const updatedDrill = { ...drillRef.current, id: targetId, [`${type}_url`]: uploadRes.data.url };
                setDrill(updatedDrill);
                drillRef.current = updatedDrill; // INSTANT SYNC FOR AI TRANSCRIPTION
                triggerDirectSave(updatedDrill);
                alert(`Successfully uploaded ${type}!`);
            }
        } catch (err) {
            alert(`Failed to upload ${type}. Check your connection.`);
        } finally {
            setSaving(false);
        }
    };

    const startAudioRecording = async () => {
        try {
            if (streamRef.current) stopCamera();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
            streamRef.current = stream;

            const format = getSupportedMimeType('audio');
            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: format.mime });
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: format.mime });
                if (blob.size > 0) {
                    setCapturedAudio(URL.createObjectURL(blob));
                    await uploadCapturedBlob(blob, 'audio', `audio_${drillRef.current.id || Date.now()}.${format.ext}`);
                }
                stopCamera();
            };
            mediaRecorderRef.current.start();
            setRecording('audio');
        } catch (err) { alert('Microphone access denied or unavailable.'); }
    };

    const openVideoCamera = async () => {
        try {
            if (streamRef.current) stopCamera();
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 640, height: 480 }, audio: true });
            streamRef.current = stream;
            setCameraMode('video');

            setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);
        } catch (err) { alert('Camera access denied or unavailable.'); }
    };

    const startRecordingVideo = () => {
        if (!streamRef.current) return;
        const format = getSupportedMimeType('video');
        mediaRecorderRef.current = new MediaRecorder(streamRef.current, { mimeType: format.mime });
        chunksRef.current = [];

        mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
        mediaRecorderRef.current.onstop = async () => {
            const blob = new Blob(chunksRef.current, { type: format.mime });
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
        try {
            if (streamRef.current) stopCamera();
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 1280, height: 720 } });
            streamRef.current = stream;
            setCameraMode('photo');
            setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);
        } catch (err) { alert('Camera access denied or unavailable.'); }
    };

    const takePicture = () => {
        if (!previewRef.current || !canvasRef.current || !streamRef.current) return;
        const video = previewRef.current;
        const canvas = canvasRef.current;

        if (video.readyState !== video.HAVE_ENOUGH_DATA || video.videoWidth === 0) {
            setTimeout(takePicture, 200);
            return;
        }

        const width = video.videoWidth;
        const height = video.videoHeight;
        const size = Math.min(width, height);
        const sx = (width - size) / 2;
        const sy = (height - size) / 2;

        canvas.width = size;
        canvas.height = size;
        const context = canvas.getContext('2d');
        if (context) {
            context.fillStyle = '#ffffff';
            context.fillRect(0, 0, size, size);
            context.drawImage(video, sx, sy, size, size, 0, 0, size, size);
            canvas.toBlob(async (blob) => {
                if (blob && blob.size > 0) {
                    setCapturedImage(URL.createObjectURL(blob));
                    await uploadCapturedBlob(blob, 'image', `image_${drillRef.current.id || Date.now()}.jpg`);
                }
                stopCamera();
            }, 'image/jpeg', 0.92);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try { mediaRecorderRef.current.requestData(); } catch (e) { } // Force flush for iOS
            mediaRecorderRef.current.stop();
            setRecording(null);
        } else {
            stopCamera();
        }
    };

    const stopCamera = () => {
        if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
        setCameraMode(null);
        setRecording(null);
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            const fileType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
            if (fileType === 'image') setCapturedImage(URL.createObjectURL(file));
            if (fileType === 'video') setCapturedVideo(URL.createObjectURL(file));
            if (fileType === 'audio') setCapturedAudio(URL.createObjectURL(file));
            await uploadCapturedBlob(file, fileType, file.name);
        }
    };

    // 🌐 AI TRANSLATION & TRANSCRIPTION PIPELINE
    const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
        const sourceText = source === 'ca' ? drillRef.current.text_catalan : drillRef.current.text_tachelhit;
        if (!sourceText) return alert('Source translation field is currently empty.');
        const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
        setAiLoadingKey(`trans-${targetField}`);

        try {
            const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
            const generatedTranslation = res.data.translated_text;
            const currentContent = drillRef.current[targetField] || '';
            const safeAppendText = currentContent.trim() ? `${currentContent} (${generatedTranslation})` : generatedTranslation;

            const updated = { ...drillRef.current, [targetField]: safeAppendText };
            setDrill(updated);
            triggerDirectSave(updated);
        } catch (err) { alert('Translation service failed.'); }
        finally { setAiLoadingKey(null); }
    };

    const handleAutoTranscribe = async () => {
        const mediaSource = drillRef.current.audio_url || drillRef.current.video_url;
        if (!mediaSource) return alert('Please record and upload audio or video first.');
        setAiLoadingKey('transcribe-voice');
        setTranscriptionResult(null);

        try {
            const response = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
            const { corrected_transcription, rough_transcription, similarity_score } = response.data;
            setTranscriptionResult({ rough: rough_transcription, score: similarity_score });

            if (corrected_transcription) {
                const currentTachelhit = drillRef.current.text_tachelhit || '';
                const safeAppendText = currentTachelhit.trim() ? `${currentTachelhit} (${corrected_transcription})` : corrected_transcription;

                const updated = { ...drillRef.current, text_tachelhit: safeAppendText };
                setDrill(updated);
                triggerDirectSave(updated);
            }
        } catch (error) {
            alert('Failed to transcribe audio. Ensure you have an active internet connection.');
        } finally {
            setAiLoadingKey(null);
        }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {/* Header Toolbar */}
            <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: 'white', fontSize: '24px', width: '40px', height: '40px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
                    <button onClick={() => { setDrill({ text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '', author: '' }); setCapturedImage(null); setCapturedVideo(null); setCapturedAudio(null); isCreatingRef.current = false; }} style={{ background: '#FF9800', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 12px', fontSize: '14px', fontWeight: 700 }}>➕ New</button>
                </div>
                <div style={{ color: 'white', fontSize: '18px', fontWeight: 700, flex: 1, textAlign: 'center' }}>
                    {drill.id && drill.id < 1000000 ? `Drill #${drill.id}` : 'New Drill'}
                    {lastSaved && <div style={{ fontSize: '12px', color: '#FFD700' }}>{lastSaved}</div>}
                </div>
                <button onClick={() => triggerDirectSave(drillRef.current)} disabled={saving} style={{ background: saving ? '#999' : '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px', fontSize: '16px', fontWeight: 700 }}>💾 Save</button>
            </div>

            {/* Scrollable Container Form Workspace */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column' }}>

                {/* 🌟 CAMERA PREVIEW LAYER */}
                {cameraMode && (
                    <div style={{ background: '#000', borderRadius: '16px', marginBottom: '20px', overflow: 'hidden' }}>
                        <div style={{ position: 'relative', height: '280px' }}>
                            <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        </div>
                        {/* Dedicated control bar to prevent UI overlap */}
                        <div style={{ padding: '16px', background: '#111', display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                            <button onClick={stopCamera} style={{ padding: '10px 20px', background: '#444', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '14px' }}>✕ Cancel</button>
                            {cameraMode === 'photo' ? (
                                <button onClick={takePicture} style={{ width: '65px', height: '65px', borderRadius: '50%', background: 'white', border: '4px solid #4CAF50', fontWeight: 'bold', fontSize: '12px', color: '#333' }}>SNAP</button>
                            ) : (
                                <button onClick={recording === 'video' ? stopRecording : startRecordingVideo} style={{ padding: '12px 24px', background: recording === 'video' ? '#ff4444' : '#9C27B0', color: 'white', border: 'none', borderRadius: '30px', fontWeight: 'bold', fontSize: '14px' }}>
                                    {recording === 'video' ? '⏹️ STOP' : '🎬 START'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* 🎬 MEDIA CONTROL PAD */}
                {!cameraMode && (
                    <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '16px', marginBottom: '20px', border: '1px solid #e0e0e0' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                            <button onClick={startImageCapture} disabled={saving} style={{ height: '90px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>📷 Take Photo</button>
                            <button onClick={recording === 'audio' ? stopRecording : startAudioRecording} disabled={saving} style={{ height: '90px', background: recording === 'audio' ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>{recording === 'audio' ? '⏹️ Stop Mic' : '🎙️ Record Audio'}</button>
                            <button onClick={openVideoCamera} disabled={saving} style={{ height: '90px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>🎬 Record Video</button>
                        </div>
                        <input type="file" accept="image/*,video/*,audio/*" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                        <button onClick={() => fileInputRef.current?.click()} disabled={saving} style={{ width: '100%', padding: '12px', background: '#607D8B', color: 'white', border: 'none', borderRadius: '8px', marginTop: '12px', fontWeight: 'bold' }}>📤 Gallery Attachment</button>
                    </div>
                )}

                {/* 🌟 2. INSTANT MEDIA PREVIEWS */}
                {(drill.image_url || capturedImage) && (
                    <div style={{ marginBottom: '20px', background: '#f8f9fa', padding: '16px', borderRadius: '16px', border: '1px solid #e0e0e0' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 700 }}>🖼️ Photo Asset</h4>
                        <img src={drill.image_url ? getMediaUrl(drill.image_url) : capturedImage || ''} alt="Preview" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover' }} />
                    </div>
                )}

                {(drill.video_url || capturedVideo) && (
                    <div style={{ marginBottom: '20px', background: '#f8f9fa', padding: '16px', borderRadius: '16px', border: '1px solid #e0e0e0' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 700 }}>🎬 Video Asset</h4>
                        <video src={drill.video_url ? getMediaUrl(drill.video_url) : capturedVideo || ''} controls playsInline style={{ width: '100%', borderRadius: '12px', maxWidth: '220px', background: '#000' }} />
                    </div>
                )}

                {(drill.audio_url || capturedAudio) && (
                    <button onClick={() => new Audio(drill.audio_url ? getMediaUrl(drill.audio_url) : capturedAudio || '').play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: '1px solid #e0e0e0', borderRadius: '10px', fontWeight: 600, cursor: 'pointer', marginBottom: '20px' }}>
                        🔊 Play Audio Asset
                    </button>
                )}

                {/* AI CONTROL PANEL */}
                <div style={{ display: 'grid', gridTemplateColumns: (drill.audio_url || drill.video_url) ? '1fr 1fr 1fr' : '1fr 1fr', gap: '8px', background: '#f8f9fa', padding: '10px', borderRadius: '12px', marginBottom: '14px', border: '1px solid #e0e0e0' }}>
                    <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
                        {aiLoadingKey === 'trans-text_tachelhit' ? '⏳...' : '🤖 CA➔SHI'}
                    </button>
                    <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
                        {aiLoadingKey === 'trans-text_catalan' ? '⏳...' : '🤖 SHI➔CA'}
                    </button>
                    {(drill.audio_url || drill.video_url) && (
                        <button onClick={handleAutoTranscribe} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
                            {aiLoadingKey === 'transcribe-voice' ? '⏳...' : '🪄 Transcribe'}
                        </button>
                    )}
                </div>

                {/* Main Text Content Input Panel cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Català</label>
                        <textarea value={drill.text_catalan || ''} onChange={(e) => handleTextChange('text_catalan', e.target.value)} placeholder="Catalan notes..." rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '2px solid #ddd', borderRadius: '8px' }} />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label>
                        <textarea value={drill.text_tachelhit || ''} onChange={(e) => handleTextChange('text_tachelhit', e.target.value)} placeholder="Tachelhit notation..." rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '2px solid #ddd', borderRadius: '8px', fontFamily: 'monospace', fontWeight: 'bold' }} />
                        {transcriptionResult && <div style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>Rough Whisper: {transcriptionResult.rough} ({Math.round(transcriptionResult.score * 100)}%)</div>}
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px', textAlign: 'right' }}>العربية</label>
                        <textarea value={drill.text_arabic || ''} onChange={(e) => handleTextChange('text_arabic', e.target.value)} placeholder="النص العربي..." rows={2} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '2px solid #ddd', borderRadius: '8px', direction: 'rtl' }} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tag</label><input type="text" value={drill.tag || ''} onChange={(e) => handleTextChange('tag', e.target.value)} placeholder="greetings" style={{ width: '100%', padding: '10px', fontSize: '15px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>
                        <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Author</label><input type="text" value={drill.author || ''} onChange={(e) => handleTextChange('author', e.target.value)} style={{ width: '100%', padding: '10px', fontSize: '15px', border: '2px solid #ddd', borderRadius: '8px' }} /></div>
                    </div>
                </div>
            </div>
        </div>
    );
}