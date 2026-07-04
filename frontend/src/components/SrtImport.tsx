import React, { useState } from 'react';
import { API_BASE } from '../config';
import { useNavigate } from 'react-router-dom';

interface SrtSegment {
  sequence: number;
  start_time: string;
  end_time: string;
  text: string;
}

interface SrtImportRequest {
  srt_content: string;
  video_url: string;
  tag?: string;
  author?: string;
  create_test?: boolean;
  test_title?: string;
}

const SrtImport: React.FC = () => {
  const navigate = useNavigate();
  const [srtContent, setSrtContent] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [tag, setTag] = useState('youtube_srt');
  const [author, setAuthor] = useState('');
  const [createTest, setCreateTest] = useState(true);
  const [testTitle, setTestTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ drills_created: number; test_id?: number } | null>(null);
  const [parsedSegments, setParsedSegments] = useState<SrtSegment[]>([]);
  const [previewMode, setPreviewMode] = useState(false);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setSrtContent(content);
      parseSrtContent(content);
    };
    reader.readAsText(file);
  };

  const parseSrtContent = (content: string) => {
    try {
      const lines = content.split('\n');
      const segments: SrtSegment[] = [];
      let currentSegment: Partial<SrtSegment> = {};

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (!line) {
          // Empty line indicates end of segment
          if (currentSegment.sequence && currentSegment.start_time && currentSegment.end_time && currentSegment.text) {
            segments.push(currentSegment as SrtSegment);
          }
          currentSegment = {};
          continue;
        }

        if (!currentSegment.sequence && /^\d+$/.test(line)) {
          // Sequence number
          currentSegment.sequence = parseInt(line, 10);
        } else if (!currentSegment.start_time && line.includes('-->')) {
          // Timestamp line
          const [start, end] = line.split('-->').map(s => s.trim());
          currentSegment.start_time = start;
          currentSegment.end_time = end;
        } else if (currentSegment.start_time) {
          // Text line
          if (currentSegment.text) {
            currentSegment.text += ' ' + line;
          } else {
            currentSegment.text = line;
          }
        }
      }

      // Add last segment if exists
      if (currentSegment.sequence && currentSegment.start_time && currentSegment.end_time && currentSegment.text) {
        segments.push(currentSegment as SrtSegment);
      }

      setParsedSegments(segments);
      setPreviewMode(true);
    } catch (err) {
      console.error('Error parsing SRT:', err);
      setError('No s\'ha pogut analitzar el fitxer SRT. Comprova\'n el format.');
    }
  };

  const handleParse = () => {
    if (!srtContent.trim()) {
      setError('Cal proporcionar contingut SRT');
      return;
    }
    parseSrtContent(srtContent);
  };

  const handleImport = async () => {
    if (!srtContent.trim()) {
      setError('Cal proporcionar contingut SRT');
      return;
    }
    if (!videoUrl.trim()) {
      setError('Cal proporcionar l\'URL del vídeo de YouTube');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: SrtImportRequest = {
        srt_content: srtContent,
        video_url: videoUrl,
        tag: tag || undefined,
        author: author || undefined,
        create_test: createTest,
        test_title: testTitle || undefined,
      };

      const response = await fetch(`${API_BASE}/srt/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to import SRT');
      }

      const result = await response.json();
      setSuccess({
        drills_created: result.drills_created?.length || 0,
        test_id: result.test_id,
      });

      // Reset form after successful import
      setSrtContent('');
      setVideoUrl('');
      setTestTitle('');
      setParsedSegments([]);
      setPreviewMode(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    // SRT format: HH:MM:SS,mmm
    const [time, _milliseconds] = timestamp.split(',');
    return time;
  };

  const sectionCardStyle: React.CSSProperties = {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    padding: '24px',
    borderRadius: 'var(--r-xl)',
    boxShadow: 'var(--shadow-sm)',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '8px',
    fontWeight: 700,
    fontSize: '14px',
    color: 'var(--text-soft)',
  };

  const sectionHeadingStyle: React.CSSProperties = {
    marginTop: 0,
    marginBottom: '16px',
    fontSize: '17px',
    fontFamily: 'var(--font-display)',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  };

  const stepBadgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '26px',
    height: '26px',
    borderRadius: 'var(--r-pill)',
    background: 'var(--brand-gradient)',
    color: '#fff',
    fontSize: '13px',
    fontWeight: 800,
    flexShrink: 0,
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: 'var(--r-md)',
    border: '1px solid var(--border)',
    background: 'var(--surface-2)',
    fontSize: '15px',
    color: 'var(--text)',
  };

  return (
    <div className="srt-import" style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: '48px' }}>
      {/* Section header */}
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '18px 24px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Importa des de SRT</h1>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-soft)', fontSize: '14px' }}>
            Converteix un fitxer de subtítols SRT en drills amb marques de temps.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
      <div className="import-form" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="input-section" style={sectionCardStyle}>
          <h3 style={sectionHeadingStyle}><span style={stepBadgeStyle}>1</span> Fitxer SRT</h3>

          <div style={{ marginBottom: '16px', padding: '20px', background: 'var(--surface-2)', borderRadius: 'var(--r-lg)', border: '2px dashed var(--border-strong)', textAlign: 'center' }}>
            <label htmlFor="srt-file" style={{ display: 'block', marginBottom: '10px', fontWeight: 700, fontSize: '14px', color: 'var(--text)' }}>
              ⬆️ Puja un fitxer SRT
            </label>
            <input
              id="srt-file"
              type="file"
              accept=".srt,.txt"
              onChange={handleFileUpload}
              style={{ fontSize: '13px' }}
            />
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', marginBottom: 0 }}>
              O enganxa el contingut SRT a sota
            </p>
          </div>

          <div>
            <label htmlFor="srt-content" style={labelStyle}>
              Contingut SRT
            </label>
            <textarea
              id="srt-content"
              value={srtContent}
              onChange={(e) => setSrtContent(e.target.value)}
              placeholder={`1
00:00:01,000 --> 00:00:04,000
Hello, this is the first line.

2
00:00:05,000 --> 00:00:08,000
This is the second line.`}
              rows={10}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: 'var(--r-md)',
                border: '1px solid var(--border)',
                background: 'var(--surface-2)',
                fontFamily: 'monospace',
                fontSize: '14px',
                color: 'var(--text)',
                resize: 'vertical'
              }}
            />
          </div>

          <button
            onClick={handleParse}
            disabled={!srtContent.trim()}
            style={{
              marginTop: '16px',
              padding: '11px 22px',
              background: srtContent.trim() ? 'var(--brand-gradient)' : 'var(--border)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--r-md)',
              cursor: srtContent.trim() ? 'pointer' : 'not-allowed',
              opacity: srtContent.trim() ? 1 : 0.7,
              fontWeight: 700,
              fontSize: '14px',
              boxShadow: srtContent.trim() ? 'var(--shadow-brand)' : 'none',
            }}
          >
            {previewMode ? 'Actualitza la previsualització' : 'Previsualitza els segments'}
          </button>
        </div>

        <div className="input-section" style={sectionCardStyle}>
          <h3 style={sectionHeadingStyle}><span style={stepBadgeStyle}>2</span> Configuració del vídeo</h3>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="video-url" style={labelStyle}>
              URL del vídeo de YouTube
            </label>
            <input
              id="video-url"
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              style={inputStyle}
            />
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Cada drill enllaçarà amb aquest vídeo a la marca de temps corresponent
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
            <div>
              <label htmlFor="srt-tag" style={labelStyle}>
                Etiqueta
              </label>
              <input
                id="srt-tag"
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                placeholder="youtube_srt"
                style={inputStyle}
              />
            </div>

            <div>
              <label htmlFor="srt-author" style={labelStyle}>
                Autor <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(opcional)</span>
              </label>
              <input
                id="srt-author"
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="El teu nom"
                style={inputStyle}
              />
            </div>
          </div>
        </div>

        <div className="input-section" style={sectionCardStyle}>
          <h3 style={sectionHeadingStyle}><span style={stepBadgeStyle}>3</span> Configuració del test</h3>

          <div style={{ marginBottom: '15px' }}>
            <label htmlFor="create-test" style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                id="create-test"
                type="checkbox"
                checked={createTest}
                onChange={(e) => setCreateTest(e.target.checked)}
              />
              <span style={{ fontWeight: 700, color: 'var(--text)' }}>Crea un test amb tots els drills</span>
            </label>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '30px', marginTop: '5px' }}>
              Crea un test amb tots els drills importats per practicar
            </p>
          </div>

          {createTest && (
            <div>
              <label htmlFor="test-title" style={labelStyle}>
                Títol del test <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(opcional)</span>
              </label>
              <input
                id="test-title"
                type="text"
                value={testTitle}
                onChange={(e) => setTestTitle(e.target.value)}
                placeholder="p. ex., 'Vocabulari de l'episodi 1'"
                style={inputStyle}
              />
            </div>
          )}
        </div>

        {error && (
          <div role="alert" style={{ padding: '15px', background: 'var(--rose-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--rose)' }}>
            <p style={{ color: 'var(--rose)', margin: 0, fontWeight: 600 }}>Error: {error}</p>
          </div>
        )}

        {success && (
          <div role="status" aria-live="polite" style={{ padding: '16px', background: 'var(--emerald-soft)', borderRadius: 'var(--r-md)', border: '1px solid var(--emerald)' }}>
            <p style={{ color: 'var(--emerald)', margin: 0, fontWeight: 700 }}>
              ✅ S'han creat {success.drills_created} drills correctament!
            </p>
            {success.test_id && (
              <p style={{ color: 'var(--emerald)', margin: '5px 0 0 0' }}>
                Test creat amb ID: {success.test_id}
              </p>
            )}
            <button
              onClick={() => navigate('/tests')}
              style={{
                marginTop: '12px',
                padding: '9px 18px',
                background: 'var(--emerald)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '14px',
              }}
            >
              Mostra els tests
            </button>
          </div>
        )}

        {previewMode && parsedSegments.length === 0 && (
          <div className="preview-empty" role="status" style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', textAlign: 'center', color: 'var(--text-muted)' }}>
            No s'ha trobat cap segment. Comprova el format SRT.
          </div>
        )}

        {previewMode && parsedSegments.length > 0 && (
          <div className="preview-section" style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)' }}>
            <h3 style={{ marginTop: 0, marginBottom: '16px', fontSize: '17px', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Previsualització
              <span style={{ display: 'inline-flex', alignItems: 'center', padding: '4px 12px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)' }}>{parsedSegments.length} segments trobats</span>
            </h3>

            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <caption style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 }}>Segments SRT analitzats</caption>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--surface-2)', zIndex: 1 }}>
                  <tr>
                    <th scope="col" style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>#</th>
                    <th scope="col" style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Inici</th>
                    <th scope="col" style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Fi</th>
                    <th scope="col" style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border)' }}>Text</th>
                  </tr>
                </thead>
                <tbody>
                  {parsedSegments.slice(0, 20).map((segment, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: 'var(--brand-1)' }}>{segment.sequence}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: 'var(--text-soft)' }}>{formatTime(segment.start_time)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: 'var(--text-soft)' }}>{formatTime(segment.end_time)}</td>
                      <td style={{ padding: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-tifinagh)' }}>
                        {segment.text}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {parsedSegments.length > 20 && (
                <div style={{ padding: '12px', textAlign: 'center', background: 'var(--surface-2)', borderTop: '1px solid var(--border)' }}>
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>
                    ... i {parsedSegments.length - 20} segments més
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '12px' }}>
          <button
            onClick={handleImport}
            disabled={loading || !srtContent.trim() || !videoUrl.trim()}
            aria-busy={loading}
            style={{
              padding: '15px 40px',
              background: (loading || !srtContent.trim() || !videoUrl.trim()) ? 'var(--border)' : 'var(--brand-gradient)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--r-md)',
              fontSize: '16px',
              fontWeight: 700,
              cursor: (loading || !srtContent.trim() || !videoUrl.trim()) ? 'not-allowed' : 'pointer',
              opacity: (loading || !srtContent.trim() || !videoUrl.trim()) ? 0.7 : 1,
              boxShadow: (loading || !srtContent.trim() || !videoUrl.trim()) ? 'none' : 'var(--shadow-brand)',
            }}
          >
            {loading ? '⏳ Important...' : 'Importa l\'SRT i crea els drills'}
          </button>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Es crearà un drill per cada segment SRT amb marques de temps
          </p>
        </div>
      </div>
      </div>
    </div>
  );
};

export default SrtImport;
