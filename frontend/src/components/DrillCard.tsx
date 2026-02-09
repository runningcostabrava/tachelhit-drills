import { useState, useRef } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

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
  const [generating, setGenerating] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const handleSave = async () => {
    try {
      await axios.put(`${API_BASE}/drills/${drill.id}`, editedDrill);
      setIsEditing(false);
      onUpdate();
    } catch (error) {
      console.error('Error updating drill:', error);
      alert('Failed to update drill');
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

  const startVideoRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 640, height: 480 },
        audio: true
      });
      streamRef.current = stream;

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

  const generateImage = async () => {
    if (!editedDrill.text_catalan) {
      alert('Please add Catalan text first!');
      return;
    }

    const searchPhrase = prompt(
      '🔍 Edit search phrase for image:\n\n(The Catalan text will be auto-translated)',
      editedDrill.text_catalan
    );

    if (!searchPhrase || !searchPhrase.trim()) return;

    setGenerating(true);
    try {
      await axios.post(`${API_BASE}/generate-image/${drill.id}`, {
        search_query: searchPhrase.trim()
      });
      onUpdate();
    } catch (err: any) {
      alert(`Image generation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <>
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

        {/* Image */}
        {drill.image_url && (
          <img
            src={`${API_BASE}${drill.image_url}`}
            alt="Drill"
            style={{
              width: '100%',
              height: '180px',
              objectFit: 'cover',
              borderRadius: '8px',
              marginBottom: '12px',
              cursor: 'pointer'
            }}
            onClick={() => setIsEditing(true)}
          />
        )}

        {/* Text Fields - Display Only */}
        <div
          style={{ marginBottom: '12px', cursor: 'pointer' }}
          onClick={() => setIsEditing(true)}
        >
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#333', marginBottom: '6px' }}>
            {drill.text_catalan || <span style={{ color: '#999' }}>Tap to add Catalan text</span>}
          </div>
          <div style={{ fontSize: '15px', color: '#555', marginBottom: '6px' }}>
            {drill.text_tachelhit || <span style={{ color: '#999' }}>Tap to add Tachelhit text</span>}
          </div>
          <div style={{ fontSize: '15px', color: '#555', direction: 'rtl' }}>
            {drill.text_arabic || <span style={{ color: '#999' }}>انقر لإضافة نص عربي</span>}
          </div>
        </div>

      {/* Media Controls */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '8px',
        marginBottom: '12px'
      }}>
        {/* Audio */}
        {drill.audio_url && !recording ? (
          <button
            onClick={() => {
              const audio = new Audio(`${API_BASE}${drill.audio_url}`);
              audio.play();
            }}
            style={{
              padding: '10px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ▶️ Audio
          </button>
        ) : null}

        {recording === 'audio' ? (
          <button
            onClick={stopRecording}
            style={{
              padding: '10px',
              background: '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ⏹ Stop
          </button>
        ) : !recording && (
          <button
            onClick={startAudioRecording}
            style={{
              padding: '10px',
              background: drill.audio_url ? '#2196F3' : '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🎤 {drill.audio_url ? 'Re-record' : 'Record'}
          </button>
        )}

        {/* Video */}
        {drill.video_url && !recording ? (
          <button
            onClick={() => setShowVideo(true)}
            style={{
              padding: '10px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ▶️ Video
          </button>
        ) : null}

        {recording === 'video' ? (
          <button
            onClick={stopRecording}
            style={{
              padding: '10px',
              background: '#ff4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ⏹ Stop Video
          </button>
        ) : !recording && (
          <button
            onClick={startVideoRecording}
            style={{
              padding: '10px',
              background: drill.video_url ? '#2196F3' : '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🎥 {drill.video_url ? 'Re-record' : 'Record'}
          </button>
        )}

        {/* Image Generate */}
        <button
          onClick={generateImage}
          disabled={generating}
          style={{
            padding: '10px',
            background: generating ? '#999' : (drill.image_url ? '#2196F3' : '#4CAF50'),
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: generating ? 'not-allowed' : 'pointer',
            gridColumn: drill.audio_url && drill.video_url ? 'span 2' : 'span 1'
          }}
        >
          {generating ? '⏳ Generating...' : (drill.image_url ? '🔄 Regenerate' : '🎨 Generate')}
        </button>
      </div>

      {/* Video Recording Preview */}
      {recording === 'video' && (
        <div style={{
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
        }}>
          <div style={{ textAlign: 'center' }}>
            <video
              ref={previewRef}
              autoPlay
              muted
              playsInline
              style={{
                width: '100%',
                maxWidth: '640px',
                borderRadius: '12px',
                marginBottom: '20px'
              }}
              onLoadedMetadata={() => {
                if (previewRef.current && streamRef.current) {
                  previewRef.current.srcObject = streamRef.current;
                }
              }}
            />
            <div style={{ fontSize: '18px', color: 'white', marginBottom: '20px', fontWeight: 600 }}>
              🔴 Recording...
            </div>
            <button
              onClick={stopRecording}
              style={{
                padding: '16px 40px',
                background: '#ff4444',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                fontSize: '18px',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              ⏹ Stop Recording
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
              src={`${API_BASE}${drill.video_url}`}
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
