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
  is_correction_dataset?: boolean;
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
  // Estilos CSS para la animación de pulso
  const pulseStyle = `
    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.5; }
      100% { opacity: 1; }
    }
  `;
  const [editedDrill, setEditedDrill] = useState(drill);
  const [recording, setRecording] = useState<'audio' | 'video' | null>(null);
  const [showVideo, setShowVideo] = useState(false);
  const [showCameraChoice, setShowCameraChoice] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<'user' | 'environment'>('user');
  const [hasChanges, setHasChanges] = useState(false);
  const [showImageCapture, setShowImageCapture] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionResult, setTranscriptionResult] = useState<{rough: string, score: number} | null>(null);

  // Variables para permisos (mantenidas para futuras expansiones)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_permissionDenied, _setPermissionDenied] = useState<{audio: boolean; video: boolean}>({audio: false, video: false});

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const handleAutoTranscribe = async () => {
    const currentUrl = editedDrill.audio_url;
    if (!currentUrl) {
      alert('Please record audio first');
      return;
    }
    
    setIsTranscribing(true);
    setTranscriptionResult(null);
    try {
      console.log('🪄 [MOBILE_TRANSCR] Requesting transcription for:', currentUrl);
      const response = await axios.post(`${API_BASE}/transcribe/`, {
        audio_url: currentUrl
      });
      const { corrected_transcription, rough_transcription, similarity_score } = response.data;
      
      setTranscriptionResult({
        rough: rough_transcription,
        score: similarity_score
      });

      if (corrected_transcription) {
        setEditedDrill(prev => ({ ...prev, text_tachelhit: corrected_transcription }));
        setHasChanges(true);
        // Also auto-save it
        await axios.put(`${API_BASE}/drills/${drill.id}`, { text_tachelhit: corrected_transcription });
        onUpdate();
      }
    } catch (error) {
      console.error('Transcription failed:', error);
      alert('Failed to transcribe audio. Make sure you have drills marked as "Dataset" for best results.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const [isTranslating, setIsTranslating] = useState(false);

  const handleTranslate = async (source: string, target: string) => {
    const text = source === 'ca' ? editedDrill.text_catalan : editedDrill.text_tachelhit;
    if (!text) {
      alert(`Please enter ${source === 'ca' ? 'Catalan' : 'Tachelhit'} text first.`);
      return;
    }

    setIsTranslating(true);
    try {
      const res = await axios.post(`${API_BASE}/translate`, {
        text: text,
        source_lang: source,
        target_lang: target
      });
      const field = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
      setEditedDrill(prev => ({ ...prev, [field]: res.data.translated_text }));
      setHasChanges(true);
    } catch (err) {
      console.error('Translation failed:', err);
      alert('Translation failed. Please check your connection.');
    } finally {
      setIsTranslating(false);
    }
  };

  const toggleCorrectionDataset = async () => {
    const newValue = !editedDrill.is_correction_dataset;
    try {
      await axios.put(`${API_BASE}/drills/${drill.id}`, { is_correction_dataset: newValue });
      setEditedDrill({ ...editedDrill, is_correction_dataset: newValue });
      onUpdate();
    } catch (error) {
      console.error('Error toggling correction dataset:', error);
    }
  };

  useEffect(() => {
    setEditedDrill(drill);
    setHasChanges(false);
    
    // Limpiar streams al desmontar
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      // Limpiar cualquier timer pendiente
      // Los timers se limpian en sus respectivos handlers
    };
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
    
    // Verificar que el drill tenga un ID válido
    if (!drill || !drill.id) {
      alert('No se puede grabar audio: el drill no tiene un ID válido. Por favor, guarda el drill primero.');
      return;
    }

    // Comprovar si el navegador suporta MediaRecorder
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('El teu navegador no suporta la gravació d\'àudio. Si us plau, utilitza Chrome, Firefox o Edge.');
      return;
    }

    // Detectar iOS/Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    
    console.log('🎤 [Mobile] isIOS:', isIOS, 'isSafari:', isSafari, 'isAndroid:', isAndroid);
    console.log('🎤 [Mobile] UserAgent completo:', navigator.userAgent);
    console.log('🎤 [Mobile] Plataforma:', navigator.platform);

    try {
      // Primero, detener cualquier stream existente
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
      
      console.log('🎤 [Mobile] Requesting media with constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('🎤 [Mobile] Got stream:', stream.id, 'active:', stream.active);
      
      // Guardar la referencia del stream
      streamRef.current = stream;
      
      // Determinar el tipus MIME compatible
      let mimeType = 'audio/webm';
      let extension = 'webm';
      
      if (typeof MediaRecorder === 'undefined') {
        alert('MediaRecorder no suportat en aquest navegador. Prova Chrome o Firefox a Android.');
        stream.getTracks().forEach(track => track.stop());
        return;
      }

      // Detectar Chrome en Windows (según tu diagnóstico)
      const isChromeWindows = /Chrome/.test(navigator.userAgent) && /Windows/.test(navigator.userAgent);
      
      // iOS/Safari normalmente solo soporta AAC en MP4
      if (isIOS || isSafari) {
        mimeType = 'audio/mp4';
        extension = 'm4a';
        console.log('🎤 [Mobile] iOS/Safari detectat, utilitzant MP4/AAC');
      } else if (isAndroid) {
        // Android: preferir webm con opus
        if (MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
          mimeType = 'audio/webm; codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
          extension = 'mp4';
        } else {
          mimeType = 'audio/ogg; codecs=opus';
          extension = 'ogg';
        }
      } else if (isChromeWindows) {
        // Chrome en Windows: usar webm con opus (según diagnóstico)
        if (MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
          mimeType = 'audio/webm; codecs=opus';
          console.log('🎤 [Desktop] Chrome/Windows detectado, usando audio/webm; codecs=opus');
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
          console.log('🎤 [Desktop] Chrome/Windows detectado, usando audio/webm');
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
          extension = 'mp4';
          console.log('🎤 [Desktop] Chrome/Windows detectado, usando audio/mp4');
        } else {
          mimeType = 'audio/ogg; codecs=opus';
          extension = 'ogg';
          console.log('🎤 [Desktop] Chrome/Windows detectado, usando audio/ogg');
        }
      } else {
        // Otros navegadores/plataformas
        if (MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
          mimeType = 'audio/webm; codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
          extension = 'mp4';
        } else {
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
        
        // Detener el stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        
        if (chunksRef.current.length === 0) {
          console.warn('No hi ha dades d\'àudio gravades');
          // No mostrar alerta
          setRecording(null);
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mimeType });
        console.log('🎤 [Mobile] Blob creat, mida:', blob.size, 'tipus:', blob.type);
        
        // Verificar que el blob no esté vacío
        if (blob.size < 1024) {
          // No mostrar alerta
          setRecording(null);
          return;
        }
        
        const formData = new FormData();
        formData.append('file', blob, `audio_${drill.id}_${Date.now()}.${extension}`);

        try {
          console.log('📤 [Mobile] Pujant àudio a:', `${API_BASE}/upload-media/${drill.id}/audio`);
          const response = await axios.post(`${API_BASE}/upload-media/${drill.id}/audio`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 30000 // 30 segundos para móviles lentos
          });
          console.log('✅ Audio subido:', response.data);
          onUpdate();
        } catch (err: any) {
          console.error('❌ [Mobile] Error en pujar l\'àudio:', err);
          console.error('   Detalls:', err.response?.data || err.message);
          console.error('   Status:', err.response?.status);
          
          // Si es error 405, probar con un endpoint alternativo
          if (err.response?.status === 405) {
            console.log('⚠️ 405 Method Not Allowed, intentando endpoint alternativo...');
            try {
              // Intentar con un endpoint diferente
              const altResponse = await axios.post(`${API_BASE}/drills/${drill.id}/audio`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 30000
              });
              console.log('✅ Audio subido mediante endpoint alternativo:', altResponse.data);
              onUpdate();
            } catch (altErr: any) {
              console.error('❌ Error también en endpoint alternativo:', altErr);
            }
          }
        } finally {
          // Asegurar que el estado de grabación se restablece
          setRecording(null);
        }
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('Error de MediaRecorder:', event);
        alert('Error durant la gravació. Si us plau, torna-ho a provar.');
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('audio');
      console.log('🎤 [Mobile] Gravació d\'àudio iniciada amb tipus MIME:', mimeType);
      
      // Configurar un temporizador para detener automáticamente después de 60 segundos
      const autoStopTimer = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          console.log('⏱️ Deteniendo grabación automáticamente después de 60 segundos');
          mediaRecorderRef.current.stop();
        }
      }, 60000);
      
      // Guardar referencia del timer para limpiarlo si es necesario
      const timerRef = { current: autoStopTimer };
      
      // Limpiar el timer cuando se detenga la grabación
      const originalOnStop = mediaRecorderRef.current.onstop;
      mediaRecorderRef.current.onstop = async (...args) => {
        clearTimeout(timerRef.current);
        if (originalOnStop) {
          // @ts-ignore
          return originalOnStop.apply(mediaRecorderRef.current, args);
        }
      };
    } catch (err: any) {
      console.error('Accés al micròfon denegat:', err);
      // No mostrar alerta de error como solicitaste
      setRecording(null);
      // Limpiar stream si existe
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    }
  };

  // Helper to stop all tracks in the current stream and any active MediaRecorder
  const _stopCameraStream = () => {
    // Stop MediaRecorder if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('MediaRecorder still active, stopping it...');
      mediaRecorderRef.current.stop();
    }
    // Stop stream tracks
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
      // Detener cualquier stream existente
      _stopCameraStream();

      // Intentar con facingMode exacto primero
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
        // Fallback: intentar sin 'exact'
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

      // Asegurar que el elemento video esté disponible antes de asignar srcObject
      // Esperar un momento para que el DOM se actualice
      setTimeout(() => {
        if (previewRef.current) {
          previewRef.current.srcObject = stream;
          previewRef.current.play().catch(e => {
            console.error('Error playing video preview:', e);
          });
        } else {
          console.warn('previewRef.current is null, retrying...');
          // Intentar de nuevo después de un breve retraso
          setTimeout(() => {
            if (previewRef.current) {
              previewRef.current.srcObject = stream;
              previewRef.current.play();
            }
          }, 100);
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
          onUpdate();
        } catch (err) {
          console.error('Video upload failed:', err);
          // No mostrar alerta
        }

        _stopCameraStream();
        setRecording(null);
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('Error de MediaRecorder (video):', event);
        // No mostrar alerta
        _stopCameraStream();
        setRecording(null);
      };

      mediaRecorderRef.current.start();
      setRecording('video');
    } catch (err: any) {
      console.error('Camera access denied:', err);
      // No mostrar alerta
      _stopCameraStream();
      setRecording(null);
    }
  };

  const startImageCapture = async (facing: 'user' | 'environment') => {
    setCameraFacing(facing);
    try {
      _stopCameraStream();
      
      // Para la cámara trasera, usar 'environment', para frontal 'user'
      // No usar 'exact' porque algunos navegadores no lo soportan
      const constraints = {
        video: { 
          facingMode: facing,
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };
      
      console.log('📸 Solicitando cámara con constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      streamRef.current = stream;
      
      // Esperar un momento para que el elemento video esté disponible
      setTimeout(() => {
        if (previewRef.current) {
          previewRef.current.srcObject = stream;
          previewRef.current.play().catch(e => {
            console.error('Error playing video:', e);
          });
        } else {
          console.warn('previewRef.current aún no está disponible');
          // Intentar de nuevo en 100ms
          setTimeout(() => {
            if (previewRef.current) {
              previewRef.current.srcObject = stream;
              previewRef.current.play();
            }
          }, 100);
        }
      }, 100);
      
      setShowImageCapture(true);
    } catch (err: any) {
      console.error('Camera access denied for image capture:', err);
      // No mostrar alerta automática
      // Solo mostrar alerta si es un error de permiso
      if (err.name === 'NotAllowedError') {
        // No mostrar alerta como solicitaste
      } else if (err.name === 'NotFoundError') {
        // No mostrar alerta
      }
    }
  };

  const takePicture = () => {
    if (!previewRef.current || !canvasRef.current || !streamRef.current) return;

    const video = previewRef.current;
    const canvas = canvasRef.current;

    // Esperar a que el video esté listo
    if (video.readyState !== video.HAVE_ENOUGH_DATA) {
      console.log('Video not ready, waiting...');
      setTimeout(takePicture, 500);
      return;
    }

    // Esperar un poco más para asegurar que el video tenga fotogramas
    setTimeout(() => {
      // Get video dimensions
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
        // Limpiar canvas con color blanco primero
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, width, height);
        
        // Dibujar el video
        context.drawImage(video, 0, 0, width, height);
        
        // Verificar que el canvas no esté vacío o negro
        const imageData = context.getImageData(0, 0, 1, 1).data;
        console.log('Pixel sample:', imageData[0], imageData[1], imageData[2]);
        
        // Si el pixel es completamente negro (0,0,0), podría ser un problema
        if (imageData[0] === 0 && imageData[1] === 0 && imageData[2] === 0) {
          console.warn('Canvas appears to be black, trying alternative approach...');
          // Intentar de nuevo con un pequeño retraso
          setTimeout(() => {
            context.drawImage(video, 0, 0, width, height);
            takePicture();
          }, 300);
          return;
        }
        
        canvas.toBlob(async (blob) => {
          if (blob && blob.size > 1024) {
            const formData = new FormData();
            formData.append('file', blob, `image_${drill.id}_${Date.now()}.jpg`);
            try {
              await axios.post(`${API_BASE}/upload-media/${drill.id}/image`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
              });
              onUpdate();
              // No mostrar mensaje de confirmación
            } catch (err) {
              console.error('Image upload failed:', err);
              alert('Failed to upload image');
            }
          } else {
            console.error('Blob is too small or empty:', blob?.size);
            alert('La foto no se pudo capturar correctamente. Intenta de nuevo.');
          }
          setShowImageCapture(false);
          _stopCameraStream();
        }, 'image/jpeg', 0.9);
      }
    }, 300); // Esperar 300ms adicionales para asegurar que el video esté listo
  };

  const stopRecording = () => {
    console.log('🛑 Deteniendo grabación, tipo:', recording);
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('🛑 MediaRecorder está activo, llamando stop()');
      mediaRecorderRef.current.stop();
      // El estado se establecerá en null en onstop
    } else {
      console.log('🛑 MediaRecorder no está activo o no existe');
      // Si no hay MediaRecorder activo, pero hay un stream, detenerlo
      if (streamRef.current) {
        console.log('🛑 Deteniendo stream directamente');
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      // Restablecer inmediatamente el estado de grabación
      setRecording(null);
    }
  };

  const switchCamera = () => {
    const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
    setCameraFacing(newFacing);

    // Detener grabación y stream de manera sincrónica
    if (recording === 'video') {
      stopRecording(); // Esto detiene MediaRecorder (se ejecuta onstop)
    }
    // Asegurar que el stream se detiene inmediatamente
    _stopCameraStream();

    // Esperar un momento para que el estado se actualice y los recursos se liberen
    setTimeout(() => {
      // Verificar que no haya una grabación activa antes de iniciar una nueva
      if (!recording || recording !== 'video') {
        startVideoRecording(newFacing);
      } else {
        // Si aún hay grabación, reintentar después de otro breve retraso
        setTimeout(() => startVideoRecording(newFacing), 200);
      }
    }, 300);
  };

  const currentIndex = allDrills.findIndex(d => d.id === drill.id);
  const hasNext = currentIndex < allDrills.length - 1;
  const hasPrev = currentIndex > 0;

  return (
    <>
      <style>{pulseStyle}</style>
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
          
          {/* Media Playback - Audio y Video existentes */}
          {(editedDrill.audio_url || editedDrill.video_url) && (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              gap: '10px', 
              marginBottom: '12px',
              flexWrap: 'wrap'
            }}>
              {editedDrill.audio_url && (
                <button 
                  onClick={() => {
                    const audio = new Audio(getMediaUrl(editedDrill.audio_url));
                    audio.play();
                  }}
                  style={{ 
                    fontSize: '14px', 
                    padding: '8px 12px',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>▶️</span> Reproducir Audio
                </button>
              )}
              {editedDrill.video_url && (
                <button 
                  onClick={() => setShowVideo(true)}
                  style={{ 
                    fontSize: '14px', 
                    padding: '8px 12px',
                    background: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>🎥</span> Ver Video
                </button>
              )}
            </div>
          )}
          
          {/* Media Recording Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-around', gap: '10px', flexWrap: 'wrap' }}>
            <button 
              onClick={() => startImageCapture('environment')} 
              style={{ 
                fontSize: '32px', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer',
                padding: '5px'
              }}
              title="Tomar foto"
            >
              📷
            </button>
            {recording === 'audio' ? (
              <button 
                onClick={stopRecording} 
                style={{ 
                  fontSize: '32px', 
                  background: 'none', 
                  border: 'none', 
                  cursor: 'pointer', 
                  color: '#ff4444',
                  padding: '5px'
                }}
                title="Detener grabación de audio"
              >
                ⏹️
              </button>
            ) : (
              <button 
                onClick={startAudioRecording} 
                style={{ 
                  fontSize: '32px', 
                  background: 'none', 
                  border: 'none', 
                  cursor: 'pointer',
                  padding: '5px'
                }}
                title="Grabar audio"
              >
                🎙️
              </button>
            )}
            <button 
              onClick={() => setShowCameraChoice(true)} 
              style={{ 
                fontSize: '32px', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer',
                padding: '5px'
              }}
              title="Grabar video"
            >
              🎬
            </button>
            <button 
              onClick={() => startImageCapture('user')} 
              style={{ 
                fontSize: '32px', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer',
                padding: '5px'
              }}
              title="Probar cámara frontal"
            >
              🤳
            </button>
          </div>
          {recording === 'audio' && (
            <div style={{ 
              textAlign: 'center', 
              marginTop: '8px', 
              color: '#ff4444', 
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}>
              <div style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: '#ff4444',
                animation: 'pulse 1s infinite'
              }}></div>
              Grabando audio... Toca ⏹️ para detener
            </div>
          )}
        </div>

        {/* Catalan */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{
              fontSize: '14px',
              fontWeight: 600,
              color: '#333'
            }}>
              Català
            </label>
            <button
              onClick={() => handleTranslate('ca', 'shi')}
              disabled={isTranslating || !editedDrill.text_catalan}
              style={{
                background: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '12px',
                cursor: (isTranslating || !editedDrill.text_catalan) ? 'not-allowed' : 'pointer',
                opacity: (isTranslating || !editedDrill.text_catalan) ? 0.6 : 1
              }}
            >
              {isTranslating ? '⏳...' : '→ Tachelhit'}
            </button>
          </div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{
              fontSize: '14px',
              fontWeight: 600,
              color: '#333'
            }}>
              Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)
            </label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
               <button
                onClick={() => handleTranslate('shi', 'ca')}
                disabled={isTranslating || !editedDrill.text_tachelhit}
                style={{
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '12px',
                  cursor: (isTranslating || !editedDrill.text_tachelhit) ? 'not-allowed' : 'pointer',
                  opacity: (isTranslating || !editedDrill.text_tachelhit) ? 0.6 : 1
                }}
              >
                {isTranslating ? '⏳...' : '→ Catalan'}
              </button>
               <button
                onClick={handleAutoTranscribe}
                disabled={isTranscribing || !editedDrill.audio_url}
                style={{
                  background: isTranscribing ? '#eee' : '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '12px',
                  cursor: (isTranscribing || !editedDrill.audio_url) ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {isTranscribing ? '⏳...' : '🪄 Auto'}
              </button>
              <label style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '4px', 
                fontSize: '12px', 
                cursor: 'pointer',
                color: editedDrill.is_correction_dataset ? '#4CAF50' : '#666',
                fontWeight: editedDrill.is_correction_dataset ? 700 : 400
              }}>
                <input 
                  type="checkbox" 
                  checked={editedDrill.is_correction_dataset || false} 
                  onChange={toggleCorrectionDataset}
                />
                Dataset
              </label>
            </div>
          </div>
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
          {transcriptionResult && (
            <div style={{ marginTop: '4px', fontSize: '11px', color: '#666' }}>
              Rough: <span style={{ fontFamily: 'monospace' }}>{transcriptionResult.rough}</span> (Score: {Math.round(transcriptionResult.score * 100)}%)
            </div>
          )}
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
            <h3 style={{...modalStyles.title}}>Tomar Foto</h3>
            <div style={{ position: 'relative', marginBottom: '15px' }}>
              <video 
                ref={previewRef} 
                autoPlay 
                muted 
                playsInline 
                style={{ 
                  width: '100%', 
                  borderRadius: '8px',
                  transform: cameraFacing === 'user' ? 'scaleX(-1)' : 'none'
                }} 
              />
              <div style={{
                position: 'absolute',
                bottom: '10px',
                left: '10px',
                background: 'rgba(0,0,0,0.7)',
                color: 'white',
                padding: '5px 10px',
                borderRadius: '5px',
                fontSize: '12px'
              }}>
                Cámara {cameraFacing === 'user' ? 'frontal' : 'trasera'}
              </div>
            </div>
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <div style={{ marginTop: '15px', display: 'flex', justifyContent: 'space-around', gap: '10px' }}>
              <button 
                onClick={() => {
                  const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
                  startImageCapture(newFacing);
                }}
                style={{
                  padding: '10px 15px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                🔄 Cambiar Cámara
              </button>
              <button 
                onClick={takePicture} 
                style={{
                  padding: '10px 20px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold'
                }}
              >
                📸 Tomar Foto
              </button>
            </div>
            <div style={{ marginTop: '15px', display: 'flex', justifyContent: 'center' }}>
              <button 
                onClick={() => { 
                  setShowImageCapture(false); 
                  _stopCameraStream(); 
                }} 
                style={{
                  padding: '8px 16px',
                  background: '#f44336',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Cancelar
              </button>
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
    </>
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
