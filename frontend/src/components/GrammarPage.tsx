import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import { FaBullseye, FaCheck, FaChevronLeft, FaChevronRight, FaLightbulb, FaMapMarkerAlt, FaMicrophone, FaPen, FaRedo, FaTimes, FaVolumeUp } from 'react-icons/fa';
import { api, type GrammarUnit, type GrammarUnitPage, type GrammarWishUnit, type LessonExample, type LessonProposal, type LessonStep } from '../api';
import { API_BASE, getMediaUrl } from '../config';
import RecordAudioModal from './RecordAudioModal';
import AiAssistant from './AiAssistant';
import { GlossWords } from './WordGloss';
import type { Drill } from '../types';

// The grammar course: the library organised as a sequence of grammar units (backend/grammar.py).
// Course view: the units in order, with how many drills illustrate each. Unit view: the lesson as
// cards the learner steps through (explanations with the library's own examples -picture and voice-,
// a pattern table, quick checks, a tip, a dialect note), then a button that turns the unit into a test.

const LEVEL_LABEL: Record<number, string> = { 1: 'Nivell 1 · bàsic', 2: 'Nivell 2 · mitjà', 3: 'Nivell 3 · avançat' };

// Course progress lives in this browser: which units were finished and the quick-check score.
type Progress = Record<string, { right: number; total: number; at: string }>;
// Two ways to read a unit: «Targetes» (one card at a time, the quick checks gate the next card) and
// «Document» (the whole lesson on one page, every example with its play button, the quick checks
// answerable in place). Remembered on the device.
type ViewMode = 'cards' | 'document';
const VIEW_KEY = 'grammar_view';
function loadView(): ViewMode { try { return localStorage.getItem(VIEW_KEY) === 'document' ? 'document' : 'cards'; } catch { return 'cards'; } }
const PROGRESS_KEY = 'grammar_progress';
function loadProgress(): Progress { try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}'); } catch { return {}; } }
function saveProgress(slug: string, right: number, total: number) {
  try { localStorage.setItem(PROGRESS_KEY, JSON.stringify({ ...loadProgress(), [slug]: { right, total, at: new Date().toISOString() } })); } catch { /* private mode */ }
}

export default function GrammarPage({ deep = false }: { deep?: boolean } = {}) {
  const { slug } = useParams<{ slug?: string }>();
  if (slug === 'gravacions') return <WishlistView />;
  return slug ? <UnitView key={`${slug}:${deep}`} slug={slug} deep={deep} /> : <CourseView />;
}

function CourseView() {
  const navigate = useNavigate();
  const [units, setUnits] = useState<GrammarUnit[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [status, setStatus] = useState<{ running: boolean; done: number; pending: number } | null>(null);
  const [progress] = useState<Progress>(loadProgress);
  useEffect(() => {
    api.grammarUnits().then((r) => { setUnits(r.units); setCounts(r.counts); setStatus(r.status); }).catch(() => toast.error('No s’ha pogut carregar el curs'));
  }, []);
  const levels = [1, 2, 3];
  const done = units.filter((u) => progress[u.slug]).length;
  const nextUnit = units.find((u) => !progress[u.slug] && counts[u.slug]);
  return (
    <div style={{ padding: '20px 16px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Gramàtica</h1>
      <div style={{ color: 'var(--text-soft)', fontSize: '14px', marginBottom: '14px' }}>
        El curs: cada unitat explica un punt de gramàtica pas a pas, amb les frases, les imatges i les veus de la biblioteca.
        {status?.running && <span> · classificant drills ({status.done} fets, {status.pending} pendents)</span>}
      </div>
      {units.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', border: '1px solid var(--border)', marginBottom: '18px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <div style={{ fontWeight: 800, color: 'var(--text)' }}>{done === 0 ? 'Comença el curs' : done >= units.length ? 'Curs acabat!' : `${done} de ${units.length} unitats fetes`}</div>
            {nextUnit && <div style={{ fontSize: '13px', color: 'var(--text-soft)' }}>Següent: {nextUnit.title}</div>}
          </div>
          {nextUnit && <button onClick={() => navigate(`/grammar/${nextUnit.slug}`)} style={{ padding: '10px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>{done ? 'Continua' : 'Comença'} <FaChevronRight /></button>}
        </div>
      )}
      <div style={{ fontSize: '13px', color: 'var(--text-soft)', margin: '-8px 0 16px' }}>
        <button onClick={() => navigate('/stories')} style={{ background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: 0, marginRight: 14, display: 'inline-flex', alignItems: 'center', gap: 6 }}>Històries i cançons</button>
        <button onClick={() => navigate('/credits')} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontWeight: 600, cursor: 'pointer', padding: 0, marginLeft: 14, fontSize: '13px' }}>Crèdits i fonts</button>
        <button onClick={() => navigate('/veus')} style={{ background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: 0, display: 'inline-flex', alignItems: 'center', gap: 6 }}><FaMicrophone size={12} /> Posa-hi veu</button>
        {' '}· demana com es diu una frase, o grava les que saps. A cada targeta del curs pots proposar un canvi.
      </div>
      {levels.map((lv) => (
        <section key={lv} style={{ marginBottom: '22px' }}>
          <h2 style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>{LEVEL_LABEL[lv]}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px' }}>
            {units.filter((u) => u.level === lv).map((u) => (
              <button key={u.slug} onClick={() => navigate(`/grammar/${u.slug}`)}
                style={{ textAlign: 'left', padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '6px', minHeight: '84px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>Unitat {units.findIndex((x) => x.slug === u.slug) + 1}{progress[u.slug] && <span style={{ color: 'var(--emerald)', display: 'inline-flex', alignItems: 'center', gap: 3 }}><FaCheck size={10} /> feta{progress[u.slug].total ? ` · ${progress[u.slug].right}/${progress[u.slug].total}` : ''}</span>}</div>
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

// ---------------- the unit: a lesson in cards ----------------

type Card = { type: 'intro' } | LessonStep;

function UnitView({ slug, deep = false }: { slug: string; deep?: boolean }) {
  const navigate = useNavigate();
  const [page, setPage] = useState<GrammarUnitPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({}); // card index -> chosen option
  const [isAdmin, setIsAdmin] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [units, setUnits] = useState<GrammarUnit[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [signedIn, setSignedIn] = useState(false);
  const [proposals, setProposals] = useState<LessonProposal[]>([]);
  const [view, setViewState] = useState<ViewMode>(loadView);
  // the copilot, opened on one example: «Explica'm» word by word, then any question about it
  const [ask, setAsk] = useState<{ id: number; label: string } | null>(null);
  const [recording, setRecording] = useState<Drill | null>(null);  // the recorder, on one sentence
  const setView = (v: ViewMode) => { setViewState(v); try { localStorage.setItem(VIEW_KEY, v); } catch { /* private mode */ } };
  const loadProposals = useCallback(() => { api.lessonProposals(slug).then(setProposals).catch(() => setProposals([])); }, [slug]);

  useEffect(() => {
    setPage(null); setError(null); setI(0); setAnswers({});
    (deep ? api.grammarDeep(slug) : api.grammarUnit(slug)).then(setPage).catch((e) => setError(e?.message || 'Error'));
    api.me().then((m) => { setIsAdmin(!!m?.is_admin); setSignedIn(!!m); if (m) loadProposals(); }).catch(() => {});
  }, [slug, deep, loadProposals]);
  // a lesson being written arrives on its own: the page never waits for it
  const writing = !!page?.lesson?.writing;
  useEffect(() => {
    if (!writing) return;
    let alive = true;
    const t = window.setInterval(() => {
      (deep ? api.grammarDeep(slug, 1).then((r) => ({ lesson: r.lesson })) : api.grammarLesson(slug)).then((r) => {
        if (!alive || r.lesson.writing) return;
        setPage((p) => (p && p.slug === slug ? { ...p, lesson: r.lesson } : p));
        setI(0); setAnswers({});
      }).catch(() => {});
    }, 8000);
    return () => { alive = false; window.clearInterval(t); };
  }, [writing, slug, deep]);
  useEffect(() => { api.grammarUnits().then((r) => { setUnits(r.units); setCounts(r.counts); }).catch(() => {}); }, []);
  const nextUnit = useMemo(() => {
    const k = units.findIndex((u) => u.slug === slug);
    return k >= 0 ? units.slice(k + 1).find((u) => counts[u.slug]) || null : null;
  }, [units, counts, slug]);

  const cards = useMemo<Card[]>(() => (page ? [{ type: 'intro' }, ...page.lesson.steps] : []), [page]);
  const card = cards[i];
  const cover = useMemo(() => {
    if (!page) return null;
    for (const s of page.lesson.steps) {
      if (s.type === 'explain') { const e = s.examples.find((x) => x.image_url); if (e) return e; }
    }
    return page.drills.find((d) => d.image_url) ? { image_url: page.drills.find((d) => d.image_url)!.image_url } : null;
  }, [page]);

  const canGoNext = !!card && (card.type !== 'quiz' || answers[i] !== undefined) && i < cards.length - 1;
  const next = useCallback(() => { if (canGoNext) setI((x) => x + 1); }, [canGoNext]);
  useEffect(() => {  // reaching the last card = unit done
    if (!card || card.type !== 'end') return;
    const quizzes = cards.map((c, k) => ({ c, k })).filter(({ c }) => c.type === 'quiz');
    saveProgress(slug, quizzes.filter(({ c, k }) => c.type === 'quiz' && answers[k] === c.answer).length, quizzes.length);
  }, [card, cards, answers, slug]);
  const prev = useCallback(() => setI((x) => Math.max(0, x - 1)), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (view !== 'cards') return;
      if (e.key === 'ArrowRight') next();
      if (e.key === 'ArrowLeft') prev();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [next, prev, view]);

  const makeTest = async () => {
    if (!page) return;
    // real sentences only: single words and the deck's conjugation lists stay out of the test
    const ids = (page.practice?.length ? page.practice : page.drills.map((d) => d.id)).slice(0, 200);
    if (!ids.length) { toast.error('Aquesta unitat encara no té frases per practicar'); return; }
    try {
      await axios.post(`${API_BASE}/tests/`, {
        title: page.title, description: `Unitat de gramàtica «${page.title}» (${ids.length} frases)`,
        question_type: 'text_input', hint_level: 'none', hint_percentage: 30, hint_tries_before_reveal: 3,
        time_limit_seconds: null, passing_score: 70, drill_ids: ids.join(','),
      });
      toast.success(`Test «${page.title}» creat amb ${ids.length} frases`);
      navigate('/tests');
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut crear el test')); }
  };
  // a speaker records the sentence where they met it; anyone else can ask for a voice
  const recordExample = useCallback((e: LessonExample) => {
    api.drill(e.id).then(setRecording).catch(() => toast.error('No s’ha pogut obrir la gravadora'));
  }, []);
  const wantVoice = useCallback((e: LessonExample) => {
    api.askForVoice(e.id).then(() => toast.success('Demanada a les nostres veus')).catch(() => toast.error('No s’ha pogut demanar'));
  }, []);
  const rewrite = async () => {
    setRewriting(true);
    try { setPage(await (deep ? api.grammarDeepRewrite(slug) : api.grammarRewrite(slug))); setI(0); setAnswers({}); toast.success('Lliçó reescrita'); }
    catch { toast.error('No s’ha pogut reescriure la lliçó'); }
    finally { setRewriting(false); }
  };

  return (
    <div style={{ padding: '16px 16px 96px', maxWidth: '640px', margin: '0 auto' }}>
      <button onClick={() => navigate('/grammar')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: '6px' }}><FaChevronLeft /> Totes les unitats</button>
      {error && <div style={{ color: 'var(--rose)' }}>{error}</div>}
      {!page && !error && <LoadingUnit />}
      {ask && <AiAssistant drillId={ask.id} drillLabel={ask.label} autoAction="explain" onClose={() => setAsk(null)} />}
      {recording && <RecordAudioModal drill={recording} onClose={() => setRecording(null)} onSaved={() => { setRecording(null); toast.success('Gravada. Gràcies per la teva veu.'); }} />}
      {page && card && (
        <div style={{ display: 'flex', gap: 6, margin: '0 0 10px' }}>
          {([['cards', 'Targetes'], ['document', 'Document']] as [ViewMode, string][]).map(([m, label]) => (
            <button key={m} onClick={() => setView(m)} style={{ padding: '6px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: view === m ? 'var(--brand-1)' : 'var(--surface)', color: view === m ? '#fff' : 'var(--text)', fontWeight: 800, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>{label}</button>
          ))}
        </div>
      )}
      {page && card && view === 'document' && (
        <div style={{ paddingBottom: 24 }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>{LEVEL_LABEL[page.level]} · {cards.length - 2} passos{deep ? ' · a fons' : ''}</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', margin: '2px 0 12px', lineHeight: 1.2 }}>{page.title}</h1>
          {cards.map((c, k) => (
            <div key={k} className="lesson-card" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '18px', marginTop: '12px', boxShadow: 'var(--shadow-sm)' }}>
              {c.type === 'intro' && <IntroCard page={page} cover={cover?.image_url || null} />}
              {c.type === 'explain' && <ExplainCard step={c} onAsk={setAsk} onRecord={recordExample} onWant={wantVoice} signedIn={signedIn} isAdmin={isAdmin} />}
              {c.type === 'pattern' && <PatternCard step={c} />}
              {c.type === 'quiz' && <QuizCard step={c} chosen={answers[k]} onChoose={(j) => setAnswers((a) => ({ ...a, [k]: j }))} active={false} />}
              {(c.type === 'tip' || c.type === 'dialect') && <NoteCard step={c} />}
              {c.type === 'end' && <EndCard page={page} answers={answers} cards={cards} onTest={makeTest} isAdmin={isAdmin} onRewrite={rewrite} rewriting={rewriting} onEdit={() => navigate(`/grammar/${slug}/editor`)} nextUnit={nextUnit} proposals={proposals} onDecided={loadProposals} deep={deep} />}
              {(c.type === 'explain' || c.type === 'tip' || c.type === 'dialect' || c.type === 'intro') && page.lesson.steps.length > 0 && <ProposeChange slug={slug} step={k - 1} current={c.type === 'intro' ? page.lesson.intro : c.text} signedIn={signedIn} onSent={loadProposals} />}
            </div>
          ))}
          <div style={{ marginTop: 14, textAlign: 'center' }}>
            <button onClick={() => { const quizzes = cards.map((c, k) => ({ c, k })).filter(({ c }) => c.type === 'quiz'); saveProgress(slug, quizzes.filter(({ c, k }) => c.type === 'quiz' && answers[k] === c.answer).length, quizzes.length); toast.success('Unitat marcada com a feta'); }} style={{ padding: '12px 20px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>He acabat aquesta unitat</button>
          </div>
        </div>
      )}
      {page && card && view === 'cards' && (
        <>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>{LEVEL_LABEL[page.level]} · {i + 1} / {cards.length}{deep ? ' · a fons' : ''}</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', margin: '2px 0 10px', lineHeight: 1.2 }}>{page.title}</h1>
          <Progress n={cards.length} i={i} answers={answers} cards={cards} />
          <div key={i} className="lesson-card" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '18px', marginTop: '12px', boxShadow: 'var(--shadow-sm)', minHeight: '240px' }}>
            {card.type === 'intro' && <IntroCard page={page} cover={cover?.image_url || null} />}
            {card.type === 'explain' && <ExplainCard step={card} onAsk={setAsk} onRecord={recordExample} onWant={wantVoice} signedIn={signedIn} isAdmin={isAdmin} />}
            {card.type === 'pattern' && <PatternCard step={card} />}
            {card.type === 'quiz' && <QuizCard step={card} chosen={answers[i]} onChoose={(k) => setAnswers((a) => ({ ...a, [i]: k }))} />}
            {(card.type === 'tip' || card.type === 'dialect') && <NoteCard step={card} />}
            {card.type === 'end' && <EndCard page={page} answers={answers} cards={cards} onTest={makeTest} isAdmin={isAdmin} onRewrite={rewrite} rewriting={rewriting} onEdit={() => navigate(`/grammar/${slug}/editor`)} nextUnit={nextUnit} proposals={proposals} onDecided={loadProposals} deep={deep} />}
        {(card.type === 'explain' || card.type === 'tip' || card.type === 'dialect' || card.type === 'intro') && page.lesson.steps.length > 0 && <ProposeChange slug={slug} step={i - 1} current={card.type === 'intro' ? page.lesson.intro : card.text} signedIn={signedIn} onSent={loadProposals} />}
          </div>
          <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, padding: '10px 16px calc(10px + env(safe-area-inset-bottom))', background: 'var(--bg)', borderTop: '1px solid var(--border)', zIndex: 5 }}>
            <div style={{ maxWidth: '640px', margin: '0 auto', display: 'flex', gap: '10px' }}>
              <button onClick={prev} disabled={i === 0} style={{ flex: 1, padding: '12px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: i === 0 ? 'var(--text-muted)' : 'var(--text)', fontWeight: 700, cursor: i === 0 ? 'default' : 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><FaChevronLeft /> Enrere</button>
              <button onClick={next} disabled={!canGoNext} style={{ flex: 2, padding: '12px', borderRadius: 'var(--r-pill)', border: 'none', background: canGoNext ? 'var(--brand-gradient)' : 'var(--surface-2)', color: canGoNext ? '#fff' : 'var(--text-muted)', fontWeight: 700, cursor: canGoNext ? 'pointer' : 'default', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                {card.type === 'quiz' && answers[i] === undefined ? 'Tria una resposta' : card.type === 'end' ? 'Final' : i === 0 ? 'Comencem' : 'Següent'} <FaChevronRight />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// The lessons are written ahead of time and cached, so a wait is almost always the server being
// busy; only a unit whose lesson was never written (or just changed) is written on open.
function LoadingUnit() {
  const [slow, setSlow] = useState(false);
  useEffect(() => { const t = window.setTimeout(() => setSlow(true), 7000); return () => window.clearTimeout(t); }, []);
  return (
    <div style={{ color: 'var(--text-muted)', padding: '24px 0' }}>
      Carregant la unitat…{slow ? ' El servidor va carregat ara mateix; si aquesta lliçó és nova s’està escrivint i pot trigar fins a un minut.' : ''}
    </div>
  );
}

function Progress({ n, i, answers, cards }: { n: number; i: number; answers: Record<number, number>; cards: Card[] }) {
  return (
    <div style={{ display: 'flex', gap: '3px' }}>
      {Array.from({ length: n }).map((_, k) => {
        const c = cards[k];
        const quizOk = c?.type === 'quiz' && answers[k] !== undefined ? answers[k] === c.answer : null;
        const bg = k > i ? 'var(--surface-2)' : quizOk === false ? 'var(--rose)' : quizOk === true ? 'var(--emerald)' : 'var(--brand-1)';
        return <div key={k} style={{ flex: 1, height: 5, borderRadius: 3, background: bg, transition: 'background var(--t-fast)' }} />;
      })}
    </div>
  );
}

function IntroCard({ page, cover }: { page: GrammarUnitPage; cover: string | null }) {
  const n = page.lesson.steps.filter((s) => s.type === 'explain').length;
  const q = page.lesson.steps.filter((s) => s.type === 'quiz').length;
  return (
    <div>
      {cover && <img src={getMediaUrl(cover)} alt="" style={{ width: '100%', maxHeight: 220, objectFit: 'cover', borderRadius: 'var(--r-lg)', marginBottom: 14, display: 'block' }} onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
      <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--brand-1)', marginBottom: 6 }}>En aquesta unitat</div>
      <p style={{ fontSize: '16px', lineHeight: 1.55, margin: '0 0 12px', color: 'var(--text)' }}>{page.lesson.intro || 'Un punt de gramàtica explicat pas a pas amb frases reals de la biblioteca.'}</p>
      <div style={{ fontSize: '13px', color: 'var(--text-soft)' }}>{n} explicacions{q ? ` · ${q} preguntes ràpides` : ''} · {page.total} frases de la biblioteca</div>
      {page.lesson.error && <div style={{ marginTop: 10, fontSize: '12px', color: 'var(--rose)' }}>La lliçó no s’ha pogut escriure ara mateix; torna-ho a provar d’aquí a una estona.</div>}
    </div>
  );
}

function ExplainCard({ step, onAsk, onRecord, onWant, signedIn, isAdmin }: { step: Extract<LessonStep, { type: 'explain' }>; onAsk?: (a: { id: number; label: string }) => void; onRecord?: (e: LessonExample) => void; onWant?: (e: LessonExample) => void; signedIn?: boolean; isAdmin?: boolean }) {
  return (
    <div>
      <h2 style={{ fontSize: '18px', margin: '0 0 8px', lineHeight: 1.25 }}>{step.title}</h2>
      <p style={{ fontSize: '16px', lineHeight: 1.55, margin: '0 0 14px', color: 'var(--text)' }}>{inline(step.text)}</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {step.examples.map((e) => <Example key={e.id} e={e} onAsk={onAsk} onRecord={onRecord} onWant={onWant} signedIn={signedIn} isAdmin={isAdmin} />)}
      </div>
    </div>
  );
}

function Example({ e, highlight, onAsk, onRecord, onWant, signedIn, isAdmin }: { e: LessonExample; highlight?: 'ok' | 'ko'; onAsk?: (a: { id: number; label: string }) => void; onRecord?: (e: LessonExample) => void; onWant?: (e: LessonExample) => void; signedIn?: boolean; isAdmin?: boolean }) {
  const play = () => { if (e.audio_url) new Audio(getMediaUrl(e.audio_url)).play().catch(() => {}); };
  const border = highlight === 'ok' ? 'var(--emerald)' : highlight === 'ko' ? 'var(--rose)' : 'var(--border)';
  // the word-by-word reading and why this sentence is in this unit: both stored, both free
  const [words, setWords] = useState(false);
  const [why, setWhy] = useState(false);
  const [wanted, setWanted] = useState(false);   // asked a speaker for a voice, just now
  // An admin corrects the sentence where they read it. The speakers' own words change only here,
  // by a person who decided to: «Smun ino» is «el meu amic», not «Amic», and only a human knows.
  const [edit, setEdit] = useState<{ shi: string; ca: string } | null>(null);
  const [suggest, setSuggest] = useState<string | null>(null);   // somebody else's way of saying it
  const [saving, setSaving] = useState(false);
  const [shown, setShown] = useState({ shi: e.shi, ca: e.ca });
  const saveEdit = async () => {
    if (!edit) return;
    setSaving(true);
    try {
      await api.editDrillText(e.id, { text_tachelhit: edit.shi.trim(), text_catalan: edit.ca.trim() });
      setShown({ shi: edit.shi.trim(), ca: edit.ca.trim() });
      setEdit(null);
      toast.success('Frase corregida');
    } catch (err: any) { toast.error(err?.message || 'No s’ha pogut desar'); }
    finally { setSaving(false); }
  };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 12px', background: 'var(--surface-2)', border: `1px solid ${border}`, borderRadius: 'var(--r-lg)', flexWrap: 'wrap' }}>
      {e.image_url && <img src={getMediaUrl(e.image_url)} alt="" style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 'var(--r-md)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 800, fontSize: '17px', color: 'var(--text)', lineHeight: 1.3 }}>{withFocus(shown.shi, e.focus)}</div>
        {e.tif && <div lang="zgh" style={{ fontFamily: 'var(--font-tifinagh)', fontSize: '15px', color: 'var(--text-muted)', lineHeight: 1.4 }}>{e.tif}</div>}
        <div style={{ fontSize: '14px', color: 'var(--text-soft)' }}>{shown.ca}</div>
        {(e.recorded || e.origin || e.region) && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 2 }}>{e.recorded ? `veu de ${e.author || 'parlant'}` : 'veu sintètica'}{e.origin || e.region ? ` · ${e.origin || e.region}` : ''}</div>}
        {((e.gloss && e.gloss.length > 0) || e.why) && (
          <div style={{ display: 'flex', gap: '10px', marginTop: 4, flexWrap: 'wrap' }}>
            {e.gloss && e.gloss.length > 0 && (
              <button onClick={() => setWords((v) => !v)} style={linkBtn}>
                {words ? 'amaga les paraules' : 'paraula per paraula'}
              </button>
            )}
            {e.why && (
              <button onClick={() => setWhy((v) => !v)} style={linkBtn}>
                {why ? 'amaga el perquè' : 'per què és aquí'}
              </button>
            )}
            {isAdmin ? (
              <button onClick={() => setEdit(edit ? null : { shi: shown.shi, ca: shown.ca })} style={{ ...linkBtn, color: 'var(--text-soft)' }}>
                {edit ? 'deixa-ho' : 'edita el drill'}
              </button>
            ) : signedIn && (
              <button onClick={() => setSuggest(suggest === null ? shown.shi : null)} style={{ ...linkBtn, color: 'var(--text-soft)' }}>
                {suggest === null ? 'suggereix un canvi' : 'deixa-ho'}
              </button>
            )}
            {!e.recorded && onWant && (
              <button onClick={() => { if (!wanted) { onWant(e); setWanted(true); } }} style={{ ...linkBtn, color: wanted ? 'var(--emerald)' : 'var(--saffron-strong)' }}>
                {wanted ? 'demanada ✓' : 'demana una veu'}
              </button>
            )}
          </div>
        )}
      </div>
      {signedIn && onRecord && <button onClick={() => onRecord(e)} title="Grava-ho amb la teva veu" aria-label="Grava-ho tu" style={{ flexShrink: 0, width: 36, height: 36, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaMicrophone size={13} /></button>}
      {onAsk && <button onClick={() => onAsk({ id: e.id, label: e.ca || e.shi })} title="Explica'm aquesta frase paraula per paraula" aria-label="Explica'm aquesta frase" style={{ flexShrink: 0, width: 36, height: 36, padding: 0, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', cursor: 'pointer', fontSize: '15px', lineHeight: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>💡</button>}
      <button onClick={play} disabled={!e.audio_url} aria-label="Escolta" style={{ flexShrink: 0, width: 40, height: 40, borderRadius: 'var(--r-pill)', border: 'none', background: e.audio_url ? (e.recorded ? 'var(--brand-1)' : 'var(--sky)') : 'var(--surface)', color: e.audio_url ? '#fff' : 'var(--text-muted)', cursor: e.audio_url ? 'pointer' : 'default', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={15} /></button>
      {words && e.gloss && <div style={{ flexBasis: '100%' }}><GlossWords words={e.gloss} size="sm" /></div>}
      {suggest !== null && (
        <div style={{ flexBasis: '100%', display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          <div style={{ fontSize: '12px', color: 'var(--text-soft)' }}>Com ho dius tu? Es desa com una segona versió d&apos;aquesta frase, amb el mateix significat.</div>
          <input value={suggest} onChange={(ev) => setSuggest(ev.target.value)} placeholder="la teva manera de dir-ho"
                 style={{ padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '15px', fontWeight: 700 }} />
          <div>
            <button onClick={async () => {
              const said = (suggest || '').trim();
              if (said.length < 2) { toast.error('Escriu com ho dius tu'); return; }
              try { await api.addVariant(e.id, said); setSuggest(null); toast.success('Desat com una altra manera de dir-ho. Gràcies!'); }
              catch (err: any) { toast.error(err?.message || 'No s’ha pogut desar'); }
            }} style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}>Desa la meva versió</button>
          </div>
        </div>
      )}
      {edit && (
        <div style={{ flexBasis: '100%', display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          <input value={edit.shi} onChange={(ev) => setEdit({ ...edit, shi: ev.target.value })} placeholder="en amazic, tal com es diu"
                 style={{ padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '15px', fontWeight: 700 }} />
          <input value={edit.ca} onChange={(ev) => setEdit({ ...edit, ca: ev.target.value })} placeholder="en català"
                 style={{ padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '14px' }} />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={saveEdit} disabled={saving || !edit.shi.trim()} style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', opacity: saving ? 0.6 : 1 }}>{saving ? 'Desant…' : 'Desa la correcció'}</button>
            {onRecord && <button onClick={() => onRecord(e)} style={{ ...linkBtn, color: 'var(--brand-1)' }}>torna a gravar-ho</button>}
          </div>
        </div>
      )}
      {why && e.why && (
        <div style={{ flexBasis: '100%', marginTop: 8, padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface)', border: '1px solid var(--border)', fontSize: '13px', lineHeight: 1.5, color: 'var(--text-soft)' }}>
          {e.why}
        </div>
      )}
    </div>
  );
}

// the two quiet links under a sentence: the words, and why the sentence is in this unit
const linkBtn = { padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontSize: '12px', fontWeight: 700, cursor: 'pointer' };

function PatternCard({ step }: { step: Extract<LessonStep, { type: 'pattern' }> }) {
  return (
    <div>
      <h2 style={{ fontSize: '18px', margin: '0 0 10px' }}>{step.title || 'Les formes'}</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '15px' }}>
        <tbody>
          {step.rows.map((r, k) => (
            <tr key={k} style={{ borderTop: k ? '1px solid var(--border)' : 'none' }}>
              <td style={{ padding: '8px 6px 8px 0', fontWeight: 800, whiteSpace: 'nowrap', color: 'var(--brand-1)' }}>{r[0]}</td>
              <td style={{ padding: '8px 6px', color: 'var(--text)' }}>{r[1]}</td>
              <td style={{ padding: '8px 0 8px 6px', color: 'var(--text-soft)', fontSize: '14px' }}>{r[2]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QuizCard({ step, chosen, onChoose, active = true }: { step: Extract<LessonStep, { type: 'quiz' }>; chosen?: number; onChoose: (k: number) => void; active?: boolean }) {
  const answered = chosen !== undefined;
  const kind = step.kind || 'meaning';
  const play = useCallback(() => { if (step.example.audio_url) new Audio(getMediaUrl(step.example.audio_url)).play().catch(() => {}); }, [step.example.audio_url]);
  // «Escolta» speaks by itself only when this is the card the learner is on. The whole lesson on
  // one page renders every card at once: without this, a unit opens with four voices at a time.
  useEffect(() => { if (active && kind === 'listen' && !answered) play(); }, [active, kind, answered, play]);
  const choose = (k: number) => {
    if (answered) return;
    onChoose(k);
    if (k === step.answer && kind !== 'listen') play();
  };
  return (
    <div>
      <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--saffron-strong)', marginBottom: 6 }}>{kind === 'listen' ? 'Escolta' : kind === 'picture' ? 'Mira' : 'Pregunta ràpida'}</div>
      <h2 style={{ fontSize: '18px', margin: '0 0 12px', lineHeight: 1.3 }}>{step.question}</h2>
      {kind === 'listen' && (
        <button onClick={play} aria-label="Torna a escoltar" style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '0 auto 14px', padding: '14px 22px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, fontSize: '15px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)' }}><FaVolumeUp size={20} /> Torna a escoltar</button>
      )}
      {kind === 'picture' && step.example.image_url && (
        <img src={getMediaUrl(step.example.image_url)} alt="" style={{ display: 'block', width: '100%', maxHeight: 240, objectFit: 'cover', borderRadius: 'var(--r-lg)', marginBottom: 14 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {step.options.map((o, k) => {
          const isAnswer = k === step.answer; const isChosen = k === chosen;
          const bg = !answered ? 'var(--surface-2)' : isAnswer ? 'var(--emerald-soft)' : isChosen ? 'var(--rose-soft)' : 'var(--surface-2)';
          const border = !answered ? 'var(--border)' : isAnswer ? 'var(--emerald)' : isChosen ? 'var(--rose)' : 'var(--border)';
          return (
            <button key={k} onClick={() => choose(k)} style={{ textAlign: 'left', padding: '12px 14px', borderRadius: 'var(--r-lg)', border: `1px solid ${border}`, background: bg, color: 'var(--text)', fontWeight: 700, fontSize: '16px', cursor: answered ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ flex: 1 }}>{o}</span>
              {answered && isAnswer && <FaCheck color="var(--emerald)" />}
              {answered && isChosen && !isAnswer && <FaTimes color="var(--rose)" />}
            </button>
          );
        })}
      </div>
      {answered && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: chosen === step.answer ? 'var(--emerald)' : 'var(--rose)', marginBottom: 8 }}>{chosen === step.answer ? 'Molt bé!' : 'No ben bé. Aquesta és la frase:'}</div>
          <Example e={step.example} highlight="ok" />
        </div>
      )}
    </div>
  );
}

function NoteCard({ step }: { step: Extract<LessonStep, { type: 'tip' | 'dialect' }> }) {
  const tip = step.type === 'tip';
  return (
    <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
      <div style={{ flexShrink: 0, width: 44, height: 44, borderRadius: 'var(--r-pill)', background: tip ? 'var(--saffron-soft)' : 'var(--sky-soft)', color: tip ? 'var(--saffron-strong)' : 'var(--sky)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
        {tip ? <FaLightbulb size={20} /> : <FaMapMarkerAlt size={20} />}
      </div>
      <div>
        <h2 style={{ fontSize: '18px', margin: '0 0 6px' }}>{tip ? 'Fixa-t’hi' : 'Per aquí ho diuen així'}</h2>
        <p style={{ fontSize: '16px', lineHeight: 1.55, margin: 0, color: 'var(--text)' }}>{inline(step.text)}</p>
      </div>
    </div>
  );
}

// «Proposa un canvi»: anyone signed in can suggest a better text for a card (or a note); an admin
// accepts it into the lesson or rejects it.
function ProposeChange({ slug, step, current, signedIn, onSent }: { slug: string; step: number; current: string; signedIn: boolean; onSent: () => void }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setOpen(false); setText(''); }, [step, slug]);
  const send = async () => {
    if (text.trim().length < 3) { toast.error('Escriu la proposta'); return; }
    setBusy(true);
    try { await api.proposeLessonChange(slug, step, text.trim()); toast.success('Proposta enviada. Un administrador la revisarà.'); setOpen(false); setText(''); onSent(); }
    catch (e: any) { toast.error(e?.message || 'No s’ha pogut enviar'); } finally { setBusy(false); }
  };
  if (!open) return <div style={{ marginTop: 10, textAlign: 'right' }}><button onClick={() => { if (!signedIn) { navigate('/profile'); return; } setOpen(true); setText(current); }} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', padding: 4 }}>Proposa un canvi en aquesta targeta</button></div>;
  return (
    <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--r-lg)', border: '1px dashed var(--border)', background: 'var(--surface-2)' }}>
      <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>La teva versió d’aquesta targeta</div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} style={{ width: '100%', boxSizing: 'border-box', padding: 10, borderRadius: 'var(--r-md)', border: '1px solid var(--border)', fontSize: 14, fontFamily: 'inherit', background: 'var(--surface)', color: 'var(--text)', lineHeight: 1.45 }} />
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
        <button onClick={() => setOpen(false)} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 }}>Cancel·la</button>
        <button onClick={send} disabled={busy} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 }}>Envia la proposta</button>
      </div>
    </div>
  );
}

function EndCard({ page, answers, cards, onTest, isAdmin, onRewrite, rewriting, onEdit, nextUnit, proposals, onDecided, deep }: { page: GrammarUnitPage; answers: Record<number, number>; cards: Card[]; onTest: () => void; isAdmin: boolean; onRewrite: () => void; rewriting: boolean; onEdit: () => void; nextUnit: GrammarUnit | null; proposals: LessonProposal[]; onDecided: () => void; deep: boolean }) {
  const decide = async (id: number, accept: boolean) => {
    try { await api.decideProposal(id, accept); toast.success(accept ? 'Canvi aplicat a la lliçó' : 'Proposta rebutjada'); onDecided(); } catch (e: any) { toast.error(e?.message || 'No s’ha pogut'); }
  };
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const quizzes = cards.map((c, k) => ({ c, k })).filter(({ c }) => c.type === 'quiz');
  const right = quizzes.filter(({ c, k }) => c.type === 'quiz' && answers[k] === c.answer).length;
  const play = (url?: string | null) => { if (url) new Audio(getMediaUrl(url)).play().catch(() => {}); };
  return (
    <div>
      <h2 style={{ fontSize: '18px', margin: '0 0 6px' }}>Unitat acabada</h2>
      {quizzes.length > 0 && <p style={{ margin: '0 0 12px', color: 'var(--text-soft)', fontSize: '15px' }}>Preguntes ràpides: {right} de {quizzes.length} encertades.</p>}
      <p style={{ margin: '0 0 14px', fontSize: '15px', lineHeight: 1.5, color: 'var(--text)' }}>Ara practica-ho: un test amb les {Math.min(page.practice?.length ?? page.drills.length, 200)} frases de la biblioteca que mostren aquest punt (només frases: ni paraules soltes ni llistes de conjugació).</p>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {nextUnit && <button onClick={() => navigate(`/grammar/${nextUnit.slug}`)} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Següent unitat: {nextUnit.title} <FaChevronRight /></button>}
        {!deep && <button onClick={() => navigate(`/grammar/${page.slug}/a-fons`)} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer' }}><FaLightbulb /> A fons</button>}
        {deep && <button onClick={() => navigate(`/grammar/${page.slug}`)} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer' }}><FaChevronLeft /> Torna a la lliçó</button>}
        {(page.practice?.length ?? page.drills.length) > 0 && <button onClick={onTest} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: nextUnit ? '1px solid var(--brand-1)' : 'none', background: nextUnit ? 'var(--surface)' : 'var(--brand-gradient)', color: nextUnit ? 'var(--brand-1)' : '#fff', fontWeight: 700, cursor: 'pointer' }}><FaBullseye /> Practica aquesta unitat</button>}
        <button onClick={() => setShowAll((v) => !v)} style={{ padding: '10px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer' }}>{showAll ? 'Amaga els exemples' : `Tots els exemples · ${page.total}`}</button>
        {isAdmin && page.lesson.study && <details style={{ width: '100%', order: 9 }}><summary style={{ cursor: 'pointer', fontSize: '13px', color: 'var(--text-soft)', fontWeight: 700 }}>Full d’estudi (del compendi, només administradors)</summary><pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: 1.5, color: 'var(--text)', fontFamily: 'var(--font-sans)', margin: '8px 0 0' }}>{page.lesson.study}</pre></details>}
        {proposals.length > 0 && (
          <div style={{ width: '100%', order: 8, padding: 12, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{isAdmin ? 'Propostes pendents de revisar' : 'Les teves propostes pendents'}</div>
            {proposals.map((p) => (
              <div key={p.id} style={{ padding: '8px 0', borderTop: '1px solid var(--border)', fontSize: 14 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{p.display_name || 'Anònim'}{p.region ? ` · ${p.region}` : ''} · targeta {p.step + 2}</div>
                <div style={{ lineHeight: 1.45, color: 'var(--text)' }}>{p.text}</div>
                {isAdmin && <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  <button onClick={() => decide(p.id, true)} style={{ padding: '6px 12px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--emerald)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', fontSize: 12 }}>Accepta</button>
                  <button onClick={() => decide(p.id, false)} style={{ padding: '6px 12px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: 12 }}>Rebutja</button>
                </div>}
              </div>
            ))}
          </div>
        )}
        {isAdmin && <button onClick={onEdit} title="Edita la lliçó a mà (administrador). En desar-la, la màquina deixa de tocar-la." style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer' }}><FaPen /> Edita la lliçó</button>}
        {isAdmin && <button onClick={onRewrite} disabled={rewriting} title="Torna a escriure la lliçó (administrador)" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontWeight: 700, cursor: rewriting ? 'default' : 'pointer' }}><FaRedo /> {rewriting ? 'Reescrivint…' : 'Reescriu la lliçó'}</button>}
      </div>
      {showAll && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: 14 }}>
          {page.drills.map((d) => (
            <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 10px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
              {d.image_url && <img src={getMediaUrl(d.image_url)} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 'var(--r-sm)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, color: 'var(--text)', fontSize: '14px' }}>{d.text_tachelhit}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-soft)' }}>{d.text_catalan}{d.region ? <span style={{ color: 'var(--text-muted)' }}> · {d.region}</span> : null}</div>
              </div>
              <button onClick={() => play(d.audio_url || d.audio_tts_shi_url)} disabled={!d.audio_url && !d.audio_tts_shi_url} aria-label="Escolta" style={{ flexShrink: 0, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : d.audio_tts_shi_url ? 'var(--sky)' : 'var(--surface)', color: d.audio_url || d.audio_tts_shi_url ? '#fff' : 'var(--text-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={12} /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// The piece of the sentence that shows the rule, marked in the speaker's own spelling.
function withFocus(shi: string, focus?: string | null) {
  if (!focus) return shi;
  const k = shi.toLowerCase().indexOf(focus.toLowerCase());
  if (k < 0) return shi;
  return <>{shi.slice(0, k)}<mark style={{ background: 'var(--saffron-soft)', color: 'var(--saffron-strong)', borderRadius: 4, padding: '0 3px' }}>{shi.slice(k, k + focus.length)}</mark>{shi.slice(k + focus.length)}</>;
}

// **bold** is the only mark-up a lesson text carries.
function inline(s: string) {
  const parts = (s || '').split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p.replace(/`/g, '')}</span>);
}

// ---------------- what our speakers could record next ----------------

// For Halima and Driss (Aït Mraw): the units where the course has few voices of theirs, with the
// sentences (from the Beni Mellal deck or elsewhere) worth saying in their own words. The microphone
// opens the usual recorder, where «Com ho dius tu?» keeps their wording when it differs.
function WishlistView() {
  const navigate = useNavigate();
  const [units, setUnits] = useState<GrammarWishUnit[] | null>(null);
  const [recording, setRecording] = useState<Drill | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    api.grammarWishlist().then((r) => setUnits(r.units)).catch(() => toast.error('No s’ha pogut carregar la llista'));
  }, [tick]);
  const play = (url?: string | null) => { if (url) new Audio(getMediaUrl(url)).play().catch(() => {}); };
  return (
    <div style={{ padding: '20px 16px', maxWidth: '900px', margin: '0 auto' }}>
      <button onClick={() => navigate('/grammar')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: '6px' }}><FaChevronLeft /> El curs</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Frases per gravar</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: '14px', margin: '0 0 16px', lineHeight: 1.5 }}>
        Per a la Halima i en Driss: les unitats del curs on encara hi ha poques veus d’Aït Mraw, amb frases que valdria la pena
        sentir dites a la vostra manera. Premeu el micròfon, i si al vostre poble es diu amb altres paraules, escriviu-les a «Com ho dius tu?».
        Les unitats amb menys veus vostres van primer.
      </p>
      {!units && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
      {units?.map((u) => (
        <section key={u.slug} style={{ marginBottom: '18px', padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
            <button onClick={() => navigate(`/grammar/${u.slug}`)} style={{ background: 'transparent', border: 'none', padding: 0, cursor: 'pointer', fontWeight: 800, color: 'var(--text)', fontSize: '15px', textAlign: 'left' }}>{u.title}</button>
            <span style={{ fontSize: '12px', fontWeight: 700, color: u.aitmraw_voiced < 5 ? 'var(--danger, #c0392b)' : u.aitmraw_voiced < 15 ? 'var(--warning, #b7791f)' : 'var(--emerald)' }}>
              {u.aitmraw_voiced} {u.aitmraw_voiced === 1 ? 'veu' : 'veus'} d’Aït Mraw · {u.total} exemples
            </span>
          </div>
          {u.wanted.length === 0 && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Cap frase pendent.</div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {u.wanted.map((d) => (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 10px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
                {d.image_url && <img src={getMediaUrl(d.image_url)} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 'var(--r-sm)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, color: 'var(--text)', fontSize: '14px' }}>{d.text_tachelhit}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-soft)' }}>{d.text_catalan}{d.region ? <span style={{ color: 'var(--text-muted)' }}> · {d.region}</span> : null}</div>
                </div>
                <button onClick={() => play(d.audio_url || d.audio_tts_shi_url)} disabled={!d.audio_url && !d.audio_tts_shi_url} aria-label="Escolta" title="Escolta com ho diuen" style={{ flexShrink: 0, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : d.audio_tts_shi_url ? 'var(--sky)' : 'var(--surface)', color: d.audio_url || d.audio_tts_shi_url ? '#fff' : 'var(--text-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={12} /></button>
                <button onClick={() => setRecording(d)} aria-label="Grava-ho tu" title="Grava-ho a la teva manera" style={{ flexShrink: 0, width: 34, height: 34, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaMicrophone size={14} /></button>
              </div>
            ))}
          </div>
        </section>
      ))}
      {recording && <RecordAudioModal drill={recording} onClose={() => setRecording(null)} onSaved={() => { setRecording(null); setTick((t) => t + 1); }} />}
    </div>
  );
}
