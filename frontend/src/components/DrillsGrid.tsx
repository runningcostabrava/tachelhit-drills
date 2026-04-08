
import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { useNavigate } from 'react-router-dom'; // Import useNavigate only

import ImageGenerationModal from './ImageGenerationModal';
import VoiceDrillCreator from './VoiceDrillCreator';
import axios from 'axios';
import TestConfigPanel from './TestConfigPanel';
import { API_BASE, getMediaUrl } from '../config';
import DrillCard from './DrillCard';
import { offlineManager } from '../utils/offlineCache';
import { isYouTubeUrl, getYouTubeVideoId } from '../utils/youtubeUtils';

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
                        // Fix: Ensure we aren't double-encoding the URL if getMediaUrl is already absolute
                        src={value.startsWith('http') ? value : getMediaUrl(value)}
                        onEnded={handleAudioEnded}
                        style={{ display: 'none' }}
                        preload="auto"
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
    const ytPlayerRef = useRef<any>(null);
    const ytPlayerReadyRef = useRef(false);


    // Helper function to format time in seconds to MM:SS format
    const formatTime = (seconds: number) => {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

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
        
        // Non-YouTube video check
        if (!isYouTubeUrl(value)) {
            setTimeout(() => {
                if (playbackRef.current) {
                    console.log('✅ Playback ref exists after timeout');
                    console.log('📺 Video element src:', playbackRef.current.src);
                } else {
                    console.warn('⚠️ Playback ref still null after timeout');
                }
            }, 100);
        }
    };

    // Consolidated YouTube initialization and player creation
    useEffect(() => {
        if (showPlayback && isYouTubeUrl(value)) {
            console.log('🎬 Initializing YouTube Player');
            
            // Fix: Use the imported utility instead of (window as any)
            const videoId = getYouTubeVideoId(value); 
            if (!videoId) return;

            const initPlayer = () => {
                const elementId = `yt-player-${data.id}`;
                
                // Fix: Slight delay to ensure the Portal has injected the element into the DOM
                setTimeout(() => {
                    const targetDiv = document.getElementById(elementId);
                    if (!targetDiv) {
                        console.warn("⚠️ Player target DIV not found yet. Retrying...");
                        return;
                    }

                    if (ytPlayerRef.current) {
                        try { ytPlayerRef.current.destroy(); } catch (e) {}
                    }

                    console.log('📺 Creating new YT Player instance');
                    ytPlayerRef.current = new (window as any).YT.Player(elementId, {
                        videoId: videoId,
                        playerVars: {
                            autoplay: 1,
                            controls: 1,
                            start: Math.floor(data.video_start_time || 0),
                            end: Math.ceil(data.video_end_time || 0)
                        },
                        events: {
                            onReady: () => {
                                console.log('✅ YT Player Ready');
                                ytPlayerReadyRef.current = true;
                                setPlaying(true);
                            },
                            onStateChange: (event: any) => {
                                if (event.data === (window as any).YT.PlayerState.ENDED) {
                                    console.log('🔄 YT Player Ended - Looping');
                                    event.target.seekTo(data.video_start_time || 0);
                                    event.target.playVideo();
                                }
                                if (event.data === (window as any).YT.PlayerState.PLAYING) setPlaying(true);
                                if (event.data === (window as any).YT.PlayerState.PAUSED) setPlaying(false);
                            },
                            onError: (e: any) => console.error('❌ YT Player Error:', e)
                        }
                    });
                }, 50); // Small buffer for the Portal
            };

            if (!(window as any).YT || !(window as any).YT.Player) {
                console.log('📦 Loading YouTube IFrame API');
                if (!document.getElementById('youtube-iframe-api')) {
                    const tag = document.createElement('script');
                    tag.id = 'youtube-iframe-api';
                    tag.src = "https://www.youtube.com/iframe_api";
                    const firstScriptTag = document.getElementsByTagName('script')[0];
                    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);
                }
                
                const prevOnReady = (window as any).onYouTubeIframeAPIReady;
                (window as any).onYouTubeIframeAPIReady = () => {
                    if (prevOnReady) prevOnReady();
                    initPlayer();
                };
            } else {
                initPlayer();
            }
        }

        return () => {
            if (ytPlayerRef.current) {
                console.log('🧹 Cleaning up YT Player');
                try { ytPlayerRef.current.destroy(); } catch (e) {}
                ytPlayerRef.current = null;
                ytPlayerReadyRef.current = false;
            }
        };
    }, [showPlayback, value, data.id, data.video_start_time, data.video_end_time]);

    const closePlayback = () => {
        console.log('✖️ Closing playback');
        if (playbackRef.current && !isYouTubeUrl(value)) {
            playbackRef.current.pause();
        }
        if (ytPlayerRef.current) {
            try { ytPlayerRef.current.pauseVideo(); } catch (e) {}
        }
        setShowPlayback(false);
        setPlaying(false);
    };

    const togglePlayPause = () => {
        if (isYouTubeUrl(value)) {
            if (ytPlayerRef.current && ytPlayerReadyRef.current) {
                if (playing) {
                    ytPlayerRef.current.pauseVideo();
                } else {
                    ytPlayerRef.current.playVideo();
                }
            }
        } else if (playbackRef.current) {
            if (playing) {
                playbackRef.current.pause();
                setPlaying(false);
            } else {
                playbackRef.current.play();
                setPlaying(true);
            }
        }
    };

    const goBack2Seconds = () => {
        if (isYouTubeUrl(value)) {
            if (ytPlayerRef.current && ytPlayerReadyRef.current) {
                const currentTime = ytPlayerRef.current.getCurrentTime();
                const startTime = data.video_start_time || 0;
                ytPlayerRef.current.seekTo(Math.max(startTime, currentTime - 2));
            }
        } else if (playbackRef.current) {
            playbackRef.current.currentTime = Math.max(0, playbackRef.current.currentTime - 2);
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
        <div onClick={(e) => {
            e.stopPropagation(); // Stops the grid from reacting to the click
            closePlayback();
        }} 
        style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
        }}>
            <div onClick={(e) => e.stopPropagation()} style={{
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
                
                {/* Video container with subtitle overlay */}
                <div style={{ position: 'relative', width: '800px', maxWidth: '90vw' }}>
                    {isYouTubeUrl(value) ? (
                        // YouTube Player
                        <div
                            id={`yt-player-${data.id}`}
                            style={{
                                width: '100%',
                                height: '600px',
                                maxHeight: '70vh',
                                backgroundColor: '#000',
                                borderRadius: '8px',
                                display: 'block',
                                border: 'none'
                            }}
                        />
                    ) : (
                        // Regular video
                        <video
                            ref={playbackRef}
                            src={getMediaUrl(value)}
                            controls
                            onEnded={handleVideoEnded}
                            style={{
                                width: '100%',
                                height: '600px',
                                maxHeight: '70vh',
                                backgroundColor: '#000',
                                borderRadius: '8px',
                                display: 'block',
                                objectFit: 'contain'
                            }}
                        />
                    )}
                    
                    {/* Subtitle overlay */}
                    {(data.text_catalan || data.text_tachelhit || data.text_arabic) && (
                        <div style={{
                            position: 'absolute',
                            bottom: '20px',
                            left: '0',
                            right: '0',
                            padding: '10px 20px',
                            backgroundColor: 'rgba(0, 0, 0, 0.7)',
                            color: 'white',
                            textAlign: 'center',
                            borderRadius: '0 0 8px 8px',
                            backdropFilter: 'blur(4px)',
                            zIndex: 10
                        }}>
                            {/* Arabic subtitle - first, prominent */}
                            {data.text_arabic && (
                                <div style={{
                                    fontSize: '20px',
                                    direction: 'rtl',
                                    fontWeight: 'bold',
                                    marginBottom: data.text_catalan || data.text_tachelhit ? '8px' : '0',
                                    color: '#9C27B0'
                                }}>
                                    {data.text_arabic}
                                </div>
                            )}
                            
                            {/* Tachelhit subtitle */}
                            {data.text_tachelhit && (
                                <div style={{
                                    fontSize: '18px',
                                    fontWeight: 'bold',
                                    marginBottom: data.text_catalan ? '5px' : '0',
                                    color: '#FFD700'
                                }}>
                                    {data.text_tachelhit}
                                </div>
                            )}
                            
                            {/* Catalan subtitle - smaller, underneath */}
                            {data.text_catalan && (
                                <div style={{
                                    fontSize: '16px',
                                    marginBottom: '0',
                                    color: '#4CAF50',
                                    opacity: 0.9
                                }}>
                                    {data.text_catalan}
                                </div>
                            )}
                        </div>
                    )}
                </div>
                
                {/* Video info */}
                <div style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                        <strong>Drill ID:</strong> {data.id}
                        {data.video_start_time && (
                            <span style={{ marginLeft: '15px' }}>
                                <strong>Start time:</strong> {formatTime(data.video_start_time)}
                            </span>
                        )}
                        {data.video_end_time && (
                            <span style={{ marginLeft: '15px' }}>
                                <strong>End time:</strong> {formatTime(data.video_end_time)}
                            </span>
                        )}
                    </div>
                </div>
                
                <div style={{ marginTop: '15px', textAlign: 'center', display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    <button
                        onClick={goBack2Seconds}
                        style={{
                            padding: '10px 24px',
                            background: '#2196F3',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '15px',
                            fontWeight: 600
                        }}
                        title="Go back 2 seconds"
                    >
                        ↺ 2s
                    </button>
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
// Image cell renderer
const ImageCellRenderer = (props: any) => {
    const { value, data, api } = props;
    const [generating, setGenerating] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [_error, setError] = useState<string | null>(null);
    const [showImageGenModal, setShowImageGenModal] = useState(false); // State to control modal visibility

    // This function now handles the actual API call based on modal input
    const handleGenerateImage = async (searchQuery: string, useAi: boolean) => {
        console.log('🖼️ Generating image for drill:', data.id);
        console.log('📝 Catalan text:', data.text_catalan);
        console.log('🔍 Search Phrase:', searchQuery);
        console.log('🤖 Use AI Generation:', useAi);

        setGenerating(true);
        setError(null);

        try {
            console.log('⬆️ Sending generate request...');
            const res = await axios.post(`${API_BASE}/generate-image/${data.id}`, {
                search_query: searchQuery,
                use_ai: useAi // Pass the user's choice to the backend
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

    const openGenerateModal = () => {
        if (!data.text_catalan) {
            alert('Please add Catalan text before generating an image!');
            return;
        }
        setShowImageGenModal(true);
    };

    const closeGenerateModal = () => {
        setShowImageGenModal(false);
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
                    onClick={openGenerateModal} // Call to open modal
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
            {createPortal( // Render modal via Portal to escape AG Grid's stacking context
                <ImageGenerationModal
                    isOpen={showImageGenModal}
                    onClose={closeGenerateModal}
                    onGenerate={handleGenerateImage}
                    defaultSearchQuery={data.text_catalan || ''}
                />,
                document.body
            )}
        </>
    );
};

const GlossaryModal = ({ onClose }: { onClose: () => void }) => {
    const [rowData, setRowData] = useState<any[]>([]);
    const [newWord, setNewWord] = useState({ sound: '', spelling: '' });

    const fetchGlossary = async () => {
        const res = await axios.get(`${API_BASE}/glossary/`);
        setRowData(res.data);
    };

    useEffect(() => { fetchGlossary(); }, []);

    const handleAdd = async () => {
        if (!newWord.sound || !newWord.spelling) return;
        await axios.post(`${API_BASE}/glossary/`, { word_sound: newWord.sound, correct_spelling: newWord.spelling });
        setNewWord({ sound: '', spelling: '' });
        fetchGlossary();
    };

    const handleDelete = async (id: number) => {
        await axios.delete(`${API_BASE}/glossary/${id}`);
        fetchGlossary();
    };

    const columnDefs: any[] = [
        { field: 'word_sound', headerName: 'Sound', flex: 1 },
        { field: 'correct_spelling', headerName: 'Spelling', flex: 1 },
        {
            field: 'id',
            headerName: '',
            width: 100,
            cellRenderer: (p: any) => (
                <button
                    onClick={() => handleDelete(p.value)}
                    style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    Delete
                </button>
            )
        }
    ];

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ background: 'white', padding: '20px', borderRadius: '12px', width: '600px', maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ marginTop: 0 }}>📖 Personal Dictionary (AI Learning)</h3>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                    <input placeholder="Sound (e.g. anayr)" value={newWord.sound} onChange={e => setNewWord({ ...newWord, sound: e.target.value })} style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <input placeholder="Correct Spelling" value={newWord.spelling} onChange={e => setNewWord({ ...newWord, spelling: e.target.value })} style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <button onClick={handleAdd} style={{ padding: '8px 16px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Add</button>
                </div>
                <div className="ag-theme-alpine" style={{ flex: 1, width: '100%' }}>
                    <AgGridReact
                        rowData={rowData}
                        columnDefs={columnDefs}
                        theme="legacy"
                    />
                </div>
                <button onClick={onClose} style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', border: '1px solid #ccc', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>Close</button>
            </div>
        </div>
    );
};

// Translate cell renderer
const TranslateCellRenderer = (props: any) => {
    const { data, api } = props;
    const [translating, setTranslating] = useState(false);

    const handleTranslate = async (source: string, target: string) => {
        const text = source === 'ca' ? data.text_catalan : data.text_tachelhit;
        if (!text) {
            alert(`Please enter ${source === 'ca' ? 'Catalan' : 'Tachelhit'} text first.`);
            return;
        }

        setTranslating(true);
        try {
            const res = await axios.post(`${API_BASE}/translate`, {
                text: text,
                source_lang: source,
                target_lang: target
            });
            const field = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
            const newText = data[field] ? `${data[field]} (${res.data.translated_text})` : res.data.translated_text;
            api.applyTransaction({ update: [{ ...data, [field]: newText }] });
            // Also save to backend
            await axios.put(`${API_BASE}/drills/${data.id}`, { [field]: newText });
        } catch (err) {
            console.error('Translation failed:', err);
            alert('Translation failed. Check console.');
        } finally {
            setTranslating(false);
        }
    };

    return (
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '100%' }}>
            <button
                onClick={() => handleTranslate('ca', 'shi')}
                disabled={translating || !data.text_catalan}
                style={{
                    padding: '4px 8px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: translating ? 'not-allowed' : 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                    opacity: !data.text_catalan ? 0.5 : 1
                }}
                title="Translate Catalan to Tachelhit"
            >
                {translating ? '...' : 'CA→SHI'}
            </button>
            <button
                onClick={() => handleTranslate('shi', 'ca')}
                disabled={translating || !data.text_tachelhit}
                style={{
                    padding: '4px 8px',
                    background: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: translating ? 'not-allowed' : 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                    opacity: !data.text_tachelhit ? 0.5 : 1
                }}
                title="Translate Tachelhit to Catalan"
            >
                {translating ? '...' : 'SHI→CA'}
            </button>
        </div>
    );
};

export default function DrillsGrid({ rowData, refreshData }: { rowData: any[]; refreshData: () => void }) {
    const [selectedDrillIds, setSelectedDrillIds] = useState<number[]>([]);
    const [showTestConfig, setShowTestConfig] = useState(false);
    const [showBulkEdit, setShowBulkEdit] = useState(false);
    const [bulkTag, setBulkTag] = useState('');
    const [bulkAuthor, setBulkAuthor] = useState('');
    const [showBulkVideoUrlUpdate, setShowBulkVideoUrlUpdate] = useState(false);
    const [bulkVideoUrl, setBulkVideoUrl] = useState('');
    const [bulkUpdateTimestamps, setBulkUpdateTimestamps] = useState(true);
    const [showVoiceCreator, setShowVoiceCreator] = useState(false);
    const [showNewDrillOptions, setShowNewDrillOptions] = useState(false); // New state for dropdown
    const [editingDrill, setEditingDrill] = useState<any>(null); // State for modal editing
    const [showGlossary, setShowGlossary] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchCategory, setSearchCategory] = useState('all'); // 'all', 'catalan', 'tachelhit', 'arabic', 'tag', 'author'
    const [isGridReady, setIsGridReady] = useState(false); // Track if grid is ready
    const gridRef = useRef<any>(null);
    const navigate = useNavigate(); // Initialize useNavigate

    // Depurar cambios en showVoiceCreator
    useEffect(() => {
        console.log('🔄 showVoiceCreator cambió a:', showVoiceCreator);
    }, [showVoiceCreator]);

    // Apply search filter when search query or category changes
    useEffect(() => {
        console.log('🔍 Search effect triggered:', { searchQuery, searchCategory, isGridReady });

        if (!isGridReady) {
            console.warn('🔍 Grid is not ready yet, skipping search');
            return;
        }

        if (!gridRef.current) {
            console.warn('🔍 gridRef.current is null');
            return;
        }

        if (!gridRef.current.api) {
            console.warn('🔍 gridRef.current.api is null');
            return;
        }

        const api = gridRef.current.api;
        console.log('🔍 AG Grid API available:', !!api);

        // Check if API methods exist
        if (typeof api.setFilterModel !== 'function') {
            console.warn('🔍 api.setFilterModel is not a function:', api.setFilterModel);
            return;
        }

        if (!searchQuery.trim()) {
            console.log('🔍 Clearing filters (empty search)');
            // Clear all filters if search is empty
            try {
                api.setFilterModel(null);
                // Try to clear quick filter if it exists
                if (typeof api.setQuickFilter === 'function') {
                    api.setQuickFilter(null);
                }
            } catch (error) {
                console.error('🔍 Error clearing filters:', error);
            }
            return;
        }

        const searchTerm = searchQuery.toLowerCase();
        console.log('🔍 Applying search:', { searchTerm, searchCategory });

        try {
            if (searchCategory === 'all') {
                // For "all" search, we need to implement OR logic across multiple fields
                // We'll use a custom approach: filter the data manually and set row data
                console.log('🔍 Implementing OR search across all fields');

                // First, get all row data
                const allRows: any[] = [];
                api.forEachNode((node: any) => {
                    allRows.push(node.data);
                });

                // Filter rows where ANY of the searchable fields contains the search term
                const filteredRows = allRows.filter(row => {
                    const fieldsToSearch = [
                        row.text_catalan?.toLowerCase() || '',
                        row.text_tachelhit?.toLowerCase() || '',
                        row.text_arabic?.toLowerCase() || '',
                        row.tag?.toLowerCase() || '',
                        row.author?.toLowerCase() || ''
                    ];

                    return fieldsToSearch.some(field => field.includes(searchTerm));
                });

                console.log(`🔍 Found ${filteredRows.length} rows matching "${searchTerm}"`);

                // Clear any existing filters
                api.setFilterModel(null);

                // Set the filtered rows
                api.setRowData(filteredRows);
            } else {
                // For specific field searches, use normal filter model
                // Clear any existing quick filter
                if (typeof api.setQuickFilter === 'function') {
                    api.setQuickFilter(null);
                }

                const filterModel: any = {};
                switch (searchCategory) {
                    case 'catalan':
                        filterModel.text_catalan = {
                            filterType: 'text',
                            type: 'contains',
                            filter: searchTerm
                        };
                        break;
                    case 'tachelhit':
                        filterModel.text_tachelhit = {
                            filterType: 'text',
                            type: 'contains',
                            filter: searchTerm
                        };
                        break;
                    case 'arabic':
                        filterModel.text_arabic = {
                            filterType: 'text',
                            type: 'contains',
                            filter: searchTerm
                        };
                        break;
                    case 'tag':
                        filterModel.tag = {
                            filterType: 'text',
                            type: 'contains',
                            filter: searchTerm
                        };
                        break;
                    case 'author':
                        filterModel.author = {
                            filterType: 'text',
                            type: 'contains',
                            filter: searchTerm
                        };
                        break;
                }
                console.log('🔍 Setting filter model:', filterModel);
                api.setFilterModel(filterModel);
            }
            console.log('🔍 Search applied successfully');
        } catch (error) {
            console.error('🔍 Error applying search filter:', error);
        }
    }, [searchQuery, searchCategory, isGridReady]);

    const CopyCellRenderer = (props: any) => {
        const handleCopy = async () => {
            if (!confirm(`Copy drill #${props.data.id}? This will create a new drill with the same content.`)) return;

            try {
                // Prepare the drill data to copy
                const drillToCopy = props.data;
                const copyData = {
                    tag: drillToCopy.tag,
                    author: drillToCopy.author,
                    text_catalan: drillToCopy.text_catalan,
                    text_tachelhit: drillToCopy.text_tachelhit,
                    text_arabic: drillToCopy.text_arabic,
                    audio_url: drillToCopy.audio_url,
                    video_url: drillToCopy.video_url,
                    image_url: drillToCopy.image_url,
                };

                // Create a new drill with the same data
                const response = await axios.post(`${API_BASE}/drills/`, copyData);
                console.log('Drill copied successfully:', response.data);

                // Refresh the grid using context function
                if (props.context && props.context.refreshData) {
                    props.context.refreshData();
                } else {
                    // Fallback: reload the whole grid
                    const drillsResponse = await axios.get(`${API_BASE}/drills/`);
                    const sorted = [...(drillsResponse.data || [])].sort((a, b) =>
                        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
                    );
                    if (props.api && props.api.setRowData) {
                        props.api.setRowData(sorted);
                    }
                }

                alert(`Drill #${drillToCopy.id} copied successfully! New drill ID: ${response.data.id}`);
            } catch (error) {
                console.error('Error copying drill:', error);
                alert('Failed to copy drill');
            }
        };

        return (
            <button
                onClick={handleCopy}
                style={{
                    padding: '4px 8px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 600,
                }}
                title="Copy this drill"
            >
                Copy
            </button>
        );
    };

    const DeleteCellRenderer = (props: any) => {
        const handleDelete = async () => {
            if (!confirm(`Delete drill #${props.data.id}?`)) return;

            try {
                await axios.delete(`${API_BASE}/drills/${props.data.id}`);
                // Refresh using context
                if (props.context && props.context.refreshData) {
                    props.context.refreshData();
                } else {
                    const response = await axios.get(`${API_BASE}/drills/`);
                    const sorted = [...(response.data || [])].sort((a, b) =>
                        new Date(b.date_created).getTime() - new Date(a.date_created).getTime()
                    );
                    if (props.api && props.api.setRowData) {
                        props.api.setRowData(sorted);
                    }
                }
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
                title="Delete this drill"
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
        {
            field: 'id',
            width: 70,
            editable: false,
            cellRenderer: (params: any) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                        onClick={() => setEditingDrill(params.data)}
                        style={{
                            padding: '2px 8px',
                            background: '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '11px',
                            cursor: 'pointer'
                        }}
                    >
                        Edit
                    </button>
                    {params.value}
                </div>
            )
        },
        {
            field: 'date_created',
            headerName: 'Created',
            width: 100,
            valueFormatter: (p: any) => new Date(p.value).toLocaleDateString('es-ES')
        },
        { field: 'tag', headerName: 'Tag', width: 120, editable: true },
        {
            field: 'author',
            headerName: 'Author',
            width: 120,
            editable: true,
            cellEditor: 'agTextCellEditor',
            cellEditorParams: {
                maxLength: 100,
            },
        },
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
            headerName: 'Translate',
            width: 150,
            cellRenderer: TranslateCellRenderer,
            editable: false,
            filter: false,
            sortable: false,
        },
        {
            field: 'is_correction_dataset',
            headerName: 'Dataset',
            width: 100,
            editable: true,
            cellRenderer: (params: any) => (
                <input
                    type="checkbox"
                    checked={params.value}
                    onChange={async (e) => {
                        const val = e.target.checked;
                        try {
                            await axios.put(`${API_BASE}/drills/${params.data.id}`, { is_correction_dataset: val });
                            params.node.setDataValue('is_correction_dataset', val);
                        } catch (err) {
                            console.error('Update failed:', err);
                        }
                    }}
                    style={{ cursor: 'pointer' }}
                />
            ),
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
            field: 'copy',
            headerName: '',
            width: 70,
            cellRenderer: CopyCellRenderer,
            editable: false,
            filter: false,
            sortable: false,
        },
        {
            field: 'delete',
            headerName: '',
            width: 70,
            cellRenderer: DeleteCellRenderer,
            editable: false,
            filter: false,
            sortable: false,
        },
    ]);

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
            await axios.post(`${API_BASE}/drills/`, {});

            // Refresh the grid using the passed refreshData function
            refreshData();

            // Optionally, ensure the new row is visible (if gridRef.current exists)
            if (gridRef.current && gridRef.current.api) {
                gridRef.current.api.ensureIndexVisible(0, 'top');
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
                flexDirection: 'column',
                gap: '12px'
            }}>
                {/* Top row: Title and main buttons */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    flexWrap: 'wrap'
                }}>
                    <div>
                        <h1 style={{
                            margin: 0,
                            fontSize: '24px',
                            fontWeight: 700,
                            color: 'white',
                            letterSpacing: '0.5px'
                        }}>
                            Tachelhit Language Drills
                        </h1>
                        <h2 style={{
                            margin: '4px 0 0 0',
                            fontSize: '18px',
                            fontWeight: 600,
                            color: '#FFD700',
                            letterSpacing: '0.3px'
                        }}>
                            y10
                        </h2>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <div style={{ position: 'relative' }}>
                            <button
                                onClick={() => setShowNewDrillOptions(!showNewDrillOptions)}
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
                                + New Drill ▼
                            </button>
                            {showNewDrillOptions && (
                                <div style={{
                                    position: 'absolute',
                                    top: 'calc(100% + 10px)', // Position below the button
                                    right: 0,
                                    backgroundColor: 'white',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                    zIndex: 1000,
                                    minWidth: '220px',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    overflow: 'hidden',
                                }}>
                                    <button
                                        onClick={() => {
                                            addNewRow();
                                            setShowNewDrillOptions(false);
                                        }}
                                        style={{
                                            padding: '10px 15px',
                                            fontSize: '15px',
                                            background: 'none',
                                            border: 'none',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            color: '#333',
                                            fontWeight: 500,
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        ➕ Create Empty Drill
                                    </button>
                                    <button
                                        onClick={() => {
                                            const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
                                            if (!SpeechRecognition) {
                                                alert('Speech recognition is not supported in your browser. Please use Chrome or Edge for voice features. You can still create a drill manually.');
                                            }
                                            setShowVoiceCreator(true);
                                            setShowNewDrillOptions(false);
                                        }}
                                        style={{
                                            padding: '10px 15px',
                                            fontSize: '15px',
                                            background: 'none',
                                            border: 'none',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            color: '#333',
                                            fontWeight: 500,
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        🎤 Create Drill with Voice
                                    </button>
                                    <button
                                        onClick={() => {
                                            navigate('/video-creator');
                                            setShowNewDrillOptions(false);
                                        }}
                                        style={{
                                            padding: '10px 15px',
                                            fontSize: '15px',
                                            background: 'none',
                                            border: 'none',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            color: '#333',
                                            fontWeight: 500,
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        🎬 Create from Video (YouTube)
                                    </button>
                                </div>
                            )}
                        </div>

                        <button
                            onClick={() => setShowGlossary(true)}
                            style={{
                                padding: '10px 20px',
                                fontSize: '15px',
                                background: 'white',
                                color: '#333',
                                border: '1px solid #ccc',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.1) ',
                                transition: 'all 0.2s',
                            }}
                        >
                            📖 Glossary
                        </button>
                    </div>
                </div>

                {/* Search Box - Now more prominent and responsive */}
                <div style={{
                    width: '100%',
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center',
                    background: 'rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.2)'
                }}>
                    <div style={{ color: 'white', fontSize: '18px', flexShrink: 0 }}>🔍</div>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search drills by text, tag, author..."
                        style={{
                            flex: 1,
                            background: 'transparent',
                            border: 'none',
                            color: 'white',
                            fontSize: '16px',
                            outline: 'none',
                            minWidth: '0'
                        }}
                    />
                    <select
                        value={searchCategory}
                        onChange={(e) => setSearchCategory(e.target.value)}
                        style={{
                            background: 'rgba(255, 255, 255, 0.2)',
                            border: '1px solid rgba(255, 255, 255, 0.3)',
                            color: 'white',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            fontSize: '14px',
                            outline: 'none',
                            cursor: 'pointer',
                            flexShrink: 0
                        }}
                    >
                        <option value="all">All fields</option>
                        <option value="catalan">Català</option>
                        <option value="tachelhit">Tachelhit</option>
                        <option value="arabic">Arabic</option>
                        <option value="tag">Tag</option>
                        <option value="author">Author</option>
                    </select>
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'white',
                                fontSize: '18px',
                                cursor: 'pointer',
                                padding: '0 6px',
                                flexShrink: 0
                            }}
                            title="Clear search"
                        >
                            ✕
                        </button>
                    )}
                </div>

                {/* Action buttons row */}
                <div style={{
                    display: 'flex',
                    gap: '8px',
                    flexWrap: 'wrap',
                    justifyContent: 'center'
                }}>
                    <button
                        onClick={() => setShowBulkEdit(true)}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#9C27B0' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? 'white' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                        title="Edit Tag and Author for selected drills"
                    >
                        🏷️ Bulk Edit ({selectedDrillIds.length})
                    </button>
                    <button
                        onClick={() => setShowBulkVideoUrlUpdate(true)}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#FF5722' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? 'white' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                        title="Update video URLs for selected drills"
                    >
                        🎬 Bulk Video URL ({selectedDrillIds.length})
                    </button>
                    <button
                        onClick={handleCreateTest}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#FFD700' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? '#333' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                    >
                        📝 Create Test ({selectedDrillIds.length})
                    </button>
                    <button
                        onClick={async () => {
                            if (selectedDrillIds.length === 0) return;
                            if (!confirm(`Transcribe ${selectedDrillIds.length} drills? This will use ASR credits.`)) return;
                            for (const id of selectedDrillIds) {
                                try {
                                    const drill = rowData.find(d => d.id === id);
                                    if (!drill?.audio_url) continue;
                                    await axios.post(`${API_BASE}/transcribe/`, { audio_url: drill.audio_url });
                                } catch (err) {
                                    console.error(`Failed to transcribe ${id}:`, err);
                                }
                            }
                            alert('Bulk transcription complete');
                            refreshData();
                        }}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#667eea' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? 'white' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                    >
                        🪄 Bulk Transcribe
                    </button>

                    <button
                        onClick={async () => {
                            if (selectedDrillIds.length === 0) return;
                            const selectedDrills = rowData.filter(d => selectedDrillIds.includes(d.id));
                            if (!confirm(`Download ${selectedDrills.length} drills for offline use? This will cache all media files.`)) return;

                            try {
                                const result = await offlineManager.cacheDrillsForOffline(selectedDrills, getMediaUrl);
                                if (result.success) {
                                    alert(`✅ Successfully cached ${selectedDrills.length} drills and ${result.cachedMedia} media files for offline use!`);
                                } else {
                                    alert(`⚠️ Cached ${selectedDrills.length} drills and ${result.cachedMedia} media files, but encountered ${result.errors.length} errors. Check console for details.`);
                                }
                            } catch (error) {
                                console.error('Failed to cache drills:', error);
                                alert('❌ Failed to cache drills for offline use. Check console for details.');
                            }
                        }}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#4CAF50' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? 'white' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                        title="Download selected drills for offline use"
                    >
                        📥 Download Offline ({selectedDrillIds.length})
                    </button>

                    <button
                        onClick={async () => {
                            if (selectedDrillIds.length === 0) return;
                            if (!confirm(`⚠️ WARNING: This will permanently delete ${selectedDrillIds.length} drill(s).\n\nThis action cannot be undone. Are you sure you want to delete these drills?`)) return;
                            
                            try {
                                // Delete drills sequentially
                                for (const id of selectedDrillIds) {
                                    await axios.delete(`${API_BASE}/drills/${id}`);
                                }
                                
                                alert(`✅ Successfully deleted ${selectedDrillIds.length} drill(s).`);
                                refreshData(); // Refresh the grid
                                
                                // Clear selection
                                setSelectedDrillIds([]);
                                if (gridRef.current) {
                                    gridRef.current.api.deselectAll();
                                }
                            } catch (error) {
                                console.error('Bulk delete failed:', error);
                                alert(`❌ Failed to delete some drills. Check console for details.`);
                            }
                        }}
                        style={{
                            padding: '10px 16px',
                            fontSize: '14px',
                            background: selectedDrillIds.length > 0 ? '#ff4444' : '#e0e0e0',
                            color: selectedDrillIds.length > 0 ? 'white' : '#999',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: selectedDrillIds.length > 0 ? 'pointer' : 'not-allowed',
                            fontWeight: 600,
                            boxShadow: selectedDrillIds.length > 0 ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                            transition: 'all 0.2s',
                        }}
                        disabled={selectedDrillIds.length === 0}
                        title="Permanently delete selected drills"
                    >
                        🗑️ Bulk Delete ({selectedDrillIds.length})
                    </button>

                    <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
                        <button
                            onClick={() => {
                                const url = window.location.href;
                                navigator.clipboard.writeText(url);
                                alert(`Filtered link copied to clipboard!\n${url}`);
                            }}
                            style={{
                                padding: '10px 16px',
                                fontSize: '14px',
                                background: 'white',
                                color: '#007BFF',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                            title="Copy link to current filtered view"
                        >
                            🔗 Copy Link
                        </button>

                        <button
                            onClick={() => navigate('/tests')}
                            style={{
                                padding: '10px 16px',
                                fontSize: '14px',
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
                            📊 Tests
                        </button>
                        <button
                            onClick={() => navigate('/shorts')}
                            style={{
                                padding: '10px 16px',
                                fontSize: '14px',
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
                            📱 Shorts
                        </button>
                        <button
                            onClick={() => {
                                navigate('/demo-videos');
                            }}
                            style={{
                                padding: '10px 16px',
                                fontSize: '14px',
                                background: 'white',
                                color: '#9C27B0',
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
                            🎬 Demos
                        </button>
                        <button
                            onClick={() => navigate('/srt-import')}
                            style={{
                                padding: '10px 16px',
                                fontSize: '14px',
                                background: 'white',
                                color: '#FF5722',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                            title="Import drills from SRT subtitle files"
                        >
                            📝 Import SRT
                        </button>
                    </div>
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
                    rowData={rowData} // Use prop rowData
                    columnDefs={columnDefs}
                    theme="legacy"
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
                    onGridReady={(params: any) => {
                        console.log('✅ AG Grid is ready');
                        setIsGridReady(true);

                        // Apply filters from URL on load
                        const urlParams = new URLSearchParams(window.location.search);
                        const tag = urlParams.get('tag');
                        const author = urlParams.get('author');
                        const text = urlParams.get('text');

                        if (tag || author || text) {
                            // For OR logic (tag OR author OR text), we need to use a custom approach
                            // since AG Grid's filter model uses AND logic by default
                            const allRows: any[] = [];
                            params.api.forEachNode((node: any) => {
                                allRows.push(node.data);
                            });

                            // Filter rows where tag contains tag OR author contains author OR text contains text
                            const filteredRows = allRows.filter(row => {
                                const tagMatch = tag ? (row.tag?.toLowerCase() || '').includes(tag.toLowerCase()) : false;
                                const authorMatch = author ? (row.author?.toLowerCase() || '').includes(author.toLowerCase()) : false;
                                const textMatch = text ? (
                                    (row.text_catalan?.toLowerCase() || '').includes(text.toLowerCase()) ||
                                    (row.text_tachelhit?.toLowerCase() || '').includes(text.toLowerCase()) ||
                                    (row.text_arabic?.toLowerCase() || '').includes(text.toLowerCase())
                                ) : false;

                                // OR logic: match tag OR author OR text (if multiple provided, match any)
                                const matches = [];
                                if (tag) matches.push(tagMatch);
                                if (author) matches.push(authorMatch);
                                if (text) matches.push(textMatch);

                                // Return true if any of the provided parameters match
                                return matches.some(match => match === true);
                            });

                            console.log(`🔍 URL filter applied: tag="${tag}", author="${author}", text="${text}"`);
                            console.log(`🔍 Found ${filteredRows.length} rows matching OR logic`);

                            // Clear any existing filters
                            params.api.setFilterModel(null);

                            // Set the filtered rows
                            params.api.setRowData(filteredRows);
                        }
                    }}
                    onFilterChanged={(params: any) => {
                        // Extract filters from grid and update URL
                        const filterModel = params.api.getFilterModel();
                        const newUrl = new URL(window.location.href);

                        // Handle 'tag' filter
                        if (filterModel.tag && filterModel.tag.filter) {
                            newUrl.searchParams.set('tag', filterModel.tag.filter);
                        } else {
                            newUrl.searchParams.delete('tag');
                        }

                        // Handle 'author' filter
                        if (filterModel.author && filterModel.author.filter) {
                            newUrl.searchParams.set('author', filterModel.author.filter);
                        } else {
                            newUrl.searchParams.delete('author');
                        }

                        // Update the browser URL without reloading
                        window.history.replaceState({}, '', newUrl.toString());
                    }}
                    animateRows={true}
                    undoRedoCellEditing={true}
                    rowSelection="multiple"
                    suppressHorizontalScroll={false}
                    rowHeight={60}
                    context={{ refreshData: refreshData }} // Use prop refreshData
                />
            </div>

            {/* Test Configuration Panel */}
            {showTestConfig && (
                <TestConfigPanel
                    initialSelectedDrillIds={selectedDrillIds}
                    onClose={() => setShowTestConfig(false)}
                    onTestCreated={handleTestCreated}
                />
            )}

            {/* Bulk Edit Modal */}
            {showBulkEdit && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10000,
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '30px',
                        borderRadius: '12px',
                        width: '500px',
                        maxWidth: '90vw',
                        maxHeight: '90vh',
                        overflow: 'auto',
                    }}>
                        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>
                            Bulk Edit ({selectedDrillIds.length} drills)
                        </h2>
                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                                Tag (leave empty to keep unchanged)
                            </label>
                            <input
                                type="text"
                                value={bulkTag}
                                onChange={(e) => setBulkTag(e.target.value)}
                                placeholder="e.g., +newtag (add), -oldtag (remove), or replace"
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    fontSize: '14px',
                                    border: '1px solid #ccc',
                                    borderRadius: '6px',
                                }}
                            />
                            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                                Use prefix '+' to add, '-' to remove, or plain text to replace.
                            </div>
                        </div>
                        <div style={{ marginBottom: '25px' }}>
                            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                                Author (leave empty to keep unchanged)
                            </label>
                            <input
                                type="text"
                                value={bulkAuthor}
                                onChange={(e) => setBulkAuthor(e.target.value)}
                                placeholder="e.g., John Doe"
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    fontSize: '14px',
                                    border: '1px solid #ccc',
                                    borderRadius: '6px',
                                }}
                            />
                        </div>
                        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowBulkEdit(false);
                                    setBulkTag('');
                                    setBulkAuthor('');
                                }}
                                style={{
                                    padding: '10px 20px',
                                    fontSize: '14px',
                                    border: '1px solid #ccc',
                                    borderRadius: '6px',
                                    backgroundColor: 'white',
                                    cursor: 'pointer',
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={async () => {
                                    if (!bulkTag.trim() && !bulkAuthor.trim()) {
                                        alert('Please enter at least one field to update.');
                                        return;
                                    }
                                    try {
                                        const updates = selectedDrillIds.map(id => ({
                                            id,
                                            tag: bulkTag.trim() || undefined,
                                            author: bulkAuthor.trim() || undefined,
                                        }));
                                        // Send updates sequentially
                                        for (const update of updates) {
                                            await axios.put(`${API_BASE}/drills/${update.id}`, {
                                                tag: update.tag,
                                                author: update.author,
                                            });
                                        }
                                        alert(`Updated ${updates.length} drills successfully.`);
                                        refreshData(); // Use refreshData prop
                                        setShowBulkEdit(false);
                                        setBulkTag('');
                                        setBulkAuthor('');
                                    } catch (error) {
                                        console.error('Bulk update failed:', error);
                                        alert('Failed to update some drills. Check console.');
                                    }
                                }}
                                style={{
                                    padding: '10px 20px',
                                    fontSize: '14px',
                                    border: 'none',
                                    borderRadius: '6px',
                                    backgroundColor: '#2196F3',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontWeight: 'bold',
                                }}
                            >
                                Apply Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Video URL Update Modal */}
            {showBulkVideoUrlUpdate && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10000,
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '30px',
                        borderRadius: '12px',
                        width: '500px',
                        maxWidth: '90vw',
                        maxHeight: '90vh',
                        overflow: 'auto',
                    }}>
                        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>
                            Bulk Video URL Update ({selectedDrillIds.length} drills)
                        </h2>
                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                                Base YouTube URL
                            </label>
                            <input
                                type="text"
                                value={bulkVideoUrl}
                                onChange={(e) => setBulkVideoUrl(e.target.value)}
                                placeholder="e.g., https://youtu.be/EpJ98WysJHA?si=PsVdqj3ejFKZDKj8"
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    fontSize: '14px',
                                    border: '1px solid #ccc',
                                    borderRadius: '6px',
                                }}
                            />
                            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                                Enter the base YouTube URL. Each drill will get this URL with its timestamp appended.
                            </div>
                        </div>
                        <div style={{ marginBottom: '25px' }}>
                            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                                <input
                                    type="checkbox"
                                    checked={bulkUpdateTimestamps}
                                    onChange={(e) => setBulkUpdateTimestamps(e.target.checked)}
                                    style={{ marginRight: '8px' }}
                                />
                                Update timestamps based on video_start_time
                            </label>
                            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                                If checked, each drill will get a timestamp parameter based on its video_start_time field.
                                If unchecked, all drills will get the same URL without timestamps.
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowBulkVideoUrlUpdate(false);
                                    setBulkVideoUrl('');
                                    setBulkUpdateTimestamps(true);
                                }}
                                style={{
                                    padding: '10px 20px',
                                    fontSize: '14px',
                                    border: '1px solid #ccc',
                                    borderRadius: '6px',
                                    backgroundColor: 'white',
                                    cursor: 'pointer',
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={async () => {
                                    if (!bulkVideoUrl.trim()) {
                                        alert('Please enter a YouTube URL.');
                                        return;
                                    }
                                    try {
                                        const response = await axios.post(`${API_BASE}/drills/bulk-update-video-url`, {
                                            drill_ids: selectedDrillIds,
                                            base_video_url: bulkVideoUrl.trim(),
                                            update_timestamps: bulkUpdateTimestamps
                                        });
                                        
                                        if (response.data.success) {
                                            alert(`✅ ${response.data.message}`);
                                            refreshData(); // Refresh the grid
                                            setShowBulkVideoUrlUpdate(false);
                                            setBulkVideoUrl('');
                                            setBulkUpdateTimestamps(true);
                                        } else {
                                            alert(`❌ ${response.data.message}`);
                                        }
                                    } catch (error: any) {
                                        console.error('Bulk video URL update failed:', error);
                                        const errorMsg = error.response?.data?.detail || error.message || 'Failed to update video URLs';
                                        alert(`❌ ${errorMsg}`);
                                    }
                                }}
                                style={{
                                    padding: '10px 20px',
                                    fontSize: '14px',
                                    border: 'none',
                                    borderRadius: '6px',
                                    backgroundColor: '#FF5722',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontWeight: 'bold',
                                }}
                            >
                                Apply Updates
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Voice Drill Creator Modal */}
            {showVoiceCreator && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 20000,
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '30px',
                        borderRadius: '12px',
                        width: '600px',
                        maxWidth: '90vw',
                        maxHeight: '90vh',
                        overflow: 'auto',
                        boxShadow: '0 10px 50px rgba(0,0,0,0.5)',
                    }}>
                        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>
                            🎤 Create Drill with Voice
                        </h2>
                        <p style={{ color: '#666', marginBottom: '20px' }}>
                            Use speech‑to‑text to quickly create a drill in Catalan, then add translations and media.
                        </p>
                        <VoiceDrillCreator
                            onClose={() => {
                                console.log('Cerrando VoiceDrillCreator');
                                setShowVoiceCreator(false);
                            }}
                            onDrillCreated={() => {
                                console.log('Drill creado, refrescando lista');
                                refreshData(); // Use refreshData prop
                                setShowVoiceCreator(false);
                            }}
                        />
                    </div>
                </div>
            )}

            {/* Drill Card Modal (Desktop) */}
            {editingDrill && createPortal(
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 20000,
                    padding: '20px'
                }}>
                    <div style={{
                        background: 'white',
                        borderRadius: '16px',
                        width: '100%',
                        maxWidth: '500px',
                        maxHeight: '90vh',
                        overflow: 'auto',
                        position: 'relative',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.5)'
                    }}>
                        <button
                            onClick={() => setEditingDrill(null)}
                            style={{
                                position: 'absolute',
                                top: '15px',
                                right: '15px',
                                border: 'none',
                                background: '#eee',
                                borderRadius: '50%',
                                width: '30px',
                                height: '30px',
                                cursor: 'pointer',
                                zIndex: 1,
                                fontWeight: 'bold'
                            }}
                        >✕</button>
                        <div style={{ padding: '20px' }}>
                            <DrillCard
                                drill={editingDrill}
                                onUpdate={() => {
                                    refreshData();
                                    // Update internal state to reflect changes
                                    axios.get(`${API_BASE}/drills/`).then(res => {
                                        const updated = res.data.find((d: any) => d.id === editingDrill.id);
                                        if (updated) setEditingDrill(updated);
                                    });
                                }}
                                onDelete={async () => {
                                    if (!confirm('Delete this drill?')) return;
                                    try {
                                        await axios.delete(`${API_BASE}/drills/${editingDrill.id}`);
                                        setEditingDrill(null);
                                        refreshData();
                                    } catch (err) { alert('Delete failed'); }
                                }}
                            />
                        </div>
                    </div>
                </div>,
                document.body
            )}

            {showGlossary && createPortal(
                <GlossaryModal onClose={() => setShowGlossary(false)} />,
                document.body
            )}
        </div>
    );
}
