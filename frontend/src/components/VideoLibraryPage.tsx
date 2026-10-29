import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaPlay, FaCut } from 'react-icons/fa';
import { getYouTubeVideoId } from '../utils/youtubeUtils';
import type { Drill } from '../types';
import VideoLibraryPlayer from './VideoLibraryPlayer';
import { fetchAllDrills } from '../services/fetchAllDrills';

type LibraryVideo = { id: string; url: string; title: string; drills: Drill[] };

// Captured drills keep the YouTube link in source_url (video_url holds the
// Cloudinary clip); older hand-made drills put the YouTube link in video_url.
const youtubeLinkOf = (d: Drill): string | null => {
  for (const u of [d.source_url, d.video_url]) {
    if (u && getYouTubeVideoId(u)) return u;
  }
  return null;
};

export const groupLibraryVideos = (drills: Drill[]): LibraryVideo[] => {
  const grouped: Record<string, LibraryVideo> = {};
  for (const d of drills) {
    if (d.video_start_time === null || d.video_start_time === undefined) continue;
    const url = youtubeLinkOf(d);
    const id = url ? getYouTubeVideoId(url) : null;
    if (!url || !id) continue;
    if (!grouped[id]) grouped[id] = { id, url, title: d.source_title || d.tag || `Vídeo ${id}`, drills: [] };
    grouped[id].drills.push(d);
  }
  return Object.values(grouped)
    .map(v => ({ ...v, drills: [...v.drills].sort((a, b) => Number(a.video_start_time) - Number(b.video_start_time)) }))
    .sort((a, b) => b.drills.length - a.drills.length);
};

export default function VideoLibraryPage() {
  const navigate = useNavigate();
  const [drills, setDrills] = useState<Drill[]>([]);
  const [active, setActive] = useState<LibraryVideo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchAllDrills()
      .then(setDrills)
      .catch(err => { console.error('Failed to load drills:', err); setError(true); })
      .finally(() => setLoading(false));
  }, []);

  const videos = useMemo(() => groupLibraryVideos(drills), [drills]);

  return (
    <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <div style={{ padding: 'clamp(12px, 4vw, 24px)', background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
        <h1 id="library-title" style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: 'clamp(20px, 5vw, 24px)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
          Biblioteca de vídeos{videos.length > 0 && <span style={{ marginLeft: 10, fontSize: 14, fontWeight: 600, color: 'var(--text-muted)' }}>{videos.length}</span>}
        </h1>
        <p style={{ margin: '4px 0 0 0', color: 'var(--text-soft)', fontSize: '14px' }}>Els vídeos sencers, amb els drills que n'has capturat com a subtítols.</p>
      </div>

      <div role="region" aria-labelledby="library-title" style={{ padding: 'clamp(12px, 4vw, 32px)', display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', alignContent: 'start' }}>
        {error && (
          <div style={{ gridColumn: '1 / -1', padding: '12px 16px', background: 'var(--surface)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', color: 'var(--rose)', fontSize: 14 }}>
            No s'han pogut carregar els vídeos. Torna-ho a provar més tard.
          </div>
        )}
        {loading && !error && <div style={{ gridColumn: '1 / -1', color: 'var(--text-soft)', fontSize: 14 }}>S'estan carregant els vídeos…</div>}
        {!loading && !error && videos.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: 28, textAlign: 'center', background: 'var(--surface)', border: '1px dashed var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text-soft)', fontSize: 14 }}>
            Encara no hi ha vídeos. Captura una cançó o un conte des de <b>Captura</b> i apareixerà aquí sencer, amb els seus drills com a subtítols.
          </div>
        )}
        {videos.map(v => (
          <div
            key={v.id}
            style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', padding: 0, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)', color: 'var(--text)' }}
          >
          <button
            onClick={() => setActive(v)}
            aria-label={`Reprodueix el vídeo sencer: ${v.title}`}
            style={{ display: 'block', textAlign: 'left', padding: 0, background: 'transparent', border: 'none', cursor: 'pointer', color: 'inherit', fontFamily: 'inherit' }}
          >
            <div style={{ position: 'relative', aspectRatio: '16 / 9', background: 'var(--surface-2)' }}>
              <img src={`https://i.ytimg.com/vi/${v.id}/mqdefault.jpg`} alt="" loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              <span style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ width: 52, height: 52, borderRadius: '50%', background: 'rgba(15,23,42,0.72)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', paddingLeft: 4 }}><FaPlay size={18} /></span>
              </span>
            </div>
            <div style={{ padding: '12px 14px 14px' }}>
              <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{v.title}</div>
              <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-soft)' }}>
                {v.drills.length} {v.drills.length === 1 ? 'drill' : 'drills'}{v.drills[0]?.variety ? ` · ${v.drills[0].variety}` : ''}
              </div>
            </div>
          </button>
          {/* The other door: not watching it, auditing it. */}
          <button
            onClick={() => navigate(`/captura/video?url=${encodeURIComponent(v.url)}`)}
            style={{ margin: '0 14px 14px', padding: '7px 12px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text-soft)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
          >
            <FaCut size={11} /> Revisa els talls
          </button>
          </div>
        ))}
      </div>

      {active && <VideoLibraryPlayer videoUrl={active.url} drills={active.drills} onClose={() => setActive(null)} />}
    </div>
  );
}
