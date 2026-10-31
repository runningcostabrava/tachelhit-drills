import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FaBullseye, FaChevronLeft, FaPlay, FaVolumeUp } from 'react-icons/fa';
import { api, type PracticeCard } from '../api';
import { getMediaUrl } from '../config';

import type { Drill } from '../types';
import DrillPlayer from './DrillPlayer';

// One group of the library as a grid: every drill with its picture, both texts, who says it and a
// play button, plus «Reprodueix» (the player, one card after another) and «Practica» (a spoken
// session). A group is any of the ways Pràctica cuts the library: subject, grammar unit, recording
// day, video, person, tag or a hand-made list.

const KEYS = ['topic', 'unit', 'day', 'speaker', 'video', 'person', 'tag', 'test_id'] as const;

export default function PracticeGroupPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [drills, setDrills] = useState<Drill[] | null>(null);
  const [cards, setCards] = useState<PracticeCard[]>([]);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const q = new URLSearchParams();
    for (const k of KEYS) { const v = params.get(k); if (v) q.set(k, v); }
    q.set('with_voice', 'false'); q.set('limit', '400');
    return q.toString();
  }, [params]);
  const title = params.get('title') || params.get('topic') || params.get('unit') || params.get('video') || params.get('person') || params.get('tag') || params.get('day') || 'Grup';

  // When a hand-made list comes back empty, why? The server filtered it; the page asks what the
  // list holds and counts the reasons, instead of shrugging.
  const [whyEmpty, setWhyEmpty] = useState<{ held: number; noText: number; noMeaning: number } | null>(null);

  useEffect(() => {
    setDrills(null); setError(null); setWhyEmpty(null);
    api.practiceSession(query).then(async (r) => {
      setDrills(r.drills); setCards(r.cards);
      const testId = Number(params.get('test_id'));
      if (r.drills.length || !testId) return;
      try {
        const all = await api.practices();
        const list = all.find((t) => t.id === testId);
        const ids = (list?.drill_ids || '').split(',').map((x) => Number(x.trim())).filter(Boolean);
        if (!ids.length) { setWhyEmpty({ held: 0, noText: 0, noMeaning: 0 }); return; }
        const held = await api.drillsByIds(ids);
        setWhyEmpty({
          held: held.length,
          noText: held.filter((d) => !(d.text_tachelhit || '').trim()).length,
          noMeaning: held.filter((d) => !(d.text_catalan || '').trim()).length,
        });
      } catch { /* the plain message is still true */ }
    }).catch((e) => setError(e?.message || 'Error'));
  }, [query, params]);

  const practise = () => {
    const q = new URLSearchParams();
    for (const k of KEYS) { const v = params.get(k); if (v) q.set(k, v); }
    navigate(`/tests/sessio?${q.toString()}`);
  };
  const play = (url?: string | null) => { if (url) new Audio(getMediaUrl(url)).play().catch(() => {}); };

  if (playing && drills && drills.length > 0) return <DrillPlayer drills={drills} onExit={() => setPlaying(false)} />;

  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: 1100, margin: '0 auto' }}>
      <button onClick={() => navigate('/tests')} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: 6 }}><FaChevronLeft /> Pràctica</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: '0 0 4px' }}>{title}</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 14, margin: '0 0 14px' }}>{drills ? `${drills.length} drills` : 'Carregant…'}{drills && drills.length === 400 ? ' (els primers 400)' : ''}</p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <button onClick={() => setPlaying(true)} disabled={!drills?.length} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', opacity: drills?.length ? 1 : 0.6 }}><FaPlay size={12} /> Reprodueix</button>
        <button onClick={practise} disabled={!drills?.length} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', opacity: drills?.length ? 1 : 0.6 }}><FaBullseye size={12} /> Fes la sessió</button>
      </div>

      {error && <div style={{ color: 'var(--rose)' }}>{error}</div>}
      {drills && drills.length === 0 && (
        <div style={{ color: 'var(--text-soft)', fontSize: 14, lineHeight: 1.55, maxWidth: 560 }}>
          {!whyEmpty ? (
            'Aquest grup no té cap frase per practicar.'
          ) : whyEmpty.held === 0 ? (
            'Aquesta llista està buida: no hi ha cap frase a dins.'
          ) : (
            <>
              <strong>La llista té {whyEmpty.held} {whyEmpty.held === 1 ? 'frase' : 'frases'}, però cap no es pot practicar encara.</strong>
              <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                {whyEmpty.noText > 0 && <li>{whyEmpty.noText} no {whyEmpty.noText === 1 ? 'té' : 'tenen'} les paraules escrites en amazic.</li>}
                {whyEmpty.noMeaning > 0 && <li>{whyEmpty.noMeaning} no {whyEmpty.noMeaning === 1 ? 'diu' : 'diuen'} què vol dir en català.</li>}
                {whyEmpty.noText === 0 && whyEmpty.noMeaning === 0 && <li>El text que porten no és una frase (per exemple, hi diu literalment «text»).</li>}
              </ul>
              <p style={{ margin: '10px 0 0' }}>
                Si tenen veu, la feina és escriure el que s’hi diu: obre’n una a <strong>Frases</strong> i escriu-hi les paraules.
              </p>
            </>
          )}
        </div>
      )}
      {drills && drills.length > 0 && (
        <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', background: 'var(--surface)' }}>
          {drills.map((d, i) => {
            const c = cards[i];
            const voice = d.audio_url;
            return (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderTop: i ? '1px solid var(--border)' : 'none' }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 44, flexShrink: 0 }}>#{d.id}</span>
                {d.image_url
                  ? <img src={getMediaUrl(d.image_url)} alt="" style={{ width: 54, height: 40, objectFit: 'cover', borderRadius: 'var(--r-sm)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                  : <span style={{ width: 54, flexShrink: 0 }} />}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, color: 'var(--text)', fontSize: 15 }}>{d.text_tachelhit || <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>sense amazic</span>}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', width: 150, flexShrink: 0, textAlign: 'right' }}>{c?.speaker || d.region || ''}{d.audio_url ? '' : voice ? ' · veu sintètica' : ' · sense veu'}</div>
                <button onClick={() => play(voice)} disabled={!voice} aria-label="Escolta" style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : voice ? 'var(--sky)' : 'var(--surface-2)', color: voice ? '#fff' : 'var(--text-muted)', cursor: voice ? 'pointer' : 'default', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={12} /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
