import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FaLightbulb, FaMicrophone, FaPlay, FaStop, FaTimes } from 'react-icons/fa';
import { api, type PracticeCard, type PracticeMode } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';
import { preferredRecorderMime } from '../utils/media';
import { saveDone } from './PracticePage';
import StepSession from './StepSession';
import WordGloss from './WordGloss';

// One practice session: up to 10 sentences said by our speakers.
//
// Until 2026-10-22 this recorded the learner and put a MARK on it. The mark came from our
// transcriber, and we measured it: CER 0.78 on our own recordings, 0.87 on Aït Mraw
// (docs/ASR_EVAL_NOSTRA_2026-10-22.md). A number built on that is noise wearing the clothes of a
// score, and it fed the spaced-repetition schedule, so a bad guess sent good sentences back.
//
// The microphone stays; the judging goes. You record yourself, you hear the speaker and yourself
// one after the other, you see the two shapes of the sound side by side -- and then YOU say
// whether you have it. Your recording never leaves the page: it lives in memory until the next
// card and is never uploaded, never stored, never transcribed. (Giving a voice to the library is
// a different thing, and it lives in Veus.)
//
//  - «Escolta»: hear it, record yourself if you want, compare, and answer.
//  - «Auto»: plays each card by itself (Catalan, then the Tamazight twice) and moves on.

type Knew = 'yes' | 'no';
const MODE_KEY = 'practice_mode';
function loadMode(): PracticeMode { try { return localStorage.getItem(MODE_KEY) === 'auto' ? 'auto' : 'escolta'; } catch { return 'escolta'; } }

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

// Una pràctica feta a mà és una SEQÜÈNCIA i es juga amb l'eina de cada pas (`StepSession`); una
// col·lecció —un dia, un tema, una unitat— és una pila de frases i es juga escoltant.
//
// Qui ho decideix és aquest component, i no toca res més. Abans ho decidia el de sota a l'hora
// de pintar, i els seus hooks ja havien corregut: carregava frases, muntava el seu reproductor i,
// en mode automàtic, acabava escrivint un resultat que ningú no havia fet. Dues veus sonant
// alhora i un resultat fals (#218). Un `return` no es salta els hooks: el que s'ha de saltar és
// el component sencer.
export default function PracticeSession() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const testId = Number(params.get('test_id')) || 0;
  const [asSteps, setAsSteps] = useState<boolean | null>(testId ? null : false);

  useEffect(() => {
    if (!testId) return;        // sense pràctica, l'estat inicial ja diu que no són passos
    let viu = true;
    api.practiceSteps(testId)
      .then((r) => { if (viu) setAsSteps(r.steps.some((s) => s.kind !== 'note' || s.payload?.text)); })
      .catch(() => { if (viu) setAsSteps(false); });
    return () => { viu = false; };
  }, [testId]);

  const title = useMemo(() => {
    if (params.get('daily')) return 'Sessió d’avui';
    if (params.get('day')) return `${params.get('speaker')} · ${params.get('day')}`;
    if (params.get('topic')) return `Tema: ${params.get('topic')}`;
    if (params.get('unit')) return `Unitat: ${params.get('unit')}`;
    return 'Pràctica';
  }, [params]);

  if (asSteps === null) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Preparant la pràctica…</div>;
  }
  if (asSteps) return <StepSession testId={testId} title={title} onExit={() => navigate('/tests')} />;
  return <SessioDEscoltar />;
}

/** La pila de frases: escoltar-les, repetir-les i dir si ja te'n surts. */
function SessioDEscoltar() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [drills, setDrills] = useState<Drill[]>([]);
  const [cards, setCards] = useState<PracticeCard[]>([]);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<Record<number, Knew>>({});
  const [finished, setFinished] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setModeState] = useState<PracticeMode>(loadMode);
  const setMode = (m: PracticeMode) => { setModeState(m); try { localStorage.setItem(MODE_KEY, m); } catch { /* private mode */ } };
  // The learner's own take of THIS card. In memory, nowhere else, and dropped on the next card.
  const [myTake, setMyTake] = useState<Blob | null>(null);
  const [recording, setRecording] = useState(false);
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
  // Aquí escoltar és la feina, i per això la veu de màquina pot sonar quan ningú no ha gravat la
  // frase. El que no pot fer és passar per una persona: el nom del parlant surt igualment de la
  // targeta, i comparar la teva pronúncia amb una síntesi mentre la pantalla et posa el nom d'algú
  // al costat és ensenyar-te a imitar una màquina sense dir-t'ho.
  const voice = drill ? (drill.audio_url || drill.audio_tts_shi_url || '') : '';
  const bySynth = !!voice && !drill?.audio_url;
  const speakerLabel = bySynth
    ? 'una veu de màquina · encara ningú no l’ha gravada'
    : card ? (card.origin && card.origin !== card.speaker ? `${card.speaker} · ${card.origin}` : card.speaker) : '';

  const play = useCallback((rate = 1) => {
    if (!voice) return;
    if (audioRef.current) { audioRef.current.pause(); }
    const a = new Audio(getMediaUrl(voice)); a.playbackRate = rate; audioRef.current = a; a.play().catch(() => {});
  }, [voice]);
  useEffect(() => { if (drill && mode !== 'auto') play(1); }, [drill?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  const startRecording = async () => {
    if (!drill || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = preferredRecorderMime('audio');
      const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        if (chunks.length) setMyTake(new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' }));
      };
      rec.start(); recorderRef.current = rec; setRecording(true);
    } catch { toast.error('No s’ha pogut accedir al micròfon. Comprova els permisos del navegador.'); }
  };
  const stopRecording = () => { if (recorderRef.current && recorderRef.current.state === 'recording') recorderRef.current.stop(); };

  const finish = useCallback(() => {
    const knew = Object.values(answers).filter((a) => a === 'yes').length;
    saveDone(key, knew, drills.length);
    setFinished(true);
  }, [answers, drills.length, key]);

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
      if (!cancelled) { if (i + 1 >= drills.length) finish(); else { setI(i + 1); setMyTake(null); } }
    })();
    return () => { cancelled = true; clear(); if (audioRef.current) audioRef.current.pause(); };
  }, [mode, drill?.id, finished]);  // eslint-disable-line react-hooks/exhaustive-deps

  const leave = () => {
    if (audioRef.current) audioRef.current.pause();
    setMyTake(null);  // the take does not follow you to the next sentence
  };
  // The learner's own answer is what the schedule listens to: knew it = 3, not yet = 1.
  const answer = (knew: Knew) => {
    if (!drill) return;
    setAnswers((m) => ({ ...m, [drill.id]: knew }));
    api.reviewGrade(drill.id, knew === 'yes' ? 3 : 1).catch(() => {});
    leave();
    if (i + 1 >= drills.length) finish(); else setI(i + 1);
  };
  const next = () => { leave(); if (i + 1 >= drills.length) finish(); else setI(i + 1); };

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
      {([['escolta', 'Escolta'], ['auto', 'Auto']] as [PracticeMode, string][]).map(([m, label]) => (
        <button key={m} onClick={() => setMode(m)} style={{ flex: 1, padding: '7px 0', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: mode === m ? 'var(--brand-1)' : 'var(--surface)', color: mode === m ? '#fff' : 'var(--text)', fontWeight: 800, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>{label}</button>
      ))}
    </div>
  );

  if (loadError) return <div style={{ padding: '40px 16px', maxWidth: 520, margin: '0 auto', textAlign: 'center' }}><p style={{ color: 'var(--text-soft)' }}>{loadError}</p><button onClick={exit} style={btn('ghost')}>Torna a Pràctica</button></div>;
  if (!drill) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Preparant la sessió…</div>;

  if (finished) {
    const knew = drills.filter((d) => answers[d.id] === 'yes');
    const again = drills.filter((d) => answers[d.id] === 'no');
    return (
      <div style={{ padding: '20px 16px 32px', maxWidth: 520, margin: '0 auto' }}>
        {bar}
        <div style={{ textAlign: 'center', margin: '12px 0 20px' }}>
          <div style={{ width: 110, height: 110, borderRadius: '50%', border: `10px solid ${knew.length >= drills.length * 0.7 ? 'var(--emerald)' : 'var(--saffron)'}`, boxSizing: 'border-box', display: 'inline-flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}><span style={{ fontSize: 30, fontWeight: 800, lineHeight: 1 }}>{knew.length}</span><span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>de {drills.length}</span></div>
          <h2 style={{ margin: '10px 0 4px', fontSize: 22 }}>Sessió feta</h2>
          <p style={{ margin: 0, color: 'var(--text-soft)', fontSize: 14 }}>{knew.length} que ja et surten{again.length ? `, ${again.length} per tornar-hi` : ''}.</p>
        </div>
        {again.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Les que tornaràs a veure</div>
            {again.map((d) => <div key={d.id} style={{ padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', marginBottom: 6, fontSize: 14, fontWeight: 700 }}>{d.text_tachelhit}</div>)}
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {again.length > 0 && <button onClick={() => { setDrills(again); setCards(again.map((d) => cards[drills.indexOf(d)])); setAnswers({}); setI(0); setFinished(false); }} style={btn('ghost')}>Repeteix les {again.length}</button>}
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
      <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--brand-1)' }}>{mode === 'auto' ? 'Reproducció automàtica' : 'Escolta i digues-ho'}</div>
      {/* «Prova de dir-ho igual» NO es demana d'una síntesi: copiar-la és aprendre una pronúncia
          que no és de ningú. Amb veu de màquina, la frase es pot escoltar per entendre-la, i el
          que falta es diu en comptes d'invitar a imitar-la. */}
      <h2 style={{ margin: '2px 0 14px', fontSize: 19, lineHeight: 1.25 }}>
        {mode === 'auto' ? 'Escolta; passa sola a la següent'
          : bySynth ? 'Escolta-la per entendre-la: aquesta encara no la diu ningú'
            : `Escolta ${card?.speaker === 'Halima' ? 'la Halima' : card?.speaker === 'Driss' ? 'en Driss' : 'la veu'} i prova de dir-ho igual`}
      </h2>

      <div style={{ padding: 14, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {drill.image_url && <div style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9', borderRadius: 'var(--r-md)', overflow: 'hidden', background: 'var(--surface-2)' }}><img src={getMediaUrl(drill.image_url)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} /><span style={{ position: 'absolute', left: 10, bottom: 10, fontSize: 12, fontWeight: 700, background: 'rgba(255,255,255,0.92)', color: 'var(--text)', padding: '4px 10px', borderRadius: 'var(--r-pill)' }}>{speakerLabel}</span></div>}
        {!drill.image_url && <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>{speakerLabel}</div>}
        <p style={{ margin: 0, fontSize: 25, fontWeight: 800, lineHeight: 1.3 }}>
          <Highlighted text={drill.text_tachelhit || ''} marks={card?.highlights || []} />
        </p>
        <p style={{ margin: 0, fontSize: 15, color: 'var(--text-soft)' }}>{drill.text_catalan}</p>
        <WordGloss drill={drill} size="sm" />
        {drill.source_url && <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>Font: {drill.source_channel || 'vídeo original'}{drill.source_title ? ` · «${drill.source_title}»` : ''} · <a href={drill.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 700 }}>vídeo original ↗</a></p>}
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => play(1)} disabled={!voice} style={{ ...btn('primary'), flex: 1, height: 44, fontSize: 14 }}><FaPlay size={12} /> Escolta</button>
          <button onClick={() => play(0.7)} disabled={!voice} style={{ ...btn('ghost'), flex: 1, height: 44, fontSize: 14 }}>A poc a poc</button>
        </div>
      </div>

      {myTake && (
        <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Waveform src={voice || null} label={bySynth ? 'veu de màquina' : (card?.speaker || 'la veu')} color="var(--brand-1)" />
          <Waveform src={myTake} label="tu" color="var(--saffron-dark, #B7791F)" />
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.45 }}>
            {bySynth
              ? 'Aquesta frase no l’ha gravada ningú: el que sents és una síntesi, i no serveix per copiar-ne la pronúncia. Demana-la a les nostres veus des de la seva targeta.'
              : 'Escolta’ls un darrere l’altre i compara el ritme i on cau la força. Ningú no et posa nota: la teva gravació no surt d’aquesta pantalla i es perd quan passis de frase.'}
          </div>
        </div>
      )}

      {tip && (
        <div style={{ marginTop: 12, display: 'flex', gap: 10, padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)' }}>
          <FaLightbulb style={{ flexShrink: 0, marginTop: 3, color: 'var(--saffron-dark, #7A4A12)' }} />
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.45 }}><strong>Com sona ({tip.label}):</strong> {tip.tip}</p>
        </div>
      )}

      <div style={{ flex: 1 }} />
      {mode === 'auto' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 20 }}>
          <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: 'var(--text-soft)' }}>Sonant… passa sola</div>
          <button onClick={next} style={btn('primary')}>{i + 1 >= drills.length ? 'Acaba la sessió' : 'Següent'}</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, marginTop: 20 }}>
          {bySynth && (
            <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.5, maxWidth: 360 }}>
              Pots gravar-te per sentir-te, però no te la comparis: la veu que sona és una síntesi.
              Demana-la a les nostres veus des de la seva targeta i tindràs amb què comparar-te.
            </p>
          )}
          <button
            onPointerDown={(e) => { e.preventDefault(); startRecording(); }} onPointerUp={stopRecording}
            onPointerLeave={stopRecording} onPointerCancel={stopRecording}
            aria-label="Mantén premut per gravar-te"
            style={{ width: 72, height: 72, borderRadius: '50%', border: 'none', background: recording ? 'var(--danger, #c0392b)' : 'var(--surface-2)', color: recording ? '#fff' : 'var(--brand-1)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', touchAction: 'none', boxShadow: recording ? '0 0 0 12px rgba(192,57,43,0.18)' : 'none', transition: 'box-shadow .2s' }}>
            <FaMicrophone size={26} />
          </button>
          <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-soft)' }}>
            {recording ? 'Parla… deixa anar quan acabis' : myTake ? 'Torna-ho a provar si vols' : 'Mantén premut i digues-ho tu'}
          </span>
          <div style={{ fontSize: 13, color: 'var(--text-soft)', fontWeight: 700, marginTop: 4 }}>Ja la saps dir?</div>
          <div style={{ display: 'flex', gap: 10, width: '100%' }}>
            <button onClick={() => answer('no')} style={{ ...btn('ghost'), flex: 1 }}>Encara no</button>
            <button onClick={() => answer('yes')} style={{ ...btn('primary'), flex: 1 }}>Sí, ja la sé</button>
          </div>
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
