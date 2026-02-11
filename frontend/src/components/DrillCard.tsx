import { useState, useRef } from 'react';
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
  const [cameraFacing, setCameraFacing] = useState<'user' | 'environment'>('user');
  const [permissionDenied, setPermissionDenied] = useState<{audio: boolean; video: boolean}>({audio: false, video: false});

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

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
        video: { facingMode: cameraFacing, width: 640, height: 480 },
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
            padding: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
          }}>
            <h2 style={{ margin: 0, color: 'white', fontSize: '20px', fontWeight: 700 }}>
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
          <div style={{ padding: '20px' }}>
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
              </label>
              <input
                value={editedDrill.tag || ''}
                onChange={(e) => setEditedDrill({ ...editedDrill, tag: e.target.value })}
                placeholder="e.g., greetings, colors, numbers..."
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
              <textarea
                value={editedDrill.text_catalan || ''}
                onChange={(e) => setEditedDrill({ ...editedDrill, text_catalan: e.target.value })}
                placeholder="Enter Catalan text..."
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
            </div>

            {/* Tachelhit */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                color: '#333',
                marginBottom: '8px'
              }}>
                Tachelhit (ⵜⴰⵛⵍⵃⵉⵜ)
              </label>
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
                  padding: '16px',
                  background: '#e0e0e0',
                  color: '#333',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: '16px',
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
                  padding: '16px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: '16px',
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
        gap: '10px',
        marginBottom: '12px'
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
              padding: '16px',
              background: drill.audio_url ? 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)' : 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '16px',
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
              padding: '16px',
              background: drill.video_url ? 'linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%)' : 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '16px',
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
                const audio = new Audio(getMediaUrl(drill.audio_url));
                audio.play();
              }}
              style={{
                flex: 1,
                padding: '10px',
                background: 'white',
                color: '#4CAF50',
                border: '2px solid #4CAF50',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              ▶️ Play Audio
            </button>
          )}
          {drill.video_url && (
            <button
              onClick={() => setShowVideo(true)}
              style={{
                flex: 1,
                padding: '10px',
                background: 'white',
                color: '#9C27B0',
                border: '2px solid #9C27B0',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              ▶️ Play Video
            </button>
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
          onClick={() => setShowVideo(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.9)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <video
              src={getMediaUrl(drill.video_url)}
              controls
              autoPlay
              playsInline
              style={{
                width: '100%',
                maxWidth: '640px',
                borderRadius: '12px'
              }}
            />
          </div>
        </div>
      )}

      {/* Edit Button */}
      <button
        onClick={() => setIsEditing(true)}
        style={{
          width: '100%',
          padding: '12px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          fontSize: '15px',
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
