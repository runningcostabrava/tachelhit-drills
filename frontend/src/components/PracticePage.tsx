import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaChevronRight, FaListUl, FaMicrophone } from 'react-icons/fa';
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
  useEffect(() => { api.practiceCollections().then(setCol).catch(() => toast.error('No s’ha pogut carregar la pràctica')); }, []);
  const topics = useMemo(() => (col ? (allTopics ? col.topics : col.topics.slice(0, 8)) : []), [col, allTopics]);
  const go = (q: string) => navigate(`/tests/sessio?${q}`);
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
                <button key={key} onClick={() => go(`day=${d.day}&speaker=${encodeURIComponent(d.speaker)}`)} style={cardStyle}>
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
            {topics.map((t) => (
              <button key={t.slug} onClick={() => go(`topic=${t.slug}`)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: done[`topic:${t.slug}`] ? 'var(--brand-gradient-soft)' : 'var(--surface-2)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', color: 'var(--text)', fontFamily: 'inherit' }}>{t.label} · {t.count}</button>
            ))}
            {col.topics.length > 8 && <button onClick={() => setAllTopics((v) => !v)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allTopics ? 'Menys temes' : 'Tots els temes'}</button>}
          </div>
        </section>
      )}

      {col && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per unitat de gramàtica</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {col.units.filter((u) => u.count > 0).map((u, i) => (
              <button key={u.slug} onClick={() => go(`unit=${u.slug}`)} style={{ ...cardStyle, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 700 }}><span style={{ color: 'var(--text-muted)', marginRight: 8 }}>{i + 1}</span>{u.title}</span>
                <span style={{ fontSize: '12px', color: done[`unit:${u.slug}`] ? 'var(--emerald)' : 'var(--text-soft)', fontWeight: 700, whiteSpace: 'nowrap' }}>{done[`unit:${u.slug}`] ? `${done[`unit:${u.slug}`].right}/${done[`unit:${u.slug}`].total} bé` : `${u.count} frases`} <FaChevronRight size={10} /></span>
              </button>
            ))}
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
              <button key={t.id} onClick={() => go(`test_id=${t.id}`)} style={{ ...cardStyle, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 700 }}>{t.title}</span>
                <span style={{ fontSize: '12px', color: 'var(--text-soft)', fontWeight: 700, whiteSpace: 'nowrap' }}>{t.count} drills <FaChevronRight size={10} /></span>
              </button>
            ))}
            {col.lists.length === 0 && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Encara no tens cap llista.</div>}
          </div>
        </section>
      )}
      {!col && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
    </div>
  );
}
