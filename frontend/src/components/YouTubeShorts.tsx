import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';
import { toast } from '../toast';

interface Short {
  id: number;
  drill_id: number;
  video_path: string;
  text_catalan: string;
  text_tachelhit: string;
  text_arabic: string;
  date_created: string;
}

interface Drill {
  id: number;
  text_catalan: string;
  text_tachelhit: string;
  text_arabic: string;
  image_url: string;
  audio_url: string;
  video_url: string;
}

export default function YouTubeShorts() {
  const [shorts, setShorts] = useState<Short[]>([]);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<number | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<Short | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setError(null);
    try {
      const [shortsRes, drillsRes] = await Promise.all([
        axios.get(`${API_BASE}/shorts/`),
        axios.get(`${API_BASE}/drills/`)
      ]);
      setShorts(shortsRes.data);
      setDrills(drillsRes.data);
      setLoading(false);
    } catch (error: any) {
      console.error('Error loading data:', error);
      setError(`No s'han pogut carregar les dades: ${error.message}`);
      setLoading(false);
    }
  };

  const handleGenerateShort = async (drillId: number) => {
    if (!confirm('Generar YouTube Short per aquest drill? Pot trigar uns segons...')) return;

    setGenerating(drillId);
    setError(null);
    try {
      await axios.post(`${API_BASE}/generate-short/${drillId}`);
      toast.success('Short generat correctament!');
      await loadData();
    } catch (error: any) {
      console.error('Error generating short:', error);
      const errMsg = error.response?.data?.detail || error.message || 'Error desconegut';
      setError(`Error generant el short: ${errMsg}`);
      toast.error(`Error generant el short: ${errMsg}`);
    } finally {
      setGenerating(null);
    }
  };

  const handleDeleteShort = async (shortId: number) => {
    if (!confirm('Eliminar aquest short?')) return;

    try {
      await axios.delete(`${API_BASE}/shorts/${shortId}`);
      setShorts(shorts.filter(s => s.id !== shortId));
      if (selectedVideo?.id === shortId) {
        setSelectedVideo(null);
      }
    } catch (error) {
      console.error('Error deleting short:', error);
      toast.error('Error eliminant el short');
    }
  };

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', background: 'var(--bg)', color: 'var(--text-soft)' }}>
        <div style={{ width: '40px', height: '40px', border: '4px solid var(--border)', borderTopColor: 'var(--brand-1)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <p style={{ margin: 0, fontWeight: 600 }}>Carregant...</p>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: '14px'
      }}>
        <h1 style={{
          margin: 0,
          fontFamily: 'var(--font-display)',
          fontSize: '22px',
          fontWeight: 700,
          color: 'var(--text)',
          letterSpacing: '-0.02em',
        }}>
          Reels
        </h1>
        <span style={{
          color: 'var(--text-soft)',
          fontSize: '13px',
          fontWeight: 700,
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          padding: '4px 12px',
          borderRadius: 'var(--r-pill)',
        }}>
          {shorts.length} shorts
        </span>
      </div>

      <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', overflow: 'hidden' }}>
        {/* Left: Drills list for generation */}
        <div style={{
          flex: '1 1 320px',
          minWidth: '280px',
          maxWidth: '100%',
          borderRight: '1px solid var(--border)',
          overflowY: 'auto',
          padding: '20px',
          background: 'var(--surface-2)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '17px', fontFamily: 'var(--font-display)' }}>Generar Shorts</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Selecciona un drill per generar un YouTube Short
          </p>

          {drills.filter(d => d.text_catalan && d.text_tachelhit).map(drill => {
            const hasShort = shorts.some(s => s.drill_id === drill.id);
            return (
              <div
                key={drill.id}
                style={{
                  padding: '14px',
                  background: 'var(--surface)',
                  borderRadius: 'var(--r-lg)',
                  marginBottom: '12px',
                  border: hasShort ? '1.5px solid var(--emerald)' : '1px solid var(--border)',
                  boxShadow: 'var(--shadow-xs)',
                }}
              >
                <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '14px', color: 'var(--text)' }}>{drill.text_catalan}</strong>
                  {hasShort && (
                    <span style={{
                      fontSize: '11px',
                      color: 'var(--emerald)',
                      fontWeight: 700,
                      background: 'var(--emerald-soft)',
                      padding: '2px 8px',
                      borderRadius: 'var(--r-pill)',
                    }}>
                      ✓ Generat
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-soft)', marginBottom: '10px', fontFamily: 'var(--font-tifinagh)' }}>
                  {drill.text_tachelhit}
                </div>
                <button
                  onClick={() => handleGenerateShort(drill.id)}
                  disabled={generating !== null}
                  aria-label={`Genera Short per ${drill.text_catalan}`}
                  aria-busy={generating === drill.id}
                  style={{
                    padding: '8px 12px',
                    fontSize: '13px',
                    background: generating !== null ? 'var(--border)' : 'var(--brand-gradient)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-md)',
                    cursor: generating !== null ? 'not-allowed' : 'pointer',
                    fontWeight: 700,
                    width: '100%',
                    opacity: generating !== null && generating !== drill.id ? 0.6 : 1,
                    boxShadow: generating !== null ? 'none' : 'var(--shadow-brand)',
                  }}
                >
                  {generating === drill.id ? '⏳ Generant...' : '🎬 Generar Short'}
                </button>
              </div>
            );
          })}
        </div>

        {/* Middle: Shorts list */}
        <div style={{
          flex: '1 1 400px',
          minWidth: '300px',
          maxWidth: '100%',
          borderRight: '1px solid var(--border)',
          overflowY: 'auto',
          padding: '20px',
          background: 'var(--bg)'
        }}>
          <h3 style={{ marginTop: 0, fontSize: '17px', fontFamily: 'var(--font-display)' }}>Shorts Generats</h3>

          {error && (
            <div style={{
              padding: '12px 14px',
              background: 'var(--rose-soft)',
              color: 'var(--rose)',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--rose)',
              marginBottom: '16px'
            }}>
              <strong>Error:</strong> {error}
              <button
                onClick={() => setError(null)}
                style={{
                  marginLeft: '8px',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--rose)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                  fontSize: '13px',
                }}
              >
                Descarta
              </button>
            </div>
          )}

          {shorts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', background: 'var(--surface)', border: '1px dashed var(--border-strong)', borderRadius: 'var(--r-xl)' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px' }}>🎞️</div>
              <p style={{ margin: '0 0 4px 0', fontWeight: 600, color: 'var(--text-soft)' }}>Cap short generat encara</p>
              <p style={{ fontSize: '13px', margin: 0 }}>Selecciona un drill a l'esquerra per començar</p>
            </div>
          ) : (
            shorts.map(short => (
              <div
                key={short.id}
                onClick={() => setSelectedVideo(short)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedVideo(short); } }}
                aria-label={`Short: ${short.text_catalan}`}
                style={{
                  padding: '16px',
                  border: selectedVideo?.id === short.id ? '1.5px solid var(--brand-1)' : '1px solid var(--border)',
                  borderRadius: 'var(--r-lg)',
                  marginBottom: '12px',
                  cursor: 'pointer',
                  background: selectedVideo?.id === short.id ? 'var(--brand-gradient-soft)' : 'var(--surface)',
                  boxShadow: 'var(--shadow-xs)',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ marginBottom: '8px' }}>
                  <strong style={{ fontSize: '15px', color: 'var(--text)' }}>
                    {short.text_catalan}
                  </strong>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-soft)', marginBottom: '8px', fontFamily: 'var(--font-tifinagh)' }}>
                  {short.text_tachelhit}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                  {new Date(short.date_created).toLocaleString('ca-ES')}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedVideo(short);
                    }}
                    aria-label="Veure el short"
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      fontSize: '13px',
                      background: 'var(--sky)',
                      color: 'white',
                      border: 'none',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                    }}
                  >
                    ▶ Veure
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteShort(short.id);
                    }}
                    aria-label="Elimina el short"
                    style={{
                      padding: '8px 12px',
                      fontSize: '13px',
                      background: 'var(--rose-soft)',
                      color: 'var(--rose)',
                      border: '1px solid var(--rose)',
                      borderRadius: 'var(--r-md)',
                      cursor: 'pointer',
                      fontWeight: 700,
                    }}
                  >
                    🗑 Eliminar
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right: Video player */}
        <div style={{ flex: 1, padding: '30px', background: 'var(--surface-2)', overflowY: 'auto' }}>
          {selectedVideo ? (
            <div>
              <h2 style={{ marginTop: 0, fontSize: '22px', fontFamily: 'var(--font-display)' }}>Preview del Short</h2>

              <div style={{
                marginBottom: '20px',
                padding: '18px',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-xl)',
                boxShadow: 'var(--shadow-sm)',
              }}>
                <div style={{ marginBottom: '8px', color: 'var(--text)' }}>
                  <strong style={{ color: 'var(--text-soft)' }}>Català:</strong> {selectedVideo.text_catalan}
                </div>
                <div style={{ marginBottom: '8px', color: 'var(--text)', fontFamily: 'var(--font-tifinagh)' }}>
                  <strong style={{ color: 'var(--text-soft)', fontFamily: 'var(--font-sans)' }}>Tachelhit:</strong> {selectedVideo.text_tachelhit}
                </div>
                <div style={{ marginBottom: '8px', color: 'var(--text)' }}>
                  <strong style={{ color: 'var(--text-soft)' }}>العربية:</strong> {selectedVideo.text_arabic}
                </div>
              </div>

              {/* Vertical Video Player (Shorts Style) */}
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                background: '#000',
                borderRadius: 'var(--r-xl)',
                padding: '20px',
                boxShadow: 'var(--shadow-lg)'
              }}>
                <div style={{
                  position: 'relative',
                  width: '360px',
                  maxWidth: '100%',
                  aspectRatio: '9/16',
                  borderRadius: 'var(--r-md)',
                  overflow: 'hidden',
                  boxShadow: 'var(--shadow-lg)'
                }}>
                  <video
                    key={selectedVideo.id}
                    controls
                    loop
                    playsInline
                    aria-label={`Vídeo del short: ${selectedVideo.text_catalan}`}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover'
                    }}
                    src={getMediaUrl(selectedVideo.video_path)}
                  >
                    El teu navegador no suporta video.
                  </video>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{
                marginTop: '24px',
                display: 'flex',
                gap: '12px',
                justifyContent: 'center',
                flexWrap: 'wrap'
              }}>
                <a
                  href={getMediaUrl(selectedVideo.video_path)}
                  download={`tachelhit_short_${selectedVideo.drill_id}.mp4`}
                  aria-label="Descarrega el Short"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px 24px',
                    background: 'var(--emerald)',
                    color: 'white',
                    textDecoration: 'none',
                    borderRadius: 'var(--r-md)',
                    fontWeight: 700,
                    fontSize: '14px',
                    boxShadow: 'var(--shadow-md)'
                  }}
                >
                  <span style={{ fontSize: '18px' }}>⬇</span>
                  Descarrega el Short
                </a>

                <button
                  onClick={() => {
                    const title = `${selectedVideo.text_catalan} - Tachelhit`;
                    const description = `Català: ${selectedVideo.text_catalan}\nTachelhit: ${selectedVideo.text_tachelhit}\nالعربية: ${selectedVideo.text_arabic}`;

                    // Open YouTube upload page
                    const uploadUrl = `https://www.youtube.com/upload`;
                    window.open(uploadUrl, '_blank');

                    // Copy description to clipboard
                    navigator.clipboard.writeText(`${title}\n\n${description}\n\n#Tachelhit #LanguageLearning #Shorts`);
                    toast.success("Títol i descripció copiats al porta-retalls! Enganxa'ls en pujar a YouTube.");
                  }}
                  aria-label="Puja a YouTube"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px 24px',
                    background: 'var(--rose)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-md)',
                    fontWeight: 700,
                    fontSize: '14px',
                    cursor: 'pointer',
                    boxShadow: 'var(--shadow-md)'
                  }}
                >
                  <span style={{ fontSize: '18px' }}>📤</span>
                  Puja a YouTube
                </button>

                <button
                  onClick={() => {
                    const text = `${selectedVideo.text_catalan}\n${selectedVideo.text_tachelhit}`;
                    const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&hashtags=Tachelhit,LanguageLearning`;
                    window.open(shareUrl, '_blank');
                  }}
                  aria-label="Comparteix a X"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px 24px',
                    background: 'var(--sky)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--r-md)',
                    fontWeight: 700,
                    fontSize: '14px',
                    cursor: 'pointer',
                    boxShadow: 'var(--shadow-md)'
                  }}
                >
                  <span style={{ fontSize: '18px' }}>🐦</span>
                  Comparteix a X
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '40px', marginBottom: '12px' }}>📺</div>
              <p style={{ fontSize: '17px', fontWeight: 600, color: 'var(--text-soft)' }}>Selecciona un short per veure'l</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
