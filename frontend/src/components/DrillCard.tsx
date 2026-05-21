import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';
import { isYouTubeUrl, getYouTubeVideoId } from '../utils/youtubeUtils';
import { syncManager } from '../services/OfflineSyncManager';
import { FaCut as FaScissors } from 'react-icons/fa';

interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  author?: string;
  date_created: string;
  is_correction_dataset: boolean;
}

interface DrillCardProps {
  drill: Drill;
  onUpdate: () => void;
  onDelete: () => void;
  onSelect?: (selected: boolean) => void;
  isSelected?: boolean;
}

export default function DrillCard({ drill, onUpdate, onDelete, onSelect, isSelected }: DrillCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedDrill, setEditedDrill] = useState(drill);
  const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
  const [showVideo, setShowVideo] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<'user' | 'environment'>('user');
  const ytPlayerRef = useRef<any>(null);
  const ytPlayerReadyRef = useRef(false);
  const [permissionDenied, setPermissionDenied] = useState<{audio: boolean; video: boolean}>({audio: false, video: false});
  const [isTrimming, setIsTrimming] = useState(false);
  const [trimRange, setTrimRange] = useState({ start: 0, end: 5 });
  const [isProcessingTrim, setIsProcessingTrim] = useState(false);
  const [videoTrimRange, setVideoTrimRange] = useState({ start: 0, end: 5 });
  const [isVideoTrimming, setIsVideoTrimming] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionDebug, setTranscriptionResult] = useState<{rough?: string, score?: number} | null>(null);
  const [playerTime, setPlayerTime] = useState(0);
  const [playerDuration, setPlayerDuration] = useState(60);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Sync audio ref events with state
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setPlayerTime(audio.currentTime);
    const onLoadedMetadata = () => setPlayerDuration(audio.duration);
    const onPlay = () => setIsAudioPlaying(true);
    const onPause = () => setIsAudioPlaying(false);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      // Pausar y resetear el audio al desmontar para evitar fugas
      audio.pause();
      audio.currentTime = 0;
    };
  }, [drill.audio_url, audioRef]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Stop any ongoing recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      // Stop any media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      // Pause audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, []);

  const handleSave = async () => {
    try {
      console.log('💾 Saving drill to:', `${API_BASE}/drills/${drill.id}`);
      const response = await axios.put(`${API_BASE}/drills/${drill.id}`, editedDrill);
      console.log('✅ Save response:', response.data);
      setIsEditing(false);
      onUpdate();
    } catch (error: any) {
      console.error('❌ Error updating drill:', error);
      console.error('   Error details:', error.response?.data || error.message);
      alert(`Failed to update drill: ${error.message}`);
    }
  };

  const handleAutoTranscribe = async () => {
    // Use editedDrill URL as it's the most up-to-date locally
    const currentUrl = editedDrill.audio_url || drill.audio_url;
    
    if (!currentUrl) {
      alert('Please record audio first');
      return;
    }
    setIsTranscribing(true);
    setTranscriptionResult(null);
    try {
      console.log('🪄 [TRANSCR] Requesting transcription for:', currentUrl);
      const response = await axios.post(`${API_BASE}/transcribe/`, {
        audio_url: currentUrl
      });
      const { corrected_transcription, rough_transcription, similarity_score } = response.data;
      
      setTranscriptionResult({
        rough: rough_transcription,
        score: similarity_score
      });

      if (corrected_transcription) {
        setEditedDrill(prev => {
          const newText = prev.text_tachelhit ? `${prev.text_tachelhit} (${corrected_transcription})` : corrected_transcription;
          
          // Also auto-save it
          axios.put(`${API_BASE}/drills/${drill.id}`, { text_tachelhit: newText })
            .then(() => onUpdate())
            .catch(console.error);
            
          return { ...prev, text_tachelhit: newText };
        });
      }
    } catch (error) {
      console.error('Transcription failed:', error);
      alert('Failed to transcribe audio. Make sure you have drills marked as "Dataset" for best results.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleToggleCorrection = async (val: boolean) => {
    try {
      await axios.put(`${API_BASE}/drills/${drill.id}`, { is_correction_dataset: val });
      onUpdate();
    } catch (error) {
      console.error('Error toggling correction dataset:', error);
    }
  };

  const handleTrim = async (mode: 'audio' | 'video') => {
    setIsProcessingTrim(true);
    try {
      const range = mode === 'audio' ? trimRange : videoTrimRange;
      const endpoint = mode === 'audio' ? 'trim-audio' : 'trim-video';
      await axios.post(`${API_BASE}/drills/${drill.id}/${endpoint}`, {
        start_time: range.start,
        end_time: range.end
      });
      if (mode === 'audio') setIsTrimming(false);
      else setIsVideoTrimming(false);
      onUpdate();
      alert(`${mode === 'audio' ? 'Audio' : 'Video'} trimmed successfully!`);
    } catch (error) {
      console.error('Trim failed:', error);
      alert(`Failed to trim ${mode}`);
    } finally {
      setIsProcessingTrim(false);
    }
  };

  const startAudioRecording = async () => {
    console.log('🎤 [DEBUG] Starting audio recording...');
    console.log('🎤 [DEBUG] API_BASE:', API_BASE);
    console.log('🎤 [DEBUG] User agent:', navigator.userAgent);
    console.log('🎤 [DEBUG] MediaRecorder supported:', typeof MediaRecorder !== 'undefined');
    console.log('🎤 [DEBUG] navigator.mediaDevices:', navigator.mediaDevices);
    console.log('🎤 [DEBUG] navigator.mediaDevices.getUserMedia:', navigator.mediaDevices?.getUserMedia);
    
    // Check if permission was previously denied
    if (permissionDenied.audio) {
      alert('Microphone access was previously denied. Please enable it in your browser settings and refresh the page.');
      return;
    }
    
    if (typeof MediaRecorder !== 'undefined') {
      console.log('🎤 [DEBUG] MediaRecorder.isTypeSupported audio/webm:', MediaRecorder.isTypeSupported('audio/webm'));
      console.log('🎤 [DEBUG] MediaRecorder.isTypeSupported audio/mp4:', MediaRecorder.isTypeSupported('audio/mp4'));
      console.log('🎤 [DEBUG] MediaRecorder.isTypeSupported audio/ogg:', MediaRecorder.isTypeSupported('audio/ogg; codecs=opus'));
    }
    
    // Comprovar si el navegador suporta MediaRecorder
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const msg = 'Your browser does not support audio recording. Please use Chrome, Firefox, or Edge.';
      console.error('❌ [DEBUG]', msg);
      alert(msg);
      return;
    }

    // Detectar iOS/Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isChrome = /chrome/i.test(navigator.userAgent);
    const isFirefox = /firefox/i.test(navigator.userAgent);
    
    console.log('🎤 [DEBUG] isIOS:', isIOS, 'isSafari:', isSafari, 'isChrome:', isChrome, 'isFirefox:', isFirefox);

    try {
      const constraints: MediaStreamConstraints = { 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      };
      
      console.log('🎤 [DEBUG] Requesting media with constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('🎤 [DEBUG] Got stream:', stream.id, 'active:', stream.active, 'tracks:', stream.getTracks().length);
      
      // Determinar el tipus MIME compatible
      let mimeType = 'audio/webm';
      let extension = 'webm';
      
      if (typeof MediaRecorder === 'undefined') {
        const msg = 'MediaRecorder not supported in this browser. Try Chrome or Firefox on Android.';
        console.error('❌ [DEBUG]', msg);
        alert(msg);
        stream.getTracks().forEach(track => track.stop());
        return;
      }

      // iOS/Safari normalmente solo soporta AAC en MP4
      if (isIOS || isSafari) {
        mimeType = 'audio/mp4';
        extension = 'm4a';
        console.log('🎤 [DEBUG] iOS/Safari detected, using MP4/AAC');
      } else {
        if (!MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/mp4';
          extension = 'mp4';
          console.log('🎤 [DEBUG] audio/webm not supported, falling back to mp4');
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/ogg; codecs=opus';
          extension = 'ogg';
          console.log('🎤 [DEBUG] mp4 not supported, falling back to ogg');
        }
      }
      
      console.log('🎤 [DEBUG] Using MIME type for recording:', mimeType, 'extension:', extension);
      
      const options = { mimeType };
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        console.log('🎤 [DEBUG] Data available, size:', e.data.size, 'type:', e.data.type);
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        console.log('🎤 [DEBUG] Recording stopped, chunks:', chunksRef.current.length);
        if (chunksRef.current.length === 0) {
          console.warn('🎤 [DEBUG] No audio data recorded');
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mimeType });
        console.log('🎤 [DEBUG] Blob created, size:', blob.size, 'type:', blob.type);
        
        const formData = new FormData();
        formData.append('file', blob, `audio_${drill.id}_${Date.now()}.${extension}`);

        try {
          console.log('📤 [DEBUG] Uploading audio to:', `${API_BASE}/upload-media/${drill.id}/audio`);
          console.log('📤 [DEBUG] FormData entries:');
          for (const pair of formData.entries()) {
            console.log('   ', pair[0], pair[1]);
          }
          
          // Test if endpoint is reachable first
          console.log('📤 [DEBUG] Testing endpoint reachability...');
          try {
            const testResponse = await axios.get(`${API_BASE}/health`);
            console.log('✅ [DEBUG] Health check OK:', testResponse.data);
          } catch (testErr: any) {
            console.error('❌ [DEBUG] Health check failed:', testErr.message);
          }

          const response = await axios.post(`${API_BASE}/upload-media/${drill.id}/audio`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 30000, // 30 seconds timeout
          });
          console.log('✅ [DEBUG] Audio upload response:', response.data);
          
          // Update local state immediately so transcribe uses the NEW url
          if (response.data.url) {
            setEditedDrill(prev => ({ ...prev, audio_url: response.data.url }));
          }
          
          onUpdate();
          alert('Audio recorded and uploaded successfully!');
        } catch (err: any) {
          console.error('❌ [DEBUG] Audio upload failed:', err);
          console.error('   [DEBUG] Error name:', err.name);
          console.error('   [DEBUG] Error code:', err.code);
          console.error('   [DEBUG] Error message:', err.message);
          console.error('   [DEBUG] Error response data:', err.response?.data);
          console.error('   [DEBUG] Error response status:', err.response?.status);
          console.error('   [DEBUG] Error response headers:', err.response?.headers);
          
          let errorMsg = 'Failed to upload audio. ';
          if (err.code === 'ECONNABORTED') {
            errorMsg += 'Request timed out.';
          } else if (err.response?.status === 413) {
            errorMsg += 'File too large.';
          } else if (err.response?.status === 415) {
            errorMsg += 'Unsupported media type.';
          } else if (err.response?.status) {
            errorMsg += `Server error: ${err.response.status}`;
          } else if (err.message.includes('Network Error')) {
            errorMsg += 'Network error. Check your connection.';
          } else {
            errorMsg += err.message;
          }
          alert(errorMsg);
        } finally {
          stream.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('🎤 [DEBUG] MediaRecorder error:', event);
        alert('Error during recording. Please try again.');
        stream.getTracks().forEach(track => track.stop());
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('audio');
      console.log('🎤 [DEBUG] Audio recording started with MIME type:', mimeType, 'state:', mediaRecorderRef.current.state);
      // Force UI update
      setTimeout(() => {
        console.log('🎤 [DEBUG] Current recording state after start:', recording);
      }, 100);
    } catch (err: any) {
      console.error('🎤 [DEBUG] Microphone access denied:', err);
      console.error('🎤 [DEBUG] Error name:', err.name);
      console.error('🎤 [DEBUG] Error message:', err.message);
      if (err.name === 'NotAllowedError') {
        setPermissionDenied(prev => ({...prev, audio: true}));
        alert('Microphone access denied. To enable it:\n1. Click the lock icon in your browser\'s address bar.\n2. Change "Microphone" to "Allow".\n3. Refresh this page and try again.');
      } else if (err.name === 'NotFoundError') {
        alert('No microphone found. Please connect a microphone and try again.');
      } else if (err.name === 'NotReadableError') {
        alert('Microphone is already in use by another application.');
      } else {
        alert('Cannot access microphone: ' + err.message);
      }
    }
  };

  const startVideoRecording = async () => {
    // Check if permission was previously denied
    if (permissionDenied.video) {
      alert('Camera access was previously denied. Please enable it in your browser settings and refresh the page.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: cameraFacing, width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true
      });
      streamRef.current = stream;

      // Set preview immediately
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
      }

      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const formData = new FormData();
        formData.append('file', blob, `video_${drill.id}_${Date.now()}.webm`);

        try {
          await axios.post(`${API_BASE}/upload-media/${drill.id}/video`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          onUpdate();
        } catch (err) {
          console.error('Video upload failed:', err);
          alert('Failed to upload video');
        }

        stream.getTracks().forEach(track => track.stop());
        streamRef.current = null;
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('video');
    } catch (err: any) {
      console.error('Camera access denied:', err);
      if (err.name === 'NotAllowedError') {
        setPermissionDenied(prev => ({...prev, video: true}));
        alert('Camera access denied. To enable it:\n1. Click the lock icon in your browser\'s address bar.\n2. Change "Camera" to "Allow".\n3. Refresh this page and try again.');
      } else {
        alert('Please allow camera access');
      }
    }
  };

  const switchCamera = async () => {
    const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
    setCameraFacing(newFacing);

    if (recording === 'video' && streamRef.current) {
      // Stop current recording
      stopRecording();
      // Wait a bit for cleanup
      setTimeout(() => {
        // Start new recording with new camera
        startVideoRecording();
      }, 300);
    }
  };

  const stopRecording = () => {
    console.log('🛑 [DEBUG] stopRecording called, current recording state:', recording);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('🛑 [DEBUG] Stopping MediaRecorder, state:', mediaRecorderRef.current.state);
      mediaRecorderRef.current.stop();
      setRecording(null);
      console.log('🛑 [DEBUG] Recording state set to null');
    } else {
      console.log('🛑 [DEBUG] No active MediaRecorder found');
    }
  };

  const openPlayback = () => {
    setShowVideo(true);
    setPlaying(false);
    if (drill.video_url && isYouTubeUrl(drill.video_url)) {
      setTimeout(() => {
        initializeYouTubePlayer();
      }, 100);
    }
  };

  const closePlayback = () => {
    if (ytPlayerRef.current) {
      try { ytPlayerRef.current.pauseVideo(); } catch (e) {}
    }
    setShowVideo(false);
    setPlaying(false);
  };

  const initializeYouTubePlayer = () => {
    const videoId = getYouTubeVideoId(drill.video_url || '');
    if (!videoId) {
      // Fallback for native video duration
      const video = document.querySelector(`#video-playback-${drill.id}`) as HTMLVideoElement;
      if (video) {
        const dur = video.duration;
        if (dur) {
          setVideoTrimRange(prev => ({ ...prev, end: Math.min(prev.end, dur) }));
        }
      }
      return;
    }

    if (!(window as any).YT || !(window as any).YT.Player) {
      const tag = document.createElement('script');
      tag.src = "https://www.youtube.com/iframe_api";
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);
      
      (window as any).onYouTubeIframeAPIReady = () => {
        createYTPlayer(videoId);
      };
    } else {
      createYTPlayer(videoId);
    }
  };

  const createYTPlayer = (videoId: string) => {
    const elementId = `yt-player-card-${drill.id}`;
    
    setTimeout(() => {
      if (!document.getElementById(elementId)) {
        console.warn(`⚠️ Target div ${elementId} not found yet. YouTube player aborted.`);
        return;
      }

      if (ytPlayerRef.current) {
        try { ytPlayerRef.current.destroy(); } catch (e) {}
      }

      ytPlayerRef.current = new (window as any).YT.Player(elementId, {
        videoId: videoId,
        playerVars: {
          autoplay: 1,
          controls: 1,
          start: Math.floor((drill as any).video_start_time || 0),
          end: Math.ceil((drill as any).video_end_time || 0),
          rel: 0,
          modestbranding: 1
        },
        events: {
          onReady: () => {
            ytPlayerReadyRef.current = true;
            setPlaying(true);
            // Explicitly seek to start time on ready to ensure it starts correctly
            if ((drill as any).video_start_time) {
              ytPlayerRef.current.seekTo((drill as any).video_start_time);
            }
            ytPlayerRef.current.playVideo();
          },
          onStateChange: (event: any) => {
            if (event.data === (window as any).YT.PlayerState.ENDED) {
              event.target.seekTo((drill as any).video_start_time || 0);
              event.target.playVideo();
            }
            if (event.data === (window as any).YT.PlayerState.PLAYING) {
              setPlaying(true);
              // Robustness: if we are past the end time, loop now
              const curr = event.target.getCurrentTime();
              if ((drill as any).video_end_time && curr >= (drill as any).video_end_time) {
                event.target.seekTo((drill as any).video_start_time || 0);
              }
            }
            if (event.data === (window as any).YT.PlayerState.PAUSED) setPlaying(false);
          }
        }
      });
    }, 50);
  };

  const togglePlayPause = () => {
    if (drill.video_url && isYouTubeUrl(drill.video_url)) {
      if (ytPlayerRef.current && ytPlayerReadyRef.current) {
        if (playing) {
          ytPlayerRef.current.pauseVideo();
        } else {
          ytPlayerRef.current.playVideo();
        }
      }
    }
  };

  const goBack2Seconds = () => {
    if (drill.video_url && isYouTubeUrl(drill.video_url)) {
      if (ytPlayerRef.current && ytPlayerReadyRef.current) {
        const currentTime = ytPlayerRef.current.getCurrentTime();
        const startTime = (drill as any).video_start_time || 0;
        ytPlayerRef.current.seekTo(Math.max(startTime, currentTime - 2));
      }
    } else {
      const video = document.querySelector(`#video-playback-${drill.id}`) as HTMLVideoElement;
      if (video) {
        video.currentTime = Math.max(0, video.currentTime - 2);
      }
    }
  };


  // Add CSS for pulse animation
  const pulseStyle = `
    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.7; }
      100% { opacity: 1; }
    }
  `;

  return (
    <>
      <style>{pulseStyle}</style>
      {/* Edit Modal */}
      {isEditing && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'white',
          zIndex: 10000,
          overflow: 'auto'
        }}>
          {/* Modal Header */}
          <div style={{
            position: 'sticky',
            top: 0,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: isMobile ? '12px' : '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
          }}>
            <h2 style={{ margin: 0, color: 'white', fontSize: isMobile ? '18px' : '20px', fontWeight: 700 }}>
              Edit Drill #{drill.id}
            </h2>
            <button
              onClick={() => {
                setEditedDrill(drill);
                setIsEditing(false);
              }}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                color: 'white',
                fontSize: '24px',
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ✕
            </button>
          </div>

          {/* Modal Content */}
          <div style={{ padding: isMobile ? '15px' : '20px' }}>
            {/* Tag */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#333',
                marginBottom: '8px'
              }}>
                Tag (optional)
                <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>
                  Use '+' to add, '-' to remove, or replace
                </span>
              </label>
              <input
                value={editedDrill.tag || ''}
                onChange={(e) => setEditedDrill({ ...editedDrill, tag: e.target.value })}
                placeholder="e.g., greetings, colors, numbers... Use +tag to add, -tag to remove"
                style={{
                  width: '100%',
                  padding: '14px',
                  fontSize: '16px',
                  border: '2px solid #e0e0e0',
                  borderRadius: '8px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
              />
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                Current tags: {drill.tag || 'none'}
              </div>
            </div>

            {/* Author */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#333',
                marginBottom: '8px'
              }}>
                Author (optional)
              </label>
              <input
                value={editedDrill.author || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  setEditedDrill({ ...editedDrill, author: value === '' ? undefined : value });
                }}
                placeholder="e.g., John Doe (leave empty to clear)"
                style={{
                  width: '100%',
                  padding: '14px',
                  fontSize: '16px',
                  border: '2px solid #e0e0e0',
                  borderRadius: '8px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
              />
              <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={async () => {
                    if (!editedDrill.text_arabic) return;
                    try {
                      const res = await axios.post(`${API_BASE}/translate`, {
                        text: editedDrill.text_arabic,
                        source_lang: 'ar',
                        target_lang: 'ca'
                      });
                      setEditedDrill({ ...editedDrill, text_catalan: res.data.translated_text });
                    } catch (err) {
                      console.error('Translation to Catalan failed:', err);
                      alert('Translation failed. Please check your connection.');
                    }
                  }}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    background: '#9C27B0',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  → Catalan
                </button>
              </div>
            </div>

            {/* Catalan */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#333',
                marginBottom: '8px'
              }}>
                Català
              </label>
              <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '8px', alignItems: 'stretch' }}>
                <textarea
                  value={editedDrill.text_catalan || ''}
                  onChange={(e) => setEditedDrill({ ...editedDrill, text_catalan: e.target.value })}
                  placeholder="Enter Catalan text..."
                  rows={3}
                  style={{
                    flex: 1,
                    padding: '14px',
                    fontSize: '16px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    outline: 'none',
                    resize: 'vertical',
                    fontFamily: 'system-ui',
                    transition: 'border-color 0.2s',
                    minHeight: '100px'
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#667eea'}
                  onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
                />
                <div style={{ display: 'flex', flexDirection: isMobile ? 'row' : 'column', gap: '8px', minWidth: isMobile ? 'auto' : '120px' }}>
                  <button
                    onClick={async () => {
                      if (!editedDrill.text_catalan) return;
                      try {
                        const res = await axios.post(`${API_BASE}/translate`, {
                          text: editedDrill.text_catalan,
                          source_lang: 'ca',
                          target_lang: 'shi'
                        });
                        const newText = editedDrill.text_tachelhit ? `${editedDrill.text_tachelhit} (${res.data.translated_text})` : res.data.translated_text;
                        setEditedDrill({ ...editedDrill, text_tachelhit: newText });
                      } catch (err) {
                        console.error('Translation to Tachelhit failed:', err);
                        alert('Translation failed. Please check your connection.');
                      }
                    }}
                    style={{
                      padding: isMobile ? '8px 12px' : '10px 16px',
                      fontSize: isMobile ? '12px' : '14px',
                      background: '#4CAF50',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      flex: 1
                    }}
                  >
                    → Tachelhit
                  </button>
                  <button
                    onClick={async () => {
                      if (!editedDrill.text_catalan) return;
                      try {
                        const res = await axios.post(`${API_BASE}/translate`, {
                          text: editedDrill.text_catalan,
                          source_lang: 'ca',
                          target_lang: 'ar'
                        });
                        setEditedDrill({ ...editedDrill, text_arabic: res.data.translated_text });
                      } catch (err) {
                        console.error('Translation to Arabic failed:', err);
                        alert('Translation failed. Please check your connection.');
                      }
                    }}
                    style={{
                      padding: isMobile ? '8px 12px' : '10px 16px',
                      fontSize: isMobile ? '12px' : '14px',
                      background: '#2196F3',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      flex: 1
                    }}
                  >
                    → Arabic
                  </button>
                </div>
              </div>
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
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                                    {drill.audio_url && (
                                                      <button
                                                        onClick={async () => {
                                                          if (audioRef.current) {
                                                            const localUrl = await syncManager.getLocalMediaUrl(drill.audio_url!);
                                                            audioRef.current.src = localUrl;
                                                            audioRef.current.play();
                                                          }
                                                        }}
                                                        style={{
                                                          padding: '4px 8px',
                                                          background: '#e8f5e9',
                                                          color: '#2e7d32',
                                                          border: '1px solid #2e7d32',
                                                          borderRadius: '6px',
                                                          fontSize: '11px',
                                                          fontWeight: 600,
                                                          cursor: 'pointer',
                                                          display: 'flex',
                                                          alignItems: 'center',
                                                          gap: '4px'
                                                        }}
                                                      >
                                                        ▶️ Play Audio
                                                      </button>
                                                    )}
                                      
                                      {drill.audio_url && (
                                        <>
                                            <button
                                                onClick={handleAutoTranscribe}
                                                disabled={isTranscribing}
                                                style={{
                                                    padding: '4px 8px',
                                                    background: '#f0f4ff',
                                                    color: '#667eea',
                                                    border: '1px solid #667eea',
                                                    borderRadius: '6px',
                                                    fontSize: '11px',
                                                    fontWeight: 600,
                                                    cursor: isTranscribing ? 'not-allowed' : 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px'
                                                }}
                                            >
                                                {isTranscribing ? '🪄 Transcribing...' : '🪄 Auto-Transcribe'}
                                            </button>
                                        </>
                                      )}
                                    </div>
                        
                      </div>
                      <textarea
                        value={editedDrill.text_tachelhit || ''}
                        onChange={(e) => setEditedDrill({ ...editedDrill, text_tachelhit: e.target.value })}
                        placeholder="Enter Tachelhit text..."
                        rows={3}
                        style={{
                          width: '100%',
                          padding: '14px',
                          fontSize: '16px',
                          border: '2px solid #e0e0e0',
                          borderRadius: '8px',
                          outline: 'none',
                          resize: 'vertical',
                          fontFamily: 'system-ui',
                          transition: 'border-color 0.2s'
                        }}
                                    onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                    onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
                                  />
                                  <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                                    <button
                                      onClick={async () => {
                                        if (!editedDrill.text_tachelhit) return;
                                        try {
                                          const res = await axios.post(`${API_BASE}/translate`, {
                                            text: editedDrill.text_tachelhit,
                                            source_lang: 'shi',
                                            target_lang: 'ca'
                                          });
                                          const newText = editedDrill.text_catalan ? `${editedDrill.text_catalan} (${res.data.translated_text})` : res.data.translated_text;
                                          setEditedDrill({ ...editedDrill, text_catalan: newText });
                                        } catch (err) {
                                          console.error('Translation to Catalan failed:', err);
                                          alert('Translation failed. Please check your connection.');
                                        }
                                      }}
                                      style={{
                                        padding: '6px 12px',
                                        fontSize: '12px',
                                        background: '#9C27B0',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      → Catalan
                                    </button>
                                  </div>
                                  {transcriptionDebug && (
                                    <div style={{ 
                                      marginTop: '8px', 
                                      padding: '8px', 
                                      background: '#f0f4ff', 
                                      borderRadius: '6px', 
                                      fontSize: '11px', 
                                      border: '1px dashed #667eea' 
                                    }}>
                                      <div style={{ color: '#667eea', fontWeight: 700, marginBottom: '2px' }}>
                                        AI Debug Info:
                                      </div>
                                      <div><strong>Whisper heard:</strong> "{transcriptionDebug.rough}"</div>
                                      <div><strong>Confidence Score:</strong> {Math.round((transcriptionDebug.score || 0) * 100)}%</div>
                                      <div style={{ marginTop: '4px', fontStyle: 'italic', color: '#666' }}>
                                        * Matches against your "Dataset" drills.
                                      </div>
                                    </div>
                                  )}
                                </div>
                        
                                {/* Arabic */}
                        
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#333',
                marginBottom: '8px',
                textAlign: 'right'
              }}>
                العربية
              </label>
              <textarea
                value={editedDrill.text_arabic || ''}
                onChange={(e) => setEditedDrill({ ...editedDrill, text_arabic: e.target.value })}
                placeholder="أدخل النص العربي..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '14px',
                  fontSize: '16px',
                  border: '2px solid #e0e0e0',
                  borderRadius: '8px',
                  outline: 'none',
                  resize: 'vertical',
                  direction: 'rtl',
                  fontFamily: 'system-ui',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
              />
            </div>

            {/* Save/Cancel Buttons */}
            <div style={{
              position: 'sticky',
              bottom: 0,
              background: 'white',
              padding: '20px 0',
              marginTop: '30px',
              display: 'flex',
              gap: '12px'
            }}>
              <button
                onClick={() => {
                  setEditedDrill(drill);
                  setIsEditing(false);
                }}
                style={{
                  flex: 1,
                  padding: isMobile ? '14px' : '16px',
                  background: '#e0e0e0',
                  color: '#333',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: isMobile ? '15px' : '16px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                style={{
                  flex: 1,
                  padding: isMobile ? '14px' : '16px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: isMobile ? '15px' : '16px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
                }}
              >
                ✓ Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drill Card */}
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '16px',
        boxShadow: isSelected ? '0 4px 12px rgba(102, 126, 234, 0.4)' : '0 2px 8px rgba(0,0,0,0.1)',
        border: isSelected ? '2px solid #667eea' : '1px solid #e0e0e0',
        transition: 'all 0.2s'
      }}>
        {/* Header with ID and Select */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {onSelect && (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={(e) => onSelect(e.target.checked)}
                style={{
                  width: '20px',
                  height: '20px',
                  cursor: 'pointer',
                  accentColor: '#667eea'
                }}
              />
            )}
            <span style={{ fontSize: '14px', color: '#666', fontWeight: 600 }}>
              #{drill.id}
            </span>
            {drill.tag && (
              <span style={{
                fontSize: '12px',
                background: '#e0e7ff',
                color: '#667eea',
                padding: '4px 8px',
                borderRadius: '4px',
                fontWeight: 500
              }}>
                {drill.tag}
              </span>
            )}
            {drill.author && (
              <span style={{
                fontSize: '12px',
                background: '#e0f7fa',
                color: '#00796b',
                padding: '4px 8px',
                borderRadius: '4px',
                fontWeight: 500
              }}>
                👤 {drill.author}
              </span>
            )}
            
            {/* Correction Dataset Toggle */}
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px', 
              fontSize: '12px', 
              color: drill.is_correction_dataset ? '#4CAF50' : '#666',
              fontWeight: 600,
              cursor: 'pointer'
            }}>
              <input 
                type="checkbox" 
                checked={drill.is_correction_dataset} 
                onChange={(e) => handleToggleCorrection(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              {drill.is_correction_dataset ? '📚 In Dataset' : 'Add to Dataset'}
            </label>
          </div>
          <button
            onClick={onDelete}
            style={{
              background: '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🗑️
          </button>
        </div>

        {/* Text Fields - Compact Display */}
        <div
          style={{
            marginBottom: '12px',
            cursor: 'pointer',
            padding: '12px',
            background: '#f8f9fa',
            borderRadius: '8px'
          }}
          onClick={() => setIsEditing(true)}
        >
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#333', marginBottom: '4px' }}>
            {drill.text_catalan || <span style={{ color: '#999', fontSize: '13px' }}>+ Add Catalan</span>}
          </div>
          <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>
            {drill.text_tachelhit || <span style={{ color: '#999', fontSize: '12px' }}>+ Add Tachelhit</span>}
          </div>
          <div style={{ fontSize: '13px', color: '#666', direction: 'rtl' }}>
            {drill.text_arabic || <span style={{ color: '#999', fontSize: '12px' }}>+ أضف عربي</span>}
          </div>
        </div>

      {/* Recording Controls - Prominent */}
      <div style={{
        display: 'flex',
        gap: isMobile ? '6px' : '10px',
        marginBottom: '12px',
        flexDirection: isMobile ? 'column' : 'row'
      }}>
        {/* Audio Recording */}
        {recording === 'audio' ? (
          <button
            onClick={stopRecording}
            style={{
              flex: 1,
              padding: '16px',
              background: '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '16px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(255, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              animation: 'pulse 1.5s ease-in-out infinite'
            }}
          >
            <span style={{ fontSize: '20px' }}>⏹</span>
            <span>Stop Audio Recording</span>
          </button>
        ) : !recording ? (
          <button
            onClick={startAudioRecording}
            style={{
              flex: 1,
              padding: isMobile ? '12px' : '16px',
              background: drill.audio_url ? 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)' : 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: isMobile ? '14px' : '16px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '20px' }}>🎤</span>
            <span>{drill.audio_url ? 'Re-record Audio' : 'Record Audio'}</span>
          </button>
        ) : null}

        {/* Video Recording */}
        {recording === 'video' ? (
          <button
            onClick={stopRecording}
            style={{
              flex: 1,
              padding: '16px',
              background: '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '16px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(255, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              animation: 'pulse 1.5s ease-in-out infinite'
            }}
          >
            <span style={{ fontSize: '20px' }}>⏹</span>
            <span>Stop Video Recording</span>
          </button>
        ) : !recording ? (
          <button
            onClick={startVideoRecording}
            style={{
              flex: 1,
              padding: isMobile ? '12px' : '16px',
              background: drill.video_url ? 'linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%)' : 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: isMobile ? '14px' : '16px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '20px' }}>🎥</span>
            <span>{drill.video_url ? 'Re-record Video' : 'Record Video'}</span>
          </button>
        ) : null}
      </div>

      {/* Play Buttons (if recorded) */}
      {(drill.audio_url || drill.video_url) && !recording && (
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '12px'
        }}>
          {drill.audio_url && (
            <button
              onClick={() => {
                if (audioRef.current) {
                  audioRef.current.play();
                }
              }}
              style={{
                flex: 1,
                padding: isMobile ? '8px' : '10px',
                background: 'white',
                color: '#4CAF50',
                border: '2px solid #4CAF50',
                borderRadius: '8px',
                fontSize: isMobile ? '13px' : '14px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              ▶️ Play Audio
            </button>
          )}
          {drill.audio_url && (
            <audio 
              ref={audioRef} 
              src={drill.audio_url.startsWith('http') ? drill.audio_url : getMediaUrl(drill.audio_url)} 
              style={{ display: 'none' }}
              preload="auto"
            />
          )}
          {drill.video_url && (
            <button
              onClick={openPlayback}
              style={{
                flex: 1,
                padding: isMobile ? '8px' : '10px',
                background: 'white',
                color: '#9C27B0',
                border: '2px solid #9C27B0',
                borderRadius: '8px',
                fontSize: isMobile ? '13px' : '14px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              ▶️ Play Video
            </button>
          )}
        </div>
      )}

      {/* Video Trimmer Controls */}
      {drill.video_url && !recording && (
        <div style={{
          marginBottom: '12px',
          padding: '12px',
          background: '#f3e5f5',
          borderRadius: '8px',
          border: '1px solid #d1c4e9'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#4a148c' }}>✂️ Video Trimmer</span>
            <button 
              onClick={() => setIsVideoTrimming(!isVideoTrimming)}
              style={{ padding: '4px 8px', fontSize: '11px', background: 'none', border: '1px solid #4a148c', color: '#4a148c', borderRadius: '4px', cursor: 'pointer' }}
            >
              {isVideoTrimming ? 'Cancel' : 'Open'}
            </button>
          </div>
          
          {isVideoTrimming && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', display: 'block' }}>INICI: {videoTrimRange.start.toFixed(1)}s</label>
                  <input 
                    type="range" 
                    min="0" 
                    max={playerDuration} 
                    step="0.1" 
                    value={videoTrimRange.start} 
                    onChange={e => setVideoTrimRange(prev => ({...prev, start: parseFloat(e.target.value)}))}
                    style={{ width: '100%' }} 
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', display: 'block' }}>FINAL: {videoTrimRange.end.toFixed(1)}s</label>
                  <input 
                    type="range" 
                    min="0" 
                    max={playerDuration} 
                    step="0.1" 
                    value={videoTrimRange.end} 
                    onChange={e => setVideoTrimRange(prev => ({...prev, end: parseFloat(e.target.value)}))}
                    style={{ width: '100%' }} 
                  />
                </div>
              </div>
              <button 
                onClick={() => handleTrim('video')}
                disabled={isProcessingTrim}
                style={{ 
                  padding: '10px', 
                  background: '#9c27b0', 
                  color: 'white',
                  border: 'none', 
                  borderRadius: '10px', 
                  fontWeight: 700, 
                  fontSize: '14px',
                  cursor: isProcessingTrim ? 'not-allowed' : 'pointer',
                  opacity: isProcessingTrim ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                {isProcessingTrim ? 'Processant...' : <><FaScissors /> Retallar Vídeo</>}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Audio Trimmer Controls */}
      {drill.audio_url && !recording && (
        <div style={{
          marginBottom: '12px',
          padding: '12px',
          background: '#fff9e6',
          borderRadius: '8px',
          border: '1px solid #ffe680'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#856404' }}>✂️ Audio Trimmer</span>
            <button 
              onClick={() => setIsTrimming(!isTrimming)}
              style={{ padding: '4px 8px', fontSize: '11px', background: 'none', border: '1px solid #856404', color: '#856404', borderRadius: '4px', cursor: 'pointer' }}
            >
              {isTrimming ? 'Cancel' : 'Open'}
            </button>
          </div>
          
          {isTrimming && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {/* Integrated Audio Player Controls */}
              <div style={{ background: '#f0f0f0', padding: '10px', borderRadius: '8px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <button 
                    onClick={() => {
                      if (audioRef.current) {
                        if (isAudioPlaying) audioRef.current.pause();
                        else audioRef.current.play();
                      }
                    }}
                    style={{ padding: '8px 12px', background: '#2196F3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    {isAudioPlaying ? '⏸ Pause' : '▶️ Play'}
                  </button>
                  <button 
                    onClick={() => { if (audioRef.current) audioRef.current.currentTime -= 5; }}
                    style={{ padding: '8px', background: 'white', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}
                  >-5s</button>
                  <button 
                    onClick={() => { if (audioRef.current) audioRef.current.currentTime += 5; }}
                    style={{ padding: '8px', background: 'white', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}
                  >+5s</button>
                  <div style={{ flex: 1, fontSize: '12px', textAlign: 'right', fontFamily: 'monospace' }}>
                    {playerTime.toFixed(1)}s / {playerDuration.toFixed(1)}s
                  </div>
                </div>
                <input 
                  type="range" 
                  min="0" 
                  max={playerDuration || 100} 
                  step="0.1" 
                  value={playerTime}
                  onChange={(e) => { if (audioRef.current) audioRef.current.currentTime = parseFloat(e.target.value); }}
                  style={{ width: '100%', cursor: 'pointer', accentColor: '#2196F3' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', display: 'block' }}>Start (sec)</label>
                  <div style={{ display: 'flex', gap: '2px' }}>
                    <button onClick={() => setTrimRange({...trimRange, start: Math.max(0, parseFloat((trimRange.start - 0.4).toFixed(1)))})} style={{ padding: '4px' }}>-</button>
                    <input 
                      type="number" 
                      value={trimRange.start} 
                      onChange={e => setTrimRange({...trimRange, start: parseFloat(e.target.value)})}
                      style={{ width: '100%', padding: '6px', fontSize: '12px' }}
                      step="0.1"
                    />
                    <button onClick={() => setTrimRange({...trimRange, start: parseFloat((trimRange.start + 0.4).toFixed(1))})} style={{ padding: '4px' }}>+</button>
                  </div>
                  <button 
                    onClick={() => setTrimRange({...trimRange, start: Number(audioRef.current?.currentTime.toFixed(1) || 0)})}
                    style={{ width: '100%', marginTop: '4px', fontSize: '10px', padding: '4px', cursor: 'pointer' }}
                  >📍 Set current</button>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', display: 'block' }}>End (sec)</label>
                  <div style={{ display: 'flex', gap: '2px' }}>
                    <button onClick={() => setTrimRange({...trimRange, end: Math.max(0, parseFloat((trimRange.end - 0.4).toFixed(1)))})} style={{ padding: '4px' }}>-</button>
                    <input 
                      type="number" 
                      value={trimRange.end} 
                      onChange={e => setTrimRange({...trimRange, end: parseFloat(e.target.value)})}
                      style={{ width: '100%', padding: '6px', fontSize: '12px' }}
                      step="0.1"
                    />
                    <button onClick={() => setTrimRange({...trimRange, end: parseFloat((trimRange.end + 0.4).toFixed(1))})} style={{ padding: '4px' }}>+</button>
                  </div>
                  <button 
                    onClick={() => setTrimRange({...trimRange, end: Number(audioRef.current?.currentTime.toFixed(1) || 0)})}
                    style={{ width: '100%', marginTop: '4px', fontSize: '10px', padding: '4px', cursor: 'pointer' }}
                  >📍 Set current</button>
                </div>
              </div>
              <button 
                onClick={() => handleTrim('audio')}
                disabled={isProcessingTrim}
                style={{ 
                  padding: '8px', 
                  background: '#ffc107', 
                  border: 'none', 
                  borderRadius: '6px', 
                  fontWeight: 700, 
                  fontSize: '13px',
                  cursor: isProcessingTrim ? 'not-allowed' : 'pointer',
                  opacity: isProcessingTrim ? 0.7 : 1
                }}
              >
                {isProcessingTrim ? 'Processing...' : 'Apply Audio Trim'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Video Recording Preview */}
      {recording === 'video' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'black',
          zIndex: 10000,
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Video Preview */}
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative'
          }}>
            <video
              ref={previewRef}
              autoPlay
              muted
              playsInline
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover'
              }}
              onLoadedMetadata={() => {
                if (previewRef.current && streamRef.current) {
                  previewRef.current.srcObject = streamRef.current;
                }
              }}
            />

            {/* Recording Indicator */}
            <div style={{
              position: 'absolute',
              top: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(255, 0, 0, 0.9)',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '25px',
              fontSize: '16px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}>
              <span style={{
                width: '12px',
                height: '12px',
                background: 'white',
                borderRadius: '50%',
                animation: 'pulse 1.5s ease-in-out infinite'
              }}></span>
              Recording
            </div>

            {/* Camera Switch Button */}
            <button
              onClick={switchCamera}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                width: '50px',
                height: '50px',
                borderRadius: '50%',
                background: 'rgba(255, 255, 255, 0.3)',
                backdropFilter: 'blur(10px)',
                border: '2px solid white',
                color: 'white',
                fontSize: '24px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              🔄
            </button>
          </div>

          {/* Controls */}
          <div style={{
            padding: '30px 20px',
            background: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            justifyContent: 'center',
            gap: '20px'
          }}>
            <button
              onClick={stopRecording}
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #ff4444 0%, #cc0000 100%)',
                color: 'white',
                border: '4px solid white',
                fontSize: '32px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 6px 20px rgba(255, 68, 68, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ⏹
            </button>
          </div>
        </div>
      )}

      {/* Video Playback Modal */}
      {showVideo && drill.video_url && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            closePlayback();
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.9)',
            zIndex: 30000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: isMobile ? '10px' : '20px'
          }}
        >
          <div onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '800px', background: 'white', padding: '20px', borderRadius: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
              <h3 style={{ margin: 0 }}>Video Playback</h3>
              <button onClick={closePlayback} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>
            
            {isYouTubeUrl(drill.video_url) ? (
              <div
                id={`yt-player-card-${drill.id}`}
                style={{
                  width: '100%',
                  height: isMobile ? '300px' : '450px',
                  backgroundColor: '#000',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                }}
              />
            ) : (
              <video
                id={`video-playback-${drill.id}`}
                autoPlay
                src={getMediaUrl(drill.video_url)}
                controls
                style={{
                  width: '100%',
                  maxHeight: '70vh',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                }}
                onLoadedMetadata={(e) => {
                  const dur = (e.target as HTMLVideoElement).duration;
                  if (dur) {
                    setVideoTrimRange(prev => ({ ...prev, end: Math.min(prev.end, dur) }));
                  }
                }}
              />
            )}
            
            <div style={{ marginTop: '15px', display: 'flex', gap: '10px', justifyContent: 'center' }}>
              {drill.video_url && isYouTubeUrl(drill.video_url) && (
                <button
                  onClick={togglePlayPause}
                  style={{
                    padding: '10px 20px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600
                  }}
                >
                  {playing ? '⏸ Pause' : '▶ Play'}
                </button>
              )}
              <button
                onClick={goBack2Seconds}
                style={{
                  padding: '10px 20px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                ↺ 2s
              </button>
              <button
                onClick={closePlayback}
                style={{
                  padding: '10px 20px',
                  background: '#666',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Video Player (Integrated) */}
      {drill.video_url && !isYouTubeUrl(drill.video_url) && !recording && !showVideo && (
        <div style={{ marginBottom: '12px', borderRadius: '12px', overflow: 'hidden', background: '#000' }}>
            <video 
                src={getMediaUrl(drill.video_url)} 
                controls 
                playsInline 
                preload="metadata"
                style={{ width: '100%', maxHeight: '250px', display: 'block', objectFit: 'contain' }} 
            />
        </div>
      )}

      {/* Edit Button */}
      <button
        onClick={() => setIsEditing(true)}
        style={{
          width: '100%',
          padding: isMobile ? '10px' : '12px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          fontSize: isMobile ? '14px' : '15px',
          fontWeight: 600,
          cursor: 'pointer',
          boxShadow: '0 2px 6px rgba(102, 126, 234, 0.3)',
          marginTop: '8px'
        }}
      >
        ✏️ Edit Text
      </button>
    </div>
    </>
  );
}
