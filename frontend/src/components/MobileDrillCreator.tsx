import { Filesystem, Directory } from '@capacitor/filesystem';
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
    const [drill, setDrill] = useState<Drill>({
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        tag: '',
        author: ''
    });

    const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
    const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
    const [, setCameraFacing] = useState<'user' | 'environment'>('environment');
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [pastedImage, setPastedImage] = useState<string | null>(null);
    const [transcriptionResult, setTranscriptionResult] = useState<{ rough: string, score: number } | null>(null);

    const [saving, setSaving] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [autoSaveTimer, setAutoSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
    const [lastSaved, setLastSaved] = useState<string | null>(null);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        return () => {
            if (capturedImage && capturedImage.startsWith('blob:')) URL.revokeObjectURL(capturedImage);
            if (capturedVideo && capturedVideo.startsWith('blob:')) URL.revokeObjectURL(capturedVideo);
            if (pastedImage && pastedImage.startsWith('blob:')) URL.revokeObjectURL(pastedImage);
            if (autoSaveTimer) clearTimeout(autoSaveTimer);
        };
    }, [capturedImage, capturedVideo, pastedImage, autoSaveTimer]);

    // Initialize speech recognition with immediate, safe non-closure background saving
    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'ca-ES';
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;

            recognitionRef.current.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                setDrill(prev => {
                    const fresh = { ...prev, text_catalan: transcript };
                    triggerDirectSave(fresh); // Bypasses closure bug completely
                    return fresh;
                });
            };
        }
    }, []);

    const triggerDirectSave = async (freshDrill: Drill) => {
        const status = await Network.getStatus();
        const cleanPayload = { ...freshDrill };
        if (cleanPayload.audio_url?.startsWith('file://')) cleanPayload.audio_url = '';
        if (cleanPayload.video_url?.startsWith('file://')) cleanPayload.video_url = '';
        if (cleanPayload.image_url?.startsWith('file://')) cleanPayload.image_url = '';

        if (status.connected) {
            try {
                if (freshDrill.id && freshDrill.id < 1000000) {
                    await axios.put(`${API_BASE}/drills/${freshDrill.id}`, cleanPayload);
                } else {
                    const res = await axios.post(`${API_BASE}/drills/`, cleanPayload);
                    setDrill(res.data);
                }
                setLastSaved(`Online: ${new Date().toLocaleTimeString()}`);
            } catch (err) {
                saveOffline(freshDrill);
            }
        } else {
            saveOffline(freshDrill);
        }
    };

    const triggerAutoSave = () => {
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
        const timer = setTimeout(() => {
            triggerDirectSave(drill);
        }, 2000);
        setAutoSaveTimer(timer);
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

        const cached = JSON.parse(localStorage.getItem('cached_drills') || '[]');
        const filteredCached = cached.filter((d: any) => d.id !== currentDrill.id);
        filteredCached.unshift(currentDrill);
        localStorage.setItem('cached_drills', JSON.stringify(filteredCached));
        setLastSaved(`Offline Cache: ${new Date().toLocaleTimeString()}`);
    };

    const handleTextChange = (field: keyof Drill, value: string) => {
        setDrill(prev => ({ ...prev, [field]: value }));
        triggerAutoSave();
    };

    const startVoiceRecording = () => {
        if (!recognitionRef.current) return alert('Speech-to-Text not initialized.');
        recognitionRef.current.start();
    };

    const startAudioRecording = async () => {
        if (!drill.id) {
            const temp = { ...drill, id: Date.now(), text_catalan: drill.text_catalan || `Audio Drill (${new Date().toLocaleDateString()})` };
            setDrill(temp);
            saveOffline(temp);
        }
        try {
            if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
            streamRef.current = stream;

            let mimeType = 'audio/webm';
            if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream) mimeType = 'audio/mp4';

            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
            chunksRef.current = [];
            mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: mimeType });
                if (blob.size < 1024) return;

                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = async () => {
                    try {
                        const base64Data = (reader.result as string).split(',')[1];
                        const ext = mimeType.includes('mp4') ? 'm4a' : 'webm';
                        const fileName = `drills_media/audio_${drill.id || Date.now()}.${ext}`;

                        const savedFile = await Filesystem.writeFile({ path: fileName, data: base64Data, directory: Directory.Data, recursive: true });
                        setDrill(prev => {
                            const updated = { ...prev, audio_url: savedFile.uri };
                            triggerDirectSave(updated);
                            return updated;
                        });
                    } catch (err) { console.error(err); }
                    finally { setRecording(null); }
                };
            };
            mediaRecorderRef.current.start();
            setRecording('audio');
        } catch (err) { console.error(err); }
    };

    const startVideoRecording = async (facing: 'user' | 'environment' = 'environment') => {
        if (!drill.id) {
            const temp = { ...drill, id: Date.now(), text_catalan: drill.text_catalan || `Video Drill (${new Date().toLocaleDateString()})` };
            setDrill(temp);
            saveOffline(temp);
        }
        try {
            if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing, width: 640, height: 480 }, audio: true });
            streamRef.current = stream;
            setCameraMode('video');
            setCameraFacing(facing);

            setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];
            mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                if (blob.size < 1024) { stopCamera(); return; }

                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = async () => {
                    try {
                        const base64Data = (reader.result as string).split(',')[1];
                        const savedFile = await Filesystem.writeFile({ path: `drills_media/video_${drill.id || Date.now()}.webm`, data: base64Data, directory: Directory.Data, recursive: true });
                        setCapturedVideo(URL.createObjectURL(blob)); // Instant video preview load
                        setDrill(prev => {
                            const updated = { ...prev, video_url: savedFile.uri };
                            triggerDirectSave(updated);
                            return updated;
                        });
                    } catch (err) { console.error(err); }
                    finally { stopCamera(); setRecording(null); }
                };
            };
        } catch (err) { console.error(err); }
    };

    const startImageCapture = async (facing: 'user' | 'environment' = 'environment') => {
        if (!drill.id) {
            const temp = { ...drill, id: Date.now(), text_catalan: drill.text_catalan || `Image Drill (${new Date().toLocaleDateString()})` };
            setDrill(temp);
            saveOffline(temp);
        }
        try {
            if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing, width: 1280, height: 720 } });
            streamRef.current = stream;
            setCameraMode('photo');
            setCameraFacing(facing);
            setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);
        } catch (err) { console.error(err); }
    };

    const takePicture = () => {
        if (!previewRef.current || !canvasRef.current || !streamRef.current) return;
        const video = previewRef.current;
        const canvas = canvasRef.current;

        if (video.readyState !== video.HAVE_ENOUGH_DATA) {
            setTimeout(takePicture, 500);
            return;
        }

        const width = video.videoWidth || 640;
        const height = video.videoHeight || 480;
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
                if (blob && blob.size > 1024) {
                    setCapturedImage(URL.createObjectURL(blob)); // Instant photo preview load
                    const reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = async () => {
                        try {
                            const base64Data = (reader.result as string).split(',')[1];
                            const savedFile = await Filesystem.writeFile({ path: `drills_media/image_${drill.id || Date.now()}.jpg`, data: base64Data, directory: Directory.Data, recursive: true });
                            setDrill(prev => {
                                const updated = { ...prev, image_url: savedFile.uri };
                                triggerDirectSave(updated);
                                return updated;
                            });
                        } catch (err) { console.error(err); }
                    };
                }
                stopCamera();
            }, 'image/jpeg', 0.9);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            setRecording(null);
        } else {
            stopCamera();
            setRecording(null);
        }
    };

    const stopCamera = () => {
        if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
        setCameraMode(null);
        setRecording(null);
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setCapturedImage(null); setCapturedVideo(null); setPastedImage(null); setUploadedFile(file);
            if (file.type.startsWith('image/')) setCapturedImage(URL.createObjectURL(file));
            else if (file.type.startsWith('video/')) setCapturedVideo(URL.createObjectURL(file));
        }
    };

    const handleSave = async () => {
        if (saving) return;
        setSaving(true);
        try {
            const status = await Network.getStatus();
            const sanitizePayload = (d: any) => {
                const clean = { ...d };
                if (clean.audio_url?.startsWith('file://')) clean.audio_url = '';
                if (clean.video_url?.startsWith('file://')) clean.video_url = '';
                if (clean.image_url?.startsWith('file://')) clean.image_url = '';
                return clean;
            };

            const outPayload = sanitizePayload(drill);

            if (status.connected) {
                if (!drill.id || (typeof drill.id === 'number' && drill.id >= 1000000)) {
                    const response = await axios.post(`${API_BASE}/drills/`, outPayload);
                    setDrill(response.data);
                } else {
                    await axios.put(`${API_BASE}/drills/${drill.id}`, outPayload);
                }

                if (uploadedFile) {
                    const fileType = uploadedFile.type.startsWith('image/') ? 'image' : uploadedFile.type.startsWith('video/') ? 'video' : null;
                    if (fileType && drill.id) {
                        const formData = new FormData();
                        formData.append('file', uploadedFile, uploadedFile.name);
                        await axios.post(`${API_BASE}/upload-media/${drill.id}/${fileType}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                    }
                }
                alert('Drill successfully synchronized to cloud database!');
            } else {
                saveOffline(drill);
                alert('Drill securely saved to phone storage cache!');
            }
            onDrillCreated();
        } catch (error) {
            alert('Failed to execute save command.');
        } finally {
            setSaving(false);
        }
    };

    const handleAutoTranscribe = async () => {
        if (!drill.audio_url) return alert('Please record audio first');
        setIsTranscribing(true); setTranscriptionResult(null);
        try {
            const response = await axios.post(`${API_BASE}/transcribe/`, { audio_url: drill.audio_url });
            const { corrected_transcription, rough_transcription, similarity_score } = response.data;
            setTranscriptionResult({ rough: rough_transcription, score: similarity_score });
            if (corrected_transcription) {
                setDrill(prev => {
                    const updated = { ...prev, text_tachelhit: corrected_transcription };
                    triggerDirectSave(updated);
                    return updated;
                });
            }
        } catch (error) {
            alert('Failed to transcribe audio.');
        } finally {
            setIsTranscribing(false);
        }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 10000, display: 'flex', flexDirection: 'column' }}>
            {/* Header Toolbar */}
            <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: 'white', fontSize: '24px', width: '40px', height: '40px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
                    <button onClick={handleCreateNew} style={{ background: '#FF9800', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 12px', fontSize: '14px', fontWeight: 700, cursor: 'pointer' }}>➕ New</button>
                </div>
                <div style={{ color: 'white', fontSize: '18px', fontWeight: 700, flex: 1, textAlign: 'center' }}>
                    {drill.id && drill.id < 1000000 ? `Drill #${drill.id}` : 'New Drill'}
                    {lastSaved && <div style={{ fontSize: '12px', color: '#FFD700' }}>{lastSaved}</div>}
                </div>
                <button onClick={handleSave} disabled={saving} style={{ background: saving ? '#999' : '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px', fontSize: '16px', fontWeight: 700 }}>💾 Save</button>
            </div>

            {/* Scrollable Container Form Workspace */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column' }}>
                
                {/* 🌟 1. CAMERA PREVIEW LAYER: Forced non-selfie standard preview order at the absolute top */}
                {cameraMode && (
                    <div style={{ background: '#000', borderRadius: '16px', marginBottom: '20px', overflow: 'hidden' }}>
                        <div style={{ position: 'relative', height: '280px' }}>
                            <video 
                                ref={previewRef} 
                                autoPlay 
                                muted 
                                playsInline 
                                style={{ 
                                    width: '100%', 
                                    height: '100%', 
                                    objectFit: 'cover' // ❌ Removed mirrored scale transforms completely to avoid selfie layout distortions
                                }} 
                            />
                            <button onClick={stopCamera} style={{ position: 'absolute', top: '12px', right: '12px', width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,0,0,0.8)', color: 'white', border: 'none', fontSize: '18px', cursor: 'pointer' }}>✕</button>
                        </div>
                        <div style={{ padding: '16px', background: '#111', display: 'flex', justifyContent: 'center' }}>
                            {cameraMode === 'photo' ? (
                                <button onClick={takePicture} style={{ width: '75px', height: '75px', borderRadius: '50%', background: 'white', border: '5px solid #4CAF50', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}>CAPTURE</button>
                            ) : (
                                <button onClick={recording === 'video' ? stopRecording : () => { mediaRecorderRef.current?.start(); setRecording('video'); }} style={{ padding: '12px 30px', background: recording === 'video' ? '#ff4444' : '#9C27B0', color: 'white', border: 'none', borderRadius: '30px', fontWeight: 'bold', fontSize: '16px' }}>
                                    {recording === 'video' ? '⏹️ STOP RECORD' : '🎬 START RECORD'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* 🌟 2. INSTANT MEDIA PREVIEWS: Renders immediately under active lens blocks */}
                {(drill.image_url || capturedImage || pastedImage) && (
                    <div style={{ marginBottom: '20px', background: '#f8f9fa', padding: '16px', borderRadius: '16px', border: '1px solid #e0e0e0' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 700 }}>🖼️ Square Photo Capture</h4>
                        <img src={drill.image_url ? getMediaUrl(drill.image_url) : capturedImage || pastedImage || ''} alt="Preview" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover' }} />
                    </div>
                )}

                {drill.video_url || capturedVideo ? (
                    <div style={{ marginBottom: '20px', background: '#f8f9fa', padding: '16px', borderRadius: '16px', border: '1px solid #e0e0e0' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 700 }}>🎬 Video Preview Asset</h4>
                        <video src={drill.video_url ? getMediaUrl(drill.video_url) : capturedVideo || ''} controls playsInline style={{ width: '100%', borderRadius: '12px', maxWidth: '220px', background: '#000' }} />
                    </div>
                ) : null}

                {/* Quick Action Trigger Pad */}
                <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '16px', marginBottom: '20px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                        <button onClick={() => startImageCapture('environment')} style={{ height: '90px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>📷 Take Photo</button>
                        <button onClick={recording === 'audio' ? stopRecording : startAudioRecording} style={{ height: '90px', background: recording === 'audio' ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>{recording === 'audio' ? '⏹️ Stop Mic' : '🎙️ Record Audio'}</button>
                        <button onClick={() => startVideoRecording('environment')} style={{ height: '90px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>🎬 Record Video</button>
                        <button onClick={startVoiceRecording} style={{ height: '90px', background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold' }}>🗣️ Speak (Català)</button>
                    </div>
                    <input type="file" accept="image/*,video/*" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                    <button onClick={() => fileInputRef.current?.click()} style={{ width: '100%', padding: '12px', background: '#607D8B', color: 'white', border: 'none', borderRadius: '8px', marginTop: '12px', fontWeight: 'bold' }}>📤 Gallery Attachment</button>
                </div>

                {/* Main Text Content Input Panel cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Català</label>
                        <textarea value={drill.text_catalan || ''} onChange={(e) => handleTextChange('text_catalan', e.target.value)} placeholder="Catalan notes..." rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '2px solid #ddd', borderRadius: '8px' }} />
                    </div>
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <label style={{ fontSize: '13px', fontWeight: 600 }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label>
                            {drill.audio_url && <button onClick={handleAutoTranscribe} disabled={isTranscribing} style={{ background: '#667eea', color: 'white', padding: '4px 10px', borderRadius: '4px', border: 'none', fontSize: '11px' }}>{isTranscribing ? '⏳...' : '🪄 Auto-Transcribe'}</button>}
                        </div>
                        <textarea value={drill.text_tachelhit || ''} onChange={(e) => handleTextChange('text_tachelhit', e.target.value)} placeholder="Tachelhit notation..." rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '2px solid #ddd', borderRadius: '8px', fontFamily: 'monospace', fontWeight: 'bold' }} />
                        {transcriptionResult && <div style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>Rough: {transcriptionResult.rough} ({Math.round(transcriptionResult.score * 100)}%)</div>}
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

    function handleCreateNew() {
        setDrill({ text_catalan: '', text_tachelhit: '', text_arabic: '', tag: '', author: '' });
        setCapturedImage(null); setCapturedVideo(null); setUploadedFile(null); setPastedImage(null); setTranscriptionResult(null); setLastSaved(null);
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
    }
}