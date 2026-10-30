import { useEffect, useMemo, useRef, useState } from 'react';
import { FaVolumeUp } from 'react-icons/fa';
import { api } from '../api';
import { getMediaUrl } from '../config';
import type { Drill } from '../types';
import { duesCares } from '../utils/tifinag';
import { LESSONS, START_DRILL_IDS, WORDS, type Screen, type StartLesson, type StartWord } from '../lessons/startEnglish';

// «Start here · English» (#487, #500): the one part of the app written for English speakers.
//
// The rest of the app stays in Catalan (owner, 29-10-2026). Two short lessons for someone who is
// coming to run in the Atlas: each screen does one job and the learner says everything aloud.
// Nothing here records or uploads a voice; speaking is checked by the learner against the model.

const KEY = 'start_en_progress';
function readProgress(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; }
}
function saveProgress(p: Record<string, number>) {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private window: the lesson still works */ }
}

/** The person, if we know them, and where they are from. Never a corpus label. */
function whoSpeaks(d?: Drill): string {
  if (!d) return '';
  const tag = d.tag || '';
  const place = (d.region || '').trim();
  if (/\bHalima\b/.test(tag)) return `Halima · ${place || 'Aït Mraw'}`;
  if (/\bDriss\b/.test(tag)) return `Driss · ${place || 'Aït Mraw'}`;
  if (/ILoveLanguages/i.test(`${tag} ${d.speaker || ''}`)) return 'A native speaker · Central Atlas, region unknown';
  return place || 'A speaker from our library';
}

function usePlayer() {
  const ref = useRef<HTMLAudioElement | null>(null);
  useEffect(() => () => { ref.current?.pause(); }, []);
  return (url: string | null | undefined, rate = 1): Promise<number> => new Promise((done) => {
    if (!url) { done(0); return; }
    ref.current?.pause();
    const a = new Audio(getMediaUrl(url));
    a.playbackRate = rate;
    ref.current = a;
    a.onended = () => done(a.duration || 0);
    a.onerror = () => done(0);
    a.play().catch(() => done(0));
  });
}

const CARD: React.CSSProperties = { minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12, padding: 18, borderRadius: 'var(--r-xl)',
                                    border: '1px solid var(--border)', background: 'var(--surface)' };
const BTN: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '10px 16px', minHeight: 44, borderRadius: 'var(--r-pill)',
                                   border: '1px solid var(--brand-1)', background: 'transparent', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14 };
const GO: React.CSSProperties = { ...BTN, border: 'none', background: 'var(--brand-gradient)', color: '#fff' };
const OPT: React.CSSProperties = { textAlign: 'left', padding: '12px 14px', minHeight: 48, borderRadius: 'var(--r-lg)', fontFamily: 'inherit', fontSize: 15,
                                   cursor: 'pointer', background: 'var(--bg)', color: 'var(--text)', border: '1px solid var(--border)' };

function Word({ w }: { w: StartWord }) {
  const c = duesCares(w.lat);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <div lang="zgh" className="tifinagh" style={{ fontSize: 30, lineHeight: 1.3, color: 'var(--brand-1)', overflowWrap: 'anywhere' }}>{c.tif}</div>
      <div style={{ fontSize: 19, fontWeight: 700, overflowWrap: 'anywhere' }}>{w.lat}</div>
      <div style={{ fontSize: 15, color: 'var(--text-soft)' }}>{w.say}</div>
    </div>
  );
}

function shuffled<T>(x: T[]): T[] { return [...x].sort(() => Math.random() - 0.5); }

function ScreenView({ s, drills, onNext, onMiss }: { s: Screen; drills: Record<number, Drill>; onNext: () => void; onMiss: () => void }) {
  const play = usePlayer();
  const [picked, setPicked] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [step, setStep] = useState(0);
  const [bar, setBar] = useState(0);
  const url = (key: string) => drills[WORDS[key]?.drillId]?.audio_url;
  const first = 'key' in s ? s.key : null;
  const opts = useMemo(() => ('others' in s ? shuffled([s.key, ...s.others]) : []), [s]);

  useEffect(() => {
    if (!first || s.t === 'situation' || s.t === 'pickAudio') return;
    let on = true;
    (async () => {
      await play(url(first));
      if (on && s.t === 'meet') await play(url(first));
    })();
    return () => { on = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s, drills]);

  const Next = <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={onNext}>Next</button>;
  const Listen = ({ k, rate = 1, label = 'Listen' }: { k: string; rate?: number; label?: string }) => (
    <button type="button" style={BTN} onClick={() => play(url(k), rate)}><FaVolumeUp size={12} /> {label}</button>
  );

  switch (s.t) {
    case 'goal':
      return <div style={CARD}><h2 style={{ margin: 0, fontSize: 20 }}>{s.title}</h2>
        <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.7 }}>{s.can.map((c) => <li key={c}>{c}</li>)}</ul>{Next}</div>;
    case 'sound':
      return <div style={CARD}><h2 style={{ margin: 0, fontSize: 20 }}>{s.title}</h2><p style={{ margin: 0, lineHeight: 1.6, maxWidth: '60ch' }}>{s.body}</p>{Next}</div>;
    case 'meet': {
      const w = WORDS[s.key];
      return <div style={CARD}><div style={{ fontSize: 17, fontWeight: 700 }}>{w.en}</div><Word w={w} />
        {w.note && <div style={{ fontSize: 14, color: 'var(--text-soft)', lineHeight: 1.5 }}>{w.note}</div>}
        <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{whoSpeaks(drills[w.drillId])}</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><Listen k={s.key} /><Listen k={s.key} rate={0.75} label="Slow" /></div>{Next}</div>;
    }
    case 'pick':
    case 'pickAudio': {
      const right = picked === s.key;
      return <div style={CARD}>
        {s.t === 'pick' ? <><div>What did you hear?</div><div><Listen k={s.key} /></div></> : <div style={{ fontSize: 17, fontWeight: 700 }}>Which one means “{WORDS[s.key].en}”?</div>}
        <div style={{ display: 'grid', gap: 8 }}>{opts.map((o, i) => {
          const shown = picked !== null && (o === s.key || o === picked);
          const border = shown ? (o === s.key ? 'var(--emerald)' : 'var(--rose, #b3364a)') : 'var(--border)';
          return s.t === 'pick'
            ? <button key={o} type="button" disabled={picked !== null} style={{ ...OPT, border: `1px solid ${border}` }} onClick={() => setPicked(o)}>{WORDS[o].en}</button>
            : <div key={o} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button type="button" style={BTN} onClick={() => play(url(o))}><FaVolumeUp size={12} /> {i + 1}</button>
                <button type="button" disabled={picked !== null} style={{ ...OPT, flex: 1, border: `1px solid ${border}` }} onClick={() => setPicked(o)}>This one</button>
              </div>;
        })}</div>
        {picked !== null && <><Word w={WORDS[s.key]} />
          <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={() => { if (!right) onMiss(); onNext(); }}>Next</button></>}
      </div>;
    }
    case 'shadow': {
      const w = WORDS[s.key];
      const go = async () => {
        setStep(1);
        const dur = await play(url(s.key));
        setBar(Math.max(1.5, dur * 1.5));
        setStep(2);
        await new Promise((r) => setTimeout(r, Math.max(1.5, dur * 1.5) * 1000));
        await play(url(s.key));
        setStep(3);
      };
      return <div style={CARD}><div style={{ fontSize: 17, fontWeight: 700 }}>Say it with the speaker</div><Word w={w} />
        {step === 0 && <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={go}>Start</button>}
        {step === 1 && <div>Listen…</div>}
        {step === 2 && <div><strong>Your turn, out loud.</strong>
          <div style={{ height: 6, marginTop: 8, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
            <div style={{ height: '100%', background: 'var(--brand-1)', animation: `start-en-bar ${bar}s linear forwards` }} /></div></div>}
        {step === 3 && <><div>{s.check}</div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" style={GO} onClick={onNext}>Yes</button>
          <button type="button" style={BTN} onClick={onNext}>Nearly</button>
          <button type="button" style={BTN} onClick={() => { onMiss(); onNext(); }}>Again later</button></div></>}
      </div>;
    }
    case 'situation': {
      const w = WORDS[s.key];
      return <div style={CARD}><div style={{ fontSize: 17, fontWeight: 700 }}>{s.prompt}</div><div>What do you say? Say it out loud first.</div>
        {!revealed ? <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={() => { setRevealed(true); play(url(s.key)); }}>Show me</button>
          : <><Word w={w} /><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" style={GO} onClick={onNext}>I had it</button>
            <button type="button" style={BTN} onClick={() => { onMiss(); onNext(); }}>Again later</button></div></>}
      </div>;
    }
    case 'exchange': {
      const line = s.lines[step];
      if (!line) return <div style={CARD}><div style={{ fontWeight: 700 }}>Well done.</div>{Next}</div>;
      const w = WORDS[line.key];
      const go = async () => {
        if (line.you) { await new Promise((r) => setTimeout(r, 2500)); }
        await play(url(line.key));
        setStep((x) => x + 1);
      };
      return <div style={CARD}><div style={{ fontSize: 17, fontWeight: 700 }}>{s.title}</div>
        <div>{line.you ? 'Your line: say it, then you will hear it.' : 'They say:'}</div>
        <div style={{ color: 'var(--text-soft)' }}>{w.en}</div>{line.you && <Word w={w} />}
        <button key={step} type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={go}>{line.you ? 'I’m saying it' : 'Play'}</button></div>;
    }
    case 'read':
      return <div style={CARD}><div style={{ fontSize: 17, fontWeight: 700 }}>Read one word in Tifinagh</div>
        <div lang="zgh" className="tifinagh" style={{ fontSize: 44, color: 'var(--brand-1)' }}>{s.tif}</div>
        {!revealed ? <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={() => setRevealed(true)}>Show the letters</button>
          : <><div>{s.letters.join(' · ')}</div><div><strong>{s.lat}</strong>: {s.en}</div>{Next}</>}
      </div>;
    default:
      return null;
  }
}

function Lesson({ lesson, drills, onExit, onDone }: { lesson: StartLesson; drills: Record<number, Drill>; onExit: () => void; onDone: () => void }) {
  const [queue, setQueue] = useState<Screen[]>(lesson.screens);
  const [i, setI] = useState(0);
  const [missed, setMissed] = useState(0);
  const s = queue[i];
  useEffect(() => { if (s?.t === 'done') onDone(); }, [s, onDone]);
  if (s.t === 'done') {
    return <div style={CARD}><h2 style={{ margin: 0, fontSize: 20 }}>{lesson.title}: done</h2>
      <p style={{ margin: 0 }}>{missed === 0 ? 'Everything first time.' : `You came back to ${missed} ${missed === 1 ? 'item' : 'items'}, which is how it sticks.`} Come back tomorrow and say them from memory.</p>
      <button type="button" style={{ ...GO, alignSelf: 'flex-start' }} onClick={onExit}>Back to the lessons</button></div>;
  }
  return <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', fontSize: 13, color: 'var(--text-soft)' }}>
      <span>{lesson.title}</span>
      <button type="button" onClick={onExit} style={{ border: 'none', background: 'none', color: 'var(--text-soft)', cursor: 'pointer', fontFamily: 'inherit', minHeight: 36 }}>Leave</button></div>
    <div style={{ height: 4, borderRadius: 2, background: 'var(--border)', overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${(100 * i) / (queue.length - 1)}%`, background: 'var(--brand-1)' }} /></div>
    <ScreenView key={i} s={s} drills={drills} onNext={() => setI((x) => x + 1)}
                onMiss={() => { setMissed((m) => m + 1); setQueue((q) => { const c = [...q]; c.splice(Math.min(i + 4, q.length - 1), 0, s); return c; }); }} />
  </div>;
}

const H2: React.CSSProperties = { fontFamily: 'var(--font-display)', fontSize: 20, margin: '0 0 8px', lineHeight: 1.25 };
const P: React.CSSProperties = { margin: '0 0 10px', fontSize: 15, lineHeight: 1.65, maxWidth: '66ch' };

export default function StartEnglish() {
  const [drills, setDrills] = useState<Record<number, Drill>>({});
  const [open, setOpen] = useState<string | null>(null);
  const [done, setDone] = useState<Record<string, number>>(readProgress);

  useEffect(() => {
    document.title = 'Start here · Tamazight';
    let alive = true;
    Promise.all(START_DRILL_IDS.map((id) => api.drill(id).then((d) => [id, d] as const).catch(() => null)))
      .then((rows) => { if (alive) setDrills(Object.fromEntries(rows.filter((r): r is readonly [number, Drill] => !!r))); });
    return () => { alive = false; };
  }, []);

  const lesson = LESSONS.find((l) => l.id === open);
  return (
    <div lang="en" style={{ padding: '22px 16px 60px', maxWidth: 640, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <style>{'@keyframes start-en-bar { from { width: 0 } to { width: 100% } }'}</style>
      {lesson ? <Lesson lesson={lesson} drills={drills} onExit={() => setOpen(null)}
                        onDone={() => setDone((d) => { const n = { ...d, [lesson.id]: Date.now() }; saveProgress(n); return n; })} /> : <>
        <div style={{ fontSize: 12, letterSpacing: '.1em', textTransform: 'uppercase', fontWeight: 800, color: 'var(--brand-1)' }}>Start here · English</div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, margin: '6px 0 8px', lineHeight: 1.15 }}>
          Your first Tamazight <span lang="zgh" className="tifinagh" style={{ color: 'var(--brand-1)', fontWeight: 400 }}>ⵜⴰⵎⴰⵣⵉⵖⵜ</span>
        </h1>
        <p style={{ ...P, color: 'var(--text-soft)' }}>Two short lessons for the route from Aït Bouguemmez to Kalaat M’Gouna. Real voices, and you speak in every step.</p>
        <div style={{ display: 'grid', gap: 10 }}>
          {LESSONS.map((l) => (
            <button key={l.id} type="button" onClick={() => setOpen(l.id)} style={{ ...OPT, display: 'flex', justifyContent: 'space-between', gap: 10, fontWeight: 700 }}>
              <span>{l.title}</span><span style={{ fontWeight: 400, color: 'var(--text-soft)', whiteSpace: 'nowrap' }}>{done[l.id] ? 'Done ✓' : `${l.minutes} min`}</span>
            </button>))}
        </div>

        <details style={{ marginTop: 26 }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700, minHeight: 36 }}>About the language and these voices</summary>
          <div style={{ marginTop: 12 }}>
            <h2 style={H2}>The language</h2>
            <p style={P}>
              Tamazight is the Amazigh language family of North Africa. In Morocco it has three big
              branches: Tarifit in the north, Central Atlas Tamazight, and Tashelhit in the south-west.
              Distant varieties are not always mutually intelligible. It has been an official language of
              Morocco since 2011. Many people in the Azilal area call their own speech <em>tashelhit</em>.
            </p>
            <p style={P}>
              The Tifinagh alphabet you see here is the modern Moroccan standard of 2003, descended from
              an ancient script. Village manuscripts in the Atlas were written in Arabic letters.
            </p>
            <h2 style={H2}>Where we run</h2>
            <p style={P}>
              Our route crosses the Central High Atlas from the Aït Bouguemmez valley, in Azilal province,
              over the M’Goun massif and down the M’Goun valley to Kalaat M’Gouna, in Tinghir province.
              Speech changes from valley to valley, so you will hear other forms. Our lesson says
              {' '}<em>manimsh tjit</em>; on the south side you will hear <em>manik tgit</em>.
            </p>
            <h2 style={H2}>The voices</h2>
            <p style={P}>
              Halima and Driss are from Aït Mraw, and our speech notes are about them, not about every
              valley on the route. A few items come from a native speaker recorded by
              ILoveLanguages!, whose region we do not know, and one from Beni Mellal. Each card says who
              is speaking. Around here people usually greet with <em>salam ɛlikum</em> and answer with
              {' '}<em>labas, lhamdullah</em>. We have no recording of those yet, so they are not in the lessons.
            </p>
          </div>
        </details>
      </>}
    </div>
  );
}
