import { useState, useEffect } from 'react';
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

  // Sync local states if navigation triggers card object reloads
  useEffect(() => {
    setLocalDrill({ ...drill });
  }, [drill]);

  const handleFieldChange = async (field: keyof Drill, value: string) => {
    const updated = { ...localDrill, [field]: value };
    setLocalDrill(updated);
    try {
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [field]: value });
      onUpdate();
    } catch (err) {
      console.error('Auto-save step failed inside editor context:', err);
    }
  };

  // 🌐 Non-Destructive Card Translator Handler
  const handleTranslateAction = async (source: 'ca' | 'shi', target: 'ca' | 'shi') => {
    const sourceText = source === 'ca' ? localDrill.text_catalan : localDrill.text_tachelhit;
    if (!sourceText) return alert('Source translation field is currently empty.');

    const targetField = target === 'shi' ? 'text_tachelhit' : 'text_catalan';
    setAiLoadingKey(`trans-${targetField}`);

    try {
      const res = await axios.post(`${API_BASE}/translate`, {
        text: sourceText,
        source_lang: source,
        target_lang: target
      });

      const generatedTranslation = res.data.translated_text;
      const currentContent = localDrill[targetField] || '';

      // Safe append: keeps previously written texts safe from deletion
      const safeAppendText = currentContent.trim()
        ? `${currentContent} (${generatedTranslation})`
        : generatedTranslation;

      setLocalDrill(prev => ({ ...prev, [targetField]: safeAppendText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { [targetField]: safeAppendText });
      onUpdate();
    } catch (err) {
      alert('Translation service failed inside editing module.');
    } finally {
      setAiLoadingKey(null);
    }
  };

  // 🪄 Non-Destructive Card Voice Transcriber Handler
  const handleTranscribeAction = async () => {
    const mediaSource = localDrill.audio_url || localDrill.video_url;
    if (!mediaSource) return;
    setAiLoadingKey('transcribe-voice');

    try {
      const res = await axios.post(`${API_BASE}/transcribe/`, { audio_url: mediaSource });
      const transcriptionResult = res.data.corrected_transcription;
      const currentTachelhit = localDrill.text_tachelhit || '';

      const safeAppendText = currentTachelhit.trim()
        ? `${currentTachelhit} (${transcriptionResult})`
        : transcriptionResult;

      setLocalDrill(prev => ({ ...prev, text_tachelhit: safeAppendText }));
      await axios.put(`${API_BASE}/drills/${localDrill.id}`, { text_tachelhit: safeAppendText });
      onUpdate();
    } catch (err) {
      alert('AI Speech transcription failed inside editing module.');
    } finally {
      setAiLoadingKey(null);
    }
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'white', zIndex: 11000, display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar Controls */}
      <div style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'white' }}>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: '24px', cursor: 'pointer' }}>✕</button>
        <span style={{ fontWeight: 700, fontSize: '18px' }}>Edit Card #{localDrill.id}</span>
        <div style={{ width: '24px' }} />
      </div>

      {/* Editor Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Media Attachments previews displayed instantly at the top */}
        {localDrill.image_url && (
          <img src={getMediaUrl(localDrill.image_url)} alt="Drill Asset" style={{ width: '100%', aspectRatio: '1/1', borderRadius: '12px', objectFit: 'cover', border: '1px solid #eee' }} />
        )}

        {localDrill.video_url && (
          <video src={getMediaUrl(localDrill.video_url)} controls playsInline style={{ width: '100%', borderRadius: '12px', background: '#000' }} />
        )}

        {localDrill.audio_url && (
          <button onClick={() => new Audio(getMediaUrl(localDrill.audio_url!)).play()} style={{ width: '100%', padding: '12px', background: '#f3f4f6', border: 'none', borderRadius: '10px', fontWeight: 600, cursor: 'pointer' }}>
            🔊 Test Audio Recording Playback
          </button>
        )}

        {/* 🌐 PORTED INLINE CONTROL PANEL: Integrated right into the editor module */}
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

        {/* Text Area form cards inputs */}
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

      {/* Navigation Footer Target target switches */}
      <div style={{ display: 'flex', borderTop: '1px solid #eee', padding: '12px', background: '#f8f9fa', justifyContent: 'space-between' }}>
        <button onClick={() => onNavigate('prev')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600 }}>◀ Previous</button>
        <button onClick={() => onNavigate('next')} style={{ padding: '12px 24px', background: '#374151', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600 }}>Next ▶</button>
      </div>
    </div>
  );
}