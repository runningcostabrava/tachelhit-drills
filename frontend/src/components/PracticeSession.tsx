import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { FaLightbulb, FaMicrophone, FaPlay, FaStop, FaTimes } from 'react-icons/fa';
import { api, type PracticeCard, type PracticeMode, type PronunciationWord } from '../api';
import { API_BASE, getMediaUrl } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';
import { fileNameFor, preferredRecorderMime } from '../utils/media';
import { saveDone } from './PracticePage';
import WordGloss from './WordGloss';

// One practice session: up to 10 sentences of our speakers, each an exercise the learner SAYS.
//  - «Escolta i repeteix»: hear the speaker (normal or slow), see the hard sounds and a tip, hold
//    the microphone and repeat.
//  - «Digues-ho tu» (every third card): only the Catalan and the picture; say it in Tamazight
//    first, then the speaker's sentence and voice appear.
// After each recording the result card shows the score and the speaker's words coloured by
// whether the learner's utterance had them (by sound), with the tip for the sound that failed.
// The session ends with the score, the sounds that cost most, and a grade sent to the
// spaced-repetition schedule so «Sessió d'avui» brings the hard ones back.

type Phase = 'prompt' | 'recording' | 'checking' | 'result';
type Result = { score: number; heard: string; words: PronunciationWord[] };
// Three ways to run a session: «Parla» records and scores you; «Escolta» is listen-and-next, no
// microphone; «Auto» plays each card (Catalan, then the Tamazight twice) and moves on by itself.
const MODE_KEY = 'practice_mode';
function loadMode(): PracticeMode { try { const m = localStorage.getItem(MODE_KEY); return m === 'escolta' || m === 'auto' ? m : 'parla'; } catch { return 'parla'; } }

function scoreGrade(score: number): number { return score >= 0.85 ? 3 : score >= 0.65 ? 2 : score >= 0.4 ? 1 : 0; }

// The shape of a voice: 90 loudness bars drawn from the decoded audio, so the learner can compare
// the speaker's rhythm and stresses with their own, and replay either as often as they want.
function Waveform({ src, label, color, autoHeight = 54 }: { src: string | Blob | null; label: string; color: string; autoHeight?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [bars, setBars] = useState<number[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const url = useMemo(() => (src instanceof Blob ? URL.createObjectURL(src) : src ? getMediaUrl(src) : ''), [src]);
  useEffect(() => () => { if (src instanceof Blob && url) URL.revokeObjectURL(url); }, [src, url]);
  useEffect(() => {
    let cancelled = false;
    setBars(null); setFailed(false);
    if (!url) return;
    (async () => {
      try {
        const buf = src instanceof Blob ? await src.arrayBuffer() : await (await fetch(url, { mode: 'cors' })).arrayBuffer();
        const Ctx = (window.AudioContext || (window as any).webkitAudioContext) as typeof AudioContext;
        const ctx = new Ctx();
        const audio = await ctx.decodeAudioData(buf.slice(0));
        const data = audio.getChannelData(0);
        const n = 90, step = Math.max(1, Math.floor(data.length / n)); const out: number[] = [];
        for (let i = 0; i < n; i++) { let sum = 0; for (let j = i * step; j < Math.min(data.length, (i + 1) * step); j += 4) sum += data[j] * data[j]; out.push(Math.sqrt(sum / (step / 4))); }
        const peak = Math.max(...out, 1e-6);
        if (!cancelled) setBars(out.map((v) => v / peak));
        ctx.close().catch(() => {});
      } catch { if (!cancelled) setFailed(true); }
    })();
    return () => { cancelled = true; };
  }, [url, src]);
  useEffect(() => {
    const c = canvasRef.current; if (!c || !bars) return;
    const dpr = window.devicePixelRatio || 1; const w = c.clientWidth, h = autoHeight; c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext('2d'); if (!g) return; g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
    const bw = w / bars.length; g.fillStyle = color;
    bars.forEach((v, i) => { const bh = Math.max(2, v * (h - 4)); g.fillRect(i * bw + bw * 0.2, (h - bh) / 2, bw * 0.6, bh); });
  }, [bars, color, autoHeight]);
  const toggle = () => {
    if (!url) return;
    if (audioRef.current && playing) { audioRef.current.pause(); setPlaying(false); return; }
    const a = new Audio(url); audioRef.current = a; a.onended = () => setPlaying(false); a.onerror = () => setPlaying(false);
    setPlaying(true); a.play().catch(() => setPlaying(false));
  };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button onClick={toggle} disabled={!url} aria-label={`Escolta: ${label}`} style={{ flexShrink: 0, width: 38, height: 38, borderRadius: '50%', border: 'none', background: url ? color : 'var(--surface-2)', color: '#fff', cursor: url ? 'pointer' : 'default', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>{playing ? <FaStop size={12} /> : <FaPlay size={12} />}</button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 2 }}>{label}</div>
        {bars ? <canvas ref={canvasRef} style={{ width: '100%', height: autoHeight, display: 'block' }} /> : <div style={{ height: autoHeight, display: 'flex', alignItems: 'center', fontSize: 12, color: 'var(--text-muted)' }}>{!url ? 'sense veu' : failed ? 'no s’ha pogut dibuixar; prem per escoltar' : 'dibuixant…'}</div>}
      </div>
    </div>
  );
}

function Highlighted({ text, marks }: { text: string; marks: string[] }) {
  // bold the spellings that carry a hard sound, longest first so «gh» wins over «g»
  const ms = [...marks].sort((a, b) => b.length - a.length).filter(Boolean);
  if (!ms.length) return <>{text}</>;
  const re = new RegExp(`(${ms.map((m) => m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');
  return <>{text.split(re).map((part, i) => (ms.includes(part) ? <mark key={i} style={{ background: 'var(--brand-gradient-soft)', color: 'inherit', borderRadius: 6, padding: '0 3px' }}>{part}</mark> : <span key={i}>{part}</span>))}</>;
}

export default function PracticeSession() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [drills, setDrills] = useState<Drill[]>([]);
  const [cards, setCards] = useState<PracticeCard[]>([]);
  const [i, setI] = useState(0);
  const [phase, setPhase] = useState<Phase>('prompt');
  const [result, setResult] = useState<Result | null>(null);
  const [results, setResults] = useState<Record<number, Result>>({});
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [myTake, setMyTake] = useState<Blob | null>(null);  // the learner's last recording of this card
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setModeState] = useState<PracticeMode>(loadMode);
  const setMode = (m: PracticeMode) => { setModeState(m); try { localStorage.setItem(MODE_KEY, m); } catch { /* private mode */ } };
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const autoTimer = useRef<number | null>(null);

  const key = useMemo(() => {
    if (params.get('daily')) return 'daily';
    if (params.get('day')) return `day:${params.get('day')}:${params.get('speaker')}`;
    if (params.get('topic')) return `topic:${params.get('topic')}`;
    if (params.get('unit')) return `unit:${params.get('unit')}`;
    if (params.get('test_id')) return `test:${params.get('test_id')}`;
    return 'session';
  }, [params]);
  const title = useMemo(() => {
    if (params.get('daily')) return 'Sessió d’avui';
    if (params.get('day')) return `${params.get('speaker')} · ${params.get('day')}`;
    if (params.get('topic')) return `Tema: ${params.get('topic')}`;
    if (params.get('unit')) return `Unitat: ${params.get('unit')}`;
    return 'Pràctica';
  }, [params]);

  useEffect(() => { document.title = `${title} · Pràctica`; }, [title]);
  useEffect(() => {
    const load = async () => {
      try {
        if (params.get('daily')) {
          const due = await api.reviewsDue(10);
          const ids = due.filter((d) => d.text_tachelhit && (d.audio_url || d.audio_tts_shi_url)).map((d) => d.id);
          if (!ids.length) { setLoadError('Avui no tens cap frase pendent. Tria un dia, un tema o una unitat.'); return; }
          const s = await api.practiceSession(`ids=${ids.join(',')}`);
          setDrills(s.drills); setCards(s.cards);
        } else {
          const q = new URLSearchParams();
          for (const k of ['day', 'speaker', 'topic', 'unit', 'test_id']) { const v = params.get(k); if (v) q.set(k, v); }
          q.set('limit', '10');
          const s = await api.practiceSession(q.toString());
          if (!s.drills.length) { setLoadError('Aquesta selecció encara no té frases amb veu per practicar.'); return; }
          setDrills(s.drills); setCards(s.cards);
        }
      } catch (e: any) { setLoadError(e?.message || 'Error'); }
    };
    load();
  }, [params]);

  const drill = drills[i]; const card = cards[i];
  const sayFirst = mode === 'parla' && i % 3 === 2;  // every third card: say it before hearing it (only when speaking)
  const voice = drill ? (drill.audio_url || drill.audio_tts_shi_url || '') : '';
  const speakerLabel = card ? (card.origin && card.origin !== card.speaker ? `${card.speaker} · ${card.origin}` : card.speaker) : '';

  const play = useCallback((rate = 1) => {
    if (!voice) return;
    if (audioRef.current) { audioRef.current.pause(); }
    const a = new Audio(getMediaUrl(voice)); a.playbackRate = rate; audioRef.current = a; a.play().catch(() => {});
  }, [voice]);
  useEffect(() => { if (drill && !sayFirst && phase === 'prompt' && mode !== 'auto') play(1); }, [drill?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  // «Auto»: Catalan voice, then the Tamazight twice, then the next card; stops when the mode changes
  useEffect(() => {
    if (mode !== 'auto' || !drill || finished) return;
    let cancelled = false;
    const clear = () => { if (autoTimer.current) { window.clearTimeout(autoTimer.current); autoTimer.current = null; } };
    const playOnce = (url: string, rate = 1) => new Promise<void>((resolve) => {
      if (!url) { resolve(); return; }
      if (audioRef.current) audioRef.current.pause();
      const a = new Audio(getMediaUrl(url)); a.playbackRate = rate; audioRef.current = a;
      a.onended = () => resolve(); a.onerror = () => resolve();
      a.play().catch(() => resolve());
    });
    const wait = (ms: number) => new Promise<void>((resolve) => { autoTimer.current = window.setTimeout(resolve, ms); });
    (async () => {
      if (drill.audio_tts_url) { await playOnce(drill.audio_tts_url); if (cancelled) return; await wait(500); }
      await playOnce(voice); if (cancelled) return; await wait(900);
      await playOnce(voice); if (cancelled) return; await wait(1600);
      if (!cancelled) { if (i + 1 >= drills.length) finish(); else { setI(i + 1); setPhase('prompt'); setResult(null); setRevealed(false); } }
    })();
    return () => { cancelled = true; clear(); if (audioRef.current) audioRef.current.pause(); };
  }, [mode, drill?.id, finished]);  // eslint-disable-line react-hooks/exhaustive-deps

  const startRecording = async () => {
    if (!drill || phase === 'recording' || phase === 'checking') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = preferredRecorderMime('audio');
      const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (!chunks.length) { setPhase('prompt'); return; }
        setPhase('checking');
        try {
          const blob = new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' });
          setMyTake(blob);
          const fd = new FormData();
          fd.append('drill_id', String(drill.id));
          fd.append('audio', blob, fileNameFor(blob, 'audio', 'practice'));
          const res = await fetch(`${API_BASE}/pronunciation/check`, { method: 'POST', body: fd });
          if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'No s’ha pogut avaluar');
          const data = await res.json();
          const r: Result = { score: data.score, heard: data.heard_latin || data.heard, words: data.words || [] };
          setResult(r); setResults((m) => ({ ...m, [drill.id]: r })); setRevealed(true); setPhase('result');
          api.reviewGrade(drill.id, scoreGrade(data.score)).catch(() => {});
          if (sayFirst) setTimeout(() => play(1), 300);
        } catch (e: any) { toast.error(e?.message || 'No s’ha pogut avaluar'); setPhase('prompt'); }
      };
      rec.start(); recorderRef.current = rec; setPhase('recording');
    } catch { toast.error('No s’ha pogut accedir al micròfon. Comprova els permisos del navegador.'); }
  };
  const stopRecording = () => { if (recorderRef.current && recorderRef.current.state === 'recording') recorderRef.current.stop(); };

  const next = () => {
    if (audioRef.current) audioRef.current.pause();
    if (i + 1 >= drills.length) { finish(); return; }
    setI(i + 1); setPhase('prompt'); setResult(null); setRevealed(false); setMyTake(null);
  };
  const retry = () => { setPhase('prompt'); setResult(null); if (!sayFirst) play(1); };
  const finish = () => {
    const rs = Object.values(results);
    const right = rs.filter((r) => r.score >= 0.65).length;
    saveDone(key, right, drills.length);
    setFinished(true);
  };

  // which sounds cost most across the session: the tips of the words that came out different
  const hardSounds = useMemo(() => {
    const count: Record<string, { label: string; tip: string; n: number }> = {};
    drills.forEach((d, k) => {
      const r = results[d.id]; const c = cards[k];
      if (!r || !c) return;
      const bad = r.words.filter((w) => !w.ok).map((w) => w.word.toLowerCase());
      c.tips.forEach((t) => { if (bad.some((w) => w.includes(t.found.toLowerCase()))) { count[t.sound] = count[t.sound] || { label: t.label, tip: t.tip, n: 0 }; count[t.sound].n += 1; } });
    });
    return Object.values(count).sort((a, b) => b.n - a.n).slice(0, 3);
  }, [results, drills, cards]);

  const exit = () => navigate('/tests');
  const bar = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
      <button onClick={exit} aria-label="Surt de la sessió" style={{ width: 36, height: 36, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--surface-2)', color: 'var(--text)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><FaTimes /></button>
      <div style={{ flex: 1, height: 10, borderRadius: 5, background: 'var(--surface-2)', overflow: 'hidden' }}><div style={{ width: `${drills.length ? ((finished ? drills.length : i) / drills.length) * 100 : 0}%`, height: 10, background: 'var(--brand-1)', transition: 'width .3s' }} /></div>
      <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-soft)' }}>{Math.min(i + 1, drills.length)} / {drills.length}</span>
    </div>
  );
  const modeBar = (
    <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
      {([['parla', 'Parla'], ['escolta', 'Escolta'], ['auto', 'Auto']] as [PracticeMode, string][]).map(([m, label]) => (
        <button key={m} onClick={() => setMode(m)} style={{ flex: 1, padding: '7px 0', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: mode === m ? 'var(--brand-1)' : 'var(--surface)', color: mode === m ? '#fff' : 'var(--text)', fontWeight: 800, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>{label}</button>
      ))}
    </div>
  );

  if (loadError) return <div style={{ padding: '40px 16px', maxWidth: 520, margin: '0 auto', textAlign: 'center' }}><p style={{ color: 'var(--text-soft)' }}>{loadError}</p><button onClick={exit} style={btn('ghost')}>Torna a Pràctica</button></div>;
  if (!drill) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Preparant la sessió…</div>;

  if (finished) {
    const rs = drills.map((d) => results[d.id]).filter(Boolean);
    const right = rs.filter((r) => r.score >= 0.65).length;
    const hard = drills.filter((d) => results[d.id] && results[d.id].score < 0.65);
    return (
      <div style={{ padding: '20px 16px 32px', maxWidth: 520, margin: '0 auto' }}>
        {bar}
        <div style={{ textAlign: 'center', margin: '12px 0 20px' }}>
          <div style={{ width: 110, height: 110, borderRadius: '50%', border: `10px solid ${right >= drills.length * 0.7 ? 'var(--emerald)' : 'var(--saffron)'}`, boxSizing: 'border-box', display: 'inline-flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}><span style={{ fontSize: 30, fontWeight: 800, lineHeight: 1 }}>{right}</span><span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>de {drills.length}</span></div>
          <h2 style={{ margin: '10px 0 4px', fontSize: 22 }}>Sessió feta</h2>
          <p style={{ margin: 0, color: 'var(--text-soft)', fontSize: 14 }}>{rs.length} frases dites, {right} enteses senceres.</p>
        </div>
        {hardSounds.length > 0 && (
          <div style={{ padding: 14, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', marginBottom: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Sons que et costen</div>
            {hardSounds.map((s) => <div key={s.label} style={{ marginBottom: 8 }}><div style={{ fontWeight: 800, fontSize: 17 }}>{s.label} <span style={{ fontSize: 12, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>· {s.n} {s.n === 1 ? 'vegada' : 'vegades'}</span></div><div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45 }}>{s.tip}</div></div>)}
          </div>
        )}
        {hard.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Les que tornaràs a veure</div>
            {hard.map((d) => <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', marginBottom: 6, fontSize: 14, fontWeight: 700 }}><span>{d.text_tachelhit}</span><span style={{ color: 'var(--saffron-dark, #7A4A12)' }}>{Math.round(results[d.id].score * 100)}</span></div>)}
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {hard.length > 0 && <button onClick={() => { setDrills(hard); setCards(hard.map((d) => cards[drills.indexOf(d)])); setResults({}); setI(0); setPhase('prompt'); setResult(null); setRevealed(false); setFinished(false); }} style={btn('ghost')}>Repeteix les {hard.length} difícils</button>}
          <button onClick={exit} style={btn('primary')}>Fet per avui</button>
        </div>
      </div>
    );
  }

  const tip = card?.tips[0];
  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: 520, margin: '0 auto', minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      {bar}
      {modeBar}
      <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--brand-1)' }}>{mode === 'auto' ? 'Reproducció automàtica' : mode === 'escolta' ? 'Escolta' : sayFirst ? 'Digues-ho tu' : 'Escolta i repeteix'}</div>
      <h2 style={{ margin: '2px 0 14px', fontSize: 19, lineHeight: 1.25 }}>{mode === 'auto' ? 'Escolta; passa sola a la següent' : mode === 'escolta' ? 'Escolta tantes vegades com vulguis' : sayFirst ? 'Com ho diries en amazic?' : `Escolta ${card?.speaker === 'Halima' ? 'la Halima' : card?.speaker === 'Driss' ? 'en Driss' : 'la veu'} i digues-ho igual`}</h2>

      <div style={{ padding: 14, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {drill.image_url && <div style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9', borderRadius: 'var(--r-md)', overflow: 'hidden', background: 'var(--surface-2)' }}><img src={getMediaUrl(drill.image_url)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', filter: sayFirst && !revealed ? 'none' : 'none' }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} /><span style={{ position: 'absolute', left: 10, bottom: 10, fontSize: 12, fontWeight: 700, background: 'rgba(255,255,255,0.92)', color: 'var(--text)', padding: '4px 10px', borderRadius: 'var(--r-pill)' }}>{speakerLabel}</span></div>}
        {!drill.image_url && <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>{speakerLabel}</div>}
        {sayFirst && !revealed ? (
          <>
            <p style={{ margin: 0, fontSize: 24, fontWeight: 800, lineHeight: 1.3 }}>{drill.text_catalan}</p>
            <p style={{ margin: 0, fontSize: 14, color: 'var(--text-soft)' }}>Primer digues-ho tu. Després sentiràs com ho diu {card?.speaker} i veuràs la frase.</p>
          </>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: 25, fontWeight: 800, lineHeight: 1.3 }}>
              {phase === 'result' && result ? result.words.map((w, k) => <span key={k} style={{ color: w.ok ? 'var(--emerald)' : 'var(--saffron-dark, #B7791F)', borderBottom: w.ok ? 'none' : '3px solid var(--saffron-dark, #B7791F)', marginRight: 8 }}>{w.word}</span>)
                : <Highlighted text={drill.text_tachelhit || ''} marks={card?.highlights || []} />}
            </p>
            <p style={{ margin: 0, fontSize: 15, color: 'var(--text-soft)' }}>{drill.text_catalan}</p>
            <WordGloss drill={drill} size="sm" />
            {drill.source_url && <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>Font: {drill.source_channel || 'vídeo original'}{drill.source_title ? ` · «${drill.source_title}»` : ''} · <a href={drill.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 700 }}>vídeo original ↗</a></p>}
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => play(1)} disabled={!voice} style={{ ...btn('primary'), flex: 1, height: 44, fontSize: 14 }}><FaPlay size={12} /> Escolta</button>
              <button onClick={() => play(0.7)} disabled={!voice} style={{ ...btn('ghost'), flex: 1, height: 44, fontSize: 14 }}>A poc a poc</button>
            </div>
          </>
        )}
      </div>

      {myTake && (phase === 'checking' || phase === 'result') && (
        <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Waveform src={voice || null} label={card?.speaker || 'la veu'} color="var(--brand-1)" />
          <Waveform src={myTake} label="tu" color="var(--saffron-dark, #B7791F)" />
          {phase === 'checking' && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Compara el ritme i la força de cada síl·laba mentre s’avalua la pronúncia (uns segons).</div>}
        </div>
      )}
      {phase === 'result' && result ? (
        <div style={{ marginTop: 12, padding: 14, borderRadius: 'var(--r-lg)', background: result.score >= 0.65 ? 'var(--emerald-soft, #E5F2EA)' : 'var(--brand-gradient-soft)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <div style={{ width: 54, height: 54, borderRadius: '50%', border: `6px solid ${result.score >= 0.65 ? 'var(--emerald)' : 'var(--saffron)'}`, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, flexShrink: 0 }}>{Math.round(result.score * 100)}</div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 16 }}>{result.score >= 0.85 ? 'Molt bé!' : result.score >= 0.65 ? 'Gairebé!' : 'Torna-ho a provar'}</div>
              <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{result.words.filter((w) => !w.ok).length === 0 ? 'S’han entès totes les paraules.' : `Diferent del que diu ${card?.speaker}: ${result.words.filter((w) => !w.ok).map((w) => `«${w.word}»`).join(', ')}.`}</div>
              {result.heard && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Hem sentit: «{result.heard}»</div>}
            </div>
          </div>
          {(() => { const bad = result.words.filter((w) => !w.ok).map((w) => w.word.toLowerCase()); const t = card?.tips.find((x) => bad.some((w) => w.includes(x.found.toLowerCase()))) || (bad.length ? card?.tips[0] : null); return t ? <p style={{ margin: '6px 0 0', fontSize: 14, lineHeight: 1.45 }}><strong>{t.label}:</strong> {t.tip}</p> : null; })()}
        </div>
      ) : tip && !(sayFirst && !revealed) ? (
        <div style={{ marginTop: 12, display: 'flex', gap: 10, padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)' }}>
          <FaLightbulb style={{ flexShrink: 0, marginTop: 3, color: 'var(--saffron-dark, #7A4A12)' }} />
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.45 }}><strong>Consell de pronúncia ({tip.label}):</strong> {tip.tip}</p>
        </div>
      ) : null}

      <div style={{ flex: 1 }} />
      {phase === 'result' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 20 }}>
          <button onClick={retry} style={btn('ghost')}>Torna-ho a provar</button>
          <button onClick={next} style={btn('primary')}>{i + 1 >= drills.length ? 'Acaba la sessió' : 'Següent'}</button>
        </div>
      ) : mode !== 'parla' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 20 }}>
          {mode === 'auto' && <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: 'var(--text-soft)' }}>Sonant… passa sola</div>}
          <button onClick={next} style={btn('primary')}>{i + 1 >= drills.length ? 'Acaba la sessió' : 'Següent'}</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 20 }}>
          <button
            onPointerDown={(e) => { e.preventDefault(); startRecording(); }} onPointerUp={stopRecording} onPointerLeave={stopRecording} onPointerCancel={stopRecording}
            disabled={phase === 'checking'} aria-label="Mantén premut per parlar"
            style={{ width: 84, height: 84, borderRadius: '50%', border: 'none', background: phase === 'recording' ? 'var(--danger, #c0392b)' : 'var(--brand-1)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', touchAction: 'none', boxShadow: phase === 'recording' ? '0 0 0 12px rgba(192,57,43,0.18)' : 'none', transition: 'box-shadow .2s' }}>
            <FaMicrophone size={32} />
          </button>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-soft)' }}>{phase === 'checking' ? 'Escoltant el que has dit…' : phase === 'recording' ? 'Parla… deixa anar quan acabis' : 'Mantén premut i parla'}</span>
          <button onClick={() => { if (sayFirst && !revealed) { setRevealed(true); play(1); } else next(); }} style={{ background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', padding: 8, fontFamily: 'inherit' }}>{sayFirst && !revealed ? 'No ho sé · ensenya-m’ho' : 'Ara no puc parlar · salta'}</button>
        </div>
      )}
    </div>
  );
}

function btn(kind: 'primary' | 'ghost'): React.CSSProperties {
  return kind === 'primary'
    ? { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 50, padding: '0 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 15, cursor: 'pointer', fontFamily: 'inherit' }
    : { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 50, padding: '0 18px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 800, fontSize: 15, cursor: 'pointer', fontFamily: 'inherit' };
}
// axios is imported for parity with the other pages' test creation; sessions use fetch for the upload
void axios;
