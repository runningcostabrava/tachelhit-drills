import { useState, useEffect, useCallback } from 'react';
import { getMediaUrl, getUserToken } from '../config';
import { api, type CorpusStats } from '../api';
import { toast } from '../toast';
import type { Drill } from '../types';

export default function CorpusPage() {
  const [q, setQ] = useState('');
  const [variety, setVariety] = useState('');
  const [onlyUnverified, setOnlyUnverified] = useState(false);
  const [results, setResults] = useState<Drill[]>([]);
  const [stats, setStats] = useState<CorpusStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [gaps, setGaps] = useState<{ kind: string; label: string; count: number }[]>([]);
  const [activeGap, setActiveGap] = useState<string | null>(null);
  const [showCoverage, setShowCoverage] = useState(false);

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

  useEffect(() => {
    api.corpusStats().then(setStats).catch(() => {});
    api.corpusGapsSummary().then(r => setGaps(r.gaps)).catch(() => {});
  }, []);

  // Search only drives results when no gap filter is active
  useEffect(() => { if (!activeGap) runSearch(0, false); }, [runSearch, activeGap]);
  const search = () => { setActiveGap(null); runSearch(0, false); };

  const loadGap = async (kind: string) => {
    setActiveGap(kind);
    setLoading(true);
    try {
      const r = await api.corpusGapDrills(kind, 100);
      setResults(r.drills);
      setHasMore(false);
    } catch (e) {
      console.error('Gap load failed', e);
    } finally {
      setLoading(false);
    }
  };

  const clearGap = () => { setActiveGap(null); runSearch(0, false); };

  const playAudio = (d: Drill) => {
    const url = d.audio_url ? getMediaUrl(d.audio_url) : '';
    if (url) new Audio(url).play().catch(() => {});
  };

  const toggleVerify = async (d: Drill) => {
    if (!getUserToken()) {
      toast.info('Per verificar contribucions necessites un compte — crea\'l a 👤 Perfil.');
      return;
    }
    try {
      await api.verifyDrill(d.id, !d.verified);
      setResults(prev => prev.map(x => x.id === d.id ? { ...x, verified: !d.verified } : x));
      toast.success(d.verified ? 'Verificació retirada' : '✓ Verificat');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const chip = (label: string, bg: string, color: string) => (
    <span style={{ padding: '3px 10px', borderRadius: 'var(--r-pill)', fontSize: '11px', fontWeight: 700, background: bg, color }}>
      {label}
    </span>
  );

  // Horizontal proportion bar used across the coverage dashboard
  const bar = (label: string, value: number, total: number, color: string) => {
    const pct = total > 0 ? Math.round((value / total) * 100) : 0;
    return (
      <div key={label} style={{ marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
          <span style={{ color: 'var(--text-soft)', fontWeight: 600 }}>{label}</span>
          <span style={{ color: 'var(--text-muted)' }}>{value}{total ? ` · ${pct}%` : ''}</span>
        </div>
        <div style={{ height: '8px', borderRadius: 'var(--r-pill)', background: 'var(--surface-2)', overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 'var(--r-pill)', transition: 'width 0.3s' }} />
        </div>
      </div>
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: '48px' }}>
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '18px 24px' }}>
        <div style={{ maxWidth: '860px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Corpus</h1>
          {stats && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '6px', flexWrap: 'wrap' }}>
              <p style={{ margin: 0, color: 'var(--text-soft)', fontSize: '14px' }}>
                {stats.total_drills} entrades · {stats.with_audio} amb àudio · {stats.verified} verificades
              </p>
              <button
                onClick={() => setShowCoverage(v => !v)}
                style={{ padding: '5px 12px', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontWeight: 700, fontSize: '13px' }}
              >
                {showCoverage ? 'Amaga cobertura' : 'Cobertura'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Coverage dashboard — the atlas view: what's documented, by variety/region */}
      {showCoverage && stats && (
        <div style={{ maxWidth: '860px', margin: '20px auto 0', padding: '0 24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '13px', fontWeight: 800, marginBottom: '14px', color: 'var(--text)' }}>Cobertura de mitjans</div>
              {bar('🔊 Àudio', stats.with_audio, stats.total_drills, 'var(--emerald)')}
              {bar('🎬 Vídeo', stats.with_video, stats.total_drills, 'var(--sky)')}
              {bar('Aa Llatí', stats.with_latin_script, stats.total_drills, 'var(--brand-1)')}
              {bar('✓ Verificat', stats.verified, stats.total_drills, 'var(--amber)')}
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '13px', fontWeight: 800, marginBottom: '14px', color: 'var(--text)' }}>Per varietat</div>
              {Object.entries(stats.by_variety).sort((a, b) => b[1] - a[1]).slice(0, 8)
                .map(([k, n]) => bar(k === 'unspecified' ? '— sense especificar' : k, n, stats.total_drills, 'var(--brand-2)'))}
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '13px', fontWeight: 800, marginBottom: '14px', color: 'var(--text)' }}>Per regió</div>
              {Object.entries(stats.by_region).sort((a, b) => b[1] - a[1]).slice(0, 8)
                .map(([k, n]) => bar(k === 'unspecified' ? '— sense especificar' : k, n, stats.total_drills, 'var(--sky)'))}
            </div>
          </div>
        </div>
      )}

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

        {/* Documentation-gaps work-list: what the corpus still needs */}
        {gaps.some(g => g.count > 0) && (
          <div style={{ marginBottom: '18px' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
              🛠 Necessita feina
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {gaps.filter(g => g.count > 0).map(g => (
                <button
                  key={g.kind}
                  onClick={() => (activeGap === g.kind ? clearGap() : loadGap(g.kind))}
                  style={{
                    padding: '6px 12px', borderRadius: 'var(--r-pill)', fontSize: '13px', fontWeight: 700, cursor: 'pointer',
                    background: activeGap === g.kind ? 'var(--amber)' : 'var(--amber-soft)',
                    color: activeGap === g.kind ? '#fff' : 'var(--amber-strong)',
                    border: '1px solid var(--amber)'
                  }}
                >
                  {g.label} · {g.count}
                </button>
              ))}
              {activeGap && (
                <button onClick={clearGap} style={{ padding: '6px 12px', borderRadius: 'var(--r-pill)', fontSize: '13px', fontWeight: 700, cursor: 'pointer', background: 'var(--surface-2)', color: 'var(--text-soft)', border: '1px solid var(--border)' }}>
                  ✕ Neteja
                </button>
              )}
            </div>
          </div>
        )}

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
