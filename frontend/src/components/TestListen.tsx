import { useCallback, useEffect, useRef, useState } from 'react';
import { getMediaUrl } from '../config';
import { audioSrc } from '../services/audioLocal';
import type { Drill } from '../types';
import { FaStepBackward, FaStepForward, FaPlay, FaPause, FaTimes } from 'react-icons/fa';

// Hands-free listening: the drills of a test play one after another with no
// tapping — for running, walking, cooking. Each drill: the meaning in Catalan
// (its TTS file, or the device voice), then the Tachelhit recording, repeated.
// Lock-screen / headset buttons work through the Media Session API.

type Order = 'ca-ta' | 'ta-ca' | 'ta';

interface Props {
  drills: Drill[];
  title: string;
  onExit: () => void;
}

const PREF_KEY = 'listen.prefs';

function loadPrefs(): { order: Order; repeats: number; loop: boolean } {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
    return { order: p.order || 'ca-ta', repeats: p.repeats || 2, loop: p.loop !== false };
  } catch {
    return { order: 'ca-ta', repeats: 2, loop: true };
  }
}

export default function TestListen({ drills, title, onExit }: Props) {
  const playable = drills.filter((d) => d.audio_url || d.video_url || d.text_catalan);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [prefs, setPrefs] = useState(loadPrefs);
  const [phase, setPhase] = useState<'ca' | 'ta' | 'gap'>('gap');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const runRef = useRef(0); // bumps on every change; a stale sequence sees it and stops
  const wakeLockRef = useRef<{ release: () => Promise<void> } | null>(null);

  const savePrefs = (p: Partial<typeof prefs>) => {
    const next = { ...prefs, ...p };
    setPrefs(next);
    try { localStorage.setItem(PREF_KEY, JSON.stringify(next)); } catch { /* private mode */ }
  };

  const stopAll = useCallback(() => {
    runRef.current += 1;
    const a = audioRef.current;
    if (a) { a.pause(); a.removeAttribute('src'); a.load(); }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
  }, []);

  const wait = (ms: number, run: number) => new Promise<void>((res) => setTimeout(() => res(), run === runRef.current ? ms : 0));

  const playUrl = (url: string, run: number) => new Promise<void>((resolve) => {
    const a = audioRef.current;
    if (!a || run !== runRef.current) return resolve();
    const done = () => { a.onended = null; a.onerror = null; resolve(); };
    a.onended = done;
    a.onerror = done;
    a.src = url;
    a.play().catch(done);
  });

  const speakCa = (text: string, run: number) => new Promise<void>((resolve) => {
    if (!('speechSynthesis' in window) || run !== runRef.current) return resolve();
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'ca-ES';
    u.rate = 0.95;
    const voice = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith('ca'));
    if (voice) u.voice = voice;
    const timer = setTimeout(resolve, Math.min(12000, 1500 + text.length * 80)); // some devices never fire onend
    u.onend = () => { clearTimeout(timer); resolve(); };
    u.onerror = () => { clearTimeout(timer); resolve(); };
    speechSynthesis.speak(u);
  });

  // One drill, start to finish, honouring the order and repeat preferences.
  const playDrill = useCallback(async (d: Drill, run: number) => {
    const ta = d.audio_url ? audioSrc(d.audio_url) : d.video_url ? getMediaUrl(d.video_url) : null;
    const ca = async () => {
      if (!d.text_catalan) return;
      setPhase('ca');
      if (d.audio_tts_url) await playUrl(audioSrc(d.audio_tts_url), run);
      else await speakCa(d.text_catalan, run);
      await wait(500, run);
    };
    const taPlay = async () => {
      if (!ta) return;
      for (let r = 0; r < prefs.repeats; r++) {
        if (run !== runRef.current) return;
        setPhase('ta');
        await playUrl(ta, run);
        await wait(700, run);
      }
    };
    if (prefs.order === 'ca-ta') { await ca(); await taPlay(); }
    else if (prefs.order === 'ta-ca') { await taPlay(); await ca(); }
    else { await taPlay(); }
    setPhase('gap');
    await wait(900, run);
  }, [prefs.order, prefs.repeats]);

  // The sequence runner: whenever idx / playing / prefs change, restart cleanly.
  useEffect(() => {
    if (!playing || playable.length === 0) { stopAll(); return; }
    stopAll();
    const run = runRef.current;
    const d = playable[idx];
    if (!d) return;
    playDrill(d, run).then(() => {
      if (run !== runRef.current) return;
      if (idx + 1 < playable.length) setIdx(idx + 1);
      else if (prefs.loop) setIdx(0);
      else setPlaying(false);
    });
    return () => { /* the next effect run calls stopAll() */ };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, playing, prefs.order, prefs.repeats, playable.length]);

  // Lock-screen and headset buttons; keep the screen on while playing.
  useEffect(() => {
    const d = playable[idx];
    if ('mediaSession' in navigator && d) {
      try {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: d.text_tachelhit_latin || d.text_tachelhit || `Drill #${d.id}`,
          artist: d.text_catalan || '',
          album: title,
        });
        navigator.mediaSession.setActionHandler('play', () => setPlaying(true));
        navigator.mediaSession.setActionHandler('pause', () => setPlaying(false));
        navigator.mediaSession.setActionHandler('nexttrack', () => setIdx((i) => Math.min(i + 1, playable.length - 1)));
        navigator.mediaSession.setActionHandler('previoustrack', () => setIdx((i) => Math.max(i - 1, 0)));
        navigator.mediaSession.playbackState = playing ? 'playing' : 'paused';
      } catch { /* not supported */ }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, playing, playable.length, title]);

  useEffect(() => {
    const nav = navigator as Navigator & { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } };
    if (playing && nav.wakeLock && !wakeLockRef.current) {
      nav.wakeLock.request('screen').then((l) => { wakeLockRef.current = l; }).catch(() => {});
    }
    if (!playing && wakeLockRef.current) { wakeLockRef.current.release().catch(() => {}); wakeLockRef.current = null; }
    return () => { if (wakeLockRef.current) { wakeLockRef.current.release().catch(() => {}); wakeLockRef.current = null; } };
  }, [playing]);

  useEffect(() => () => stopAll(), [stopAll]);

  const d = playable[idx];
  const big: React.CSSProperties = { width: '68px', height: '68px', borderRadius: '50%', border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' };

  return (
    <div style={{ minHeight: '100dvh', background: 'linear-gradient(180deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
      <audio ref={audioRef} preload="auto" />
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: 'calc(12px + env(safe-area-inset-top, 0px)) 16px 8px' }}>
        <button onClick={() => { stopAll(); onExit(); }} aria-label="Surt" style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.25)', color: '#fff', borderRadius: 'var(--r-pill)', padding: '8px 12px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaTimes /> Surt</button>
        <div style={{ flex: 1, minWidth: 0, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>🎧 {title}</div>
        <div style={{ fontSize: '13px', opacity: 0.8 }}>{playable.length ? `${idx + 1}/${playable.length}` : '0'}</div>
      </div>
      <div style={{ height: '4px', background: 'rgba(255,255,255,0.15)', margin: '0 16px', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${playable.length ? ((idx + 1) / playable.length) * 100 : 0}%`, background: '#fbbf24', transition: 'width 0.3s' }} />
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px', textAlign: 'center', gap: '12px' }}>
        {!d ? (
          <div style={{ opacity: 0.8 }}>Aquest test no té drills amb àudio.</div>
        ) : (
          <>
            <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.6 }}>
              {phase === 'ca' ? 'Significat' : phase === 'ta' ? 'Tamazight' : '…'}
            </div>
            <div style={{ fontSize: '30px', fontWeight: 800, lineHeight: 1.25, opacity: phase === 'ta' ? 1 : 0.85 }}>
              {d.text_tachelhit_latin || d.text_tachelhit || <span style={{ fontStyle: 'italic', opacity: 0.6 }}>sense transcripció</span>}
            </div>
            {d.text_tachelhit && d.text_tachelhit !== (d.text_tachelhit_latin || d.text_tachelhit) && (
              <div style={{ fontSize: '20px', opacity: 0.8 }}>{d.text_tachelhit}</div>
            )}
            <div style={{ fontSize: '19px', opacity: phase === 'ca' ? 1 : 0.7, marginTop: '6px' }}>{d.text_catalan}</div>
            {d.text_arabic && <div dir="rtl" style={{ fontSize: '17px', opacity: 0.6 }}>{d.text_arabic}</div>}
          </>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '22px', padding: '8px 16px 18px' }}>
        <button onClick={() => setIdx((i) => Math.max(i - 1, 0))} aria-label="Anterior" style={{ ...big, width: '56px', height: '56px', background: 'rgba(255,255,255,0.12)', color: '#fff' }}><FaStepBackward /></button>
        <button onClick={() => setPlaying((p) => !p)} aria-label={playing ? 'Pausa' : 'Reprodueix'} style={{ ...big, width: '84px', height: '84px', fontSize: '28px', background: '#fbbf24', color: '#1e293b' }}>{playing ? <FaPause /> : <FaPlay style={{ marginLeft: '4px' }} />}</button>
        <button onClick={() => setIdx((i) => (i + 1 < playable.length ? i + 1 : prefs.loop ? 0 : i))} aria-label="Següent" style={{ ...big, width: '56px', height: '56px', background: 'rgba(255,255,255,0.12)', color: '#fff' }}><FaStepForward /></button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', flexWrap: 'wrap', padding: '0 16px calc(18px + env(safe-area-inset-bottom, 0px))', fontSize: '13px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          Ordre
          <select value={prefs.order} onChange={(e) => savePrefs({ order: e.target.value as Order })} style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '8px', padding: '4px 6px' }}>
            <option value="ca-ta" style={{ color: '#000' }}>català → tamazight</option>
            <option value="ta-ca" style={{ color: '#000' }}>tamazight → català</option>
            <option value="ta" style={{ color: '#000' }}>només tamazight</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          Repeticions
          <select value={prefs.repeats} onChange={(e) => savePrefs({ repeats: Number(e.target.value) })} style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '8px', padding: '4px 6px' }}>
            {[1, 2, 3, 4].map((n) => <option key={n} value={n} style={{ color: '#000' }}>{n}</option>)}
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <input type="checkbox" checked={prefs.loop} onChange={(e) => savePrefs({ loop: e.target.checked })} /> En bucle
        </label>
      </div>
    </div>
  );
}
