import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMediaUrl, getUserToken } from '../config';
import { api, type CorpusStats } from '../api';
import type { Drill } from '../types';

export default function CorpusPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [variety, setVariety] = useState('');
  const [onlyUnverified, setOnlyUnverified] = useState(false);
  const [results, setResults] = useState<Drill[]>([]);
  const [stats, setStats] = useState<CorpusStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.corpusStats().then(setStats).catch(() => {});
  }, []);

  const PAGE = 50;
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const runSearch = useCallback(async (nextOffset: number, append: boolean) => {
    setLoading(true);
    try {
      let rows = await api.corpusSearch({
        q: q.trim(), variety: variety.trim(), limit: PAGE, offset: nextOffset,
      });
      setHasMore(rows.length === PAGE);
      if (onlyUnverified) rows = rows.filter(d => !d.verified);
      setResults(prev => (append ? [...prev, ...rows] : rows));
      setOffset(nextOffset);
    } catch (e) {
      console.error('Corpus search failed', e);
    } finally {
      setLoading(false);
    }
  }, [q, variety, onlyUnverified]);

  useEffect(() => { runSearch(0, false); }, [runSearch]);
  const search = () => runSearch(0, false);

  const playAudio = (d: Drill) => {
    const url = d.audio_url ? getMediaUrl(d.audio_url) : '';
    if (url) new Audio(url).play().catch(() => {});
  };

  const toggleVerify = async (d: Drill) => {
    if (!getUserToken()) {
      alert('Per verificar contribucions necessites un compte — crea\'l a 👤 Perfil.');
      return;
    }
    try {
      await api.verifyDrill(d.id, !d.verified);
      setResults(prev => prev.map(x => x.id === d.id ? { ...x, verified: !d.verified } : x));
    } catch (e: any) {
      alert(e.message);
    }
  };

  const chip = (label: string, bg: string, color: string) => (
    <span style={{ padding: '3px 10px', borderRadius: 'var(--r-pill)', fontSize: '11px', fontWeight: 700, background: bg, color }}>
      {label}
    </span>
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: '48px' }}>
      <div style={{ background: 'var(--brand-gradient)', borderRadius: '0 0 var(--r-2xl) var(--r-2xl)', padding: '24px 24px 28px', color: '#fff' }}>
        <div style={{ maxWidth: '860px', margin: '0 auto' }}>
          <button onClick={() => navigate('/')} style={{ marginBottom: '14px', padding: '8px 16px', background: 'rgba(255,255,255,0.18)', color: '#fff', border: '1px solid rgba(255,255,255,0.4)', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontWeight: 600, fontSize: '14px' }}>← Back</button>
          <h2 style={{ color: '#fff', fontSize: '26px', margin: 0 }}>📖 Corpus</h2>
          {stats && (
            <p style={{ margin: '8px 0 0', color: 'rgba(255,255,255,0.85)', fontSize: '14px' }}>
              {stats.total_drills} entrades · {stats.with_audio} amb àudio · {stats.verified} verificades
            </p>
          )}
        </div>
      </div>

      <div style={{ maxWidth: '860px', margin: '0 auto', padding: '20px 24px' }}>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '18px' }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
            placeholder="Cerca en ⵜⵉⴼⵉⵏⴰⵖ, llatí, català o àrab…"
            style={{ flex: 2, minWidth: '220px', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '15px', color: 'var(--text)' }}
          />
          <select
            value={variety}
            onChange={(e) => setVariety(e.target.value)}
            style={{ flex: 1, minWidth: '140px', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', color: 'var(--text)' }}
          >
            <option value="">Totes les varietats</option>
            {Object.entries(stats?.by_variety || {})
              .filter(([k]) => k !== 'unspecified')
              .map(([k, n]) => (
                <option key={k} value={k}>{k} ({n})</option>
              ))}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', cursor: 'pointer' }}>
            <input type="checkbox" checked={onlyUnverified} onChange={(e) => setOnlyUnverified(e.target.checked)} />
            Només pendents de revisar
          </label>
        </div>

        {loading && <p style={{ color: 'var(--text-soft)' }}>Cercant…</p>}
        {!loading && results.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Cap resultat.</p>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {results.map((d) => (
            <div key={d.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-sm)', padding: '16px 18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  {d.text_tachelhit && (
                    <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brand-1)', fontFamily: 'var(--font-tifinagh)' }}>{d.text_tachelhit}</div>
                  )}
                  {d.text_tachelhit_latin && (
                    <div style={{ fontSize: '14px', color: 'var(--text-soft)', fontStyle: 'italic' }}>{d.text_tachelhit_latin}</div>
                  )}
                  {d.text_catalan && (
                    <div style={{ fontSize: '14px', color: 'var(--emerald)', marginTop: '4px' }}>{d.text_catalan}</div>
                  )}
                  {d.text_arabic && (
                    <div style={{ fontSize: '15px', color: 'var(--text)', direction: 'rtl', textAlign: 'right', marginTop: '4px' }}>{d.text_arabic}</div>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {d.variety && chip(d.variety, 'var(--brand-gradient-soft)', 'var(--brand-1)')}
                    {d.region && chip(d.region, 'var(--sky-soft)', 'var(--sky)')}
                    {d.author && chip(`👤 ${d.author}`, 'var(--surface-2)', 'var(--text-soft)')}
                    {d.verified
                      ? chip('✓ verificat', 'var(--emerald-soft)', 'var(--emerald)')
                      : chip('pendent', 'var(--amber-soft)', 'var(--amber-strong)')}
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {d.audio_url && (
                      <button onClick={() => playAudio(d)} style={{ padding: '7px 14px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>
                        ▶ Àudio
                      </button>
                    )}
                    <button
                      onClick={() => toggleVerify(d)}
                      style={{ padding: '7px 14px', background: d.verified ? 'var(--surface-2)' : 'var(--emerald)', border: d.verified ? '1px solid var(--border)' : 'none', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontSize: '13px', fontWeight: 700, color: d.verified ? 'var(--text-soft)' : '#fff' }}
                    >
                      {d.verified ? 'Desverifica' : '✓ Verifica'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {hasMore && !loading && (
          <div style={{ textAlign: 'center', marginTop: '18px' }}>
            <button
              onClick={() => runSearch(offset + PAGE, true)}
              style={{ padding: '11px 26px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontWeight: 700, fontSize: '14px', color: 'var(--text)' }}
            >
              ⬇ Carrega'n més
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
