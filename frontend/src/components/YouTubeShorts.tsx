import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

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

export default function YouTubeShorts({ onBackToDrills }: { onBackToDrills: () => void }) {
  const [shorts, setShorts] = useState<Short[]>([]);
  const [drills, setDrills] = useState<Drill[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<number | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<Short | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [shortsRes, drillsRes] = await Promise.all([
        axios.get(`${API_BASE}/shorts/`),
        axios.get(`${API_BASE}/drills/`)
      ]);
      setShorts(shortsRes.data);
      setDrills(drillsRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setLoading(false);
    }
  };

  const handleGenerateShort = async (drillId: number) => {
    if (!confirm('Generar YouTube Short per aquest drill? Pot trigar uns segons...')) return;

    setGenerating(drillId);
    try {
      await axios.post(`${API_BASE}/generate-short/${drillId}`);
      alert('Short generat correctament!');
      await loadData();
    } catch (error) {
      console.error('Error generating short:', error);
      alert('Error generant el short');
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
      alert('Error eliminant el short');
    }
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center' }}>Carregant...</div>;
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '16px',
        background: 'linear-gradient(135deg, #FF0080 0%, #FF8C00 100%)',
        borderBottom: '2px solid #FF0080',
        display: 'flex',
        alignItems: 'center',
        gap: '16px'
      }}>
        <button
          onClick={onBackToDrills}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            background: 'rgba(255,255,255,0.2)',
            color: 'white',
            border: '1px solid white',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          ← Tornar als Drills
        </button>
        <h1 style={{
          margin: 0,
          fontSize: '24px',
          fontWeight: 700,
          color: 'white',
          letterSpacing: '0.5px'
        }}>
          📱 YouTube Shorts
        </h1>
        <span style={{ color: 'white', fontSize: '16px' }}>
          ({shorts.length} shorts generats)
        </span>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left: Drills list for generation */}
        <div style={{
          width: '350px',
          borderRight: '1px solid #e0e0e0',
          overflowY: 'auto',
          padding: '20px',
          background: '#f8f9fa'
        }}>
          <h3 style={{ marginTop: 0 }}>Generar Shorts</h3>
          <p style={{ fontSize: '13px', color: '#666', marginBottom: '20px' }}>
            Selecciona un drill per generar un YouTube Short
          </p>

          {drills.filter(d => d.text_catalan && d.text_tachelhit).map(drill => {
            const hasShort = shorts.some(s => s.drill_id === drill.id);
            return (
              <div
                key={drill.id}
                style={{
                  padding: '12px',
                  background: 'white',
                  borderRadius: '8px',
                  marginBottom: '12px',
                  border: hasShort ? '2px solid #4CAF50' : '1px solid #e0e0e0'
                }}
              >
                <div style={{ marginBottom: '8px' }}>
                  <strong style={{ fontSize: '14px' }}>{drill.text_catalan}</strong>
                  {hasShort && (
                    <span style={{
                      marginLeft: '8px',
                      fontSize: '12px',
                      color: '#4CAF50',
                      fontWeight: 'bold'
                    }}>
                      ✓ Generat
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                  {drill.text_tachelhit}
                </div>
                <button
                  onClick={() => handleGenerateShort(drill.id)}
                  disabled={generating === drill.id}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    background: generating === drill.id ? '#ccc' : '#FF0080',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: generating === drill.id ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    width: '100%'
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
          width: '400px',
          borderRight: '1px solid #e0e0e0',
          overflowY: 'auto',
          padding: '20px'
        }}>
          <h3 style={{ marginTop: 0 }}>Shorts Generats</h3>

          {shorts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              <p>Cap short generat encara</p>
              <p style={{ fontSize: '13px' }}>Selecciona un drill a l'esquerra per començar</p>
            </div>
          ) : (
            shorts.map(short => (
              <div
                key={short.id}
                onClick={() => setSelectedVideo(short)}
                style={{
                  padding: '16px',
                  border: selectedVideo?.id === short.id ? '2px solid #FF0080' : '1px solid #e0e0e0',
                  borderRadius: '8px',
                  marginBottom: '12px',
                  cursor: 'pointer',
                  background: selectedVideo?.id === short.id ? '#fff0f8' : 'white',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ marginBottom: '8px' }}>
                  <strong style={{ fontSize: '15px', color: '#333' }}>
                    {short.text_catalan}
                  </strong>
                </div>
                <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>
                  {short.text_tachelhit}
                </div>
                <div style={{ fontSize: '12px', color: '#999', marginBottom: '12px' }}>
                  {new Date(short.date_created).toLocaleString('ca-ES')}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedVideo(short);
                    }}
                    style={{
                      flex: 1,
                      padding: '6px 12px',
                      fontSize: '12px',
                      background: '#2196F3',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    ▶ Veure
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteShort(short.id);
                    }}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      background: '#ff4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 600,
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
        <div style={{ flex: 1, padding: '30px', background: '#f8f9fa' }}>
          {selectedVideo ? (
            <div>
              <h2 style={{ marginTop: 0 }}>Preview del Short</h2>

              <div style={{
                marginBottom: '20px',
                padding: '16px',
                background: 'white',
                borderRadius: '8px'
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Català:</strong> {selectedVideo.text_catalan}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Tachelhit:</strong> {selectedVideo.text_tachelhit}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>العربية:</strong> {selectedVideo.text_arabic}
                </div>
              </div>

              {/* Video Player */}
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                background: '#000',
                borderRadius: '12px',
                padding: '20px'
              }}>
                <video
                  key={selectedVideo.id}
                  controls
                  style={{
                    width: 'auto',
                    height: '70vh',
                    maxWidth: '100%',
                    borderRadius: '8px'
                  }}
                  src={`${API_BASE}${selectedVideo.video_path}`}
                >
                  El teu navegador no suporta video.
                </video>
              </div>

              <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <a
                  href={`${API_BASE}${selectedVideo.video_path}`}
                  download={`short_${selectedVideo.drill_id}.mp4`}
                  style={{
                    display: 'inline-block',
                    padding: '12px 24px',
                    background: '#4CAF50',
                    color: 'white',
                    textDecoration: 'none',
                    borderRadius: '8px',
                    fontWeight: 600,
                    fontSize: '14px'
                  }}
                >
                  ⬇ Descarregar Short
                </a>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
              <p style={{ fontSize: '18px' }}>Selecciona un short per veure'l</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
