import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FaCheck, FaCut, FaPlay, FaSave, FaTrash, FaExclamationTriangle } from 'react-icons/fa';
import { api, type CaptureCut, type CaptureVideo } from '../api';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import { loadYouTubeApi } from '../utils/youtubeUtils';

// What a video gave us, and the chance to disagree with it.
//
// The capture screen showed the machine's proposal and then forgot it: once the drills existed
// there was no way back to the video they came from, even though every one of them carries where
// it was cut from. So a cut that landed on the wrong phrase (drill 6854 said «tinc gana» and the
// four seconds held something else) could only be found by ear, one at a time, by accident.
//
// Here the video plays above and its cuts sit below in time order. Pressing a cut plays THAT
// stretch of the original, so you hear what the cut really holds instead of what we wrote down.
// The two things you can change are the two that matter: where it starts and ends, and what it
// says. They are saved separately on purpose — moving a cut and rewriting a sentence are
// different decisions, and the speaker's words are not collateral of a dragged handle.

const secs = (n: number | null | undefined) =>
  n == null ? '—' : `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, '0')}.${String(Math.round((n % 1) * 10))}`;

const youtubeId = (url: string): string | null => {
  const m = url.match(/(?:youtube\.com\/.*[?&]v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/);
  return m ? m[1] : null;
};

export default function CaptureReview() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const url = params.get('url') || '';

  const [data, setData] = useState<CaptureVideo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [edit, setEdit] = useState<Record<number, { start: number; end: number; tachelhit: string; catalan: string }>>({});
  const [busy, setBusy] = useState<number | null>(null);

  const player = useRef<any>(null);
  const stopAt = useRef<number | null>(null);
  const clock = useRef<number | null>(null);
  const stopClock = () => { if (clock.current != null) { window.clearInterval(clock.current); clock.current = null; } };
  useEffect(() => stopClock, []);
  const vid = useMemo(() => youtubeId(url), [url]);

  const load = useCallback(() => {
    if (!url) return;
    api.captureVideo(url)
      .then((d) => { setData(d); setLoadError(null); })
      .catch((e) => setLoadError(whyItFailed(e, 'No s’ha pogut llegir aquest vídeo')));
  }, [url]);
  useEffect(load, [load]);

  // The YouTube player, through the shared loader: never overwrite onYouTubeIframeAPIReady.
  useEffect(() => {
    if (!vid) return;
    let dead = false;
    loadYouTubeApi().then((YT: any) => {
      if (dead) return;
      player.current = new YT.Player('capture-player', {
        videoId: vid,
        playerVars: { rel: 0, modestbranding: 1 },
        events: {
          onStateChange: (e: any) => {
            // Playing one cut means stopping where the cut stops: the API has no «play until».
            // Anything that is not playing ends the watch, so pausing by hand or dragging the
            // video away does not leave a timer running for the rest of the session.
            stopClock();
            if (e.data !== YT.PlayerState.PLAYING || stopAt.current == null) return;
            clock.current = window.setInterval(() => {
              const at = player.current?.getCurrentTime?.();
              if (stopAt.current != null && at != null && at >= stopAt.current) {
                player.current?.pauseVideo?.();
                stopAt.current = null;
                stopClock();
              }
            }, 120);
          },
        },
      });
    }).catch(() => {});
    return () => { dead = true; try { player.current?.destroy?.(); } catch { /* gone already */ } };
  }, [vid]);

  const playRange = (from: number, to: number) => {
    if (!player.current?.seekTo) { toast.info('El reproductor encara no és a punt'); return; }
    stopAt.current = to;
    player.current.seekTo(from, true);
    player.current.playVideo();
  };

  const draft = (c: CaptureCut) =>
    edit[c.id] || {
      start: c.start ?? 0, end: c.end ?? 0,
      tachelhit: c.text_tachelhit || '', catalan: c.text_catalan || '',
    };
  // Built on top of the whole cut, not on top of whatever the draft happens to hold: starting
  // from `edit[id]` meant the first drag left `{start}` alone and lost the end and the texts.
  const setDraft = (c: CaptureCut, patch: Partial<ReturnType<typeof draft>>) =>
    setEdit((e) => ({ ...e, [c.id]: { ...draft(c), ...patch } }));

  const moved = (c: CaptureCut) => {
    const d = edit[c.id];
    return !!d && (d.start !== (c.start ?? 0) || d.end !== (c.end ?? 0));
  };
  const rewritten = (c: CaptureCut) => {
    const d = edit[c.id];
    return !!d && (d.tachelhit !== (c.text_tachelhit || '') || d.catalan !== (c.text_catalan || ''));
  };

  /** Cut again from the original. The text is not touched here. */
  const recut = async (c: CaptureCut) => {
    const d = draft(c);
    setBusy(c.id);
    try {
      const r = await api.recutDrill(c.id, d.start, d.end);
      toast.success(r.kept_drawing ? 'Tallat de nou (la imatge dibuixada s’ha deixat estar)' : 'Tallat de nou');
      setEdit((e) => { const n = { ...e }; delete n[c.id]; return n; });
      load();
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut tallar')); }
    finally { setBusy(null); }
  };

  /** Only the words, and only the ones you changed. */
  const saveText = async (c: CaptureCut) => {
    const d = draft(c);
    const patch: Record<string, string> = {};
    if (d.tachelhit !== (c.text_tachelhit || '')) patch.text_tachelhit = d.tachelhit;
    if (d.catalan !== (c.text_catalan || '')) patch.text_catalan = d.catalan;
    if (!Object.keys(patch).length) return;
    setBusy(c.id);
    try {
      await api.updateDrill(c.id, patch);
      toast.success('Text desat');
      setEdit((e) => { const n = { ...e }; delete n[c.id]; return n; });
      load();
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut desar')); }
    finally { setBusy(null); }
  };

  const [killing, setKilling] = useState<number | null>(null);
  const throwAway = async (c: CaptureCut) => {
    if (killing !== c.id) { setKilling(c.id); window.setTimeout(() => setKilling((k) => (k === c.id ? null : k)), 4000); return; }
    setKilling(null); setBusy(c.id);
    try { await api.deleteDrill(c.id); toast.success('Tall llençat'); load(); }
    catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut esborrar')); }
    finally { setBusy(null); }
  };

  if (!url) return <p style={{ padding: 40, textAlign: 'center' }}>Falta dir quin vídeo.</p>;
  if (loadError) return (
    <div style={{ padding: '40px 16px', maxWidth: 520, margin: '0 auto', textAlign: 'center' }}>
      <p style={{ color: 'var(--text-soft)' }}>{loadError}</p>
      <button onClick={() => navigate('/library')} style={pill}>Torna als vídeos</button>
    </div>
  );
  if (!data) return <p style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant els talls…</p>;

  const span = (data.covered_to || 0) - (data.covered_from || 0) || 1;

  return (
    <div style={{ padding: '18px 16px 40px', maxWidth: 1000, margin: '0 auto' }}>
      <button onClick={() => navigate('/library')} style={{ ...pill, marginBottom: 10 }}>← Vídeos</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 23, margin: '0 0 2px' }}>{data.title || url}</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13.5, margin: '0 0 14px' }}>
        {data.cuts.length} {data.cuts.length === 1 ? 'tall' : 'talls'} · {data.with_voice} amb veu · {data.verified} verificats
        {data.channel ? ` · ${data.channel}` : ''}
      </p>

      {vid ? (
        <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: 14, background: '#000' }}>
          <div id="capture-player" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
        </div>
      ) : (
        <p style={{ fontSize: 13.5, color: 'var(--text-muted)', marginBottom: 14 }}>
          Aquest vídeo no és de YouTube, així que no el puc reproduir aquí. Els talls sí que es poden ajustar.
        </p>
      )}

      {/* The line of the video: where we took something and where we left it alone. */}
      {data.covered_from != null && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ position: 'relative', height: 26, borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            {data.cuts.filter((c) => c.start != null && c.end != null).map((c) => (
              <button
                key={c.id}
                onClick={() => { setOpenId(c.id); playRange(c.start as number, c.end as number); }}
                title={`${secs(c.start)} – ${secs(c.end)} · ${c.text_tachelhit || 'sense text'}`}
                style={{
                  position: 'absolute', top: 0, bottom: 0,
                  left: `${(((c.start as number) - (data.covered_from as number)) / span) * 100}%`,
                  width: `${Math.max(0.6, (((c.end as number) - (c.start as number)) / span) * 100)}%`,
                  background: c.verified ? 'var(--emerald)' : c.audio_url ? 'var(--brand-1)' : 'var(--text-muted)',
                  border: openId === c.id ? '2px solid var(--text)' : 'none', borderRadius: 3, cursor: 'pointer', padding: 0,
                }}
              />
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--text-muted)', marginTop: 3 }}>
            <span>{secs(data.covered_from)}</span><span>{secs(data.covered_to)}</span>
          </div>
        </div>
      )}

      {(data.holes.length > 0 || data.overlaps.length > 0) && (
        <div style={{ padding: '10px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', fontSize: 13.5, lineHeight: 1.55, marginBottom: 14 }}>
          <strong style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><FaExclamationTriangle size={12} /> Val la pena mirar-ho</strong>
          {data.holes.length > 0 && (
            <div>{data.holes.length} {data.holes.length === 1 ? 'tros del vídeo' : 'trossos del vídeo'} sense cap frase
              {' '}({data.holes.slice(0, 4).map((h) => `${secs(h.from)}–${secs(h.to)}`).join(', ')}{data.holes.length > 4 ? '…' : ''}).
              Potser la màquina s’hi va saltar alguna cosa.</div>
          )}
          {data.overlaps.length > 0 && (
            <div>{data.overlaps.length} {data.overlaps.length === 1 ? 'parell de talls que es trepitgen' : 'parells de talls que es trepitgen'}.
              Un dels dos pot portar la frase de l’altre.</div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.cuts.map((c) => {
          const d = draft(c);
          const open = openId === c.id;
          return (
            <div key={c.id} style={{ border: `1px solid ${open ? 'var(--brand-1)' : 'var(--border)'}`, borderRadius: 'var(--r-lg)', background: 'var(--surface)', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px' }}>
                <button onClick={() => (c.start != null && c.end != null) && playRange(c.start, c.end)}
                        aria-label="Escolta aquest tros del vídeo" title="Escolta aquest tros del vídeo"
                        style={{ width: 34, height: 34, borderRadius: '50%', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', flexShrink: 0 }}>
                  <FaPlay size={11} />
                </button>
                <button onClick={() => setOpenId(open ? null : c.id)} style={{ flex: 1, textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', padding: 0, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14.5, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.text_tachelhit || <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>sense text</span>}
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-soft)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {secs(c.start)} – {secs(c.end)} · {c.text_catalan || '—'}
                  </div>
                </button>
                {c.verified && <FaCheck size={12} style={{ color: 'var(--emerald)', flexShrink: 0 }} />}
              </div>

              {open && (
                <div style={{ padding: '0 12px 14px', display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid var(--border)' }}>
                  {/* where it starts and ends */}
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>On comença i on acaba</div>
                    {(['start', 'end'] as const).map((which) => (
                      <div key={which} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{ width: 52, fontSize: 12.5, color: 'var(--text-soft)', fontWeight: 700 }}>{which === 'start' ? 'Inici' : 'Final'}</span>
                        <input type="range" min={Math.max(0, (c.start ?? 0) - 15)} max={(c.end ?? 0) + 15} step={0.1}
                               value={d[which]} aria-label={which === 'start' ? 'Inici del tall' : 'Final del tall'}
                               onChange={(e) => {
                                 const v = parseFloat(e.target.value);
                                 setDraft(c, which === 'start' ? { start: Math.min(v, d.end - 0.3) } : { end: Math.max(v, d.start + 0.3) });
                               }}
                               style={{ flex: 1, accentColor: 'var(--brand-1)' }} />
                        <span style={{ width: 62, textAlign: 'right', fontSize: 12.5, fontVariantNumeric: 'tabular-nums', color: 'var(--text)' }}>{secs(d[which])}</span>
                      </div>
                    ))}
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                      <button onClick={() => playRange(d.start, d.end)} style={pill}><FaPlay size={10} /> Escolta-ho així</button>
                      <button onClick={() => recut(c)} disabled={!moved(c) || busy === c.id}
                              style={{ ...pill, borderColor: moved(c) ? 'var(--brand-1)' : 'var(--border)', color: moved(c) ? 'var(--brand-1)' : 'var(--text-muted)', opacity: busy === c.id ? 0.5 : 1 }}>
                        <FaCut size={10} /> {busy === c.id ? 'Tallant…' : 'Talla-ho de nou des del vídeo'}
                      </button>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>
                      Torna a tallar de l’original, no del retall que ja tenim: per això es pot allargar.
                      El text no es toca. Una imatge dibuixada tampoc.
                    </p>
                  </div>

                  {/* what it says */}
                  <div>
                    <div style={{ fontSize: 11.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>Què hi diu</div>
                    <input value={d.tachelhit} onChange={(e) => setDraft(c, { tachelhit: e.target.value })}
                           lang="shi" autoCapitalize="off" autoCorrect="off" spellCheck={false}
                           aria-label="Text amazic" placeholder="amazic"
                           style={{ ...field, fontWeight: 700, color: 'var(--brand-1)' }} />
                    <input value={d.catalan} onChange={(e) => setDraft(c, { catalan: e.target.value })}
                           lang="ca" aria-label="Text català" placeholder="català" style={{ ...field, marginTop: 6 }} />
                    {c.text_tachelhit_suggested && (
                      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>
                        La màquina hi havia llegit: «{c.text_tachelhit_suggested}»
                      </p>
                    )}
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                      <button onClick={() => saveText(c)} disabled={!rewritten(c) || busy === c.id}
                              style={{ ...pill, borderColor: rewritten(c) ? 'var(--brand-1)' : 'var(--border)', color: rewritten(c) ? 'var(--brand-1)' : 'var(--text-muted)' }}>
                        <FaSave size={10} /> Desa el text
                      </button>
                      <button onClick={() => throwAway(c)} disabled={busy === c.id}
                              style={{ ...pill, borderColor: killing === c.id ? 'var(--rose, #b3261e)' : 'var(--border)', color: killing === c.id ? 'var(--rose, #b3261e)' : 'var(--text-muted)' }}>
                        <FaTrash size={10} /> {killing === c.id ? 'Segur?' : 'Llença aquest tall'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const pill: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 'var(--r-pill)',
  border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)',
  fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit',
};
const field: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '10px 12px', fontSize: 15,
  borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
  background: 'var(--surface-2)', color: 'var(--text)', fontFamily: 'inherit',
};
