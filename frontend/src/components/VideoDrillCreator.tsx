import React, { useState, useRef, useEffect } from 'react';
import { API_BASE } from '../config';

// Turn raw backend/yt-dlp errors into clear, actionable Catalan guidance
function friendlyCaptureError(msg: string): string {
  const m = (msg || '').toLowerCase();
  if (/bot|sign in to confirm|cookies|403|forbidden/.test(m)) {
    return "⚠️ YouTube està bloquejant la descàrrega des del servidor (detecció de bots). "
      + "Dues solucions: (1) descarrega el vídeo al teu ordinador i puja'l amb «Puja fitxers» aquí sota, "
      + "o (2) enganxa les teves cookies de YouTube (format Netscape) al camp «Cookies».";
  }
  if (/timeout|timed out|excedit/.test(m)) {
    return "⚠️ La descàrrega ha trigat massa. Prova amb un vídeo més curt o puja el fitxer manualment.";
  }
  return msg || 'Hi ha hagut un error.';
}

interface VideoSegment {
  start: number;
  end: number;
  text: string;
  text_catalan?: string;
  text_arabic?: string;
  text_tachelhit?: string;
  text_tachelhit_suggested?: string; // machine draft (foreign-source mode)
  text_ocr?: string;
  correction_score?: number;
  selected?: boolean;
}

interface VideoInfo {
  title: string;
  thumbnail: string;
  duration: number;
  original_language: string;
  segments: VideoSegment[];
}

const VideoDrillCreator: React.FC = () => {
  const [url, setUrl] = useState('');
  const [cookies, setCookies] = useState('');
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [vttFile, setVttFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [tempVideoPath, setTempVideoPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (error) errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, [error]);
  const [tag, setTag] = useState('video_capture');
  const [audioOnly, setAudioOnly] = useState(false);
  const [autoMode, setAutoMode] = useState(false);
  const [makeReels, setMakeReels] = useState(false);
  const [foreignSource, setForeignSource] = useState(false);
  const [lyrics, setLyrics] = useState('');
  const [autoStatus, setAutoStatus] = useState<string | null>(null);

  // Polls a fully server-side auto-drills job (URL captures). The pipeline
  // keeps running on the server even if this page is closed.
  const AUTO_STATUS_LABELS: Record<string, string> = {
    PENDING: 'A la cua…',
    IN_PROGRESS: 'Transcrivint (Whisper)…',
    TRANSCRIBING: 'Transcrivint (Whisper)…',
    CORRECTING: 'Corregint amb el teu conjunt de frases…',
    TRANSLATING: 'Traduint a Català · العربية · ⵜⴰⵛⵍⵃⵉⵜ…',
    CREATING_DRILLS: 'Retallant el contingut i creant els drills…',
    GENERATING_REELS: 'Generant els reels verticals…',
  };

  const pollAutoJob = (jobId: number, title: string) => {
    let attempts = 0;
    const maxAttempts = 400; // ~20 minutes; the full pipeline includes clipping

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setError('El procés automàtic està trigant — continua executant-se al servidor; revisa els teus drills més tard.');
        setAutoStatus(null);
        setLoading(false);
        return;
      }
      attempts++;
      try {
        const res = await fetch(`${API_BASE}/video-analysis/job/${jobId}`);
        const data = await res.json();

        if (data.status === 'FAILED') {
          setError(`El procés automàtic ha fallat: ${data.error_message}`);
          setAutoStatus(null);
          setLoading(false);
        } else if (data.drills_created) {
          alert(`⚡ Captura automàtica: s'han creat ${data.drills_created.length} drills de "${title}"!`);
          setUrl('');
          setVideoInfo(null);
          setTempVideoPath(null);
          setAutoStatus(null);
          setLoading(false);
        } else {
          setAutoStatus(AUTO_STATUS_LABELS[data.status] || `${data.status}…`);
          setTimeout(poll, 3000);
        }
      } catch (e) {
        console.error('Auto poll error:', e);
        setTimeout(poll, 3000);
      }
    };
    setTimeout(poll, 3000);
  };

  // Auto mode: correct -> translate (all languages) -> create drills from
  // EVERY segment, no manual review stop
  const runAutoPipeline = async (meta: Omit<VideoInfo, 'segments'>, rawSegments: any[], videoPath: string | null) => {
    try {
      let segs = rawSegments;

      // 1. Correction layer (Tachelhit-ish sources only)
      if (['auto', 'shi', 'ber', ''].includes(meta.original_language || 'auto')) {
        try {
          const r = await fetch(`${API_BASE}/video-analysis/correct`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ segments: segs }),
          });
          if (r.ok) segs = await r.json();
        } catch (e) {
          console.warn('Auto-correct failed, continuing with raw transcription', e);
        }
      }

      // 2. Translate into all drill languages
      const tr = await fetch(`${API_BASE}/video-analysis/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          segments: segs,
          source_lang: meta.original_language || 'auto',
          target_langs: ['ca', 'ar', 'shi'],
        }),
      });
      if (tr.ok) segs = await tr.json();

      // 3. Create drills from every segment
      const cd = await fetch(`${API_BASE}/video-analysis/create-drills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url || null,
          video_path: videoPath,
          segments: segs,
          source_lang: meta.original_language,
          tag,
          cookies: cookies || null,
        }),
      });
      if (!cd.ok) throw new Error('No s\'han pogut crear els drills');
      const result = await cd.json();
      alert(`⚡ Mode automàtic: s'han creat ${result.drills_created.length} drills de "${meta.title}"!`);
      setVideoInfo(null);
      setUrl('');
      setVideoFile(null);
      setVttFile(null);
      setTempVideoPath(null);
    } catch (err: any) {
      setError(`El mode automàtic s'ha aturat: ${err.message} — revisa els segments manualment a sota.`);
      setVideoInfo({ ...meta, segments: rawSegments.map((s: any) => ({ ...s, selected: false })) });
    } finally {
      setLoading(false);
    }
  };

  // Segments arrived (immediately or via polling): auto-process or hand to review
  const handleSegmentsReady = (meta: Omit<VideoInfo, 'segments'>, segments: any[], videoPath: string | null) => {
    if (autoMode && segments.length) {
      runAutoPipeline(meta, segments, videoPath);
    } else {
      setVideoInfo({ ...meta, segments: segments.map((s: any) => ({ ...s, selected: false })) });
      setLoading(false);
    }
  };

  // Polls a background ASR job until it completes/fails, then fills the UI
  const pollJobUntilDone = (jobId: number, meta: Omit<VideoInfo, 'segments'>, videoPath: string | null) => {
    let attempts = 0;
    const maxAttempts = 200; // ~10 minutes at 3s intervals

    const pollJob = async () => {
      if (attempts >= maxAttempts) {
        setError('L\'anàlisi ha excedit el temps. Prova amb un vídeo més curt.');
        setLoading(false);
        return;
      }
      attempts++;

      try {
        const pollRes = await fetch(`${API_BASE}/video-analysis/job/${jobId}`);
        const pollData = await pollRes.json();

        if (pollData.status === 'COMPLETED') {
          handleSegmentsReady(meta, pollData.segments, videoPath);
        } else if (pollData.status === 'FAILED') {
          setError(`L'anàlisi ha fallat: ${pollData.error_message}`);
          setLoading(false);
        } else {
          // Still processing, wait 3s
          setTimeout(pollJob, 3000);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setTimeout(pollJob, 3000);
      }
    };

    setTimeout(pollJob, 3000);
  };

  const handleAnalyze = async () => {
    if (!url && !videoFile) return;
    setLoading(true);
    setError(null);
    try {
      if (videoFile) {
        // Upload based analysis
        const formData = new FormData();
        formData.append('video', videoFile);
        if (vttFile) formData.append('subtitles', vttFile);

        const response = await fetch(`${API_BASE}/video-analysis/upload`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) throw new Error('La pujada del fitxer ha fallat');
        const data = await response.json();

        setTempVideoPath(data.video_path);
        const uploadMeta = {
          title: data.title,
          thumbnail: '',
          duration: 0,
          original_language: 'auto'
        };

        if (data.status === 'COMPLETED') {
          // Subtitles provided or fast processing
          handleSegmentsReady(uploadMeta, data.segments, data.video_path);
        } else {
          pollJobUntilDone(data.job_id, uploadMeta, data.video_path);
        }
      } else if (autoMode) {
        // Fully server-side auto pipeline: download -> transcribe -> correct
        // -> translate -> create drills. Survives closing the page.
        const response = await fetch(`${API_BASE}/video-analysis/auto-drills`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            cookies: cookies || null,
            audio_only: audioOnly,
            tag,
            lyrics: lyrics.trim() || null,
            generate_reels: makeReels,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'No s\'ha pogut iniciar el procés automàtic');
        }
        const data = await response.json();
        setAutoStatus('Descarregat — iniciant la transcripció…');
        pollAutoJob(data.job_id, data.title || url);
      } else {
        // URL capture: server downloads the media (YouTube / Instagram /
        // TikTok / podcasts / any yt-dlp-supported site), uses platform
        // subtitles when available and Whisper ASR otherwise
        const response = await fetch(`${API_BASE}/video-analysis/import-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, cookies: cookies || null, audio_only: audioOnly }),
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'No s\'ha pogut importar el vídeo');
        }
        const data = await response.json();

        setTempVideoPath(data.video_path);
        const meta = {
          title: data.title || url,
          thumbnail: data.thumbnail || '',
          duration: data.duration || 0,
          original_language: data.original_language || 'auto'
        };

        if (data.status === 'COMPLETED') {
          handleSegmentsReady(meta, data.segments, data.video_path);
        } else {
          pollJobUntilDone(data.job_id, meta, data.video_path);
        }
      }
    } catch (err: any) {
      setError(friendlyCaptureError(err.message));
      setLoading(false);
    }
  };

  const handleTranslateAll = async () => {
    if (!videoInfo || !videoInfo.segments.length) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          segments: videoInfo.segments,
          source_lang: videoInfo.original_language || 'auto',
          // Fill every drill language; the backend skips targets equal to the source
          target_langs: ['ca', 'ar', 'shi'],
          // Foreign source: the machine Tachelhit is a DRAFT (goes to _suggested),
          // never the gold field — a human corrects it into the real variety.
          draft_tachelhit: foreignSource,
        }),
      });
      if (!response.ok) throw new Error('La traducció ha fallat');
      const translatedSegments = await response.json();
      setVideoInfo({
        ...videoInfo,
        segments: translatedSegments.map((s: any, i: number) => ({
          ...s,
          selected: videoInfo.segments[i].selected
        }))
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Song lyrics: keep ASR timestamps, swap in the real lyric lines
  const handleAlignLyrics = async () => {
    if (!videoInfo || !lyrics.trim()) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/align-lyrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments: videoInfo.segments, lyrics }),
      });
      if (!response.ok) throw new Error('L\'alineació de la lletra ha fallat');
      const aligned = await response.json();
      setVideoInfo({
        ...videoInfo,
        segments: aligned.map((s: any, i: number) => ({
          ...s,
          selected: videoInfo.segments[i].selected
        }))
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Correction layer: glossary fixes + mapping onto the curated phrase dataset
  const handleCorrectAll = async () => {
    if (!videoInfo || !videoInfo.segments.length) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/correct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments: videoInfo.segments }),
      });
      if (!response.ok) throw new Error('La correcció ha fallat');
      const corrected = await response.json();
      setVideoInfo({
        ...videoInfo,
        segments: corrected.map((s: any, i: number) => ({
          ...s,
          selected: videoInfo.segments[i].selected
        }))
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // OCR: read burned-in subtitles from the captured video's frames
  const handleOcrAll = async () => {
    if (!videoInfo || !tempVideoPath) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/ocr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: tempVideoPath, segments: videoInfo.segments }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'L\'OCR ha fallat');
      }
      const withOcr = await response.json();
      setVideoInfo({
        ...videoInfo,
        segments: withOcr.map((s: any, i: number) => ({
          ...s,
          selected: videoInfo.segments[i].selected,
          // Fill empty transcriptions directly; keep OCR as a suggestion otherwise
          text: s.text || s.text_ocr || ''
        }))
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSegmentSelection = (index: number) => {
    if (!videoInfo) return;
    const newSegments = [...videoInfo.segments];
    newSegments[index].selected = !newSegments[index].selected;
    setVideoInfo({ ...videoInfo, segments: newSegments });
  };

  const handleCreateDrills = async () => {
    // File uploads and URL imports both work through tempVideoPath; a URL
    // alone is enough for the remote clipping fallback
    if (!videoInfo || (!url && !tempVideoPath)) return;
    const selectedSegments = videoInfo.segments.filter(s => s.selected);
    if (!selectedSegments.length) {
      alert('Selecciona almenys un segment');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/video-analysis/create-drills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url || null,
          video_path: tempVideoPath,
          segments: selectedSegments,
          source_lang: videoInfo.original_language,
          tag,
          cookies: cookies || null,
        }),
      });
      if (!response.ok) throw new Error('No s\'han pogut crear els drills');
      const result = await response.json();
      alert(`S'han creat ${result.drills_created.length} drills correctament!`);
      // Reset after success
      setVideoInfo(null);
      setUrl('');
      setVideoFile(null);
      setVttFile(null);
      setTempVideoPath(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const canAnalyze = !loading && (url || videoFile);

  return (
    <div className="video-drill-creator" style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: '48px' }}>
      {/* Section header */}
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '18px 24px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Captura</h1>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-soft)', fontSize: '14px' }}>
            Converteix un vídeo de YouTube, Instagram, TikTok o un podcast en drills.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
      <div className="input-group" style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        marginBottom: '24px',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-xl)',
        boxShadow: 'var(--shadow-sm)',
        padding: '24px',
      }}>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-label="Enllaç del vídeo o podcast"
          placeholder="Enganxa aquí un enllaç de YouTube / Instagram / TikTok / podcast..."
          style={{ padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', fontSize: '15px', color: 'var(--text)' }}
        />

        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--text-soft)', fontWeight: 600, cursor: 'pointer' }}>
            <input type="checkbox" checked={audioOnly} onChange={(e) => setAudioOnly(e.target.checked)} />
            🎧 Només àudio (podcast / veu — els drills tenen clips d'àudio en lloc de vídeo)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--text-soft)', fontWeight: 600, cursor: 'pointer' }}>
            <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
            ⚡ Mode automàtic (corregeix + tradueix + crea drills de TOTS els segments)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--text-soft)', fontWeight: 600, cursor: 'pointer' }}>
            <input type="checkbox" checked={foreignSource} onChange={(e) => setForeignSource(e.target.checked)} />
            🌍 Font en una altra llengua (p. ex. anglès) → genera el taixelhit com a ESBORRANY per corregir
          </label>
          {autoMode && (
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--text-soft)', fontWeight: 600, cursor: 'pointer' }}>
              <input type="checkbox" checked={makeReels} onChange={(e) => setMakeReels(e.target.checked)} />
              🎬 Genera també un reel vertical per cada drill
            </label>
          )}
        </div>

        <div style={{ padding: '20px', background: 'var(--surface-2)', borderRadius: 'var(--r-lg)', border: '2px dashed var(--border-strong)', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 12px 0', color: 'var(--text)', fontSize: '15px', fontFamily: 'var(--font-display)' }}>⬆️ O puja fitxers <span style={{ color: 'var(--text-muted)', fontWeight: 500, fontSize: '13px' }}>(Evita els bloquejos de YouTube)</span></h4>
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <div style={{ textAlign: 'left' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-soft)', marginBottom: '6px' }}>Vídeo o àudio</label>
              <input type="file" accept="video/mp4,video/webm,audio/*" aria-label="Fitxer de vídeo o àudio" onChange={(e) => setVideoFile(e.target.files?.[0] || null)} style={{ fontSize: '13px' }} />
            </div>
            <div style={{ textAlign: 'left' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-soft)', marginBottom: '6px' }}>Subtítols (.vtt)</label>
              <input type="file" accept=".vtt" aria-label="Fitxer de subtítols (.vtt)" onChange={(e) => setVttFile(e.target.files?.[0] || null)} style={{ fontSize: '13px' }} />
            </div>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-soft)', fontWeight: 600 }}>
            🎼 Lletra de la cançó <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(Opcional · una línia per frase · després de l'anàlisi, fes servir "Alinea la lletra" per substituir el text aproximat de l'ASR mantenint-ne les marques de temps)</span>
          </label>
          <textarea
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder="Enganxa aquí la lletra de la cançó..."
            style={{
              width: '100%',
              height: '80px',
              padding: '12px',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--border)',
              background: 'var(--surface-2)',
              fontSize: '13px',
              color: 'var(--text)',
              fontFamily: 'var(--font-tifinagh)',
            }}
          />
        </div>

        <div className="cookies-section">
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-soft)', fontWeight: 600 }}>
            Cookies <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(Opcional · format Netscape · calen per a contingut privat o quan la detecció de bots et bloqueja)</span>
          </label>
          <textarea
            value={cookies}
            onChange={(e) => setCookies(e.target.value)}
            placeholder="# Netscape HTTP Cookie File..."
            style={{
              width: '100%',
              height: '80px',
              padding: '12px',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--border)',
              background: 'var(--surface-2)',
              fontFamily: 'monospace',
              fontSize: '12px',
              color: 'var(--text)',
            }}
          />
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || (!url && !videoFile)}
          style={{
            padding: '13px 26px',
            borderRadius: 'var(--r-md)',
            background: canAnalyze ? 'var(--brand-gradient)' : 'var(--border)',
            color: '#fff',
            border: 'none',
            fontWeight: 700,
            fontSize: '15px',
            cursor: canAnalyze ? 'pointer' : 'not-allowed',
            opacity: canAnalyze ? 1 : 0.7,
            alignSelf: 'flex-start',
            boxShadow: canAnalyze ? 'var(--shadow-brand)' : 'none',
          }}
        >
          {loading ? (videoFile ? '⏳ Pujant i analitzant...' : '⏳ Analitzant...') : 'Analitza el vídeo / la pujada'}
        </button>
        {autoStatus && (
          <div style={{ padding: '10px 14px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-md)', fontSize: '14px', fontWeight: 600, color: 'var(--brand-1)' }}>
            ⚡ {autoStatus} <span style={{ fontWeight: 400, color: 'var(--text-soft)' }}>(continua executant-se al servidor si surts d'aquesta pàgina)</span>
          </div>
        )}
      </div>

      {error && (
        <div ref={errorRef} role="alert" aria-live="assertive" style={{ padding: '16px 18px', background: 'var(--rose-soft)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', marginBottom: '24px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
          <p style={{ color: 'var(--rose)', margin: 0, fontWeight: 600, lineHeight: 1.5 }}>{error}</p>
          <button onClick={() => setError(null)} aria-label="Tanca l'avís" style={{ background: 'none', border: 'none', color: 'var(--rose)', cursor: 'pointer', fontSize: '18px', lineHeight: 1, flexShrink: 0 }}>✕</button>
        </div>
      )}

      {videoInfo && (
        <div className="video-info" style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
            <img
              src={videoInfo.thumbnail}
              alt={videoInfo.title}
              style={{ width: '180px', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-md)' }}
            />
            <div style={{ flex: 1, minWidth: '220px' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '20px', fontFamily: 'var(--font-display)' }}>{videoInfo.title}</h3>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 12px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, background: 'var(--sky-soft)', color: 'var(--sky)' }}>⏱ {formatTime(videoInfo.duration)}</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 12px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)' }}>🌐 {videoInfo.original_language}</span>
              </div>
              <div style={{ marginTop: '8px' }}>
                <label style={{ marginRight: '10px', fontSize: '13px', fontWeight: 700, color: 'var(--text-soft)' }}>Etiqueta per als drills:</label>
                <input
                  type="text"
                  value={tag}
                  onChange={(e) => setTag(e.target.value)}
                  aria-label="Etiqueta per als drills"
                  style={{ padding: '7px 12px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)' }}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', flexWrap: 'wrap', gap: '12px' }}>
            <h4 style={{ margin: 0, fontSize: '16px', fontFamily: 'var(--font-display)' }}>Segments del vídeo <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>({videoInfo.segments.length})</span></h4>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {lyrics.trim() && (
                <button
                  onClick={handleAlignLyrics}
                  disabled={loading}
                  aria-busy={loading}
                  title="Substitueix el text aproximat de l'ASR per les línies de lletra enganxades, mantenint les marques de temps"
                  style={{ padding: '9px 18px', background: 'var(--brand-1)', color: '#fff', borderRadius: 'var(--r-md)', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)' }}
                >
                  {loading ? '⏳ Alineant…' : '🎼 Alinea la lletra'}
                </button>
              )}
              <button
                onClick={handleCorrectAll}
                disabled={loading}
                aria-busy={loading}
                title="Correccions del glossari + mapatge sobre el teu conjunt de frases curat"
                style={{ padding: '9px 18px', background: 'var(--emerald)', color: '#fff', borderRadius: 'var(--r-md)', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)' }}
              >
                {loading ? '⏳ Corregint…' : '✨ Corregeix'}
              </button>
              {tempVideoPath && (
                <button
                  onClick={handleOcrAll}
                  disabled={loading}
                  aria-busy={loading}
                  title="Llegeix els subtítols incrustats als fotogrames del vídeo"
                  style={{ padding: '9px 18px', background: 'var(--sky)', color: '#fff', borderRadius: 'var(--r-md)', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)' }}
                >
                  {loading ? '⏳ OCR…' : '🔤 OCR'}
                </button>
              )}
              <button
                onClick={handleTranslateAll}
                disabled={loading}
                aria-busy={loading}
                style={{ padding: '9px 18px', background: 'var(--brand-2)', color: '#fff', borderRadius: 'var(--r-md)', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: '14px', boxShadow: 'var(--shadow-sm)' }}
              >
                {loading ? '⏳ Traduint…' : 'Tradueix-ho tot (Català · العربية · ⵜⴰⵛⵍⵃⵉⵜ)'}
              </button>
            </div>
          </div>

          <div className="segments-list" style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'var(--surface-2)', zIndex: 1 }}>
                <tr>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>
                    <input
                      type="checkbox"
                      aria-label="Selecciona tots els segments"
                      onChange={(e) => {
                        const newSegments = videoInfo.segments.map(s => ({ ...s, selected: e.target.checked }));
                        setVideoInfo({ ...videoInfo, segments: newSegments });
                      }}
                    />
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Temps i retall</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Text original (vídeo)</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Traducció (Català)</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>العربية</th>
                </tr>
              </thead>
              <tbody>
                {videoInfo.segments.map((seg, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border)', background: seg.selected ? 'var(--brand-gradient-soft)' : 'var(--surface)' }}>
                    <td style={{ padding: '12px' }}>
                      <input
                        type="checkbox"
                        checked={seg.selected}
                        aria-label={`Selecciona el segment ${idx + 1}`}
                        onChange={() => toggleSegmentSelection(idx)}
                      />
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>I:</span>
                          <input
                            type="number"
                            value={seg.start}
                            step="0.1"
                            aria-label="Inici (segons)"
                            onChange={(e) => {
                              const newSegments = [...videoInfo.segments];
                              newSegments[idx].start = parseFloat(e.target.value);
                              setVideoInfo({ ...videoInfo, segments: newSegments });
                            }}
                            style={{ width: '64px', padding: '4px 6px', fontSize: '12px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface-2)' }}
                          />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>F:</span>
                          <input
                            type="number"
                            value={seg.end}
                            step="0.1"
                            aria-label="Fi (segons)"
                            onChange={(e) => {
                              const newSegments = [...videoInfo.segments];
                              newSegments[idx].end = parseFloat(e.target.value);
                              setVideoInfo({ ...videoInfo, segments: newSegments });
                            }}
                            style={{ width: '64px', padding: '4px 6px', fontSize: '12px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface-2)' }}
                          />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <textarea
                        value={seg.text}
                        onChange={(e) => {
                          const newSegments = [...videoInfo.segments];
                          newSegments[idx].text = e.target.value;
                          setVideoInfo({ ...videoInfo, segments: newSegments });
                        }}
                        style={{ width: '100%', minHeight: '44px', padding: '8px', fontSize: '13px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface)', fontFamily: 'var(--font-tifinagh)', color: 'var(--text)' }}
                      />
                      {(foreignSource || seg.text_tachelhit_suggested) && (
                        <div style={{ marginTop: '6px' }}>
                          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--sky)', marginBottom: '3px' }}>🤖 Taixelhit (esborrany — corregeix-lo)</div>
                          <textarea
                            value={seg.text_tachelhit_suggested || ''}
                            onChange={(e) => { const ns = [...videoInfo.segments]; ns[idx].text_tachelhit_suggested = e.target.value; setVideoInfo({ ...videoInfo, segments: ns }); }}
                            placeholder="esborrany en taixelhit…"
                            style={{ width: '100%', minHeight: '40px', padding: '8px', fontSize: '13px', borderRadius: 'var(--r-sm)', border: '1px dashed var(--sky)', background: 'var(--sky-soft)', fontFamily: 'var(--font-tifinagh)', color: 'var(--text)' }}
                          />
                        </div>
                      )}
                      {seg.text_ocr && seg.text_ocr !== seg.text && (
                        <div style={{ fontSize: '11px', marginTop: '4px', color: 'var(--text-muted)' }}>
                          🔤 OCR: <em>{seg.text_ocr}</em>{' '}
                          <button
                            onClick={() => {
                              const newSegments = [...videoInfo.segments];
                              newSegments[idx].text = seg.text_ocr || '';
                              setVideoInfo({ ...videoInfo, segments: newSegments });
                            }}
                            style={{ padding: '2px 8px', fontSize: '10px', fontWeight: 700, background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', cursor: 'pointer' }}
                          >
                            aplica
                          </button>
                        </div>
                      )}
                      {typeof seg.correction_score === 'number' && (
                        <div style={{ fontSize: '11px', marginTop: '4px', color: 'var(--text-muted)' }}>
                          ✨ confiança de coincidència: {(seg.correction_score * 100).toFixed(0)}%
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <textarea
                        value={seg.text_catalan || ''}
                        onChange={(e) => {
                          const newSegments = [...videoInfo.segments];
                          newSegments[idx].text_catalan = e.target.value;
                          setVideoInfo({ ...videoInfo, segments: newSegments });
                        }}
                        placeholder="Pendent…"
                        style={{ width: '100%', minHeight: '44px', padding: '8px', fontSize: '13px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--emerald)' }}
                      />
                    </td>
                    <td style={{ padding: '12px' }}>
                      <textarea
                        value={seg.text_arabic || ''}
                        onChange={(e) => {
                          const newSegments = [...videoInfo.segments];
                          newSegments[idx].text_arabic = e.target.value;
                          setVideoInfo({ ...videoInfo, segments: newSegments });
                        }}
                        placeholder="Pendent…"
                        dir="rtl"
                        style={{ width: '100%', minHeight: '44px', padding: '8px', fontSize: '13px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)' }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '24px', textAlign: 'right' }}>
            <button
              onClick={handleCreateDrills}
              disabled={loading || !videoInfo.segments.some(s => s.selected)}
              style={{
                padding: '14px 32px',
                background: 'var(--brand-gradient)',
                color: '#fff',
                borderRadius: 'var(--r-md)',
                border: 'none',
                fontSize: '16px',
                fontWeight: 700,
                cursor: (loading || !videoInfo.segments.some(s => s.selected)) ? 'not-allowed' : 'pointer',
                opacity: (loading || !videoInfo.segments.some(s => s.selected)) ? 0.6 : 1,
                boxShadow: 'var(--shadow-brand)',
              }}
            >
              {loading ? '⏳ Creant els drills...' : 'Crea drills dels segments seleccionats'}
            </button>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default VideoDrillCreator;
