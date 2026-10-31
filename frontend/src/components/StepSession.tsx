import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaCheck, FaLightbulb, FaMicrophone, FaPlay, FaTimes } from 'react-icons/fa';
import { api, type PracticeStep } from '../api';
import { getMediaUrl, getUserName } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';
import { preferredRecorderMime } from '../utils/media';
import { parseGlosses } from './WordGloss';
import Frase from './Frase';
import SentenceVariants, { type Variant } from './SentenceVariants';

// Playing a practice as it was WRITTEN (#199, ADR 0002).
//
// The workshop lets you choose a tool for every step — listen and pick, write what you hear, say
// it and compare yourself, fill the gap, word by word, the other script, which spelling. The
// runner ignored all of it and played every step as the same listening card, which made the
// choosing a lie. This is the other half: each step is run with the tool it was given.
//
// What is NOT here, on purpose: a mark. Nothing scores you. «Ho sabia» and «Encara no» are yours
// to press, and the only thing a wrong answer does is show you the right one.

type Props = { testId: number; title: string; onExit: () => void };

const norm = (s: string) =>
  (s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[^\p{L}\p{N}\s]/gu, '').replace(/\s+/g, ' ').trim();

// Close enough to be the same answer: somebody typing an unfamiliar script will miss an accent.
function near(a: string, b: string): boolean {
  const x = norm(a), y = norm(b);
  if (!x || !y) return false;
  if (x === y) return true;
  if (Math.abs(x.length - y.length) > 2) return false;
  let wrong = 0;
  for (let i = 0; i < Math.max(x.length, y.length); i++) if (x[i] !== y[i]) wrong++;
  return wrong <= Math.max(1, Math.floor(x.length / 8));
}

export default function StepSession({ testId, title, onExit }: Props) {
  const navigate = useNavigate();
  const [steps, setSteps] = useState<PracticeStep[] | null>(null);
  const [drills, setDrills] = useState<Record<number, Drill>>({});
  // Les altres maneres de dir cada frase (#239), demanades d'un sol cop: una pràctica ensenya
  // una versió i fins ara no deia que n'hi hagués cap més.
  const [altres, setAltres] = useState<Record<string, Variant[]>>({});
  const [i, setI] = useState(0);
  const [answer, setAnswer] = useState('');
  const [shown, setShown] = useState(false);      // the answer is on the table
  const [right, setRight] = useState<boolean | null>(null);
  const [myTake, setMyTake] = useState<Blob | null>(null);
  const [recording, setRecording] = useState(false);
  const [done, setDone] = useState(false);
  const [knew, setKnew] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    api.practiceSteps(testId).then(async (r) => {
      setSteps(r.steps);
      const ids = Array.from(new Set(r.steps.map((s) => s.drill_id).filter(Boolean))) as number[];
      if (ids.length) {
        const got = await api.drillsByIds(ids).catch(() => [] as Drill[]);
        setDrills(Object.fromEntries(got.map((d) => [d.id, d])));
        api.otherWays(ids).then(setAltres).catch(() => {});
      }
    }).catch(() => toast.error('No s’han pogut llegir els passos'));
  }, [testId]);

  const step = steps?.[i];
  const drill = step?.drill_id ? drills[step.drill_id] : undefined;
  // LA VEU D'UN PAS, i quan NO pot ser de màquina.
  //
  // Això queia a `audio_tts_shi_url` sempre que no hi havia gravació, i per tant un «digues-ho i
  // compara't amb la veu de debò» feia sonar una síntesi: qui ho feia s'emmotllava a una
  // pronúncia de màquina creient que imitava algú. En una llengua que documentem a partir de
  // parlants, és exactament el que no podem fer (docs/SCOPE.md).
  // Ni per escoltar: cap veu sintètica en amazic. Sense gravació d'una persona, el pas queda mut (#532).
  //
  const human = drill?.audio_url || '';
  const voice = human;

  const play = useCallback((rate = 1) => {
    if (!voice) return;
    audioRef.current?.pause();
    const a = new Audio(getMediaUrl(voice)); a.playbackRate = rate; audioRef.current = a;
    a.play().catch(() => {});
  }, [voice]);

  // The listening steps play by themselves: that is the step.
  useEffect(() => {
    if (!step) return;
    setAnswer(''); setShown(false); setRight(null); setMyTake(null);
    if (drill && (step.kind === 'listen_pick' || step.kind === 'write_heard' || step.kind === 'pick_written')) play(1);
  }, [i, step?.kind, drill?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Meanings to choose between, when the practice alone cannot give enough.
  //
  // The distractors used to come ONLY from this practice, so a two-sentence practice offered two
  // buttons and a one-sentence practice offered one — a choice that is not a choice. The
  // practice still comes first (its sentences are the material being learned, so they are the
  // most honest wrong answers); the library fills in, and only from the same subject or the same
  // grammar unit, never at random. One request per session.
  const [pool, setPool] = useState<string[]>([]);
  useEffect(() => {
    if (!steps) return;
    const mine = steps.map((x) => (x.drill_id ? drills[x.drill_id] : undefined)).filter(Boolean) as Drill[];
    const enough = new Set(mine.map((d) => (d.text_catalan || '').trim()).filter(Boolean)).size;
    if (enough >= 4 || !mine.length) return;
    const count = (pick: (d: Drill) => string | null | undefined) => {
      const c: Record<string, number> = {};
      mine.forEach((d) => (pick(d) || '').split(',').map((x) => x.trim()).filter(Boolean)
        .forEach((k) => { c[k] = (c[k] || 0) + 1; }));
      return Object.entries(c).sort((a, b) => b[1] - a[1])[0]?.[0];
    };
    const topic = count((d) => d.topics);
    const unit = topic ? null : count((d) => d.grammar);
    if (!topic && !unit) return;
    const q = topic ? `topic=${encodeURIComponent(topic)}` : `unit=${encodeURIComponent(unit as string)}`;
    api.practiceSession(`${q}&with_voice=0&limit=40`)
      .then((r) => setPool(r.drills.map((d) => (d.text_catalan || '').trim()).filter(Boolean)))
      .catch(() => {});
  }, [steps, drills]);  // eslint-disable-line react-hooks/exhaustive-deps

  const options = useMemo(() => {
    if (!steps || !drill || step?.kind !== 'listen_pick') return [];
    const truth = (drill.text_catalan || '').trim();
    const fromHere = steps
      .map((x) => (x.drill_id ? drills[x.drill_id] : undefined))
      .filter((d): d is Drill => !!d && d.id !== drill.id && !!(d.text_catalan || '').trim())
      .map((d) => (d.text_catalan as string).trim());
    const seen = new Set([truth]);
    const take = (from: string[]) => from.filter((t) => !seen.has(t) && (seen.add(t), true));
    const here = take(Array.from(new Set(fromHere))).sort(() => Math.random() - 0.5);
    const wide = take(Array.from(new Set(pool))).sort(() => Math.random() - 0.5);
    const picked = [...here, ...wide].slice(0, 2);
    return [truth, ...picked].sort(() => Math.random() - 0.5);
  }, [steps, drills, pool, drill?.id, step?.kind]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Quatre frases ESCRITES per triar, per a «escolta i tria la frase» (#387).
  //
  // L'«escolta i tria» de sempre dona quatre significats en català i entrena a entendre; això
  // dona quatre frases en amazic i entrena a lligar el que se sent amb el que està escrit.
  //
  // Les falses surten de la mateixa pràctica —que és el material que s'està aprenent— i es
  // trien per llargada semblant: si una és molt més curta que les altres, es veu quina és sense
  // escoltar. I la bona ha de ser text escrit per algú: la lectura de màquina viu a
  // `text_tachelhit_suggested` i no entra mai com a resposta.
  const escrites = useMemo(() => {
    if (!steps || !drill || step?.kind !== 'pick_written') return [];
    const truth = (drill.text_tachelhit || '').trim();
    if (!truth) return [];
    const altres = steps
      .map((x) => (x.drill_id ? drills[x.drill_id] : undefined))
      .filter((d): d is Drill => !!d && d.id !== drill.id && !!(d.text_tachelhit || '').trim())
      .map((d) => (d.text_tachelhit as string).trim())
      .filter((t) => t !== truth);
    const semblants = Array.from(new Set(altres))
      .sort((a, b) => Math.abs(a.length - truth.length) - Math.abs(b.length - truth.length))
      .slice(0, 6)
      .sort(() => Math.random() - 0.5)
      .slice(0, 3);
    if (!semblants.length) return [];
    return [truth, ...semblants].sort(() => Math.random() - 0.5);
  }, [steps, drills, drill?.id, step?.kind]);  // eslint-disable-line react-hooks/exhaustive-deps

  // The gap: one real word taken out of the sentence, BY POSITION.
  //
  // `text.replace(word, '···')` hides the first place that STRING occurs, which is not the same
  // thing: «tanmirt tan tanmirt» with «tan» chosen came out `···mirt ··· ···mirt`, unreadable at
  // the very step that asks you to read it. Splitting on the separators and blanking one index
  // hides exactly one word, repeated or not.
  const gap = useMemo(() => {
    const text = (drill?.text_tachelhit || '').trim();
    if (!text) return null;
    const parts = text.split(/(\s+)/);                       // the separators are kept
    const words = parts.map((_, k) => k).filter((k) => parts[k].trim().length > 2);
    if (!words.length) return null;
    const at = words[Math.floor(words.length / 2)];
    const hidden = parts[at];
    const masked = parts.slice();
    masked[at] = '·'.repeat(Math.max(3, hidden.length));
    return { hidden, shown: masked.join('') };
  }, [drill?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  // ---- which spelling is the speaker's -------------------------------------------------
  // The other way of writing the SAME sentence. Never an invented word: either the second
  // spelling this sentence already carries, or the same sentence through the swaps people
  // really make (ɣ/gh, x/kh, ɛ/3, ḥ/7, the emphatics, the doubled consonants).
  const SWAPS: [RegExp, string][] = [
    [/\u0263/g, 'gh'], [/gh/g, '\u0263'], [/x/g, 'kh'], [/kh/g, 'x'],
    [/\u025b/g, '3'], [/3/g, '\u025b'], [/\u1e25/g, '7'], [/7/g, '\u1e25'],
    [/\u1e0d/g, 'd'], [/\u1e63/g, 's'], [/\u1e93/g, 'z'], [/\u1e6d/g, 't'],
  ];
  const otherSpelling = (text: string, second?: string | null): string | null => {
    const a = (text || '').trim();
    if (!a) return null;
    const b = (second || '').trim();
    if (b && b !== a && norm(b) !== '' ) return b;        // the one it already carries
    for (const [pat, rep] of SWAPS) {
      if (pat.test(a)) {
        const made = a.replace(pat, rep);
        if (made !== a) return made;
      }
    }
    // nothing else to change: double the first long-enough word's first letter
    const w = a.split(/\s+/).find((x) => x.length > 2);
    return w ? a.replace(w, w[0] + w) : null;
  };

  const spellings = useMemo(() => {
    if (step?.kind !== 'pick_spelling' || !drill) return [];
    const mine = (drill.text_tachelhit || '').trim();
    const other = otherSpelling(mine, drill.text_tachelhit_latin);
    if (!mine || !other || other === mine) return [];
    return [mine, other].sort(() => Math.random() - 0.5);
  }, [drill?.id, step?.kind]);  // eslint-disable-line react-hooks/exhaustive-deps

  const startRecording = async () => {
    if (recording) return;
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
    } catch { toast.error('No s’ha pogut accedir al micròfon.'); }
  };
  const stopRecording = () => { if (recorderRef.current?.state === 'recording') recorderRef.current.stop(); };

  const check = (given: string, target: string, exact = false) => {
    // `near` forgives the accents on purpose — except when the accents ARE the question, which is
    // what «which spelling is the speaker's» asks.
    const ok = exact ? given.trim() === target.trim() : near(given, target);
    setRight(ok); setShown(true);
    if (ok) setKnew((k) => k + 1);
    if (drill) api.reviewGrade(drill.id, ok ? 3 : 1).catch(() => {});
  };

  // Quan s'acaba, queda constància que s'ha jugat: fins ara una pràctica jugada amb passos no
  // escrivia cap intent i les seves estadístiques sortien sempre a zero (#218). Si no es pot
  // desar, no passa res de cara a qui estudia: la sessió ja és feta.
  // L'hora d'inici es pren amb el primer pas que es veu, no en pintar: una crida impura al cos
  // del component torna a córrer a cada render.
  const començat = useRef<number | null>(null);
  const desat = useRef(false);
  const tornaHi = () => {
    setI(0); setKnew(0); setDone(false);
    desat.current = false;
  };
  // El rellotge de la sessió: comença quan la sessió comença i torna a començar amb «Torna-hi».
  useEffect(() => { if (!done) començat.current = Date.now(); }, [done]);

  const acaba = () => {
    setDone(true);
    if (desat.current || !steps) return;
    desat.current = true;
    const preguntes = steps.filter((s) => s.kind !== 'note').length;
    if (!preguntes) return;
    api.saveAttempt({
      test_id: testId,
      score: Math.round((knew / preguntes) * 100),
      total_questions: preguntes,
      correct_answers: knew,
      time_taken_seconds: Math.max(1, Math.floor((Date.now() - (començat.current ?? Date.now())) / 1000)),
      user_name: getUserName() || null,
    }).catch(() => {});
  };

  const next = () => {
    audioRef.current?.pause();
    if (!steps) return;
    if (i + 1 >= steps.length) { acaba(); return; }
    setI(i + 1);
  };
  const markAndNext = (ok: boolean) => {
    if (drill) api.reviewGrade(drill.id, ok ? 3 : 1).catch(() => {});
    if (ok) setKnew((k) => k + 1);
    next();
  };

  if (!steps) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Preparant la pràctica…</div>;
  if (!steps.length) return (
    <div style={{ padding: '40px 16px', maxWidth: 520, margin: '0 auto', textAlign: 'center' }}>
      <p style={{ color: 'var(--text-soft)' }}>Aquesta pràctica encara no té cap pas.</p>
      <button onClick={() => navigate(`/tests/${testId}/editor`)} style={btn('primary')}>Obre el taller</button>
    </div>
  );

  const bar = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
      <button onClick={onExit} aria-label="Surt" style={{ width: 36, height: 36, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--surface-2)', color: 'var(--text)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><FaTimes /></button>
      <div style={{ flex: 1, height: 10, borderRadius: 5, background: 'var(--surface-2)', overflow: 'hidden' }}>
        <div style={{ width: `${((done ? steps.length : i) / steps.length) * 100}%`, height: 10, background: 'var(--brand-1)', transition: 'width .3s' }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-soft)' }}>{Math.min(i + 1, steps.length)} / {steps.length}</span>
    </div>
  );

  if (done) {
    const asked = steps.filter((s) => s.kind !== 'note').length;
    return (
      <div style={{ padding: '20px 16px 32px', maxWidth: 520, margin: '0 auto' }}>
        {bar}
        <div style={{ textAlign: 'center', margin: '18px 0 22px' }}>
          <div style={{ width: 110, height: 110, borderRadius: '50%', border: `10px solid ${knew >= asked * 0.7 ? 'var(--emerald)' : 'var(--saffron)'}`, boxSizing: 'border-box', display: 'inline-flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: 30, fontWeight: 800, lineHeight: 1 }}>{knew}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>de {asked}</span>
          </div>
          <h2 style={{ margin: '12px 0 4px', fontSize: 22 }}>{title}</h2>
          <p style={{ margin: 0, color: 'var(--text-soft)', fontSize: 14 }}>Feta. Les que t’han costat tornaran al repàs.</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button onClick={tornaHi} style={btn('ghost')}>Torna-hi</button>
          <button onClick={onExit} style={btn('primary')}>Fet</button>
        </div>
      </div>
    );
  }

  const tool = step?.kind;
  const meaning = drill?.text_catalan || '';
  const written = drill?.text_tachelhit || '';
  // The tools nobody marks for you. `pick_spelling` has left this group: it asks a question with
  // a right answer now, so it is checked like the others.
  const selfMarked = tool === 'say_it' || tool === 'look_say' || tool === 'word_by_word' || tool === 'script_swap';

  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: 520, margin: '0 auto', minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      {bar}

      {tool === 'note' ? (
        <section style={card}>
          {step?.payload?.heading && <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: '0 0 8px' }}>{step.payload.heading}</h2>}
          {step?.payload?.image_url && <img src={getMediaUrl(step.payload.image_url)} alt="" style={{ width: '100%', borderRadius: 'var(--r-md)', marginBottom: 10 }} />}
          <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.6 }}>{step?.payload?.text}</p>
        </section>
      ) : !drill ? (
        <section style={card}><p style={{ margin: 0, color: 'var(--text-muted)' }}>Aquest pas ha perdut la seva frase.</p></section>
      ) : (
        <section style={card}>
          <div style={{ fontSize: 11.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--brand-1)', marginBottom: 8 }}>
            {tool === 'listen_pick' && 'Escolta i tria'}
            {tool === 'write_heard' && 'Escolta i escriu'}
            {tool === 'say_it' && 'Digues-ho i compara’t'}
            {tool === 'look_say' && 'Mira la imatge i digues-ho'}
            {tool === 'fill_gap' && 'Omple el buit'}
            {tool === 'word_by_word' && 'Paraula per paraula'}
            {tool === 'script_swap' && 'L’altra escriptura'}
            {tool === 'pick_spelling' && 'Quina és la bona'}
            {tool === 'pick_written' && 'Escolta i tria la frase'}
          </div>

          {/* the picture: hidden when seeing it would give the answer away */}
          {drill.image_url && tool !== 'listen_pick' && tool !== 'write_heard' && tool !== 'pick_written' && (
            <img src={getMediaUrl(drill.image_url)} alt="" style={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 'var(--r-md)', marginBottom: 10 }}
                 onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
          )}

          {(tool === 'listen_pick' || tool === 'write_heard' || tool === 'pick_written') && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', gap: 10 }}>
                <button onClick={() => play(1)} style={{ ...btn('primary'), flex: 1, height: 44, fontSize: 14 }}><FaPlay size={12} /> Torna-ho a sentir</button>
                <button onClick={() => play(0.7)} style={{ ...btn('ghost'), flex: 1, height: 44, fontSize: 14 }}>A poc a poc</button>
              </div>
            </div>
          )}

          {tool === 'listen_pick' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {options.map((o) => {
                const isRight = o === meaning;
                const chosen = answer === o;
                return (
                  <button key={o} disabled={shown} onClick={() => { setAnswer(o); check(o, meaning); }}
                          style={{ ...btn('ghost'), justifyContent: 'flex-start', height: 'auto', padding: '12px 16px', textAlign: 'left', fontSize: 14.5,
                                   borderColor: shown && isRight ? 'var(--emerald)' : chosen ? 'var(--rose)' : 'var(--brand-1)',
                                   color: shown && isRight ? 'var(--emerald)' : 'var(--text)' }}>
                    {o}
                  </button>
                );
              })}
            </div>
          )}

          {tool === 'pick_written' && (
            escrites.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {escrites.map((o) => {
                  const isRight = o === written.trim();
                  const chosen = answer === o;
                  return (
                    <button key={o} disabled={shown} onClick={() => { setAnswer(o); check(o, written, true); }}
                            style={{ ...btn('ghost'), justifyContent: 'flex-start', height: 'auto', padding: '12px 16px', textAlign: 'left',
                                     borderColor: shown && isRight ? 'var(--emerald)' : chosen && !isRight ? 'var(--rose)' : 'var(--brand-1)' }}>
                      <Frase text={o} size="md" />
                    </button>
                  );
                })}
              </div>
            ) : (
              // Sense tres frases més amb les paraules escrites no hi ha res a triar: val més
              // dir-ho que fer una pregunta d'una sola resposta.
              <>
                <p style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--text-muted)' }}>
                  Aquesta pràctica no té prou frases escrites per triar-ne quatre.
                </p>
                <Frase text={written} size="lg" />
              </>
            )
          )}

          {(tool === 'write_heard' || tool === 'fill_gap') && (
            <>
              {tool === 'fill_gap' && <p style={{ margin: '0 0 10px', fontSize: 21, fontWeight: 800, lineHeight: 1.35 }}>{gap?.shown}</p>}
              {tool === 'fill_gap' && <p style={{ margin: '0 0 10px', fontSize: 14.5, color: 'var(--text-soft)' }}>{meaning}</p>}
              <input value={answer} onChange={(e) => setAnswer(e.target.value)} disabled={shown}
                     onKeyDown={(e) => { if (e.key === 'Enter' && answer.trim()) check(answer, tool === 'fill_gap' ? (gap?.hidden || '') : written); }}
                     placeholder={tool === 'fill_gap' ? 'la paraula que falta' : 'escriu el que has sentit'}
                     style={{ width: '100%', boxSizing: 'border-box', padding: '12px 14px', fontSize: 16, borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit' }} />
              {!shown && (
                <button onClick={() => check(answer, tool === 'fill_gap' ? (gap?.hidden || '') : written)}
                        disabled={!answer.trim()} style={{ ...btn('primary'), width: '100%', marginTop: 10, opacity: answer.trim() ? 1 : 0.5 }}>
                  Comprova-ho
                </button>
              )}
            </>
          )}

          {(tool === 'say_it' || tool === 'look_say') && !human && (
            <>
              <p style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text-soft)' }}>{meaning}</p>
              <p style={{ margin: '0 0 10px', fontSize: 23, fontWeight: 800, lineHeight: 1.3 }}>{written}</p>
              {/* Sense gravació d'una persona, aquest pas no pot fer el que diu: no hi ha res amb
                  què comparar-se. Abans la frase sonava igualment, sintetitzada. I el refús ha de
                  produir l'arranjament, no un forat: d'aquí el botó. */}
              <p style={{ margin: '0 0 10px', fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.6 }}>
                D’aquesta frase no en tenim cap veu nostra: no hi ha res amb què comparar-se.
                Demana-la a les nostres veus i aquest pas funcionarà quan algú la digui.
              </p>
              <button onClick={async () => {
                if (!drill) return;
                try { await api.askForVoice(drill.id); toast.success('Demanada a les nostres veus'); }
                catch { toast.error('No s’ha pogut demanar'); }
              }} style={{ ...btn('ghost'), width: '100%' }}>
                <FaMicrophone size={12} /> Demana-la a les nostres veus
              </button>
            </>
          )}

          {(tool === 'say_it' || tool === 'look_say') && human && (
            <>
              <p style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text-soft)' }}>{meaning}</p>
              {shown && <p style={{ margin: '0 0 10px', fontSize: 23, fontWeight: 800, lineHeight: 1.3 }}>{written}</p>}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 10 }}>
                <button onPointerDown={(e) => { e.preventDefault(); startRecording(); }} onPointerUp={stopRecording}
                        onPointerLeave={stopRecording} onPointerCancel={stopRecording} aria-label="Mantén premut per gravar-te"
                        style={{ width: 68, height: 68, borderRadius: '50%', border: 'none', background: recording ? 'var(--danger, #c0392b)' : 'var(--surface-2)', color: recording ? '#fff' : 'var(--brand-1)', cursor: 'pointer', touchAction: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FaMicrophone size={24} />
                </button>
                <span style={{ fontSize: 12.5, color: 'var(--text-soft)', fontWeight: 700 }}>
                  {recording ? 'Parla… deixa anar quan acabis' : myTake ? 'Compara’t amb la veu de debò' : 'Mantén premut i digues-ho'}
                </span>
                {myTake && (
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button onClick={() => play(1)} style={{ ...btn('ghost'), height: 40, fontSize: 13 }}><FaPlay size={10} /> La veu</button>
                    <button onClick={() => { const u = URL.createObjectURL(myTake); const a = new Audio(u); a.onended = () => URL.revokeObjectURL(u); a.play().catch(() => {}); }}
                            style={{ ...btn('ghost'), height: 40, fontSize: 13 }}><FaPlay size={10} /> El que has dit</button>
                  </div>
                )}
                {!shown && <button onClick={() => { setShown(true); play(1); }} style={{ ...btn('ghost'), marginTop: 6 }}>Ensenya-me-la</button>}
              </div>
            </>
          )}

          {tool === 'word_by_word' && (
            <>
              <p style={{ margin: '0 0 4px', fontSize: 22, fontWeight: 800, lineHeight: 1.35 }}>{written}</p>
              <p style={{ margin: '0 0 12px', fontSize: 14.5, color: 'var(--text-soft)' }}>{meaning}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {parseGlosses(drill).map((g, k) => (
                  <div key={k} style={{ padding: '8px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', textAlign: 'center' }}>
                    <div style={{ fontWeight: 800, fontSize: 15 }}>{g.shi}</div>
                    <div style={{ fontSize: 12.5, color: 'var(--brand-1)', fontWeight: 600 }}>{g.ca || '—'}</div>
                  </div>
                ))}
              </div>
              {parseGlosses(drill).length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>Aquesta frase encara no està desglossada.</p>}
            </>
          )}

          {tool === 'script_swap' && (
            <>
              <p style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 800, lineHeight: 1.35 }}>{written}</p>
              <p style={{ margin: '0 0 10px', fontSize: 14.5, color: 'var(--text-soft)' }}>{meaning}</p>
              {shown ? (
                <p style={{ margin: 0, fontSize: 24, fontFamily: 'var(--font-tifinagh)', lineHeight: 1.4 }}>
                  {drill.text_tachelhit_latin || '—'}
                </p>
              ) : (
                <button onClick={() => setShown(true)} style={{ ...btn('ghost'), width: '100%' }}>Ensenya-me-la en l’altra escriptura</button>
              )}
            </>
          )}

          {tool === 'pick_spelling' && (
            <>
              <p style={{ margin: '0 0 10px', fontSize: 15, color: 'var(--text-soft)' }}>{meaning}</p>
              <p style={{ margin: '0 0 12px', fontSize: 13.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Escolta i tria com ho escriu qui parla. No hi ha una ortografia oficial: la bona és la seva.
              </p>
              {voice && <button onClick={() => play(1)} style={{ ...btn('primary'), width: '100%', marginBottom: 10 }}><FaPlay size={12} /> Escolta</button>}
              {spellings.length === 2 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {spellings.map((o) => {
                    const isRight = o.trim() === written.trim();
                    const chosen = answer === o;
                    return (
                      <button key={o} disabled={shown} onClick={() => { setAnswer(o); check(o, written, true); }}
                              style={{ ...btn('ghost'), height: 'auto', padding: '14px 16px', fontSize: 19, fontWeight: 800,
                                       borderColor: shown && isRight ? 'var(--emerald)' : chosen && !isRight ? 'var(--rose)' : 'var(--brand-1)',
                                       color: shown && isRight ? 'var(--emerald)' : 'var(--text)' }}>
                        {o}
                      </button>
                    );
                  })}
                </div>
              ) : (
                // Nothing to choose between: this sentence has only one spelling anywhere. Say so
                // instead of pretending to ask.
                <>
                  <p style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--text-muted)' }}>
                    D’aquesta frase només en tenim una manera d’escriure-la.
                  </p>
                  <p style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>{written}</p>
                </>
              )}
            </>
          )}

          {/* Les altres maneres de dir-la. Només quan el text ja és a la taula: a «escolta i
              tria» ensenyar-les abans seria dir la resposta (#239). */}
          {(shown || selfMarked) && drill && (altres[String(drill.id)] || []).length > 0 && (
            <SentenceVariants variants={altres[String(drill.id)]} size="sm" />
          )}

          {shown && right !== null && (tool === 'listen_pick' || tool === 'write_heard' || tool === 'fill_gap' || tool === 'pick_spelling' || tool === 'pick_written') && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 'var(--r-lg)', background: right ? 'var(--emerald-soft, #E5F2EA)' : 'var(--brand-gradient-soft)' }}>
              <div style={{ fontWeight: 800, fontSize: 15, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                {right ? <><FaCheck /> Sí</> : 'Era:'}
              </div>
              {!right && <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>{tool === 'fill_gap' ? gap?.hidden : written}</div>}
                  {!right && tool !== 'fill_gap' && tool !== 'pick_spelling' && <div style={{ fontSize: 14, color: 'var(--text-soft)' }}>{meaning}</div>}
            </div>
          )}
        </section>
      )}

      <div style={{ flex: 1 }} />

      {/* The steps you mark yourself keep their two buttons whether or not you asked to see the
          answer. Hiding them once `shown` was true meant «Ensenya-me-la» silently marked the step
          failed: the only way to say «ja la sé» was never to look. */}
      {tool === 'note' || !drill ? (
        <button onClick={next} style={{ ...btn('primary'), marginTop: 20 }}>Continua</button>
      ) : selfMarked ? (
        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <button onClick={() => markAndNext(false)} style={{ ...btn('ghost'), flex: 1 }}>Encara no</button>
          <button onClick={() => markAndNext(true)} style={{ ...btn('primary'), flex: 1 }}>Ja la sé</button>
        </div>
      ) : shown ? (
        <button onClick={next} style={{ ...btn('primary'), marginTop: 20 }}>
          {i + 1 >= steps.length ? 'Acaba' : 'Següent'}
        </button>
      ) : (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, marginTop: 20, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <FaLightbulb size={11} /> Respon per continuar
        </p>
      )}
    </div>
  );
}

const card: React.CSSProperties = { padding: 16, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' };

function btn(kind: 'primary' | 'ghost'): React.CSSProperties {
  return kind === 'primary'
    ? { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 50, padding: '0 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 15, cursor: 'pointer', fontFamily: 'inherit' }
    : { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 50, padding: '0 18px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 800, fontSize: 15, cursor: 'pointer', fontFamily: 'inherit' };
}
