import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaListUl, FaMicrophone, FaVideo, FaUser, FaTag } from 'react-icons/fa';
import { api, type PracticeCollections } from '../api';
import { toast } from '../toast';

// Pràctica: the library offered as short pronunciation sessions, four ways — by recording day
// (one of our speakers' sessions), by subject, by grammar unit, and the hand-made lists (the old
// tests). Every entry opens a session (PracticeSession) of up to 10 sentences.

const MONTHS = ['gen.', 'febr.', 'març', 'abr.', 'maig', 'juny', 'jul.', 'ag.', 'set.', 'oct.', 'nov.', 'des.'];
function dayLabel(day: string): string {
  const [y, m, d] = day.split('-').map(Number);
  return `${d} ${MONTHS[(m || 1) - 1]} ${y}`;
}

type Done = Record<string, { right: number; total: number; at: string }>;
const DONE_KEY = 'practice_done';
export function loadDone(): Done { try { return JSON.parse(localStorage.getItem(DONE_KEY) || '{}'); } catch { return {}; } }
export function saveDone(key: string, right: number, total: number) {
  try { localStorage.setItem(DONE_KEY, JSON.stringify({ ...loadDone(), [key]: { right, total, at: new Date().toISOString() } })); } catch { /* private mode */ }
}

const cardStyle: React.CSSProperties = { textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4, padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', color: 'var(--text)', fontFamily: 'inherit' };
const h2Style: React.CSSProperties = { margin: '0 0 8px', fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' };

export default function PracticePage() {
  const navigate = useNavigate();
  const [col, setCol] = useState<PracticeCollections | null>(null);
  const [done] = useState<Done>(loadDone);
  const [allTopics, setAllTopics] = useState(false);
  const [allVideos, setAllVideos] = useState(false);
  const [allTags, setAllTags] = useState(false);
  useEffect(() => { api.practiceCollections().then(setCol).catch(() => toast.error('No s’ha pogut carregar la pràctica')); }, []);
  const topics = useMemo(() => (col ? (allTopics ? col.topics : col.topics.slice(0, 8)) : []), [col, allTopics]);
  const go = (q: string) => navigate(`/tests/sessio?${q}`);
  const grid = (q: string) => navigate(`/tests/grup?${q}`);
  // a chip with two doors: the grid (see and play the drills) and the spoken session
  const chip = (label: string, count: number, q: string, key: string) => (
    <div key={key} style={{ display: 'inline-flex', alignItems: 'stretch', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', overflow: 'hidden', background: 'var(--surface)' }}>
      <button onClick={() => grid(q)} title="Obre la llista" style={{ padding: '8px 12px', border: 'none', background: 'transparent', color: 'var(--text)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label} <span style={{ color: 'var(--text-muted)' }}>{count}</span></button>
      <button onClick={() => go(q)} title="Practica la pronúncia" aria-label={`Practica ${label}`} style={{ padding: '8px 10px', border: 'none', borderLeft: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}><FaMicrophone size={11} /></button>
    </div>
  );
  const doneLine = (key: string) => done[key] ? `${done[key].right}/${done[key].total} bé` : null;
  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Pràctica</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: '14px', margin: '0 0 16px' }}>Sessions curtes per aprendre a dir-ho com en Driss i la Halima: escolta, repeteix i mira quines paraules s’han entès.</p>

      <button onClick={() => go('daily=1')} style={{ ...cardStyle, width: '100%', background: 'var(--brand-gradient)', color: '#fff', border: 'none', marginBottom: 20, gap: 6 }}>
        <span style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', opacity: 0.85 }}>Sessió d’avui</span>
        <span style={{ fontSize: '18px', fontWeight: 800 }}>Repàs: les frases que toca repetir avui</span>
        <span style={{ fontSize: '13px', opacity: 0.9 }}>10 frases · uns 6 minuts · <FaMicrophone size={11} /> cal el micròfon</span>
      </button>

      {col && col.days.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per dia de gravació</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
            {col.days.map((d) => {
              const key = `day:${d.day}:${d.speaker}`;
              return (
                <button key={key} onClick={() => grid(`day=${d.day}&speaker=${encodeURIComponent(d.speaker)}&title=${encodeURIComponent(`${d.speaker} · ${dayLabel(d.day)}`)}`)} style={cardStyle}>
                  <span style={{ fontSize: '12px', color: 'var(--text-soft)' }}>{dayLabel(d.day)}</span>
                  <span style={{ fontSize: '15px', fontWeight: 800 }}>{d.speaker}</span>
                  <span style={{ fontSize: '12px', color: doneLine(key) ? 'var(--emerald)' : 'var(--text-soft)' }}>{d.count} frases{doneLine(key) ? ` · ${doneLine(key)}` : ''}</span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {col && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per tema</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {topics.map((t) => chip(t.label, t.count, `topic=${t.slug}&title=${encodeURIComponent(t.label)}`, t.slug))}
            {col.topics.length > 8 && <button onClick={() => setAllTopics((v) => !v)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allTopics ? 'Menys temes' : 'Tots els temes'}</button>}
          </div>
        </section>
      )}

      {col && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per unitat de gramàtica</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {col.units.filter((u) => u.count > 0).map((u, i) => (
              <div key={u.slug} style={{ ...cardStyle, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', cursor: 'default' }}>
                <button onClick={() => grid(`unit=${u.slug}&title=${encodeURIComponent(u.title)}`)} style={{ flex: 1, textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '14px', fontWeight: 700, color: 'var(--text)', padding: 0 }}><span style={{ color: 'var(--text-muted)', marginRight: 8 }}>{i + 1}</span>{u.title}</button>
                <span style={{ fontSize: '12px', color: done[`unit:${u.slug}`] ? 'var(--emerald)' : 'var(--text-soft)', fontWeight: 700, whiteSpace: 'nowrap' }}>{done[`unit:${u.slug}`] ? `${done[`unit:${u.slug}`].right}/${done[`unit:${u.slug}`].total} bé` : `${u.count} frases`}</span>
                <button onClick={() => go(`unit=${u.slug}`)} aria-label={`Practica ${u.title}`} title="Practica la pronúncia" style={{ marginLeft: 10, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaMicrophone size={11} /></button>
              </div>
            ))}
          </div>
        </section>
      )}

      {col && col.videos.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaVideo size={11} /> Per vídeo</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(allVideos ? col.videos : col.videos.slice(0, 10)).map((v) => chip(v.title, v.count, `video=${encodeURIComponent(v.title)}&title=${encodeURIComponent(v.title)}`, v.title))}
            {col.videos.length > 10 && <button onClick={() => setAllVideos((x) => !x)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 14, fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allVideos ? 'Menys vídeos' : `Tots els vídeos (${col.videos.length})`}</button>}
          </div>
        </section>
      )}

      {col && col.people.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaUser size={11} /> Per persona</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {col.people.map((p) => chip(p.name, p.count, `person=${encodeURIComponent(p.name)}&title=${encodeURIComponent(p.name)}`, p.name))}
          </div>
        </section>
      )}

      {col && col.tags.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaTag size={11} /> Per etiqueta</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(allTags ? col.tags : col.tags.slice(0, 12)).map((t) => chip(t.tag, t.count, `tag=${encodeURIComponent(t.tag)}&title=${encodeURIComponent(t.tag)}`, t.tag))}
            {col.tags.length > 12 && <button onClick={() => setAllTags((x) => !x)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 14, fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allTags ? 'Menys etiquetes' : `Totes les etiquetes (${col.tags.length})`}</button>}
          </div>
        </section>
      )}

      {col && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <h2 style={h2Style}>Les meves llistes</h2>
            <button onClick={() => navigate('/tests/llistes')} style={{ background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 4 }}><FaListUl size={11} /> Gestiona les llistes</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {col.lists.slice(0, 6).map((t) => (
              <div key={t.id} style={{ ...cardStyle, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', cursor: 'default' }}>
                <button onClick={() => grid(`test_id=${t.id}&title=${encodeURIComponent(t.title)}`)} style={{ flex: 1, textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '14px', fontWeight: 700, color: 'var(--text)', padding: 0 }}>{t.title}</button>
                <span style={{ fontSize: '12px', color: 'var(--text-soft)', fontWeight: 700, whiteSpace: 'nowrap' }}>{t.count} drills</span>
                <button onClick={() => go(`test_id=${t.id}`)} aria-label={`Practica ${t.title}`} title="Practica la pronúncia" style={{ marginLeft: 10, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaMicrophone size={11} /></button>
              </div>
            ))}
            {col.lists.length === 0 && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Encara no tens cap llista.</div>}
          </div>
        </section>
      )}
      {!col && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
    </div>
  );
}
