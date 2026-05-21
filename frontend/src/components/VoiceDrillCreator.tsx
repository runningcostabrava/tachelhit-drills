import { useState, useRef, useEffect } from 'react';
import { FaMicrophone, FaPlus, FaCheck, FaTimes, FaCamera, FaVideo, FaKeyboard, FaFolderOpen, FaMagic, FaSave, FaScissors } from 'react-icons/fa';
import axios from 'axios';
import { API_BASE } from '../config';

interface VoiceDrillCreatorProps {
    onClose: () => void;
    onDrillCreated: () => void;
}

export default function VoiceDrillCreator({ onClose, onDrillCreated }: VoiceDrillCreatorProps) {
    const [textCatalan, setTextCatalan] = useState('');
    const [textTachelhit, setTextTachelhit] = useState('');
    const [textArabic, setTextArabic] = useState('');
    const [tag, setTag] = useState('');
    const [author, setAuthor] = useState('');
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
        if (!recognitionRef.current) return alert('Speech recognition not supported.');
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
        if (!textCatalan.trim()) return alert('Please provide Catalan text.');
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
            alert('Failed to save drill.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ background: '#F9FAFB', padding: '20px', borderRadius: '20px', border: '1px solid #E5E7EB' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 800, color: '#6B7280', marginBottom: '10px', textTransform: 'uppercase' }}>Catalan Voice Input</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <textarea value={textCatalan} onChange={e => setTextCatalan(e.target.value)} placeholder="Tap mic and speak..." rows={2} style={{ flex: 1, padding: '12px', borderRadius: '12px', border: '1px solid #D1D5DB', fontSize: '16px', outline: 'none' }} />
                    <button onClick={transcribing ? stopVoiceRecording : startVoiceRecording} style={{ width: '60px', height: '60px', borderRadius: '12px', border: 'none', background: transcribing ? '#E11D48' : '#4F46E5', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {transcribing ? <div className="pulse-ring" /> : <FaMicrophone size={24} />}
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#6B7280', marginBottom: '5px' }}>Tachelhit</label>
                    <input value={textTachelhit} onChange={e => setTextTachelhit(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid #D1D5DB' }} />
                </div>
                <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#6B7280', marginBottom: '5px' }}>Tag</label>
                    <input value={tag} onChange={e => setTag(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid #D1D5DB' }} />
                </div>
            </div>

            <div style={{ background: '#F3F4F6', padding: '15px', borderRadius: '20px' }}>
                <input type="file" accept="image/*,video/*" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    {!cameraMode ? (
                        <>
                            <button onClick={() => startCamera('photo')} style={{ padding: '12px 20px', background: 'white', borderRadius: '12px', border: '1px solid #D1D5DB', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}><FaCamera /> Photo</button>
                            <button onClick={() => startCamera('video')} style={{ padding: '12px 20px', background: 'white', borderRadius: '12px', border: '1px solid #D1D5DB', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}><FaVideo /> Video</button>
                            <button onClick={() => fileInputRef.current?.click()} style={{ padding: '12px 20px', background: 'white', borderRadius: '12px', border: '1px solid #D1D5DB', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}><FaFolderOpen /> Files</button>
                        </>
                    ) : (
                        <button onClick={stopCamera} style={{ padding: '12px 20px', background: '#374151', color: 'white', borderRadius: '12px', border: 'none' }}>Cancel Camera</button>
                    )}
                </div>

                {cameraMode && (
                    <div style={{ marginTop: '15px' }}>
                        <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', borderRadius: '15px', background: '#000' }} />
                        <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                            {cameraMode === 'photo' ? (
                                <button onClick={capturePhoto} style={{ flex: 1, padding: '12px', background: '#10B981', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>Capture</button>
                            ) : (
                                <button onClick={recording ? stopVideoRecording : startVideoRecording} style={{ flex: 1, padding: '12px', background: recording ? '#E11D48' : '#10B981', color: 'white', border: 'none', borderRadius: '12px', fontWeight: 'bold' }}>
                                    {recording ? 'Stop Recording' : 'Start Recording'}
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {(capturedImage || pastedImage || (uploadedFile && uploadedFile.type.startsWith('image/'))) && (
                <div style={{ marginTop: '15px', background: 'white', padding: '10px', borderRadius: '16px', border: '1px solid #E5E7EB' }}>
                    <p style={{ margin: '0 0 10px 0', fontSize: '12px', fontWeight: 'bold', color: '#6B7280' }}>IMAGE PREVIEW</p>
                    <img src={capturedImage || pastedImage || (uploadedFile ? URL.createObjectURL(uploadedFile) : '')} alt="Media" style={{ width: '100%', maxHeight: '200px', borderRadius: '12px', objectFit: 'cover' }} />
                </div>
            )}
            {(capturedVideo || (uploadedFile && uploadedFile.type.startsWith('video/'))) && (
                <div style={{ marginTop: '15px', background: '#000', borderRadius: '20px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <video src={capturedVideo || (uploadedFile ? URL.createObjectURL(uploadedFile) : '')} controls playsInline style={{ width: '100%', maxHeight: '250px' }} />
                    <div style={{ padding: '15px', background: '#111' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                            <span style={{ color: '#9CA3AF', fontSize: '11px', fontWeight: 'bold' }}>START: {trimTimes.start}s</span>
                            <span style={{ color: '#9CA3AF', fontSize: '11px', fontWeight: 'bold' }}>END: {trimTimes.end}s</span>
                        </div>
                        <input type="range" min="0" max="60" step="0.5" value={trimTimes.start} onChange={e => setTrimTimes(p => ({...p, start: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '10px' }} />
                        <input type="range" min="0" max="60" step="0.5" value={trimTimes.end} onChange={e => setTrimTimes(p => ({...p, end: parseFloat(e.target.value)}))} style={{ width: '100%', marginBottom: '15px' }} />
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
                <button onClick={onClose} style={{ flex: 1, padding: '15px', background: '#F3F4F6', borderRadius: '16px', border: 'none', fontWeight: 600 }}>Cancel</button>
                <button onClick={handleSave} disabled={saving} style={{ flex: 2, padding: '15px', background: '#4F46E5', color: 'white', borderRadius: '16px', border: 'none', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                    <FaSave /> {saving ? 'Creating...' : 'Create Drill'}
                </button>
            </div>
        </div>
    );
}
