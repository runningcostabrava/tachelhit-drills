import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';

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
}

interface MobileDrillEditorProps {
  drill: Drill;
  onClose: () => void;
  onUpdate: () => void;
  onNavigate: (direction: 'next' | 'prev') => void;
}

export default function MobileDrillEditor({ drill, onClose, onUpdate, onNavigate }: MobileDrillEditorProps) {
  const [localDrill, setLocalDrill] = useState<Drill>({ ...drill });
  const [aiLoadingKey, setAiLoadingKey] = useState<string | null>(null);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
  const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
  const [capturedAudio, setCapturedAudio] = useState<string | null>(null);
  const [uploadingMedia, setUploadingMedia] = useState(false);

  // 🐛 LIVE DEBUG LOGGER
  const [debugLogs, setDebugLogs] = useState<string[]>(['[System] Editor Initialized']);
  const addLog = (msg: string) => {
    setDebugLogs(prev => [`[${new Date().toLocaleTimeString().split(' ')[0]}] ${msg}`, ...prev].slice(0, 12));
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => { setLocalDrill({ ...drill }); }, [drill]);

  useEffect(() => {
    return () => {
      stopCamera();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (cameraMode && previewRef.current && streamRef.current) {
      addLog(`Binding stream to <video> for ${cameraMode}`);
      const video = previewRef.current;
      video.srcObject = streamRef.current;

      // Ensure video plays on mobile
      video.setAttribute('autoplay', '');
      video.setAttribute('muted', '');
      video.setAttribute('playsinline', '');

      video.play()
        .then(() => addLog('Video playback started'))
        .catch(e => {
          addLog(`Video playback error: ${e.message}`);
        });
    }
  }, [cameraMode, streamRef.current]);

  const handleFieldChange = (field: keyof Drill, value: string) => {
    const updated = { ...localDrill, [field]: value };
    setLocalDrill(updated);

    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [field]: value });
        onUpdate();
      } catch (err) { addLog('Auto-save step failed'); }
    }, 1500);
  };

  const getSupportedMimeType = (type: 'audio' | 'video') => {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    if (isIOS) return type === 'audio' ? { mime: 'audio/mp4', ext: 'm4a' } : { mime: 'video/mp4', ext: 'mp4' };
    return type === 'audio' ? { mime: 'audio/webm', ext: 'webm' } : { mime: 'video/webm', ext: 'webm' };
  };

  const uploadCapturedBlob = async (blob: Blob, type: 'audio' | 'video' | 'image', filename: string) => {
    addLog(`Uploading ${type} (${blob.size} bytes)...`);
    setUploadingMedia(true);
    const formData = new FormData();
    formData.append('file', blob, filename);

    try {
      const res = await axios.post(`${API_BASE}/upload-media/${localDrill.id}/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.url) {
        addLog(`Upload success: ${type}`);
        setLocalDrill(prev => ({ ...prev, [`${type}_url`]: res.data.url }));
        onUpdate();
      }
    } catch (err: any) {
      addLog(`Upload Failed: ${err.message}`);
    } finally {
      setUploadingMedia(false);
    }
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
      await new Promise(r => setTimeout(r, 200));
      addLog('Requesting video stream...');
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: true
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      addLog('Video Stream acquired!');
      setCameraMode('video');
    } catch (err: any) {
      addLog(`In-App Video Error: ${err.name} - ${err.message}`);
      if (err.name === 'NotAllowedError') alert('Camera/Mic permission denied.');
    }
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
          await uploadCapturedBlob(blob, 'audio', `audio_${localDrill.id}_${Date.now()}.${format.ext}`);
        }
        stopCamera();
      };
      mediaRecorderRef.current.start();
      setRecording('audio');
      addLog('Audio recording STARTED');
    } catch (err: any) { addLog(`In-App Audio Error: ${err.message}`); }
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
        await uploadCapturedBlob(blob, 'video', `video_${localDrill.id}_${Date.now()}.${format.ext}`);
      }
      stopCamera();
    };
    mediaRecorderRef.current.start();
    setRecording('video');
  };

  const takePicture = () => {
    addLog('Taking picture...');
    if (!previewRef.current || !canvasRef.current || !streamRef.current) {
      addLog('Missing ref for picture');
      return;
    }
    const video = previewRef.current;
    const canvas = canvasRef.current;

    if (video.readyState !== video.HAVE_ENOUGH_DATA || video.videoWidth === 0) {
      addLog('Video not ready, waiting...');
      setTimeout(takePicture, 200);
      return;
    }

    const size = Math.min(video.videoWidth, video.videoHeight);
    const sx = (video.videoWidth - size) / 2;
    const sy = (video.videoHeight - size) / 2;

    canvas.width = size;
    canvas.height = size;
    const context = canvas.getContext('2d');
    if (context) {
      context.fillStyle = '#ffffff';
      context.fillRect(0, 0, size, size);
      context.drawImage(video, sx, sy, size, size, 0, 0, size, size);
      canvas.toBlob(async (blob) => {
        addLog(`Picture snapped: ${blob?.size || 0} bytes`);
        if (blob && blob.size > 0) {
          setCapturedImage(URL.createObjectURL(blob));
          await uploadCapturedBlob(blob, 'image', `image_${localDrill.id}_${Date.now()}.jpg`);
        }
        stopCamera();
      }, 'image/jpeg', 0.92);
    }
  };

  const stopRecordingAction = () => {
    addLog('Stopping recording...');
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.requestData(); } catch (e) { }
      mediaRecorderRef.current.stop();
      setRecording(null);
    } else {
      stopCamera();
    }
  };

  const handleMediaUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) { addLog('Native capture canceled.'); return; }

    addLog(`Native capture received: ${file.name} (${file.type})`);
    const fileType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';

    if (fileType === 'image') setCapturedImage(URL.createObjectURL(file));
    if (fileType === 'video') setCapturedVideo(URL.createObjectURL(file));
    if (fileType === 'audio') setCapturedAudio(URL.createObjectURL(file));

    await uploadCapturedBlob(file, fileType, file.name);
  };

  const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
    const sourceText = source === 'ca' ? localDrill.text_catalan : localDrill.text_tachelhit;
    if (!sourceText) return alert('Field is empty.');
    const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
    setAiLoadingKey(`trans-${targetField}`);
    try {
      const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
      const currentContent = localDrill[targetField] || '';
      const safeText = currentContent.trim() ? `${currentContent} (${res.data.translated_text})` : res.data.translated_text;
      setLocalDrill(prev => ({ ...prev, [targetField]: safeText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [targetField]: safeText });
      onUpdate();
    } catch (err) { alert('Translation failed.'); } finally { setAiLoadingKey(null); }
  };

  const handleTranscribeAction = async () => {
    const mediaSource = localDrill.audio_url || localDrill.video_url;
    if (!mediaSource) return;
    setAiLoadingKey('transcribe-voice');
    try {
      const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
      const currentContent = localDrill.text_tachelhit || '';
      const safeText = currentContent.trim() ? `${currentContent} (${res.data.corrected_transcription})` : res.data.corrected_transcription;
      setLocalDrill(prev => ({ ...prev, text_tachelhit: safeText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { text_tachelhit: safeText });
      onUpdate();
    } catch (err) { alert('Transcription failed.'); } finally { setAiLoadingKey(null); }
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 11000, display: 'flex', flexDirection: 'column' }}>
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      <div style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'white' }}>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: '24px', cursor: 'pointer' }}>✕</button>
        <span style={{ fontWeight: 700, fontSize: '18px' }}>Edit Card #{localDrill.id}</span>
        <div style={{ width: '24px' }} />
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {cameraMode && (
          <div style={{ background: '#000', borderRadius: '16px', overflow: 'hidden' }}>
            <div style={{ position: 'relative', height: '280px' }}>
              <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            <div style={{ padding: '16px', background: '#111', display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
              <button onClick={stopCamera} style={{ padding: '10px 20px', background: '#444', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>✕ Cancel</button>
              {cameraMode === 'photo' ? (
                <button onClick={takePicture} style={{ width: '65px', height: '65px', borderRadius: '50%', background: 'white', border: '4px solid #4CAF50', fontWeight: 'bold', color: '#333' }}>SNAP</button>
              ) : (
                <button onClick={recording === 'video' ? stopRecordingAction : startRecordingVideo} style={{ padding: '12px 24px', background: recording === 'video' ? '#ff4444' : '#9C27B0', color: 'white', border: 'none', borderRadius: '30px', fontWeight: 'bold' }}>
                  {recording === 'video' ? '⏹️ STOP' : '🎬 START'}
                </button>
              )}
            </div>
          </div>
        )}

        {!cameraMode && (
          <div style={{ background: '#f8f9fa', padding: '12px', borderRadius: '12px', border: '1px solid #e0e0e0' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#666', textAlign: 'center' }}>IN-APP CAMERA</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
              <button onClick={startImageCapture} disabled={uploadingMedia} style={{ height: '60px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>📷 Photo</button>
              <button onClick={recording === 'audio' ? stopRecordingAction : startAudioRecording} disabled={uploadingMedia} style={{ height: '60px', background: recording === 'audio' ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>{recording === 'audio' ? '⏹️ Stop' : '🎙️ Audio'}</button>
              <button onClick={openVideoCamera} disabled={uploadingMedia} style={{ height: '60px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>🎬 Video</button>
            </div>

            <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#666', textAlign: 'center' }}>NATIVE ANDROID CAPTURE (Backup)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
              {/* 🌟 FIX: Updated HTML5 capture hints to strictly force native camera/mic apps */}
              <input type="file" accept="image/*" capture={"camera" as any} id="native-photo" style={{ display: 'none' }} onChange={handleMediaUpload} />
              <button onClick={() => document.getElementById('native-photo')?.click()} disabled={uploadingMedia} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Photo</button>

              <input type="file" accept="video/*" capture={"camcorder" as any} id="native-video" style={{ display: 'none' }} onChange={handleMediaUpload} />
              <button onClick={() => document.getElementById('native-video')?.click()} disabled={uploadingMedia} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Video</button>

              <input type="file" accept="audio/*" capture={"microphone" as any} id="native-audio" style={{ display: 'none' }} onChange={handleMediaUpload} />
              <button onClick={() => document.getElementById('native-audio')?.click()} disabled={uploadingMedia} style={{ padding: '10px', background: '#333', color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>📱 Audio</button>
            </div>

            <input type="file" accept="image/*,video/*,audio/*" ref={fileInputRef} onChange={handleMediaUpload} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} disabled={uploadingMedia} style={{ width: '100%', padding: '10px', background: '#607D8B', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}>
              {uploadingMedia ? '⏳ Uploading Media...' : '📁 Upload from Gallery'}
            </button>
          </div>
        )}

        {(localDrill.image_url || capturedImage) && (
          <img src={localDrill.image_url ? getMediaUrl(localDrill.image_url) : capturedImage || ''} alt="Drill Asset" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover', border: '1px solid #eee' }} />
        )}

        {(localDrill.video_url || capturedVideo) && (
          <video src={localDrill.video_url ? getMediaUrl(localDrill.video_url) : capturedVideo || ''} controls playsInline style={{ width: '100%', borderRadius: '12px', background: '#000' }} />
        )}

        {(localDrill.audio_url || capturedAudio) && (
          <button onClick={() => new Audio(localDrill.audio_url ? getMediaUrl(localDrill.audio_url) : capturedAudio || '').play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: 'none', borderRadius: '10px', fontWeight: 600 }}>
            🔊 Test Audio Recording Playback
          </button>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: (localDrill.audio_url || localDrill.video_url) ? '1fr 1fr 1fr' : '1fr 1fr', gap: '8px', background: '#f8f9fa', padding: '10px', borderRadius: '12px' }}>
          <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px' }}>🤖 CA➔SHI</button>
          <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px' }}>🤖 SHI➔CA</button>
          {(localDrill.audio_url || localDrill.video_url) && (
            <button onClick={handleTranscribeAction} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px' }}>🪄 Transcribe</button>
          )}
        </div>

        <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600 }}>Català</label><textarea value={localDrill.text_catalan || ''} onChange={(e) => handleFieldChange('text_catalan', e.target.value)} rows={2} style={{ width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '8px' }} /></div>
        <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600 }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label><textarea value={localDrill.text_tachelhit || ''} onChange={(e) => handleFieldChange('text_tachelhit', e.target.value)} rows={2} style={{ width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '8px' }} /></div>

        {/* 🐛 LIVE DEBUG CONSOLE UI */}
        <div style={{ background: '#111', color: '#0f0', padding: '10px', borderRadius: '8px', fontSize: '10px', fontFamily: 'monospace', height: '120px', overflowY: 'auto' }}>
          <div style={{ color: '#fff', borderBottom: '1px solid #333', paddingBottom: '4px', marginBottom: '4px' }}>LIVE DEBUGGER</div>
          {debugLogs.map((log, i) => <div key={i}>{log}</div>)}
        </div>
      </div>
      <div style={{ display: 'flex', padding: '12px', background: '#f8f9fa', justifyContent: 'space-between' }}>
        <button onClick={() => onNavigate('prev')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px' }}>◀ Prev</button>
        <button onClick={() => onNavigate('next')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px' }}>Next ▶</button>
      </div>
    </div>
  );
}
