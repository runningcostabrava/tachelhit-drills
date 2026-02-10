import { useState, useRef, useEffect } from 'react';
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

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

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
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', blob, `audio_${drill.id}_${Date.now()}.webm`);

        try {
          await axios.post(`${API_BASE}/upload-media/${drill.id}/audio`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          onUpdate();
        } catch (err) {
          console.error('Audio upload failed:', err);
          alert('Failed to upload audio');
        }

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setRecording('audio');
    } catch (err) {
      console.error('Microphone access denied:', err);
      alert('Please allow microphone access');
    }
  };

  const startVideoRecording = async (facing?: 'user' | 'environment') => {
    const facingMode = facing || cameraFacing;
    console.log('Starting video recording with facingMode:', facingMode);

    try {
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
        console.log('Exact facingMode not supported, trying without exact');
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
        // IMPORTANT: Call play() to show the video preview
        await previewRef.current.play();
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
    } catch (err) {
      console.error('Camera access denied:', err);
      alert('Please allow camera access');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setRecording(null);
    }
  };

  const switchCamera = () => {
    const newFacing = cameraFacing === 'user' ? 'environment' : 'user';
    setCameraFacing(newFacing);

    if (recording === 'video' && streamRef.current) {
      stopRecording();
      setTimeout(() => {
        startVideoRecording();
      }, 300);
    }
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
        {/* Tag */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '12px',
            fontWeight: 600,
            color: '#666',
            marginBottom: '6px'
          }}>
            Tag (optional)
          </label>
          <input
            value={editedDrill.tag || ''}
            onChange={(e) => handleChange('tag', e.target.value)}
            placeholder="e.g., greetings..."
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '14px',
              border: '2px solid #e0e0e0',
              borderRadius: '8px',
              outline: 'none'
            }}
          />
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

        {/* Recording Section */}
        <div style={{
          background: '#f8f9fa',
          padding: '14px',
          borderRadius: '10px',
          marginBottom: '16px'
        }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700 }}>
            🎙️ Recording
          </h3>

          {/* Audio Recording */}
          <div style={{ marginBottom: '12px' }}>
            {recording === 'audio' ? (
              <button
                onClick={stopRecording}
                style={{
                  width: '100%',
                  padding: '14px',
                  background: '#ff4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                ⏹ Stop Audio
              </button>
            ) : (
              <button
                onClick={startAudioRecording}
                style={{
                  width: '100%',
                  padding: '14px',
                  background: drill.audio_url ? 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)' : 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                🎤 {drill.audio_url ? 'Re-record' : 'Record'} Audio
              </button>
            )}
            {drill.audio_url && !recording && (
              <button
                onClick={() => {
                  const audio = new Audio(getMediaUrl(drill.audio_url));
                  audio.play();
                }}
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
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
          </div>

          {/* Video Recording */}
          <div>
            {recording === 'video' ? null : (
              <button
                onClick={() => setShowCameraChoice(true)}
                style={{
                  width: '100%',
                  padding: '14px',
                  background: drill.video_url ? 'linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%)' : 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '15px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                🎥 {drill.video_url ? 'Re-record' : 'Record'} Video
              </button>
            )}
            {drill.video_url && !recording && (
              <button
                onClick={() => setShowVideo(true)}
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
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
        </div>

        {/* Save Button */}
        {hasChanges && (
          <button
            onClick={handleSave}
            style={{
              width: '100%',
              padding: '18px',
              background: 'linear-gradient(135deg, #4CAF50 0%, #388E3C 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              fontSize: '18px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)',
              marginBottom: '20px'
            }}
          >
            ✓ Save Changes
          </button>
        )}
      </div>

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
            <h3 style={{
              margin: '0 0 24px 0',
              fontSize: '20px',
              fontWeight: 700,
              textAlign: 'center'
            }}>
              Choose Camera
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <button
                onClick={() => {
                  setCameraFacing('user');
                  setShowCameraChoice(false);
                  startVideoRecording('user');  // Pass facing mode directly
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
                  boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px'
                }}
              >
                <span style={{ fontSize: '32px' }}>🤳</span>
                <span>Front Camera (Selfie)</span>
              </button>

              <button
                onClick={() => {
                  setCameraFacing('environment');
                  setShowCameraChoice(false);
                  startVideoRecording('environment');  // Pass facing mode directly
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
                  boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px'
                }}
              >
                <span style={{ fontSize: '32px' }}>📷</span>
                <span>Back Camera</span>
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

      {/* Video Recording Modal */}
      {recording === 'video' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'black',
          zIndex: 20000,
          display: 'flex',
          flexDirection: 'column'
        }}>
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
            />

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
              gap: '10px'
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
                cursor: 'pointer'
              }}
            >
              🔄
            </button>
          </div>

          <div style={{
            padding: '30px 20px',
            background: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            justifyContent: 'center'
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
                cursor: 'pointer',
                boxShadow: '0 6px 20px rgba(255, 68, 68, 0.5)'
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
            zIndex: 20000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
        >
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
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
