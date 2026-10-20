import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';
import { FaBullseye, FaHeadphones, FaPen, FaLink, FaTrash, FaPlay, FaVideo, FaCheck, FaTimes, FaLayerGroup, FaCalendarAlt, FaGraduationCap, FaSpinner, FaChartBar } from 'react-icons/fa';
import type { Test } from './TestsDashboard';

interface TestStats {
  total_attempts: number;
  average_score: number;
  completion_rate: number;
  passed_attempts: number;
  average_time: number;
}

interface Props {
  tests: Test[];
  selectedTest: Test | null;
  stats: TestStats | null;
  isMobile: boolean;
  generatingDemoVideoId: number | null;
  onSelect: (test: Test | null) => void;
  onTake: (test: Test) => void;
  onListen: (test: Test) => void;
  onEdit: (test: Test) => void;
  onPlayDrills: (test: Test) => void;
  onMakeVideo: (test: Test) => void;
  onViewVideo: (url: string) => void;
  onDelete: (test: Test) => void;
  onCreate: () => void;
  questionTypeLabel: (t: string) => string;
  hintLevelLabel: (l: string) => string;
}

const drillIdsOf = (t: Test) => t.drill_ids.split(',').map((x) => parseInt(x, 10)).filter((n) => !isNaN(n));

const fmtDate = (iso?: string) => {
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('ca-ES', { day: 'numeric', month: 'short', year: 'numeric' });
};

// A soft, deterministic colour per test for cards without a picture.
const hue = (s: string) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };

const pill: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px', borderRadius: 'var(--r-pill)', background: 'var(--surface-2)', border: '1px solid var(--border)', fontSize: '12px', fontWeight: 700, color: 'var(--text-soft)', whiteSpace: 'nowrap' };
const iconBtn = (danger = false): React.CSSProperties => ({ width: '36px', height: '36px', borderRadius: 'var(--r-pill)', border: `1px solid ${danger ? 'var(--rose)' : 'var(--border)'}`, background: danger ? 'var(--rose-soft)' : 'var(--surface)', color: danger ? 'var(--rose)' : 'var(--text-soft)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0 });

export default function TestsGallery(p: Props) {
  const { tests, selectedTest, stats, isMobile } = p;
  // One picture per test: the first drill of the test that has one (one request for all tests).
  const [covers, setCovers] = useState<Record<number, string>>({});
  useEffect(() => {
    const want = new Map<number, number[]>();
    for (const t of tests) want.set(t.id, drillIdsOf(t).slice(0, 6));
    const ids = [...new Set([...want.values()].flat())];
    if (!ids.length) return;
    let cancelled = false;
    (async () => {
      const found: Record<number, string> = {};
      for (let i = 0; i < ids.length; i += 150) {
        try {
          const r = await axios.get(`${API_BASE}/drills/`, { params: { ids: ids.slice(i, i + 150).join(',') } });
          for (const d of r.data as any[]) if (d?.image_url) found[d.id] = d.image_url;
        } catch { /* offline: cards keep their colour */ }
      }
      if (cancelled) return;
      const byTest: Record<number, string> = {};
      for (const [tid, dids] of want) { const hit = dids.find((d) => found[d]); if (hit) byTest[tid] = found[hit]; }
      setCovers(byTest);
    })();
    return () => { cancelled = true; };
  }, [tests]);

  const sorted = useMemo(() => [...tests].sort((a, b) => (b.date_created || '').localeCompare(a.date_created || '')), [tests]);

  const Cover = ({ t, height }: { t: Test; height: number }) => {
    const url = covers[t.id];
    return (
      <div style={{ height, background: url ? '#000' : `linear-gradient(135deg, hsl(${hue(t.title)} 55% 88%), hsl(${(hue(t.title) + 40) % 360} 60% 78%))`, position: 'relative', overflow: 'hidden' }}>
        {url
          ? <img src={getMediaUrl(url)} alt="" draggable={false} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          : <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: height > 160 ? '56px' : '36px', color: 'rgba(0,0,0,0.25)' }}><FaGraduationCap /></div>}
        <span style={{ position: 'absolute', left: '10px', bottom: '10px', ...pill, background: 'rgba(0,0,0,0.55)', color: '#fff', border: 'none', backdropFilter: 'blur(4px)' }}>
          <FaLayerGroup /> {drillIdsOf(t).length} drills
        </span>
      </div>
    );
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: isMobile ? '14px 12px' : '22px 24px', background: 'var(--bg)' }}>
      {tests.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-soft)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', maxWidth: '520px', margin: '40px auto' }}>
          <div style={{ width: '64px', height: '64px', margin: '0 auto 16px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '30px' }}><FaGraduationCap /></div>
          <p style={{ fontSize: '18px', marginBottom: '8px', fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-display)' }}>Encara no has creat cap test</p>
          <p style={{ fontSize: '14px', margin: '0 0 16px' }}>Prem «Nou test» i tria els drills que vulguis practicar</p>
          <button onClick={p.onCreate} style={{ padding: '10px 18px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer' }}>Nou test</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(${isMobile ? '160px' : '250px'}, 1fr))`, gap: isMobile ? '12px' : '18px' }}>
          {sorted.map((t) => (
            <div key={t.id} role="button" tabIndex={0} onClick={() => p.onSelect(t)} onKeyDown={(e) => { if (e.key === 'Enter') p.onSelect(t); }}
              aria-label={`Obre el test ${t.title}`}
              style={{ background: 'var(--surface)', border: `1px solid ${selectedTest?.id === t.id ? 'var(--brand-1)' : 'var(--border)'}`, borderRadius: 'var(--r-xl)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)', cursor: 'pointer', display: 'flex', flexDirection: 'column', transition: 'transform .15s, box-shadow .15s' }}
              onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; }}>
              <Cover t={t} height={isMobile ? 110 : 140} />
              <div style={{ padding: isMobile ? '10px 12px 12px' : '12px 14px 14px', display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: isMobile ? '14px' : '15.5px', color: 'var(--text)', lineHeight: 1.25, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{t.title}</div>
                {t.description && !isMobile && (
                  <div style={{ fontSize: '12.5px', color: 'var(--text-soft)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{t.description}</div>
                )}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: 'auto', paddingTop: '4px' }}>
                  <span style={pill}>{p.questionTypeLabel(t.question_type)}</span>
                  {t.date_created && <span style={pill}><FaCalendarAlt /> {fmtDate(t.date_created)}</span>}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center', marginTop: '6px' }} onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => p.onTake(t)} aria-label="Fes el test" style={{ flex: '1 1 110px', whiteSpace: 'nowrap', minHeight: '36px', padding: '0 12px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><FaBullseye /> Fes el test</button>
                  <button onClick={() => p.onListen(t)} title="Escolta els drills del test" aria-label="Escolta" style={iconBtn()}><FaHeadphones /></button>
                  {!isMobile && <button onClick={() => p.onEdit(t)} title="Edita el test" aria-label="Edita" style={iconBtn()}><FaPen /></button>}
                  <button onClick={() => p.onDelete(t)} title="Elimina el test" aria-label="Elimina" style={iconBtn(true)}><FaTrash /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail sheet */}
      {selectedTest && (
        <div onClick={() => p.onSelect(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(15,18,32,0.55)', zIndex: 1200, display: 'flex', alignItems: isMobile ? 'stretch' : 'center', justifyContent: 'center', padding: isMobile ? 0 : '24px' }}>
          <div onClick={(e) => e.stopPropagation()} role="dialog" aria-label={selectedTest.title}
            style={{ background: 'var(--surface)', borderRadius: isMobile ? 0 : 'var(--r-xl)', width: '100%', maxWidth: '760px', maxHeight: isMobile ? '100%' : '92vh', overflowY: 'auto', boxShadow: 'var(--shadow-xl)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ position: 'relative' }}>
              <Cover t={selectedTest} height={isMobile ? 160 : 200} />
              <button onClick={() => p.onSelect(null)} aria-label="Tanca" style={{ ...iconBtn(), position: 'absolute', top: '12px', right: '12px', background: 'rgba(0,0,0,0.5)', color: '#fff', border: 'none' }}><FaTimes /></button>
            </div>
            <div style={{ padding: isMobile ? '14px 16px 18px' : '18px 22px 22px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: isMobile ? '20px' : '24px', fontWeight: 800, color: 'var(--text)', lineHeight: 1.2 }}>{selectedTest.title}</h2>
                {selectedTest.description && <p style={{ margin: '6px 0 0', color: 'var(--text-soft)', fontSize: '14px', lineHeight: 1.5 }}>{selectedTest.description}</p>}
              </div>
              {/* Configuration: one row of pills */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }} aria-label="Configuració del test">
                <span style={pill}><FaLayerGroup /> {drillIdsOf(selectedTest).length} drills</span>
                <span style={pill}>{p.questionTypeLabel(selectedTest.question_type)}</span>
                <span style={pill}>{p.hintLevelLabel(selectedTest.hint_level)}{selectedTest.hint_level === 'partial' ? ` ${selectedTest.hint_percentage ?? 0}%` : ''}{selectedTest.hint_level === 'full_after_tries' ? ` (${selectedTest.hint_tries_before_reveal ?? 0})` : ''}</span>
                <span style={pill}>{(selectedTest.time_limit_seconds ?? 0) > 0 ? `${selectedTest.time_limit_seconds}s per pregunta` : 'Sense límit de temps'}</span>
                <span style={pill}>Aprovat {selectedTest.passing_score}%</span>
                {selectedTest.date_created && <span style={pill}><FaCalendarAlt /> {fmtDate(selectedTest.date_created)}</span>}
              </div>
              {/* Statistics */}
              {stats && stats.total_attempts > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${isMobile ? 3 : 5}, 1fr)`, gap: '8px' }}>
                  {[['Intents', String(stats.total_attempts)], ['Nota mitjana', `${stats.average_score}%`], ['Compleció', `${stats.completion_rate}%`], ['Aprovats', `${stats.passed_attempts}/${stats.total_attempts}`], ['Temps mitjà', `${stats.average_time}s`]].map(([k, v]) => (
                    <div key={k} style={{ padding: '8px 10px', background: 'var(--emerald-soft)', border: '1px solid var(--emerald)', borderRadius: 'var(--r-md)' }}>
                      <div style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--emerald)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '4px' }}><FaChartBar /> {k}</div>
                      <div style={{ fontSize: '17px', fontWeight: 800, color: 'var(--text)' }}>{v}</div>
                    </div>
                  ))}
                </div>
              )}
              {/* Actions */}
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: '8px' }}>
                <button onClick={() => p.onTake(selectedTest)} style={{ minHeight: '42px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px', boxShadow: 'var(--shadow-brand)' }}><FaBullseye /> Fes el test</button>
                <button onClick={() => p.onEdit(selectedTest)} style={{ minHeight: '42px', background: 'var(--surface)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><FaPen /> Edita</button>
                <button onClick={() => p.onPlayDrills(selectedTest)} style={{ minHeight: '42px', background: 'var(--surface)', color: 'var(--brand-1)', border: '1px solid var(--brand-1)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><FaPlay /> Reprodueix</button>
                <button onClick={() => p.onMakeVideo(selectedTest)} disabled={p.generatingDemoVideoId === selectedTest.id} style={{ minHeight: '42px', background: 'var(--surface)', color: 'var(--saffron-strong)', border: '1px solid var(--saffron)', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px', opacity: p.generatingDemoVideoId === selectedTest.id ? 0.6 : 1 }}>
                  {p.generatingDemoVideoId === selectedTest.id ? <><FaSpinner /> Generant…</> : <><FaVideo /> Crea el vídeo</>}
                </button>
              </div>
              {selectedTest.video_url && (
                <button onClick={() => p.onViewVideo(selectedTest.video_url!)} style={{ alignSelf: 'flex-start', padding: '9px 16px', background: 'var(--emerald)', color: '#fff', border: 'none', borderRadius: 'var(--r-md)', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaCheck /> Mira el vídeo</button>
              )}
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px', borderTop: '1px solid var(--border)' }}>
                <button onClick={() => { const url = `${window.location.origin}/tests/${selectedTest.id}`; navigator.clipboard.writeText(url); }} style={{ ...pill, cursor: 'pointer' }} title="Copia l'enllaç del test"><FaLink /> Copia l'enllaç</button>
                <button onClick={() => p.onDelete(selectedTest)} style={{ ...pill, cursor: 'pointer', color: 'var(--rose)', borderColor: 'var(--rose)', background: 'var(--rose-soft)' }}><FaTrash /> Elimina el test</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
