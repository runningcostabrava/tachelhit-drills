import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
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
    is_correction_dataset?: boolean;
    date_created?: string;
}

export default function MobileDrillCreator({ onClose, onDrillCreated }: MobileDrillCreatorProps) {
    // Drill state
    const [drill, setDrill] = useState<Drill>({
        text_catalan: '',
        text_tachelhit: '',
        text_arabic: '',
        tag: '',
        author: ''
    });

    // Media states
    const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
    const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);
    const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [pastedImage, setPastedImage] = useState<string | null>(null);

    // UI states
    const [saving, setSaving] = useState(false);
    const [showCameraChoice, setShowCameraChoice] = useState(false);
    const [cameraFacing, setCameraFacing] = useState<'user' | 'environment'>('environment');
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [transcriptionResult, setTranscriptionResult] = useState<{ rough: string, score: number } | null>(null);
    const [autoSaveTimer, setAutoSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
    const [lastSaved, setLastSaved] = useState<string | null>(null);

    // Refs
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const recognitionRef = useRef<any>(null);

    // Cleanup blob URLs on unmount
    useEffect(() => {
        return () => {
            if (capturedImage && capturedImage.startsWith('blob:')) {
                URL.revokeObjectURL(capturedImage);
            }
            if (capturedVideo && capturedVideo.startsWith('blob:')) {
                URL.revokeObjectURL(capturedVideo);
            }
            if (pastedImage && pastedImage.startsWith('blob:')) {
                URL.revokeObjectURL(pastedImage);
            }
            if (autoSaveTimer) {
                clearTimeout(autoSaveTimer);
            }
        };
    }, [capturedImage, capturedVideo, pastedImage, autoSaveTimer]);

    // Initialize speech recognition
    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = 'ca-ES'; // Catalan
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;

            recognitionRef.current.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                setDrill(prev => ({ ...prev, text_catalan: transcript }));
                triggerAutoSave();
            };

            recognitionRef.current.onerror = (event: any) => {
                console.error('Speech recognition error', event.error);
            };

            recognitionRef.current.onend = () => {
                // Auto-save after speech recognition
                triggerAutoSave();
            };
        }
    }, []);

    // Auto-save functionality
    const triggerAutoSave = () => {
        if (autoSaveTimer) {
            clearTimeout(autoSaveTimer);
        }

        const timer = setTimeout(async () => {
            if (drill.id) {
                // Update existing drill
                try {
                    await axios.put(`${API_BASE}/drills/${drill.id}`, drill);
                    setLastSaved(new Date().toLocaleTimeString());
                } catch (error) {
                    console.error('Auto-save failed:', error);
                }
            } else if (drill.text_catalan || drill.text_tachelhit || drill.text_arabic) {
                // Create new drill if we have content
                try {
                    const response = await axios.post(`${API_BASE}/drills/`, drill);
                    setDrill(prev => ({ ...prev, id: response.data.id }));
                    setLastSaved(new Date().toLocaleTimeString());
                } catch (error) {
                    console.error('Auto-save failed:', error);
                }
            }
        }, 2000); // 2 second delay for auto-save

        setAutoSaveTimer(timer);
    };

    // Handle text changes with auto-save
    const handleTextChange = (field: keyof Drill, value: string) => {
        setDrill(prev => ({ ...prev, [field]: value }));
        triggerAutoSave();
    };

    // Start voice recording (speech-to-text)
    const startVoiceRecording = () => {
        if (!recognitionRef.current) {
            alert('Speech recognition is not supported in your browser. Try Chrome or Edge.');
            return;
        }
        recognitionRef.current.start();
    };

    // Start audio recording (microphone)
    const startAudioRecording = async () => {
        console.log('🎤 Starting audio recording');

        if (!drill.id) {
            // Create a drill first if we don't have one
            try {
                const response = await axios.post(`${API_BASE}/drills/`, drill);
                setDrill(prev => ({ ...prev, id: response.data.id }));
            } catch (error) {
                console.error('Failed to create drill:', error);
                alert('Please add some text first before recording audio.');
                return;
            }
        }

        try {
            // Stop any existing stream
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            }

            const constraints: MediaStreamConstraints = {
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            };

            // Check if we already have permission by trying to get the stream
            // without showing the permission dialog if possible
            let stream;
            try {
                // Try to get existing permissions first
                const devices = await navigator.mediaDevices.enumerateDevices();
                const hasAudioPermission = devices.some(device => device.kind === 'audioinput' && device.deviceId !== '');

                if (hasAudioPermission) {
                    // We have permission, get the stream
                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                } else {
                    // No permission yet, ask for it
                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                }
            } catch (err) {
                console.error('Failed to get audio stream:', err);
                alert('Microphone access is required for audio recording. Please allow microphone access.');
                setRecording(null);
                return;
            }

            streamRef.current = stream;

            // Determine MIME type
            let mimeType = 'audio/webm';
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
            const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

            if (isIOS || isSafari) {
                mimeType = 'audio/mp4';
            }

            const options = { mimeType };
            mediaRecorderRef.current = new MediaRecorder(stream, options);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: mimeType });

                if (blob.size < 1024) {
                    setRecording(null);
                    return;
                }

                const formData = new FormData();
                formData.append('file', blob, `audio_${drill.id}_${Date.now()}.${mimeType.includes('mp4') ? 'm4a' : 'webm'}`);

                try {
                    await axios.post(`${API_BASE}/upload-media/${drill.id}/audio`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                    // Refresh drill data
                    const response = await axios.get(`${API_BASE}/drills/${drill.id}`);
                    setDrill(response.data);
                    triggerAutoSave();
                } catch (err) {
                    console.error('Audio upload failed:', err);
                }

                if (streamRef.current) {
                    streamRef.current.getTracks().forEach(track => track.stop());
                    streamRef.current = null;
                }
                setRecording(null);
            };

            mediaRecorderRef.current.start();
            setRecording('audio');
        } catch (err: any) {
            console.error('Microphone access denied:', err);
            setRecording(null);
        }
    };

    // Start video recording
    const startVideoRecording = async (facing: 'user' | 'environment' = 'environment') => {
        console.log('Starting video recording');

        if (!drill.id) {
            // Create a drill first if we don't have one
            try {
                const response = await axios.post(`${API_BASE}/drills/`, drill);
                setDrill(prev => ({ ...prev, id: response.data.id }));
            } catch (error) {
                console.error('Failed to create drill:', error);
                alert('Please add some text first before recording video.');
                return;
            }
        }

        try {
            // Stop any existing stream
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            }

            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: { exact: facing },
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: true
                });
            } catch (err) {
                // Fallback without exact
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: facing,
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: true
                });
            }

            streamRef.current = stream;
            setCameraMode('video');
            setCameraFacing(facing);

            // Show preview
            setTimeout(() => {
                if (previewRef.current) {
                    previewRef.current.srcObject = stream;
                    previewRef.current.play().catch(e => {
                        console.error('Error playing video preview:', e);
                    });
                }
            }, 50);

            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                const formData = new FormData();
                formData.append('file', blob, `video_${drill.id}_${Date.now()}.webm`);

                try {
                    await axios.post(`${API_BASE}/upload-media/${drill.id}/video`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                    // Refresh drill data
                    const response = await axios.get(`${API_BASE}/drills/${drill.id}`);
                    setDrill(response.data);
                    triggerAutoSave();
                } catch (err) {
                    console.error('Video upload failed:', err);
                }

                stopCamera();
                setRecording(null);
            };

            mediaRecorderRef.current.start();
            setRecording('video');
        } catch (err: any) {
            console.error('Camera access denied:', err);
            setCameraMode(null);
            setRecording(null);
        }
    };

    // Start image capture
    const startImageCapture = async (facing: 'user' | 'environment' = 'environment') => {
        console.log('Starting image capture');

        if (!drill.id) {
            // Create a drill first if we don't have one
            try {
                const response = await axios.post(`${API_BASE}/drills/`, drill);
                setDrill(prev => ({ ...prev, id: response.data.id }));
            } catch (error) {
                console.error('Failed to create drill:', error);
                alert('Please add some text first before taking a picture.');
                return;
            }
        }

        try {
            // Stop any existing stream
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            }

            const constraints = {
                video: {
                    facingMode: facing,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            streamRef.current = stream;
            setCameraMode('photo');
            setCameraFacing(facing);

            // Show preview
            setTimeout(() => {
                if (previewRef.current) {
                    previewRef.current.srcObject = stream;
                    previewRef.current.play().catch(e => {
                        console.error('Error playing video:', e);
                    });
                }
            }, 100);
        } catch (err: any) {
            console.error('Camera access denied for image capture:', err);
            setCameraMode(null);
        }
    };

    // Take picture
    const takePicture = () => {
        if (!previewRef.current || !canvasRef.current || !streamRef.current) return;

        const video = previewRef.current;
        const canvas = canvasRef.current;

        // Wait for video to be ready
        if (video.readyState !== video.HAVE_ENOUGH_DATA) {
            console.log('Video not ready, waiting...');
            setTimeout(takePicture, 500);
            return;
        }

        setTimeout(() => {
            const videoTrack = streamRef.current?.getVideoTracks()[0];
            if (!videoTrack) {
                console.error('No video track available');
                return;
            }

            const settings = videoTrack.getSettings();
            const width = settings.width || 640;
            const height = settings.height || 480;

            canvas.width = width;
            canvas.height = height;

            const context = canvas.getContext('2d');
            if (context) {
                context.fillStyle = '#ffffff';
                context.fillRect(0, 0, width, height);
                context.drawImage(video, 0, 0, width, height);

                canvas.toBlob(async (blob) => {
                    if (blob && blob.size > 1024) {
                        const formData = new FormData();
                        formData.append('file', blob, `image_${drill.id}_${Date.now()}.jpg`);
                        try {
                            await axios.post(`${API_BASE}/upload-media/${drill.id}/image`, formData, {
                                headers: { 'Content-Type': 'multipart/form-data' },
                            });
                            // Refresh drill data
                            const response = await axios.get(`${API_BASE}/drills/${drill.id}`);
                            setDrill(response.data);
                            triggerAutoSave();
                        } catch (err) {
                            console.error('Image upload failed:', err);
                        }
                    }
                    stopCamera();
                }, 'image/jpeg', 0.9);
            }
        }, 300);
    };

    // Stop recording
    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        } else {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
                streamRef.current = null;
            }
            setRecording(null);
        }
    };

    // Stop camera
    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        setCameraMode(null);
    };

    // Handle file upload
    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setCapturedImage(null);
            setCapturedVideo(null);
            setPastedImage(null);
            setUploadedFile(file);

            if (file.type.startsWith('image/')) {
                setCapturedImage(URL.createObjectURL(file));
            } else if (file.type.startsWith('video/')) {
                setCapturedVideo(URL.createObjectURL(file));
            }
        }
    };

    // Handle paste event for images
    useEffect(() => {
        const handlePaste = (event: ClipboardEvent) => {
            const items = event.clipboardData?.items;
            if (items) {
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const blob = items[i].getAsFile();
                        if (blob) {
                            stopCamera();
                            setCapturedImage(null);
                            setCapturedVideo(null);
                            setUploadedFile(null);

                            const imageUrl = URL.createObjectURL(blob);
                            setPastedImage(imageUrl);
                            event.preventDefault();
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
    }, []);

    // Handle save drill
    const handleSave = async () => {
        if (saving) return;
        setSaving(true);

        try {
            if (!drill.id) {
                // Create new drill
                const response = await axios.post(`${API_BASE}/drills/`, drill);
                setDrill(prev => ({ ...prev, id: response.data.id }));
            } else {
                // Update existing drill
                await axios.put(`${API_BASE}/drills/${drill.id}`, drill);
            }

            // Handle media uploads if any
            if (uploadedFile) {
                const fileType = uploadedFile.type.startsWith('image/') ? 'image' :
                    uploadedFile.type.startsWith('video/') ? 'video' : null;
                if (fileType && drill.id) {
                    const formData = new FormData();
                    formData.append('file', uploadedFile, uploadedFile.name);
                    await axios.post(`${API_BASE}/upload-media/${drill.id}/${fileType}`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                }
            }

            alert('Drill saved successfully!');
            onDrillCreated();
            // Don't close the modal - keep it open for further editing
        } catch (error) {
            console.error('Error saving drill:', error);
            alert('Failed to save drill');
        } finally {
            setSaving(false);
        }
    };

    // Handle create new drill
    const handleCreateNew = () => {
        // Reset drill state
        setDrill({
            text_catalan: '',
            text_tachelhit: '',
            text_arabic: '',
            tag: '',
            author: ''
        });

        // Reset media states
        setCapturedImage(null);
        setCapturedVideo(null);
        setUploadedFile(null);
        setPastedImage(null);
        setTranscriptionResult(null);
        setLastSaved(null);

        // Clear auto-save timer
        if (autoSaveTimer) {
            clearTimeout(autoSaveTimer);
            setAutoSaveTimer(null);
        }

        alert('New drill form ready!');
    };

    // Handle auto-transcribe
    const handleAutoTranscribe = async () => {
        if (!drill.audio_url) {
            alert('Please record audio first');
            return;
        }

        setIsTranscribing(true);
        setTranscriptionResult(null);
        try {
            const response = await axios.post(`${API_BASE}/transcribe/`, {
                audio_url: drill.audio_url
            });
            const { corrected_transcription, rough_transcription, similarity_score } = response.data;

            setTranscriptionResult({
                rough: rough_transcription,
                score: similarity_score
            });

            if (corrected_transcription) {
                setDrill(prev => ({ ...prev, text_tachelhit: corrected_transcription }));
                triggerAutoSave();
            }
        } catch (error) {
            console.error('Transcription failed:', error);
            alert('Failed to transcribe audio.');
        } finally {
            setIsTranscribing(false);
        }
    };

    // Render the component
    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'white',
            zIndex: 10000,
            display: 'flex',
            flexDirection: 'column'
        }}>
            {/* Header */}
            <div style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                padding: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'rgba(255,255,255,0.2)',
                            border: 'none',
                            color: 'white',
                            fontSize: '24px',
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        ✕
                    </button>

                    <button
                        onClick={handleCreateNew}
                        style={{
                            background: '#FF9800',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '14px',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                        }}
                    >
                        ➕ New
                    </button>
                </div>

                <div style={{
                    color: 'white',
                    fontSize: '18px',
                    fontWeight: 700,
                    flex: 1,
                    textAlign: 'center'
                }}>
                    {drill.id ? `Drill #${drill.id}` : 'New Drill'}
                    {lastSaved && <div style={{ fontSize: '12px', color: '#FFD700' }}>Saved: {lastSaved}</div>}
                </div>

                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        background: saving ? '#999' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        padding: '8px 16px',
                        fontSize: '16px',
                        fontWeight: 700,
                        cursor: saving ? 'not-allowed' : 'pointer'
                    }}
                >
                    {saving ? 'Saving...' : '💾 Save'}
                </button>
            </div>

            {/* Content - Scrollable */}
            <div style={{
                flex: 1,
                overflow: 'auto',
                padding: '16px'
            }}>
                {/* Big Action Buttons */}
                <div style={{
                    background: '#f8f9fa',
                    padding: '20px',
                    borderRadius: '16px',
                    marginBottom: '20px',
                    textAlign: 'center'
                }}>
                    <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', fontWeight: 700 }}>
                        Capture Moments Fast
                    </h3>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: '16px',
                        marginBottom: '20px'
                    }}>
                        {/* Picture Button */}
                        <button
                            onClick={() => startImageCapture('environment')}
                            style={{
                                height: '120px',
                                background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '16px',
                                fontSize: '24px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)'
                            }}
                        >
                            <div style={{ fontSize: '40px' }}>📷</div>
                            <div>Picture</div>
                        </button>

                        {/* Audio Button */}
                        <button
                            onClick={recording === 'audio' ? stopRecording : startAudioRecording}
                            style={{
                                height: '120px',
                                background: recording === 'audio'
                                    ? 'linear-gradient(135deg, #ff4444 0%, #cc0000 100%)'
                                    : 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '16px',
                                fontSize: '24px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                boxShadow: recording === 'audio'
                                    ? '0 4px 12px rgba(255, 68, 68, 0.3)'
                                    : '0 4px 12px rgba(33, 150, 243, 0.3)'
                            }}
                        >
                            <div style={{ fontSize: '40px' }}>
                                {recording === 'audio' ? '⏹️' : '🎙️'}
                            </div>
                            <div>{recording === 'audio' ? 'Stop' : 'Audio'}</div>
                        </button>

                        {/* Video Button */}
                        <button
                            onClick={() => setShowCameraChoice(true)}
                            style={{
                                height: '120px',
                                background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '16px',
                                fontSize: '24px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                boxShadow: '0 4px 12px rgba(156, 39, 176, 0.3)'
                            }}
                        >
                            <div style={{ fontSize: '40px' }}>🎬</div>
                            <div>Video</div>
                        </button>

                        {/* Voice-to-Text Button */}
                        <button
                            onClick={startVoiceRecording}
                            style={{
                                height: '120px',
                                background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '16px',
                                fontSize: '24px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                boxShadow: '0 4px 12px rgba(255, 152, 0, 0.3)'
                            }}
                        >
                            <div style={{ fontSize: '40px' }}>🎤</div>
                            <div>Speak</div>
                        </button>
                    </div>

                    {/* File Upload Button */}
                    <div style={{ marginTop: '10px' }}>
                        <input
                            type="file"
                            accept="image/*,video/*"
                            style={{ display: 'none' }}
                            ref={fileInputRef}
                            onChange={handleFileChange}
                        />
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            style={{
                                width: '100%',
                                padding: '16px',
                                background: 'linear-gradient(135deg, #607D8B 0%, #455A64 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '12px',
                                fontSize: '18px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '10px',
                                boxShadow: '0 4px 12px rgba(96, 125, 139, 0.3)'
                            }}
                        >
                            <div style={{ fontSize: '24px' }}>📤</div>
                            <div>Upload File</div>
                        </button>
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '8px', textAlign: 'center' }}>
                            Or paste an image (Ctrl+V)
                        </div>
                    </div>
                </div>

                {/* Text Inputs */}
                <div style={{ marginBottom: '20px' }}>
                    <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: 700 }}>
                        Text Content
                    </h3>

                    {/* Catalan */}
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '14px',
                            fontWeight: 600,
                            color: '#333',
                            marginBottom: '6px'
                        }}>
                            Català
                        </label>
                        <textarea
                            value={drill.text_catalan || ''}
                            onChange={(e) => handleTextChange('text_catalan', e.target.value)}
                            placeholder="Catalan text (use voice button above)"
                            rows={3}
                            style={{
                                width: '100%',
                                padding: '12px',
                                fontSize: '16px',
                                border: '2px solid #e0e0e0',
                                borderRadius: '8px',
                                outline: 'none',
                                resize: 'vertical'
                            }}
                        />
                    </div>

                    {/* Tachelhit */}
                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <label style={{
                                fontSize: '14px',
                                fontWeight: 600,
                                color: '#333'
                            }}>
                                Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)
                            </label>
                            {drill.audio_url && (
                                <button
                                    onClick={handleAutoTranscribe}
                                    disabled={isTranscribing}
                                    style={{
                                        background: isTranscribing ? '#eee' : '#667eea',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        padding: '6px 12px',
                                        fontSize: '12px',
                                        cursor: isTranscribing ? 'not-allowed' : 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}
                                >
                                    {isTranscribing ? '⏳...' : '🪄 Auto-Transcribe'}
                                </button>
                            )}
                        </div>
                        <textarea
                            value={drill.text_tachelhit || ''}
                            onChange={(e) => handleTextChange('text_tachelhit', e.target.value)}
                            placeholder="Tachelhit text"
                            rows={3}
                            style={{
                                width: '100%',
                                padding: '12px',
                                fontSize: '16px',
                                border: '2px solid #e0e0e0',
                                borderRadius: '8px',
                                outline: 'none',
                                resize: 'vertical'
                            }}
                        />
                        {transcriptionResult && (
                            <div style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>
                                Rough: <span style={{ fontFamily: 'monospace' }}>{transcriptionResult.rough}</span>
                                (Score: {Math.round(transcriptionResult.score * 100)}%)
                            </div>
                        )}
                    </div>

                    {/* Arabic */}
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '14px',
                            fontWeight: 600,
                            color: '#333',
                            marginBottom: '6px',
                            textAlign: 'right'
                        }}>
                            العربية
                        </label>
                        <textarea
                            value={drill.text_arabic || ''}
                            onChange={(e) => handleTextChange('text_arabic', e.target.value)}
                            placeholder="أدخل النص العربي..."
                            rows={2}
                            style={{
                                width: '100%',
                                padding: '12px',
                                fontSize: '16px',
                                border: '2px solid #e0e0e0',
                                borderRadius: '8px',
                                outline: 'none',
                                resize: 'vertical',
                                direction: 'rtl'
                            }}
                        />
                    </div>

                    {/* Tag and Author */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                        <div>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: 600,
                                color: '#333',
                                marginBottom: '6px'
                            }}>
                                Tag
                            </label>
                            <input
                                type="text"
                                value={drill.tag || ''}
                                onChange={(e) => handleTextChange('tag', e.target.value)}
                                placeholder="e.g., greetings"
                                style={{
                                    width: '100%',
                                    padding: '12px',
                                    fontSize: '16px',
                                    border: '2px solid #e0e0e0',
                                    borderRadius: '8px',
                                    outline: 'none'
                                }}
                            />
                        </div>
                        <div>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: 600,
                                color: '#333',
                                marginBottom: '6px'
                            }}>
                                Author
                            </label>
                            <input
                                type="text"
                                value={drill.author || ''}
                                onChange={(e) => handleTextChange('author', e.target.value)}
                                placeholder="Your name"
                                style={{
                                    width: '100%',
                                    padding: '12px',
                                    fontSize: '16px',
                                    border: '2px solid #e0e0e0',
                                    borderRadius: '8px',
                                    outline: 'none'
                                }}
                            />
                        </div>
                    </div>
                </div>

                {/* Media Preview */}
                {(drill.image_url || capturedImage || pastedImage) && (
                    <div style={{ marginBottom: '20px' }}>
                        <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: 700 }}>
                            Image Preview
                        </h3>
                        <img
                            src={drill.image_url ? getMediaUrl(drill.image_url) : capturedImage || pastedImage || ''}
                            alt="Drill"
                            style={{
                                width: '100%',
                                maxHeight: '300px',
                                borderRadius: '12px',
                                border: '1px solid #e0e0e0',
                                objectFit: 'cover'
                            }}
                        />
                    </div>
                )}

                {/* Camera Choice Modal */}
                {showCameraChoice && (
                    <div style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0,0,0,0.8)',
                        zIndex: 20000,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '20px'
                    }}>
                        <div style={{
                            background: 'white',
                            borderRadius: '16px',
                            padding: '30px',
                            maxWidth: '400px',
                            width: '100%'
                        }}>
                            <h3 style={{ margin: '0 0 24px 0', fontSize: '20px', fontWeight: 700, textAlign: 'center' }}>
                                Choose Video Camera
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <button
                                    onClick={() => {
                                        setCameraFacing('user');
                                        setShowCameraChoice(false);
                                        startVideoRecording('user');
                                    }}
                                    style={{
                                        padding: '20px',
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '18px',
                                        fontWeight: 700,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '12px'
                                    }}
                                >
                                    <span style={{ fontSize: '32px' }}>🤳</span> Front Camera
                                </button>
                                <button
                                    onClick={() => {
                                        setCameraFacing('environment');
                                        setShowCameraChoice(false);
                                        startVideoRecording('environment');
                                    }}
                                    style={{
                                        padding: '20px',
                                        background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '18px',
                                        fontWeight: 700,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '12px'
                                    }}
                                >
                                    <span style={{ fontSize: '32px' }}>📷</span> Back Camera
                                </button>
                                <button
                                    onClick={() => setShowCameraChoice(false)}
                                    style={{
                                        padding: '14px',
                                        background: '#e0e0e0',
                                        color: '#333',
                                        border: 'none',
                                        borderRadius: '10px',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Camera Preview - Inline, not full screen */}
                {cameraMode && (
                    <div style={{
                        background: '#000',
                        borderRadius: '16px',
                        marginBottom: '20px',
                        overflow: 'hidden',
                        position: 'relative'
                    }}>
                        <div style={{ position: 'relative', height: '300px' }}>
                            <video
                                ref={previewRef}
                                autoPlay
                                muted
                                playsInline
                                style={{
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'cover',
                                    transform: cameraFacing === 'user' ? 'scaleX(-1)' : 'none'
                                }}
                            />
                            <div style={{
                                position: 'absolute',
                                top: '10px',
                                right: '10px',
                                display: 'flex',
                                gap: '8px'
                            }}>
                                <button
                                    onClick={() => {
                                        const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
                                        if (cameraMode === 'photo') {
                                            startImageCapture(newFacing);
                                        } else {
                                            startVideoRecording(newFacing);
                                        }
                                    }}
                                    style={{
                                        width: '40px',
                                        height: '40px',
                                        borderRadius: '50%',
                                        background: 'rgba(255, 255, 255, 0.3)',
                                        border: '1px solid white',
                                        color: 'white',
                                        fontSize: '18px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                    title="Switch camera"
                                >
                                    🔄
                                </button>
                                <button
                                    onClick={stopCamera}
                                    style={{
                                        width: '40px',
                                        height: '40px',
                                        borderRadius: '50%',
                                        background: 'rgba(255, 0, 0, 0.7)',
                                        border: '1px solid white',
                                        color: 'white',
                                        fontSize: '18px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                    title="Close camera"
                                >
                                    ✕
                                </button>
                            </div>
                        </div>
                        <div style={{
                            padding: '20px',
                            background: 'rgba(0, 0, 0, 0.8)',
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            gap: '20px'
                        }}>
                            {cameraMode === 'photo' ? (
                                <button
                                    onClick={takePicture}
                                    style={{
                                        width: '70px',
                                        height: '70px',
                                        borderRadius: '50%',
                                        background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
                                        color: 'white',
                                        border: '3px solid white',
                                        fontSize: '28px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                    title="Take picture"
                                >
                                    📸
                                </button>
                            ) : (
                                <button
                                    onClick={recording === 'video' ? stopRecording : () => {
                                        // Start video recording with current facing mode
                                        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                                            stopRecording();
                                        } else {
                                            // The recording should already be started when cameraMode was set to 'video'
                                            // But if not, we need to start it
                                            if (streamRef.current && !mediaRecorderRef.current) {
                                                mediaRecorderRef.current = new MediaRecorder(streamRef.current);
                                                chunksRef.current = [];

                                                mediaRecorderRef.current.ondataavailable = (e) => {
                                                    if (e.data.size > 0) {
                                                        chunksRef.current.push(e.data);
                                                    }
                                                };

                                                mediaRecorderRef.current.onstop = async () => {
                                                    const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                                                    const formData = new FormData();
                                                    formData.append('file', blob, `video_${drill.id}_${Date.now()}.webm`);

                                                    try {
                                                        await axios.post(`${API_BASE}/upload-media/${drill.id}/video`, formData, {
                                                            headers: { 'Content-Type': 'multipart/form-data' },
                                                        });
                                                        // Refresh drill data
                                                        const response = await axios.get(`${API_BASE}/drills/${drill.id}`);
                                                        setDrill(response.data);
                                                        triggerAutoSave();
                                                    } catch (err) {
                                                        console.error('Video upload failed:', err);
                                                    }

                                                    stopCamera();
                                                    setRecording(null);
                                                };

                                                mediaRecorderRef.current.start();
                                                setRecording('video');
                                            }
                                        }
                                    }}
                                    style={{
                                        width: '70px',
                                        height: '70px',
                                        borderRadius: '50%',
                                        background: recording === 'video'
                                            ? 'linear-gradient(135deg, #ff4444 0%, #cc0000 100%)'
                                            : 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
                                        color: 'white',
                                        border: '3px solid white',
                                        fontSize: '28px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                    title={recording === 'video' ? 'Stop recording' : 'Start recording'}
                                >
                                    {recording === 'video' ? '⏹' : '🎬'}
                                </button>
                            )}
                            {cameraMode === 'video' && recording !== 'video' && (
                                <div style={{ color: 'white', fontSize: '14px', textAlign: 'center' }}>
                                    Tap the button to start recording
                                </div>
                            )}
                            {cameraMode === 'video' && recording === 'video' && (
                                <div style={{ color: '#ff4444', fontSize: '16px', fontWeight: 'bold', textAlign: 'center' }}>
                                    ● RECORDING
                                </div>
                            )}
                        </div>
                        <canvas ref={canvasRef} style={{ display: 'none' }} />
                    </div>
                )}
            </div>
        </div>
    );
}
