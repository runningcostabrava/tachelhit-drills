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

  // Media capture states
  const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
  const [cameraMode, setCameraMode] = useState<'photo' | 'video' | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
  const [capturedAudio, setCapturedAudio] = useState<string | null>(null);
  const [uploadingMedia, setUploadingMedia] = useState(false);

  // Refs for media capture
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Sync local states if navigation triggers card object reloads
  useEffect(() => {
    setLocalDrill({ ...drill });
  }, [drill]);

  // Cleanup media streams on unmount or close
  useEffect(() => {
    return () => {
      stopCamera();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, []);

  const handleFieldChange = (field: keyof Drill, value: string) => {
    const updated = { ...localDrill, [field]: value };
    setLocalDrill(updated);

    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [field]: value });
        onUpdate();
      } catch (err) {
        console.error('Auto-save step failed inside editor context:', err);
      }
    }, 1500);
  };

  // ------------------------------------------------------------------
  // 🎙️ MEDIA RECORDING PIPELINE
  // ------------------------------------------------------------------

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

  const uploadCapturedBlob = async (blob: Blob, type: 'audio' | 'video' | 'image', filename: string) => {
    setUploadingMedia(true);
    const formData = new FormData();
    formData.append('file', blob, filename);

    try {
      const res = await axios.post(`${API_BASE}/upload-media/${localDrill.id}/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.url) {
        setLocalDrill(prev => {
          const updated = { ...prev, [`${type}_url`]: res.data.url };
          // If we have a local preview, we can keep it until next reload or clear it
          return updated;
        });
        onUpdate();
        alert(`Successfully updated ${type}!`);
      }
    } catch (err) {
      alert(`Failed to upload ${type}. Check your connection.`);
      console.error(err);
    } finally {
      setUploadingMedia(false);
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
        if (blob.size >= 1024) {
          setCapturedAudio(URL.createObjectURL(blob));
          await uploadCapturedBlob(blob, 'audio', `audio_${localDrill.id}_${Date.now()}.${format.ext}`);
        }
        stopCamera();
      };
      mediaRecorderRef.current.start();
      setRecording('audio');
    } catch (err) { alert('Microphone access denied or unavailable.'); console.error(err); }
  };

  const startVideoRecording = async () => {
    try {
      if (streamRef.current) stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 640, height: 480 }, audio: true });
      streamRef.current = stream;
      setCameraMode('video');

      setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);

      const format = getSupportedMimeType('video');
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: format.mime });
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: format.mime });
        if (blob.size >= 1024) {
          setCapturedVideo(URL.createObjectURL(blob));
          await uploadCapturedBlob(blob, 'video', `video_${localDrill.id}_${Date.now()}.${format.ext}`);
        }
        stopCamera();
      };
    } catch (err) { alert('Camera access denied or unavailable.'); console.error(err); }
  };

  const startImageCapture = async () => {
    try {
      if (streamRef.current) stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 1280, height: 720 } });
      streamRef.current = stream;
      setCameraMode('photo');
      setTimeout(() => { if (previewRef.current) { previewRef.current.srcObject = stream; previewRef.current.play().catch(e => console.error(e)); } }, 100);
    } catch (err) { alert('Camera access denied or unavailable.'); console.error(err); }
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
          setCapturedImage(URL.createObjectURL(blob));
          await uploadCapturedBlob(blob, 'image', `image_${localDrill.id}_${Date.now()}.jpg`);
        }
        stopCamera();
      }, 'image/jpeg', 0.9);
    }
  };

  const stopRecordingAction = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
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

  // 📤 Native File Upload Handler
  const handleMediaUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const fileType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio';
    
    if (fileType === 'image') setCapturedImage(URL.createObjectURL(file));
    if (fileType === 'video') setCapturedVideo(URL.createObjectURL(file));
    if (fileType === 'audio') setCapturedAudio(URL.createObjectURL(file));
    
    await uploadCapturedBlob(file, fileType, file.name);
  };

  // ------------------------------------------------------------------
  // 🌐 AI PIPELINES
  // ------------------------------------------------------------------

  const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
    const sourceText = source === 'ca' ? localDrill.text_catalan : localDrill.text_tachelhit;
    if (!sourceText) return alert('Source translation field is currently empty.');
    const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
    setAiLoadingKey(`trans-${targetField}`);

    try {
      const res = await axios.post(`${API_BASE}/translate`, { text: sourceText, source_lang: source, target_lang: target });
      const generatedTranslation = res.data.translated_text;
      const currentContent = localDrill[targetField] || '';
      const safeAppendText = currentContent.trim() ? `${currentContent} (${generatedTranslation})` : generatedTranslation;

      setLocalDrill(prev => ({ ...prev, [targetField]: safeAppendText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [targetField]: safeAppendText });
      onUpdate();
    } catch (err) { alert('Translation service failed inside editing module.'); }
    finally { setAiLoadingKey(null); }
  };

  const handleTranscribeAction = async () => {
    const mediaSource = localDrill.audio_url || localDrill.video_url;
    if (!mediaSource) return;
    setAiLoadingKey('transcribe-voice');

    try {
      const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
      const transcriptionResult = res.data.corrected_transcription;
      const currentTachelhit = localDrill.text_tachelhit || '';
      const safeAppendText = currentTachelhit.trim() ? `${currentTachelhit} (${transcriptionResult})` : transcriptionResult;

      setLocalDrill(prev => ({ ...prev, text_tachelhit: safeAppendText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { text_tachelhit: safeAppendText });
      onUpdate();
    } catch (err) { alert('AI Speech transcription failed inside editing module.'); }
    finally { setAiLoadingKey(null); }
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 11000, display: 'flex', flexDirection: 'column' }}>

      {/* Hidden Canvas for Photo Cropping */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Header Bar */}
      <div style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'white' }}>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: '24px', cursor: 'pointer' }}>✕</button>
        <span style={{ fontWeight: 700, fontSize: '18px' }}>Edit Card #{localDrill.id}</span>
        <div style={{ width: '24px' }} />
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* 🌟 CAMERA PREVIEW LAYER */}
        {cameraMode && (
          <div style={{ background: '#000', borderRadius: '16px', overflow: 'hidden' }}>
            <div style={{ position: 'relative', height: '280px' }}>
              <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              <button onClick={stopCamera} style={{ position: 'absolute', top: '12px', right: '12px', width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,0,0,0.8)', color: 'white', border: 'none', fontSize: '18px', cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ padding: '16px', background: '#111', display: 'flex', justifyContent: 'center' }}>
              {cameraMode === 'photo' ? (
                <button onClick={takePicture} style={{ width: '75px', height: '75px', borderRadius: '50%', background: 'white', border: '5px solid #4CAF50', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}>CAPTURE</button>
              ) : (
                <button onClick={recording === 'video' ? stopRecordingAction : () => { mediaRecorderRef.current?.start(); setRecording('video'); }} style={{ padding: '12px 30px', background: recording === 'video' ? '#ff4444' : '#9C27B0', color: 'white', border: 'none', borderRadius: '30px', fontWeight: 'bold', fontSize: '16px' }}>
                  {recording === 'video' ? '⏹️ STOP RECORD' : '🎬 START RECORD'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* 🎬 MEDIA CONTROL PAD */}
        {!cameraMode && (
          <div style={{ background: '#f8f9fa', padding: '12px', borderRadius: '12px', border: '1px solid #e0e0e0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '8px' }}>
              <button onClick={startImageCapture} disabled={uploadingMedia} style={{ height: '70px', background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}>📷 Photo</button>
              <button onClick={recording === 'audio' ? stopRecordingAction : startAudioRecording} disabled={uploadingMedia} style={{ height: '70px', background: recording === 'audio' ? '#ff4444' : '#2196F3', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer', animation: recording === 'audio' ? 'pulse 1.5s infinite' : 'none' }}>{recording === 'audio' ? '⏹️ Stop' : '🎙️ Audio'}</button>
              <button onClick={startVideoRecording} disabled={uploadingMedia} style={{ height: '70px', background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}>🎬 Video</button>
            </div>

            <input type="file" accept="image/*,video/*,audio/*" ref={fileInputRef} onChange={handleMediaUpload} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} disabled={uploadingMedia} style={{ width: '100%', padding: '10px', background: '#607D8B', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
              {uploadingMedia ? '⏳ Uploading Media...' : '📁 Upload from Gallery'}
            </button>
          </div>
        )}

        {/* Media Attachments previews */}
        {(localDrill.image_url || capturedImage) && (
          <img src={localDrill.image_url ? getMediaUrl(localDrill.image_url) : capturedImage || ''} alt="Drill Asset" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover', border: '1px solid #eee' }} />
        )}

        {(localDrill.video_url || capturedVideo) && (
          <video src={localDrill.video_url ? getMediaUrl(localDrill.video_url) : capturedVideo || ''} controls playsInline style={{ width: '100%', borderRadius: '12px', background: '#000' }} />
        )}

        {(localDrill.audio_url || capturedAudio) && (
          <button onClick={() => new Audio(localDrill.audio_url ? getMediaUrl(localDrill.audio_url) : capturedAudio || '').play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: 'none', borderRadius: '10px', fontWeight: 600, cursor: 'pointer' }}>
            🔊 Test Audio Recording Playback
          </button>
        )}

        {/* AI CONTROL PANEL */}
        <div style={{ display: 'grid', gridTemplateColumns: (localDrill.audio_url || localDrill.video_url) ? '1fr 1fr 1fr' : '1fr 1fr', gap: '8px', background: '#f8f9fa', padding: '10px', borderRadius: '12px' }}>
          <button onClick={() => handleTranslateAction('ca', 'shi')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#eef2ff', color: '#4f46e5', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
            {aiLoadingKey === 'trans-text_tachelhit' ? '⏳...' : '🤖 CA➔SHI'}
          </button>
          <button onClick={() => handleTranslateAction('shi', 'ca')} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#ecfdf5', color: '#059669', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
            {aiLoadingKey === 'trans-text_catalan' ? '⏳...' : '🤖 SHI➔CA'}
          </button>
          {(localDrill.audio_url || localDrill.video_url) && (
            <button onClick={handleTranscribeAction} disabled={aiLoadingKey !== null} style={{ padding: '10px', fontSize: '11px', fontWeight: 700, background: '#fff7ed', color: '#ea580c', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
              {aiLoadingKey === 'transcribe-voice' ? '⏳...' : '🪄 Transcribe'}
            </button>
          )}
        </div>

        {/* Text Areas */}
        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Català</label>
          <textarea value={localDrill.text_catalan || ''} onChange={(e) => handleFieldChange('text_catalan', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '1px solid #ccc', borderRadius: '8px' }} />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)</label>
          <textarea value={localDrill.text_tachelhit || ''} onChange={(e) => handleFieldChange('text_tachelhit', e.target.value)} rows={3} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '1px solid #ccc', borderRadius: '8px', fontFamily: 'monospace', fontWeight: 'bold' }} />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px', textAlign: 'right' }}>العربية</label>
          <textarea value={localDrill.text_arabic || ''} onChange={(e) => handleFieldChange('text_arabic', e.target.value)} rows={2} style={{ width: '100%', padding: '10px', fontSize: '16px', border: '1px solid #ccc', borderRadius: '8px', direction: 'rtl' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Tag</label><input type="text" value={localDrill.tag || ''} onChange={(e) => handleFieldChange('tag', e.target.value)} style={{ width: '100%', padding: '10px', fontSize: '15px', border: '1px solid #ccc', borderRadius: '8px' }} /></div>
          <div><label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Author</label><input type="text" value={localDrill.author || ''} onChange={(e) => handleFieldChange('author', e.target.value)} style={{ width: '100%', padding: '10px', fontSize: '15px', border: '1px solid #ccc', borderRadius: '8px' }} /></div>
        </div>
      </div>

      <div style={{ display: 'flex', borderTop: '1px solid #eee', padding: '12px', background: '#f8f9fa', justifyContent: 'space-between' }}>
        <button onClick={() => onNavigate('prev')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600 }}>◀ Previous</button>
        <button onClick={() => onNavigate('next')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600 }}>Next ▶</button>
      </div>
    </div>
  );
}