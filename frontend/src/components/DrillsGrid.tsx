import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import axios from 'axios';
import TestConfigPanel from './TestConfigPanel';
import { API_BASE, getMediaUrl } from '../config';

// Audio cell renderer
const AudioCellRenderer = (props: any) => {
    const { value, data } = props;
    const [recording, setRecording] = useState(false);
    const [playing, setPlaying] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => chunksRef.current.push(e.data);
            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('file', blob, `audio_${data.id}_${Date.now()}.webm`);

                try {
                    const res = await axios.post(`${API_BASE}/upload-media/${data.id}/audio`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                    props.api.applyTransaction({ update: [{ ...data, audio_url: res.data.url }] });
                } catch (err) {
                    console.error('Audio upload failed:', err);
                }

                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorderRef.current.start();
            setRecording(true);
        } catch (err) {
            console.error('Microphone access denied or failed:', err);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current) {
            mediaRecorderRef.current.stop();
            setRecording(false);
        }
    };

    const togglePlayPause = () => {
        if (audioRef.current) {
            if (playing) {
                audioRef.current.pause();
                setPlaying(false);
            } else {
                audioRef.current.play();
                setPlaying(true);
            }
        }
    };

    const handleAudioEnded = () => {
        setPlaying(false);
    };

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px', width: '100%' }}>
            {value && (
                <>
                                            <audio
                                                ref={audioRef}
                                                src={getMediaUrl(value)}
                                                onEnded={handleAudioEnded}
                                                style={{ display: 'none' }}
                                            />                    <button
                        onClick={togglePlayPause}
                        style={{
                            padding: '6px 12px',
                            background: '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            fontWeight: 500,
                            minWidth: '70px'
                        }}
                    >
                        {playing ? '⏸ Pause' : '▶ Play'}
                    </button>
                </>
            )}

            {recording ? (
                <button
                    onClick={stopRecording}
                    style={{
                        padding: '6px 12px',
                        background: '#ff4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 500,
                        minWidth: '70px'
                    }}
                >
                    ⏹ Stop
                </button>
            ) : (
                <button
                    onClick={startRecording}
                    style={{
                        padding: '6px 12px',
                        background: value ? '#2196F3' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 500,
                        minWidth: '70px'
                    }}
                >
                    {value ? '🔄 Re-record' : '● Record'}
                </button>
            )}
        </div>
    );
};

// Video cell renderer
const VideoCellRenderer = (props: any) => {
    const { value, data } = props;
    const [recording, setRecording] = useState(false);
    const [playing, setPlaying] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [showPlayback, setShowPlayback] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    // const videoRef = useRef<HTMLVideoElement | null>(null); // Unused
    const previewRef = useRef<HTMLVideoElement | null>(null);
    const playbackRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // Setup preview stream when modal opens
    useEffect(() => {
        if (showPreview && streamRef.current && previewRef.current) {
            console.log('🎬 useEffect: Setting up preview stream');
            previewRef.current.srcObject = streamRef.current;
            previewRef.current.play()
                .then(() => console.log('✅ Preview playing'))
                .catch(err => console.error('❌ Preview play failed:', err));
        }
    }, [showPreview]);

    const startRecording = async () => {
        console.log('🎥 Starting video recording for drill ID:', data.id);
        console.log('📍 Current value:', value);
        console.log('📍 Current recording state:', recording);
        console.log('📍 Current showPreview state:', showPreview);

        try {
            console.log('📷 Requesting camera access...');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
                audio: true
            });
            console.log('✅ Camera access granted, stream:', stream);
            console.log('📹 Video tracks:', stream.getVideoTracks());
            console.log('🎤 Audio tracks:', stream.getAudioTracks());
            streamRef.current = stream;

            // Show preview (useEffect will handle setting up the stream)
            console.log('🔄 Setting showPreview to true (useEffect will setup stream)');
            setShowPreview(true);

            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => {
                console.log(`📦 Data chunk received: ${e.data.size} bytes`);
                chunksRef.current.push(e.data);
            };

            mediaRecorderRef.current.onstop = async () => {
                console.log('⏹ Recording stopped');
                const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                console.log(`📹 Video blob created: ${blob.size} bytes`);

                const formData = new FormData();
                formData.append('file', blob, `video_${data.id}_${Date.now()}.webm`);

                try {
                    console.log('⬆️ Uploading video...');
                    const res = await axios.post(`${API_BASE}/upload-media/${data.id}/video`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                    console.log('✅ Upload successful:', res.data);
                    props.api.applyTransaction({ update: [{ ...data, video_url: res.data.url }] });
                } catch (err) {
                    console.error('❌ Video upload failed:', err);
                    alert('Video upload failed. Check console for details.');
                }

                // Stop preview
                if (previewRef.current) {
                    previewRef.current.srcObject = null;
                }
                setShowPreview(false);

                stream.getTracks().forEach(track => {
                    track.stop();
                    console.log(`🛑 Stopped track: ${track.kind}`);
                });
                streamRef.current = null;
            };

            mediaRecorderRef.current.start();
            setRecording(true);
            console.log('🔴 Recording started');
        } catch (err) {
            console.error('❌ Camera access denied or failed:', err);
            alert('Camera access denied. Please allow camera permissions.');
        }
    };

    const stopRecording = () => {
        console.log('🛑 Stopping recording...');
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            setRecording(false);
        }
    };

    const openPlayback = () => {
        console.log('▶️ Opening video playback for drill:', data.id);
        console.log('📹 Video URL:', value);
        console.log('🌐 Full URL:', getMediaUrl(value));
        setShowPlayback(true);
        setPlaying(false);
        // Give the DOM time to render before trying to play
        setTimeout(() => {
            if (playbackRef.current) {
                console.log('✅ Playback ref exists after timeout');
                console.log('📺 Video element src:', playbackRef.current.src);
            } else {
                console.error('❌ Playback ref still null after timeout!');
            }
        }, 100);
    };

    const closePlayback = () => {
        console.log('✖️ Closing playback');
        if (playbackRef.current) {
            playbackRef.current.pause();
        }
        setShowPlayback(false);
        setPlaying(false);
    };

    const togglePlayPause = () => {
        if (playbackRef.current) {
            if (playing) {
                console.log('⏸ Pausing video');
                playbackRef.current.pause();
                setPlaying(false);
            } else {
                console.log('▶️ Playing video');
                playbackRef.current.play();
                setPlaying(true);
            }
        }
    };

    const handleVideoEnded = () => {
        console.log('✅ Video ended');
        setPlaying(false);
    };

    // Debug render
    if (showPreview || showPlayback) {
        console.log(`🎬 Rendering modal for drill ${data.id}:`, { showPreview, showPlayback, recording, playing });
    }

    // Render modals using Portal to escape AG Grid's stacking context
    const previewModal = showPreview && recording && createPortal(
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
        }}>
                    <div style={{
                        background: 'white',
                        padding: '20px',
                        borderRadius: '12px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        maxWidth: '95vw',
                        maxHeight: '95vh',
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        <h3 style={{ margin: '0 0 15px 0', textAlign: 'center', color: '#333' }}>
                            {recording ? '🔴 Recording...' : 'Camera Preview'}
                        </h3>
                        <video
                            ref={previewRef}
                            autoPlay
                            muted
                            style={{
                                width: '640px',
                                height: '480px',
                                maxWidth: '90vw',
                                maxHeight: '70vh',
                                backgroundColor: '#000',
                                borderRadius: '8px',
                                display: 'block',
                                objectFit: 'contain'
                            }}
                        />
                        <div style={{ marginTop: '15px', textAlign: 'center' }}>
                            <button
                                onClick={stopRecording}
                                style={{
                                    padding: '12px 30px',
                                    background: '#ff4444',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    fontSize: '16px',
                                    fontWeight: 600
                                }}
                            >
                                ⏹ Stop Recording
                            </button>
                        </div>
                    </div>
                </div>,
        document.body
    );

    const playbackModal = showPlayback && value && !recording && createPortal(
        <div onClick={() => {
            console.log('🖱️ Modal background clicked');
        }} style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
        }}>
                    <div style={{
                        background: 'white',
                        padding: '20px',
                        borderRadius: '12px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        maxWidth: '90vw'
                    }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '15px'
                        }}>
                            <h3 style={{ margin: 0, color: '#333' }}>Video Playback</h3>
                            <button
                                onClick={closePlayback}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    fontSize: '24px',
                                    cursor: 'pointer',
                                    padding: '0 10px'
                                }}
                            >
                                ✕
                            </button>
                        </div>
                        <video
                            ref={playbackRef}
                            src={getMediaUrl(value)}
                            controls
                            onEnded={handleVideoEnded}
                            style={{
                                width: '640px',
                                height: '480px',
                                maxWidth: '90vw',
                                maxHeight: '70vh',
                                backgroundColor: '#000',
                                borderRadius: '8px',
                                display: 'block',
                                objectFit: 'contain'
                            }}
                        />
                        <div style={{ marginTop: '15px', textAlign: 'center', display: 'flex', gap: '10px', justifyContent: 'center' }}>
                            <button
                                onClick={togglePlayPause}
                                style={{
                                    padding: '10px 24px',
                                    background: '#4CAF50',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    fontSize: '15px',
                                    fontWeight: 600
                                }}
                            >
                                {playing ? '⏸ Pause' : '▶ Play'}
                            </button>
                            <button
                                onClick={closePlayback}
                                style={{
                                    padding: '10px 24px',
                                    background: '#666',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    fontSize: '15px',
                                    fontWeight: 600
                                }}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>,
        document.body
    );

    return (
        <>
            {/* Render modals via Portal */}
            {previewModal}
            {playbackModal}

            {/* Control Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px', width: '100%' }}>
                {value && !recording && (
                    <button
                        onClick={openPlayback}
                        style={{
                            padding: '6px 12px',
                            background: '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            fontWeight: 500,
                            minWidth: '70px'
                        }}
                    >
                        ▶ Play
                    </button>
                )}

                {!recording && (
                    <button
                        onClick={startRecording}
                        style={{
                            padding: '6px 12px',
                            background: value ? '#2196F3' : '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            fontWeight: 500,
                            minWidth: '70px'
                        }}
                    >
                        {value ? '🔄 Re-record' : '🎥 Record'}
                    </button>
                )}
            </div>
        </>
    );
};

// Image cell renderer
const ImageCellRenderer = (props: any) => {
    const { value, data, api } = props;
    const [generating, setGenerating] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [_error, setError] = useState<string | null>(null);

    const generate = async () => {
        console.log('🖼️ Generating image for drill:', data.id);
        console.log('📝 Catalan text:', data.text_catalan);

        if (!data.text_catalan) {
            alert('Please add Catalan text before generating an image!');
            return;
        }

        // Prompt user to edit the search phrase
        const defaultSearch = data.text_catalan;
        const searchPhrase = prompt(
            `🔍 Edit search phrase for image:\n\n(The Catalan text will be auto-translated to English, but you can customize it here)`,
            defaultSearch
        );

        // User cancelled
        if (searchPhrase === null) {
            console.log('❌ Image generation cancelled by user');
            return;
        }

        // User entered empty string
        if (!searchPhrase.trim()) {
            alert('Search phrase cannot be empty!');
            return;
        }

        console.log('🔍 Custom search phrase:', searchPhrase);
        setGenerating(true);
        setError(null);

        try {
            console.log('⬆️ Sending generate request...');
            const res = await axios.post(`${API_BASE}/generate-image/${data.id}`, {
                search_query: searchPhrase.trim()
            });
            console.log('✅ Image generated:', res.data);
            api.applyTransaction({ update: [{ ...data, image_url: res.data.image_url }] });
        } catch (err: any) {
            console.error('❌ Image generation failed:', err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to generate image';
            setError(errorMsg);
            alert(`Image generation failed: ${errorMsg}`);
        } finally {
            setGenerating(false);
        }
    };

    const openPreview = () => {
        console.log('🖼️ Opening image preview');
        setShowPreview(true);
    };

    const closePreview = () => {
        setShowPreview(false);
    };

    // Image preview modal
    const previewModal = showPreview && value && createPortal(
        <div
            onClick={closePreview}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10000,
                cursor: 'pointer'
            }}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                style={{
                    background: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                    maxWidth: '90vw',
                    maxHeight: '90vh',
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '15px'
                }}>
                    <h3 style={{ margin: 0, color: '#333' }}>Generated Image</h3>
                    <button
                        onClick={closePreview}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            fontSize: '24px',
                            cursor: 'pointer',
                            padding: '0 10px'
                        }}
                    >
                        ✕
                    </button>
                </div>
                <img
                    src={getMediaUrl(value)}
                    alt="Generated"
                    style={{
                        maxWidth: '800px',
                        maxHeight: '600px',
                        width: '100%',
                        objectFit: 'contain',
                        borderRadius: '8px'
                    }}
                />
                <div style={{ marginTop: '15px', textAlign: 'center' }}>
                    <button
                        onClick={closePreview}
                        style={{
                            padding: '10px 24px',
                            background: '#666',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '15px',
                            fontWeight: 600
                        }}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );

    return (
        <>
            {previewModal}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px' }}>
                {value && (
                    <img
                        src={getMediaUrl(value)}
                        alt="Generated"
                        onClick={openPreview}
                        style={{
                            maxHeight: '64px',
                            maxWidth: '80px',
                            objectFit: 'contain',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            border: '1px solid #ddd'
                        }}
                        title="Click to view full size"
                    />
                )}
                <button
                    onClick={generate}
                    disabled={generating || !data.text_catalan}
                    style={{
                        padding: '6px 12px',
                        background: generating ? '#999' : (value ? '#2196F3' : '#4CAF50'),
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: generating ? 'not-allowed' : 'pointer',
                        fontSize: '13px',
                        fontWeight: 500,
                        minWidth: '70px',
                        opacity: !data.text_catalan ? 0.5 : 1
                    }}
                    title={!data.text_catalan ? 'Add Catalan text first' : ''}
                >
                    {generating ? '⏳ ...' : (value ? '🔄 Regenerate' : '🎨 Generate')}
                </button>
            </div>
        </>
    );
};

export default function DrillsGrid({ onViewTests, onViewShorts }: { onViewTests?: () => void; onViewShorts?: () => void }) {
    const [rowData, setRowData] = useState<any[]>([]);
    const [selectedDrillIds, setSelectedDrillIds] = useState<number[]>([]);
    const [showTestConfig, setShowTestConfig] = useState(false);
    const gridRef = useRef<any>(null);

    const DeleteCellRenderer = (props: any) => {
        const handleDelete = async () => {
            if (!confirm(`Delete drill #${props.data.id}?`)) return;

            try {
                await axios.delete(`${API_BASE}/drills/${props.data.id}`);
                const response = await axios.get(`${API_BASE}/drills/`);
                const sorted = [...(response.data || [])].sort((a, b) =>
                    new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
                );
                setRowData(sorted);
            } catch (error) {
                console.error('Error deleting drill:', error);
                alert('Failed to delete drill');
            }
        };

        return (
            <button
                onClick={handleDelete}
                style={{
                    padding: '4px 8px',
                    background: '#ff4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 600,
                }}
            >
                Delete
            </button>
        );
    };

    const [columnDefs] = useState([
        {
            field: 'select',
            headerName: '',
            width: 50,
            checkboxSelection: true,
            headerCheckboxSelection: true,
            editable: false,
            filter: false,
            sortable: false,
        },
        { field: 'id', width: 70, editable: false },
        {
            field: 'date_created',
            headerName: 'Created',
            width: 100,
            valueFormatter: (p: any) => new Date(p.value).toLocaleDateString('es-ES')
        },
        { field: 'tag', headerName: 'Tag', width: 120, editable: true },
        {
            field: 'text_catalan',
            headerName: 'Català',
            width: 200,
            editable: true,
            cellStyle: { fontSize: '15px' } as any
        },
        {
            field: 'text_tachelhit',
            headerName: 'Tachelhit',
            width: 200,
            editable: true,
            cellStyle: { fontSize: '15px' } as any
        },
        {
            field: 'text_arabic',
            headerName: 'العربية',
            width: 200,
            editable: true,
            cellStyle: { fontSize: '15px', direction: 'rtl' } as any
        },
        {
            field: 'audio_url',
            headerName: 'Audio',
            width: 160,
            cellRenderer: AudioCellRenderer,
            editable: false,
        },
        {
            field: 'video_url',
            headerName: 'Video',
            width: 160,
            cellRenderer: VideoCellRenderer,
            editable: false,
        },
        {
            field: 'image_url',
            headerName: 'Image',
            width: 160,
            cellRenderer: ImageCellRenderer,
            editable: false,
        },
        {
            field: 'delete',
            headerName: '',
            width: 90,
            cellRenderer: DeleteCellRenderer,
            editable: false,
            filter: false,
            sortable: false,
        },
    ]);

    useEffect(() => {
        const fetchDrills = async () => {
            try {
                const response = await axios.get(`${API_BASE}/drills/`);
                console.log("Datos recibidos del backend:", response.data);
                console.log("Número de filas:", response.data?.length || 0);

                const sorted = [...(response.data || [])].sort((a, b) =>
                    new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
                );
                setRowData(sorted);
                console.log("RowData actualizado con:", sorted.length, "filas");
            } catch (error) {
                console.error("Error al cargar drills:", error);
            }
        };

        fetchDrills();

        //const interval = setInterval(fetchDrills, 15000);
        //return () => clearInterval(interval);
    }, []);

    const onCellValueChanged = async (params: any) => {
        if (!params.data?.id) return;
        const field = params.colDef.field;
        const newValue = params.newValue;

        try {
            await axios.put(`${API_BASE}/drills/${params.data.id}`, { [field]: newValue });
        } catch (err) {
            console.error('Update failed:', err);
        }
    };

    const addNewRow = async () => {
        try {
            // Create empty drill on backend, which returns the newly created drill
            const response = await axios.post(`${API_BASE}/drills/`, {});
            const newDrill = response.data; // Get the newly created drill from the response

            // Add the new drill to the grid using applyTransaction
            // This is more efficient and less prone to re-render issues than setRowData
            if (gridRef.current && gridRef.current.api) {
                // AG Grid expects an array of rows for add
                gridRef.current.api.applyTransaction({ add: [newDrill] });
                // Optionally, ensure the new row is visible
                gridRef.current.api.ensureIndexVisible(0, 'top'); // Assuming new drill is added at top after sort
            } else {
                // Fallback if grid API is not ready (shouldn't happen often)
                console.warn("AG Grid API not ready, falling back to full data refresh.");
                const allDrillsResponse = await axios.get(`${API_BASE}/drills/`);
                const sorted = [...(allDrillsResponse.data || [])].sort((a, b) =>
                    new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
                );
                setRowData(sorted);
            }
        } catch (error) {
            console.error("Error creating drill:", error);
            alert("No se pudo crear el nuevo ejercicio.");
        }
    };

    const onSelectionChanged = () => {
        if (!gridRef.current) return;
        const selectedNodes = gridRef.current.api.getSelectedNodes();
        const selectedIds = selectedNodes.map((node: any) => node.data.id);
        setSelectedDrillIds(selectedIds);
    };

    const handleCreateTest = () => {
        if (selectedDrillIds.length === 0) {
            alert('Please select at least one drill to create a test');
            return;
        }
        setShowTestConfig(true);
    };

    const handleTestCreated = (testId: number) => {
        console.log('Test created with ID:', testId);
        setSelectedDrillIds([]);
        if (gridRef.current) {
            gridRef.current.api.deselectAll();
        }
    };

    return (
        <div style={{
            height: '100vh',
            width: '100%',
            display: 'flex',
            flexDirection: 'column'
        }}>
            <div style={{
                padding: '16px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderBottom: '2px solid #5a67d8',
                display: 'flex',
                alignItems: 'center',
                gap: '16px'
            }}>
                <h1 style={{
                    margin: 0,
                    fontSize: '24px',
                    fontWeight: 700,
                    color: 'white',
                    letterSpacing: '0.5px'
                }}>
                    Tachelhit Language Drills
                </h1>
                <button
                    onClick={addNewRow}
                    style={{
                        padding: '10px 20px',
                        fontSize: '15px',
                        background: 'white',
                        color: '#667eea',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: 600,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                        transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                >
                    + New Drill
                </button>

                <button
                    onClick={handleCreateTest}
                    style={{
                        padding: '10px 20px',
                        fontSize: '15px',
                        background: selectedDrillIds.length > 0 ? '#FFD700' : '#e0e0e0',
                        color: selectedDrillIds.length > 0 ? '#333' : '#999',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                        fontWeight: 600,
                        boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                        transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                        if (selectedDrillIds.length > 0) {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                        }
                    }}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                    disabled={selectedDrillIds.length === 0}
                >
                    📝 Create Test ({selectedDrillIds.length})
                </button>

                <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px' }}>
                    {onViewTests && (
                        <button
                            onClick={onViewTests}
                            style={{
                                padding: '10px 20px',
                                fontSize: '15px',
                                background: 'white',
                                color: '#667eea',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                        >
                            📊 View Tests
                        </button>
                    )}
                    {onViewShorts && (
                        <button
                            onClick={onViewShorts}
                            style={{
                                padding: '10px 20px',
                                fontSize: '15px',
                                background: 'white',
                                color: '#FF0080',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                        >
                            📱 YouTube Shorts
                        </button>
                    )}
                </div>
            </div>

            <div
                className="ag-theme-alpine"
                style={{
                    flex: 1,
                    width: '100%'
                }}
            >
                <AgGridReact
                    ref={gridRef}
                    rowData={rowData}
                    columnDefs={columnDefs}
                    defaultColDef={{
                        editable: true,
                        sortable: true,
                        filter: true,
                        resizable: true,
                        minWidth: 100,
                        wrapText: true,
                        autoHeight: true,
                        cellStyle: { fontSize: '14px', lineHeight: '1.5' }
                    }}
                    getRowId={(params) => params.data.id.toString()}
                    onCellValueChanged={onCellValueChanged}
                    onSelectionChanged={onSelectionChanged}
                    animateRows={true}
                    undoRedoCellEditing={true}
                    rowSelection="multiple"
                    suppressHorizontalScroll={false}
                    rowHeight={60}
                />
            </div>

            {/* Test Configuration Panel */}
            {showTestConfig && (
                <TestConfigPanel
                    selectedDrillIds={selectedDrillIds}
                    onClose={() => setShowTestConfig(false)}
                    onTestCreated={handleTestCreated}
                />
            )}
        </div>
    );
}