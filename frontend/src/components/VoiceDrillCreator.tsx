import { useState, useRef, useEffect } from 'react';
import { FaMicrophone, FaCamera, FaVideo, FaFolderOpen, FaSave } from 'react-icons/fa';
import axios from 'axios';
import { API_BASE } from '../config';

interface VoiceDrillCreatorProps {
    onClose: () => void;
    onDrillCreated: () => void;
}

export default function VoiceDrillCreator({ onClose, onDrillCreated }: VoiceDrillCreatorProps) {
    const [textCatalan, setTextCatalan] = useState('');
    const [textTachelhit, setTextTachelhit] = useState('');
    const [textArabic] = useState('');
    const [tag, setTag] = useState('');
    const [author] = useState('');
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [pastedImage, setPastedImage] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [trimTimes, setTrimTimes] = useState({ start: 0, end: 10 });

    const fileInputRef = useRef<HTMLInputElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        return () => {
            if (capturedImage && capturedImage.startsWith('blob:')) URL.revokeObjectURL(capturedImage);
            if (capturedVideo && capturedVideo.startsWith('blob:')) URL.revokeObjectURL(capturedVideo);
            if (pastedImage && pastedImage.startsWith('blob:')) URL.revokeObjectURL(pastedImage);
        };
    }, [capturedImage, capturedVideo, pastedImage]);

    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'ca-ES';
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;
            recognitionRef.current.onresult = (event: any) => {
                setTextCatalan(event.results[0][0].transcript);
                setTranscribing(false);
            };
            recognitionRef.current.onerror = () => setTranscribing(false);
            recognitionRef.current.onend = () => setTranscribing(false);
        }
    }, []);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setCapturedImage(null); setCapturedVideo(null); setPastedImage(null);
            setUploadedFile(file);
            if (file.type.startsWith('image/')) setCapturedImage(URL.createObjectURL(file));
            else if (file.type.startsWith('video/')) setCapturedVideo(URL.createObjectURL(file));
        }
    };

    const startVoiceRecording = () => {
        if (!recognitionRef.current) return alert('El reconeixement de veu no és compatible.');
        setTranscribing(true);
        recognitionRef.current.start();
    };

    const stopVoiceRecording = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
            setTranscribing(false);
        }
    };

    const startCamera = async (mode: 'photo' | 'video') => {
        setCameraMode(mode);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: 640, height: 480 },
                audio: mode === 'video',
            });
            streamRef.current = stream;
            if (previewRef.current) previewRef.current.srcObject = stream;
        } catch (err) {
            setCameraMode(null);
        }
    };

    const capturePhoto = () => {
        if (!previewRef.current || !streamRef.current) return;
        const canvas = document.createElement('canvas');
        canvas.width = previewRef.current.videoWidth;
        canvas.height = previewRef.current.videoHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.drawImage(previewRef.current, 0, 0);
            setCapturedImage(canvas.toDataURL('image/jpeg'));
        }
        stopCamera();
    };

    const startVideoRecording = () => {
        if (!streamRef.current) return;
        mediaRecorderRef.current = new MediaRecorder(streamRef.current);
        chunksRef.current = [];
        mediaRecorderRef.current.ondataavailable = (e) => chunksRef.current.push(e.data);
        mediaRecorderRef.current.onstop = async () => {
            const blob = new Blob(chunksRef.current, { type: 'video/webm' });
            const videoUrl = URL.createObjectURL(blob);
            setCapturedVideo(videoUrl);
            stopCamera();
        };
        mediaRecorderRef.current.start();
        setRecording(true);
    };

    const stopVideoRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            setRecording(false);
        }
    };

    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        setCameraMode(null);
    };

    const handleSave = async () => {
        if (!textCatalan.trim()) return alert('Introdueix el text en català.');
        setSaving(true);
        try {
            const createResponse = await axios.post(`${API_BASE}/drills/`, {
                text_catalan: textCatalan,
                text_tachelhit: textTachelhit,
                text_arabic: textArabic,
                tag: tag || undefined,
                author: author || undefined,
            });
            const drillId = createResponse.data.id;

            let mediaToUpload: { blob: Blob, type: 'image' | 'video', filename: string } | null = null;
            if (capturedImage && !capturedImage.startsWith('blob:')) {
                const res = await fetch(capturedImage);
                mediaToUpload = { blob: await res.blob(), type: 'image', filename: `img_${drillId}.jpg` };
            } else if (capturedVideo && !capturedVideo.startsWith('blob:')) {
                const res = await fetch(capturedVideo);
                mediaToUpload = { blob: await res.blob(), type: 'video', filename: `vid_${drillId}.webm` };
            } else if (uploadedFile) {
                const type = uploadedFile.type.startsWith('image/') ? 'image' : 'video';
                mediaToUpload = { blob: uploadedFile, type: type as any, filename: uploadedFile.name };
            }

            if (mediaToUpload) {
                const formData = new FormData();
                formData.append('file', mediaToUpload.blob, mediaToUpload.filename);
                const uploadRes = await axios.post(`${API_BASE}/upload-media/${drillId}/${mediaToUpload.type}`, formData);
                await axios.put(`${API_BASE}/drills/${drillId}`, { [mediaToUpload.type + '_url']: uploadRes.data.url });
            }
            onDrillCreated();
            onClose();
        } catch (error) {
            alert('No s\'ha pogut desar el drill.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ background: 'var(--surface-2)', padding: '20px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 800, color: 'var(--text-soft)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Entrada de veu en català</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <textarea value={textCatalan} onChange={e => setTextCatalan(e.target.value)} placeholder="Toca el micròfon i parla..." rows={2} style={{ flex: 1, padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '16px', color: 'var(--text)', outline: 'none' }} />
                    <button onClick={transcribing ? stopVoiceRecording : startVoiceRecording} style={{ width: '60px', height: '60px', borderRadius: 'var(--r-md)', border: 'none', background: transcribing ? 'var(--rose)' : 'var(--brand-gradient)', color: 'white', boxShadow: transcribing ? 'none' : 'var(--shadow-brand)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {transcribing ? <div className="pulse-ring" /> : <FaMicrophone size={24} />}
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-soft)', marginBottom: '6px' }}>Tachelhit</label>
                    <input value={textTachelhit} onChange={e => setTextTachelhit(e.target.value)} style={{ width: '100%', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontFamily: 'var(--font-tifinagh)' }} />
                </div>
                <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-soft)', marginBottom: '6px' }}>Tag</label>
                    <input value={tag} onChange={e => setTag(e.target.value)} style={{ width: '100%', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)' }} />
                </div>
            </div>

            <div style={{ background: 'var(--bg)', padding: '16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)' }}>
                <input type="file" accept="image/*,video/*" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    {!cameraMode ? (
                        <>
                            <button onClick={() => startCamera('photo')} style={{ padding: '12px 20px', background: 'var(--surface)', color: 'var(--text-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}><FaCamera /> Foto</button>
                            <button onClick={() => startCamera('video')} style={{ padding: '12px 20px', background: 'var(--surface)', color: 'var(--text-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}><FaVideo /> Vídeo</button>
                            <button onClick={() => fileInputRef.current?.click()} style={{ padding: '12px 20px', background: 'var(--surface)', color: 'var(--text-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}><FaFolderOpen /> Fitxers</button>
                        </>
                    ) : (
                        <button onClick={stopCamera} style={{ padding: '12px 20px', background: 'var(--text)', color: 'white', borderRadius: 'var(--r-md)', border: 'none', fontWeight: 700 }}>Cancel·la la càmera</button>
                    )}
                </div>

                {cameraMode && (
                    <div style={{ marginTop: '15px' }}>
                        <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', borderRadius: 'var(--r-lg)', background: '#000' }} />
                        <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                            {cameraMode === 'photo' ? (
                                <button onClick={capturePhoto} style={{ flex: 1, padding: '12px', background: 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 'bold' }}>Captura</button>
                            ) : (
                                <button onClick={recording ? stopVideoRecording : startVideoRecording} style={{ flex: 1, padding: '12px', background: recording ? 'var(--rose)' : 'var(--emerald)', color: 'white', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 'bold' }}>
                                    {recording ? 'Atura la gravació' : 'Comença a gravar'}
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {(capturedImage || pastedImage || (uploadedFile && uploadedFile.type.startsWith('image/'))) && (
                <div style={{ marginTop: '15px', background: 'var(--surface)', padding: '12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
                    <p style={{ margin: '0 0 10px 0', fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>VISTA PRÈVIA DE LA IMATGE</p>
                    <img src={capturedImage || pastedImage || (uploadedFile ? URL.createObjectURL(uploadedFile) : '')} alt="Contingut" style={{ width: '100%', maxHeight: '200px', borderRadius: 'var(--r-md)', objectFit: 'cover' }} />
                </div>
            )}
            {(capturedVideo || (uploadedFile && uploadedFile.type.startsWith('video/'))) && (
                <div style={{ marginTop: '15px', background: '#0f172a', borderRadius: 'var(--r-xl)', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-md)' }}>
                    <video src={capturedVideo || (uploadedFile ? URL.createObjectURL(uploadedFile) : '')} controls playsInline style={{ width: '100%', maxHeight: '250px' }} />
                    <div style={{ padding: '15px', background: '#0f172a' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 'bold' }}>INICI: {trimTimes.start}s</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 'bold' }}>FINAL: {trimTimes.end}s</span>
                        </div>
                        <input type="range" min="0" max="60" step="0.5" value={trimTimes.start} onChange={e => setTrimTimes(p => ({...p, start: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '10px' }} />
                        <input type="range" min="0" max="60" step="0.5" value={trimTimes.end} onChange={e => setTrimTimes(p => ({...p, end: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '15px' }} />
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
                <button onClick={onClose} style={{ flex: 1, padding: '15px', background: 'var(--surface)', color: 'var(--text-soft)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', fontWeight: 700 }}>Cancel·la</button>
                <button onClick={handleSave} disabled={saving} style={{ flex: 2, padding: '15px', background: 'var(--brand-gradient)', color: 'white', borderRadius: 'var(--r-lg)', border: 'none', fontWeight: 700, boxShadow: 'var(--shadow-brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                    <FaSave /> {saving ? 'Creant…' : 'Crea el drill'}
                </button>
            </div>
        </div>
    );
}
