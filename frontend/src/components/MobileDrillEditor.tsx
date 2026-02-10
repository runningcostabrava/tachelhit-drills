import { useState, useRef, useEffect } from 'react';
import type { CSSProperties } from 'react';
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
  date_created: string;
}

interface MobileDrillEditorProps {
  drill: Drill;
  allDrills: Drill[];
  onClose: () => void;
  onUpdate: () => void;
  onNavigate: (direction: 'next' | 'prev') => void;
}

export default function MobileDrillEditor({ drill, allDrills, onClose, onUpdate, onNavigate }: MobileDrillEditorProps) {
  const [editedDrill, setEditedDrill] = useState(drill);
  const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
  const [showVideo, setShowVideo] = useState(false);
  const [showCameraChoice, setShowCameraChoice] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<'user' | 'environment'>('user');
  const [hasChanges, setHasChanges] = useState(false);
  const [showImageCapture, setShowImageCapture] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    setEditedDrill(drill);
    setHasChanges(false);
  }, [drill]);

  const handleChange = (field: string, value: string) => {
    setEditedDrill({ ...editedDrill, [field]: value });
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await axios.put(`${API_BASE}/drills/${drill.id}`, editedDrill);
      setHasChanges(false);
      onUpdate();
    } catch (error) {
      console.error('Error updating drill:', error);
      alert('Failed to update drill');
    }
  };

  const handleClose = () => {
    if (hasChanges) {
      if (confirm('You have unsaved changes. Discard them?')) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  const startAudioRecording = async () => {
    console.log('🎤 [Mobile] Starting audio recording, API_BASE:', API_BASE);
    console.log('🎤 [Mobile] User agent:', navigator.userAgent);
    
    // Comprovar si el navegador suporta MediaRecorder
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('El teu navegador no suporta la gravació d\'àudio. Si us plau, utilitza Chrome, Firefox o Edge.');
      return;
    }

    // Detectar iOS/Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    
    console.log('🎤 [Mobile] isIOS:', isIOS, 'isSafari:', isSafari);

    try {
      const constraints: MediaStreamConstraints = { 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      };
      
      console.log('🎤 [Mobile] Requesting media with constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('🎤 [Mobile] Got stream:', stream.id, 'active:', stream.active);
      
      // Determinar el tipus MIME compatible
      let mimeType = 'audio/webm';
      let extension = 'webm';
      
      if (typeof MediaRecorder === 'undefined') {
        alert('MediaRecorder no suportat en aquest navegador. Prova Chrome o Firefox a Android.');
        stream.getTracks().forEach(track => track.stop());
        return;
      }

      // iOS/Safari normalmente solo soporta AAC en MP4
      if (isIOS || isSafari) {
        mimeType = 'audio/mp4';
        extension = 'm4a';
        console.log('🎤 [Mobile] iOS/Safari detectat, utilitzant MP4/AAC');
      } else {
        if (!MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/mp4';
          extension = 'mp4';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/ogg; codecs=opus';
          extension = 'ogg';
        }
      }
      
      console.log('🎤 [Mobile] Utilitzant tipus MIME per a gravació:', mimeType);
      
      const options = { mimeType };
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        console.log('🎤 [Mobile] Dades disponibles, mida:', e.data.size);
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        console.log('🎤 [Mobile] Gravació aturada, chunks:', chunksRef.current.length);
        if (chunksRef.current.length === 0) {
          console.warn('No hi ha dades d\'àudio gravades');
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mimeType });
        console.log('🎤 [Mobile] Blob creat, mida:', blob.size, 'tipus:', blob.type);
        
        const formData = new FormData();
        formData.append('file', blob, `audio_${drill.id}_${Date.now()}.${extension}`);

        try {
          console.log('📤 [Mobile] Pujant àudio a:', `${API_BASE}/upload-media/${drill.id}/audio`);
          await axios.post(`${API_BASE}/upload-media/${drill.id}/audio`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          onUpdate();
          alert('Àudio gravat i pujat correctament!');
        } catch (err: any) {
          console.error('❌ [Mobile] Error en pujar l\'àudio:', err);
          console.error('   Detalls:', err.response?.data || err.message);
          alert('No s\'ha pogut pujar l\'àudio. Si us plau, torna-ho a provar. Error: ' + err.message);
        } finally {
          stream.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('Error de MediaRecorder:', event);
        alert('Error durant la gravació. Si us plau, torna-ho a provar.');
        stream.getTracks().forEach(track => track.stop());
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('audio');
      console.log('🎤 [Mobile] Gravació d\'àudio iniciada amb tipus MIME:', mimeType);
    } catch (err: any) {
      console.error('Accés al micròfon denegat:', err);
      if (err.name === 'NotAllowedError') {
        alert('Si us plau, permet l\'accés al micròfon a la configuració del teu navegador.');
      } else if (err.name === 'NotFoundError') {
        alert('No s\'ha trobat cap micròfon. Connecta un micròfon i torna-ho a provar.');
      } else {
        alert('No es pot accedir al micròfon: ' + err.message);
      }
    }
  };

  // Helper to stop all tracks in the current stream
  const _stopCameraStream = () => {
    if (streamRef.current) {
      console.log('Stopping current camera stream tracks...');
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const startVideoRecording = async (facing?: 'user' | 'environment') => {
    const facingMode = facing || cameraFacing;
    console.log('Starting video recording with facingMode:', facingMode);

    try {
      // Ensure any previous stream is stopped before requesting a new one
      _stopCameraStream(); 

      // Try with exact facingMode first, fallback to non-exact if it fails
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { exact: facingMode },
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: true
        });
      } catch (err) {
        // Fallback: try without 'exact' constraint
        console.log('Exact facingMode not supported, trying without exact:', err);
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: facingMode,
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: true
        });
      }

      streamRef.current = stream;

      if (previewRef.current) {
        previewRef.current.srcObject = stream;
        await previewRef.current.play(); // This is already present, ensures preview plays
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

        _stopCameraStream(); // <<< MODIFIED: Use helper to stop stream
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('video');
    } catch (err) {
      console.error('Camera access denied:', err);
      alert('Please allow camera access');
      _stopCameraStream(); // Ensure stream is stopped even if start fails
      setRecording(null);
    }
  };

  const startImageCapture = async (facing: 'user' | 'environment') => {
    setCameraFacing(facing);
    try {
      _stopCameraStream();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      setShowImageCapture(true);
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
        await previewRef.current.play();
      }
    } catch (err) {
      console.error('Camera access denied for image capture:', err);
      alert('Please allow camera access.');
    }
  };

  const takePicture = () => {
    if (!previewRef.current || !canvasRef.current || !streamRef.current) return;

    const video = previewRef.current;
    const canvas = canvasRef.current;

    // Get video dimensions
    const videoTrack = streamRef.current.getVideoTracks()[0];
    const settings = videoTrack.getSettings();
    const width = settings.width || 640;
    const height = settings.height || 480;

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (context) {
      context.drawImage(video, 0, 0, width, height);
      canvas.toBlob(async (blob) => {
        if (blob) {
          const formData = new FormData();
          formData.append('file', blob, `image_${drill.id}_${Date.now()}.jpg`);
          try {
            await axios.post(`${API_BASE}/upload-media/${drill.id}/image`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            onUpdate();
          } catch (err) {
            console.error('Image upload failed:', err);
            alert('Failed to upload image');
          }
        }
        setShowImageCapture(false);
        _stopCameraStream();
      }, 'image/jpeg', 0.9);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop(); // This will trigger onstop, which handles stream stopping and setRecording(null)
    }
  };

  const switchCamera = () => {
    const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
    setCameraFacing(newFacing);

    // Stop current recording and stream first
    if (recording === 'video') {
      stopRecording(); // This stops MediaRecorder
    }
    _stopCameraStream(); // <<< ADDED: Explicitly stop previous stream tracks regardless of recording state

    // Then start new recording with the chosen camera
    setTimeout(() => {
      startVideoRecording(newFacing); // Pass newFacing directly to ensure it's used
    }, 300);
  };

  const currentIndex = allDrills.findIndex(d => d.id === drill.id);
  const hasNext = currentIndex < allDrills.length - 1;
  const hasPrev = currentIndex > 0;

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
        <button
          onClick={handleClose}
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

        <div style={{
          color: 'white',
          fontSize: '18px',
          fontWeight: 700,
          flex: 1,
          textAlign: 'center'
        }}>
          Drill #{drill.id}
          {hasChanges && <span style={{ color: '#FFD700', marginLeft: '8px' }}>●</span>}
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => hasPrev && onNavigate('prev')}
            disabled={!hasPrev}
            style={{
              background: hasPrev ? 'rgba(255,255,255,0.2)' : 'transparent',
              border: 'none',
              color: 'white',
              fontSize: '24px',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              cursor: hasPrev ? 'pointer' : 'not-allowed',
              opacity: hasPrev ? 1 : 0.3
            }}
          >
            ←
          </button>
          <button
            onClick={() => hasNext && onNavigate('next')}
            disabled={!hasNext}
            style={{
              background: hasNext ? 'rgba(255,255,255,0.2)' : 'transparent',
              border: 'none',
              color: 'white',
              fontSize: '24px',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              cursor: hasNext ? 'pointer' : 'not-allowed',
              opacity: hasNext ? 1 : 0.3
            }}
          >
            →
          </button>
        </div>
      </div>

      {/* Content - Scrollable */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '16px'
      }}>

        {/* Image Preview */}
        {editedDrill.image_url && (
          <div style={{ marginBottom: '16px', textAlign: 'center' }}>
            <img 
              src={getMediaUrl(editedDrill.image_url)} 
              alt="Drill"
              style={{
                maxWidth: '100%',
                maxHeight: '200px',
                borderRadius: '8px',
                border: '1px solid #e0e0e0',
                objectFit: 'cover'
              }}
            />
          </div>
        )}

        {/* Media Actions */}
        <div style={{
          background: '#f8f9fa',
          padding: '14px',
          borderRadius: '10px',
          marginBottom: '16px'
        }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700 }}>
            Media
          </h3>
          <div style={{ display: 'flex', justifyContent: 'space-around', gap: '10px' }}>
            <button onClick={() => startImageCapture('environment')} style={{ fontSize: '32px', background: 'none', border: 'none', cursor: 'pointer' }}>📷</button>
            <button onClick={startAudioRecording} style={{ fontSize: '32px', background: 'none', border: 'none', cursor: 'pointer' }}>🎙️</button>
            <button onClick={() => setShowCameraChoice(true)} style={{ fontSize: '32px', background: 'none', border: 'none', cursor: 'pointer' }}>🎬</button>
          </div>
        </div>

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
            value={editedDrill.text_catalan || ''}
            onChange={(e) => handleChange('text_catalan', e.target.value)}
            placeholder="Enter Catalan text..."
            rows={2}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '15px',
              border: '2px solid #e0e0e0',
              borderRadius: '8px',
              outline: 'none',
              resize: 'vertical'
            }}
          />
        </div>

        {/* Tachelhit */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: 600,
            color: '#333',
            marginBottom: '6px'
          }}>
            Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)
          </label>
          <textarea
            value={editedDrill.text_tachelhit || ''}
            onChange={(e) => handleChange('text_tachelhit', e.target.value)}
            placeholder="Enter Tachelhit text..."
            rows={2}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '15px',
              border: '2px solid #e0e0e0',
              borderRadius: '8px',
              outline: 'none',
              resize: 'vertical'
            }}
          />
        </div>

        {/* Arabic - Smaller on mobile */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '12px',
            fontWeight: 600,
            color: '#666',
            marginBottom: '6px',
            textAlign: 'right'
          }}>
            العربية
          </label>
          <textarea
            value={editedDrill.text_arabic || ''}
            onChange={(e) => handleChange('text_arabic', e.target.value)}
            placeholder="أدخل النص العربي..."
            rows={2}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '14px',
              border: '2px solid #e0e0e0',
              borderRadius: '8px',
              outline: 'none',
              resize: 'vertical',
              direction: 'rtl'
            }}
          />
        </div>

        {/* Save Button */}
        {hasChanges && (
          <button
            onClick={handleSave}
            style={{
              width: '100%',
              padding: '20px',
              background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              fontSize: '20px',
              fontWeight: 'bold',
              cursor: 'pointer',
              boxShadow: '0 6px 20px rgba(76, 175, 80, 0.4)',
              marginBottom: '20px'
            }}
          >
            ✓ Save Changes
          </button>
        )}
      </div>

      {/* Image Capture Modal */}
      {showImageCapture && (
        <div style={{...modalStyles.overlay}}>
          <div style={{...modalStyles.modal}}>
            <h3 style={{...modalStyles.title}}>Take Picture</h3>
            <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', borderRadius: '8px' }} />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <div style={{ marginTop: '15px', display: 'flex', justifyContent: 'space-around' }}>
              <button onClick={takePicture} style={{...modalStyles.button, background: '#4CAF50'}}>Take Picture</button>
              <button onClick={() => { setShowImageCapture(false); _stopCameraStream(); }} style={{...modalStyles.button, background: '#f44336'}}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Camera Choice Modal (for video) */}
      {showCameraChoice && (
        <div style={{...modalStyles.overlay}}>
          <div style={{...modalStyles.modal}}>
            <h3 style={{...modalStyles.title}}>Choose Video Camera</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <button onClick={() => { setCameraFacing('user'); setShowCameraChoice(false); startVideoRecording('user'); }} style={{...modalStyles.button, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
                <span style={{ fontSize: '32px' }}>🤳</span> Front Camera
              </button>
              <button onClick={() => { setCameraFacing('environment'); setShowCameraChoice(false); startVideoRecording('environment'); }} style={{...modalStyles.button, background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)'}}>
                <span style={{ fontSize: '32px' }}>📷</span> Back Camera
              </button>
              <button onClick={() => setShowCameraChoice(false)} style={{...modalStyles.cancelButton}}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Video Recording Modal */}
      {recording === 'video' && (
        <div style={{...modalStyles.overlay, background: 'black'}}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            <video ref={previewRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            <div style={{ position: 'absolute', top: '20px', right: '20px' }}>
              <button onClick={switchCamera} style={{...modalStyles.iconButton}}>🔄</button>
            </div>
          </div>
          <div style={{ padding: '30px 20px', background: 'rgba(0, 0, 0, 0.9)', display: 'flex', justifyContent: 'center' }}>
            <button onClick={stopRecording} style={{...modalStyles.stopButton}}>⏹</button>
          </div>
        </div>
      )}

      {/* Video Playback Modal */}
      {showVideo && drill.video_url && (
        <div onClick={() => setShowVideo(false)} style={{...modalStyles.overlay}}>
          <video src={getMediaUrl(drill.video_url)} controls autoPlay playsInline style={{ width: '100%', maxWidth: '640px', borderRadius: '12px' }} onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>
  );
}

const modalStyles: { [key: string]: CSSProperties } = {
  overlay: {
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
  },
  modal: {
    background: 'white',
    borderRadius: '16px',
    padding: '30px',
    maxWidth: '400px',
    width: '100%'
  },
  title: {
    margin: '0 0 24px 0',
    fontSize: '20px',
    fontWeight: 700,
    textAlign: 'center'
  },
  button: {
    padding: '20px',
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
  },
  cancelButton: {
    padding: '14px',
    background: '#e0e0e0',
    color: '#333',
    border: 'none',
    borderRadius: '10px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer'
  },
  iconButton: {
    width: '50px',
    height: '50px',
    borderRadius: '50%',
    background: 'rgba(255, 255, 255, 0.3)',
    border: '2px solid white',
    color: 'white',
    fontSize: '24px',
    cursor: 'pointer'
  },
  stopButton: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #ff4444 0%, #cc0000 100%)',
    color: 'white',
    border: '4px solid white',
    fontSize: '32px',
    cursor: 'pointer'
  }
};
