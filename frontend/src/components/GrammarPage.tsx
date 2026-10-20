import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from '../toast';
import { FaBullseye, FaChevronLeft, FaVolumeUp } from 'react-icons/fa';
import { api, type GrammarUnit } from '../api';
import type { Drill } from '../types';
import { API_BASE, getMediaUrl } from '../config';

// The grammar course: the library organised as a sequence of grammar units (backend/grammar.py).
// Course view: the units in order, with how many drills illustrate each. Unit view: the lesson
// text (written once from the amazic.cat compendium) and the corpus's own examples, the
// speaker-recorded ones first, with a button that turns them into a test.

const LEVEL_LABEL: Record<number, string> = { 1: 'Nivell 1 · bàsic', 2: 'Nivell 2 · mitjà', 3: 'Nivell 3 · avançat' };

export default function GrammarPage() {
  const { slug } = useParams<{ slug?: string }>();
  return slug ? <UnitView slug={slug} /> : <CourseView />;
}

function CourseView() {
  const navigate = useNavigate();
  const [units, setUnits] = useState<GrammarUnit[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [status, setStatus] = useState<{ running: boolean; done: number; pending: number } | null>(null);
  useEffect(() => {
    api.grammarUnits().then((r) => { setUnits(r.units); setCounts(r.counts); setStatus(r.status); }).catch(() => toast.error('No s’ha pogut carregar el curs'));
  }, []);
  const levels = [1, 2, 3];
  return (
    <div style={{ padding: '20px 16px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Gramàtica</h1>
      <div style={{ color: 'var(--text-soft)', fontSize: '14px', marginBottom: '18px' }}>
        El curs: cada unitat explica un punt de gramàtica amb les frases reals de la biblioteca com a exemples.
        {status?.running && <span> · classificant drills ({status.done} fets, {status.pending} pendents)</span>}
      </div>
      {levels.map((lv) => (
        <section key={lv} style={{ marginBottom: '22px' }}>
          <h2 style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>{LEVEL_LABEL[lv]}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px' }}>
            {units.filter((u) => u.level === lv).map((u, i) => (
              <button key={u.slug} onClick={() => navigate(`/grammar/${u.slug}`)}
                style={{ textAlign: 'left', padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '6px', minHeight: '84px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>Unitat {units.findIndex((x) => x.slug === u.slug) + 1}{i === 0 ? '' : ''}</div>
                <div style={{ fontWeight: 700, color: 'var(--text)', fontSize: '15px', lineHeight: 1.25 }}>{u.title}</div>
                <div style={{ fontSize: '12px', color: counts[u.slug] ? 'var(--brand-1)' : 'var(--text-muted)' }}>{counts[u.slug] ? `${counts[u.slug]} exemples` : 'encara sense exemples'}</div>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function UnitView({ slug }: { slug: string }) {
  const navigate = useNavigate();
  const [unit, setUnit] = useState<(GrammarUnit & { lesson: string; total: number; drills: Drill[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setUnit(null); setError(null);
    api.grammarUnit(slug).then(setUnit).catch((e) => setError(e?.message || 'Error'));
  }, [slug]);
  const play = (d: Drill) => {
    const url = d.audio_url || d.audio_tts_shi_url;
    if (url) new Audio(getMediaUrl(url)).play().catch(() => {});
  };
  const makeTest = async () => {
    if (!unit) return;
    const ids = unit.drills.slice(0, 200).map((d) => d.id);
    try {
      await axios.post(`${API_BASE}/tests/`, {
        title: unit.title, description: `Unitat de gramàtica «${unit.title}» (${ids.length} drills)`,
        question_type: 'text_input', hint_level: 'none', hint_percentage: 30, hint_tries_before_reveal: 3,
        time_limit_seconds: null, passing_score: 70, drill_ids: ids.join(','),
      });
      toast.success(`Test «${unit.title}» creat amb ${ids.length} drills`);
      navigate('/tests');
    } catch { toast.error('No s’ha pogut crear el test'); }
  };
  return (
    <div style={{ padding: '20px 16px', maxWidth: '900px', margin: '0 auto' }}>
      <button onClick={() => navigate('/grammar')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: '8px' }}><FaChevronLeft /> Totes les unitats</button>
      {error && <div style={{ color: 'var(--rose)' }}>{error}</div>}
      {!unit && !error && <div style={{ color: 'var(--text-muted)' }}>Preparant la unitat… (la primera vegada s’escriu la lliçó, triga uns segons)</div>}
      {unit && (
        <>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>{LEVEL_LABEL[unit.level]}</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', margin: '2px 0 14px' }}>{unit.title}</h1>
          <article className="grammar-lesson" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '16px 18px', fontSize: '15px', lineHeight: 1.55, color: 'var(--text)', whiteSpace: 'pre-wrap', marginBottom: '18px' }}>
            {renderMarkdownLite(unit.lesson)}
          </article>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: 0, flex: 1 }}>Exemples de la biblioteca · {unit.total}</h2>
            {unit.drills.length > 0 && (
              <button onClick={makeTest} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}><FaBullseye /> Practica aquesta unitat</button>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {unit.drills.map((d) => (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                <button onClick={() => play(d)} disabled={!d.audio_url && !d.audio_tts_shi_url} aria-label="Escolta" style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : 'var(--surface-2)', color: d.audio_url ? '#fff' : 'var(--text-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={13} /></button>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, color: 'var(--text)' }}>{d.text_tachelhit}</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-soft)' }}>{d.text_catalan}{d.region ? <span style={{ color: 'var(--text-muted)' }}> · {d.region}</span> : null}</div>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', flexShrink: 0 }}>#{d.id}</span>
              </div>
            ))}
            {unit.drills.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Encara no hi ha drills classificats en aquesta unitat.</div>}
          </div>
        </>
      )}
    </div>
  );
}

// Headings, bold and bullet lines are enough for the lesson text; no Markdown library needed.
function renderMarkdownLite(md: string) {
  const lines = (md || '').replace(/\r/g, '').split('\n');
  return lines.map((line, i) => {
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) return <div key={i} style={{ fontWeight: 800, fontSize: h[1].length <= 2 ? '17px' : '15px', margin: '10px 0 4px' }}>{inline(h[2])}</div>;
    if (/^\s*[-*]\s+/.test(line)) return <div key={i} style={{ paddingLeft: '18px', textIndent: '-12px' }}>• {inline(line.replace(/^\s*[-*]\s+/, ''))}</div>;
    if (/^\|/.test(line)) return <div key={i} style={{ fontFamily: 'ui-monospace, monospace', fontSize: '13px' }}>{line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()).join('   ')}</div>;
    if (/^\s*$/.test(line)) return <div key={i} style={{ height: '6px' }} />;
    return <div key={i}>{inline(line)}</div>;
  });
}
function inline(s: string) {
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p.replace(/`/g, '')}</span>);
}
