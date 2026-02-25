import { useState, useRef, useEffect } from 'react';
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
    const [uploadedFile, setUploadedFile] = useState<File | null>(null); // New state for uploaded file
    const [pastedImage, setPastedImage] = useState<string | null>(null); // New state for pasted image
    const [saving, setSaving] = useState(false);

    // Ref for hidden file input
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Limpiar blob URLs al desmontar
    useEffect(() => {
        return () => {
            if (capturedImage && capturedImage.startsWith('blob:')) {
                URL.revokeObjectURL(capturedImage);
            }
            if (capturedVideo && capturedVideo.startsWith('blob:')) {
                URL.revokeObjectURL(capturedVideo);
            }
            // Limpiar URL del archivo subido/pegado si es un blob
            if (pastedImage && pastedImage.startsWith('blob:')) {
                URL.revokeObjectURL(pastedImage);
            }
            // uploadedFile no necesita URL.revokeObjectURL ya que es un objeto File, no una URL de blob
        };
    }, [capturedImage, capturedVideo, pastedImage]);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const recognitionRef = useRef<any>(null);

    // NEW: Handle file selection from input
    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            // Clear other media states
            setCapturedImage(null);
            setCapturedVideo(null);
            setPastedImage(null);
            setUploadedFile(file);
            // If it's an image, create a preview URL
            if (file.type.startsWith('image/')) {
                setCapturedImage(URL.createObjectURL(file));
            } else if (file.type.startsWith('video/')) {
                setCapturedVideo(URL.createObjectURL(file));
            }
        }
    };

    // NEW: Handle paste event for images
    useEffect(() => {
        const handlePaste = (event: ClipboardEvent) => {
            const items = event.clipboardData?.items;
            if (items) {
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const blob = items[i].getAsFile();
                        if (blob) {
                            // Clear other media states
                            stopCamera(); // Stop camera if active
                            setCapturedImage(null);
                            setCapturedVideo(null);
                            setUploadedFile(null);
                            
                            const imageUrl = URL.createObjectURL(blob);
                            setPastedImage(imageUrl);
                            event.preventDefault(); // Prevent default paste behavior (e.g., pasting into text area)
                            return;
                        }
                    }
                }
            }
        };

        document.addEventListener('paste', handlePaste);
        return () => {
            document.removeEventListener('paste', handlePaste);
        };
    }, []); // Empty dependency array means this runs once on mount and cleans up on unmount


    // Inicializar SpeechRecognition
    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'ca-ES'; // Catalán
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;

            recognitionRef.current.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                setTextCatalan(transcript);
                setTranscribing(false);
            };

            recognitionRef.current.onerror = (event: any) => {
                console.error('Speech recognition error', event.error);
                setTranscribing(false);
                alert('Speech recognition failed: ' + event.error);
            };

            recognitionRef.current.onend = () => {
                setTranscribing(false);
            };
        } else {
            console.warn('SpeechRecognition not supported');
        }
    }, []);

    const startVoiceRecording = () => {
        if (!recognitionRef.current) {
            alert('Speech recognition is not supported in your browser. Try Chrome or Edge.');
            return;
        }
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
            if (previewRef.current) {
                previewRef.current.srcObject = stream;
            }
        } catch (err) {
            console.error('Camera access denied:', err);
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
            const dataUrl = canvas.toDataURL('image/jpeg');
            setCapturedImage(dataUrl);
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
        if (!textCatalan.trim()) {
            alert('Please provide at least Catalan text.');
            return;
        }
        if (saving) return;
        setSaving(true);
        try {
            // 1. Crear el drill básico (sin medios)
            const drillData: any = {
                text_catalan: textCatalan,
                text_tachelhit: textTachelhit,
                text_arabic: textArabic,
                tag: tag || undefined,
                author: author || undefined,
            };
            const createResponse = await axios.post(`${API_BASE}/drills/`, drillData);
            const newDrill = createResponse.data;
            const drillId = newDrill.id;
            console.log('Drill created with ID:', drillId);

            // Determine which media to upload
            let mediaToUpload: { blob: Blob, type: 'image' | 'video', filename: string } | null = null;

            if (capturedImage && !capturedImage.startsWith('blob:')) { // Captured via camera (data URL)
                const response = await fetch(capturedImage);
                const blob = await response.blob();
                mediaToUpload = { blob, type: 'image', filename: `image_${drillId}_${Date.now()}.jpg` };
            } else if (capturedVideo && !capturedVideo.startsWith('blob:')) { // Captured via camera (blob URL)
                const response = await fetch(capturedVideo);
                const blob = await response.blob();
                mediaToUpload = { blob, type: 'video', filename: `video_${drillId}_${Date.now()}.webm` };
            } else if (uploadedFile) { // Uploaded via file input
                const fileType = uploadedFile.type.startsWith('image/') ? 'image' : (uploadedFile.type.startsWith('video/') ? 'video' : null);
                if (fileType) {
                    mediaToUpload = { blob: uploadedFile, type: fileType, filename: uploadedFile.name };
                }
            } else if (pastedImage) { // Pasted from clipboard
                const response = await fetch(pastedImage);
                const blob = await response.blob();
                mediaToUpload = { blob, type: 'image', filename: `pasted_image_${drillId}_${Date.now()}.jpg` };
            }

            if (mediaToUpload) {
                try {
                    const formData = new FormData();
                    formData.append('file', mediaToUpload.blob, mediaToUpload.filename);
                    const uploadRes = await axios.post(`${API_BASE}/upload-media/${drillId}/${mediaToUpload.type}`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                    
                    // Update the drill with the media URL
                    const updatePayload: any = {};
                    if (mediaToUpload.type === 'image') {
                        updatePayload.image_url = uploadRes.data.url;
                    } else if (mediaToUpload.type === 'video') {
                        updatePayload.video_url = uploadRes.data.url;
                    }
                    await axios.put(`${API_BASE}/drills/${drillId}`, updatePayload);
                } catch (uploadError) {
                    console.error('Error uploading media:', uploadError);
                    // Continue without media
                }
            }
            
            console.log('Drill fully created:', newDrill);
            onDrillCreated();
            onClose();
        } catch (error) {
            console.error('Error creating drill:', error);
            alert('Failed to create drill');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div>
            {/* Campos de texto */}
            <div style={{ marginBottom: '15px' }}>
                <label>Catalan (speech‑to‑text)</label>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                    <textarea
                        value={textCatalan}
                        onChange={(e) => setTextCatalan(e.target.value)}
                        placeholder="Catalan text will appear here after voice recording"
                        rows={3}
                        style={{ flex: 1, padding: '10px', fontSize: '14px' }}
                    />
                    <button
                        onClick={transcribing ? stopVoiceRecording : startVoiceRecording}
                        style={{
                            padding: '10px 20px',
                            background: transcribing ? '#ff4444' : '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                        }}
                    >
                        {transcribing ? '⏹ Stop' : '🎤 Speak'}
                    </button>
                </div>
            </div>

            <div style={{ marginBottom: '15px' }}>
                <label>Tachelhit (optional)</label>
                <textarea
                    value={textTachelhit}
                    onChange={(e) => setTextTachelhit(e.target.value)}
                    placeholder="Tachelhit translation"
                    rows={2}
                    style={{ width: '100%', padding: '10px', fontSize: '14px' }}
                />
            </div>

            <div style={{ marginBottom: '15px' }}>
                <label>Arabic (optional)</label>
                <textarea
                    value={textArabic}
                    onChange={(e) => setTextArabic(e.target.value)}
                    placeholder="Arabic translation"
                    rows={2}
                    style={{ width: '100%', padding: '10px', fontSize: '14px', direction: 'rtl' }}
                />
            </div>

            <div style={{ marginBottom: '15px' }}>
                <label>Tag (optional)</label>
                <input
                    type="text"
                    value={tag}
                    onChange={(e) => setTag(e.target.value)}
                    placeholder="e.g., greetings"
                    style={{ width: '100%', padding: '10px', fontSize: '14px' }}
                />
            </div>

            <div style={{ marginBottom: '15px' }}>
                <label>Author (optional)</label>
                <input
                    type="text"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="Your name"
                    style={{ width: '100%', padding: '10px', fontSize: '14px' }}
                />
            </div>

            {/* Media (optional) */}
            <div style={{ marginBottom: '15px' }}>
                <label>Media (optional)</label>
                <input
                    type="file"
                    accept="image/*,video/*"
                    style={{ display: 'none' }}
                    ref={fileInputRef}
                    onChange={handleFileChange}
                />

                <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
                    {!cameraMode ? (
                        <>
                            <button
                                onClick={() => startCamera('photo')}
                                style={{
                                    padding: '10px 20px',
                                    background: '#2196F3',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                }}
                            >
                                📸 Take Photo
                            </button>
                            <button
                                onClick={() => startCamera('video')}
                                style={{
                                    padding: '10px 20px',
                                    background: '#9C27B0',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                }}
                            >
                                🎥 Record Video
                            </button>
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                style={{
                                    padding: '10px 20px',
                                    background: '#FFC107',
                                    color: '#333',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                }}
                            >
                                📤 Upload File
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={stopCamera}
                            style={{
                                padding: '10px 20px',
                                background: '#ff4444',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                cursor: 'pointer',
                            }}
                        >
                            Cancel Camera
                        </button>
                    )}

                    {(capturedImage || capturedVideo || uploadedFile || pastedImage || cameraMode) && (
                        <button
                            onClick={() => {
                                stopCamera();
                                setCapturedImage(null);
                                setCapturedVideo(null);
                                setUploadedFile(null);
                                setPastedImage(null);
                            }}
                            style={{
                                padding: '10px 20px',
                                background: '#ff4444',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                cursor: 'pointer',
                            }}
                        >
                            Clear Media
                        </button>
                    )}
                </div>

                {!cameraMode && (
                    <p style={{ fontSize: '12px', color: '#666', marginTop: '-5px' }}>
                        Or paste an image from your clipboard (Ctrl+V)
                    </p>
                )}

                {cameraMode && (
                    <div>
                        <video
                            ref={previewRef}
                            autoPlay
                            muted
                            playsInline
                            style={{ width: '100%', maxHeight: '300px', borderRadius: '8px' }}
                        />
                        <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                            {cameraMode === 'photo' && (
                                <button
                                    onClick={capturePhoto}
                                    style={{
                                        padding: '10px 20px',
                                        background: '#4CAF50',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                    }}
                                >
                                    Capture Photo
                                </button>
                            )}
                            {cameraMode === 'video' && (
                                <>
                                    {!recording ? (
                                        <button
                                            onClick={startVideoRecording}
                                            style={{
                                                padding: '10px 20px',
                                                background: '#4CAF50',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '6px',
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Start Recording
                                        </button>
                                    ) : (
                                        <button
                                            onClick={stopVideoRecording}
                                            style={{
                                                padding: '10px 20px',
                                                background: '#ff4444',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '6px',
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Stop Recording
                                        </button>
                                    )}
                                </>
                            )}
                        </div>
                    </div>
                )}

                {(capturedImage || pastedImage || (uploadedFile && uploadedFile.type.startsWith('image/'))) && (
                    <div style={{ marginTop: '10px' }}>
                        <p>Captured/Uploaded Image:</p>
                        <img src={capturedImage || pastedImage || URL.createObjectURL(uploadedFile as File)} alt="Media" style={{ maxWidth: '200px', borderRadius: '8px' }} />
                    </div>
                )}
                {(capturedVideo || (uploadedFile && uploadedFile.type.startsWith('video/'))) && (
                    <div style={{ marginTop: '10px' }}>
                        <p>Captured/Uploaded Video:</p>
                        <video src={capturedVideo || URL.createObjectURL(uploadedFile as File)} controls style={{ maxWidth: '200px', borderRadius: '8px' }} />
                    </div>
                )}
            </div>

            {/* Botones de acción */}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button
                    onClick={onClose}
                    disabled={saving}
                    style={{
                        padding: '10px 20px',
                        background: '#e0e0e0',
                        color: '#333',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold',
                        opacity: saving ? 0.6 : 1,
                    }}
                >
                    Cancel
                </button>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        padding: '10px 20px',
                        background: saving ? '#999' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold',
                        opacity: saving ? 0.8 : 1,
                    }}
                >
                    {saving ? 'Saving...' : 'Save Drill'}
                </button>
            </div>
        </div>
    );
}
