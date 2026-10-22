import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaArrowDown, FaArrowUp, FaClone, FaEye, FaRobot, FaSave, FaTrash } from 'react-icons/fa';
import { api, type GrammarLesson, type LessonStep } from '../api';
import { toast } from '../toast';

// Editing a grammar lesson (#187).
//
// Lessons are written by Gemini and kept in the database; when the format version moves, or the
// unit's sentences change, they are written again. That is right for a lesson nobody has touched
// and wrong for one somebody has — so saving here marks the lesson as written by hand, and from
// then on the writer leaves it alone until it is handed back on purpose.
//
// The sentences a step shows are NOT edited here: they come from the library and carry their
// speaker, their gloss and their «why this sentence is here». This edits the teaching around
// them — what the unit says, in what order, and what it asks.

type Kind = LessonStep['type'];
const KINDS: { kind: Kind; label: string; help: string }[] = [
  { kind: 'explain', label: 'Explicació', help: 'El gruix: un títol, el que s’hi ensenya, i les frases que ho mostren.' },
  { kind: 'tip', label: 'Consell', help: 'Una cosa curta que val la pena recordar.' },
  { kind: 'dialect', label: 'Nota de varietat', help: 'Com canvia això segons on es parli.' },
  { kind: 'quiz', label: 'Pregunta', help: 'Una pregunta amb respostes; marca quina és la bona.' },
  { kind: 'pattern', label: 'Taula', help: 'Files i columnes: conjugacions, possessius, números…' },
  { kind: 'end', label: 'Final', help: 'Tanca la unitat. Hi ha de ser, i va l’últim.' },
];
const helpOf = (k: Kind) => KINDS.find((x) => x.kind === k)?.help || '';

export default function LessonEditor() {
  const { slug = '' } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [intro, setIntro] = useState('');
  const [steps, setSteps] = useState<LessonStep[]>([]);
  const [byHand, setByHand] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.title = `Edita la lliçó · ${slug}`;
    api.grammarLesson(slug).then((r) => {
      const l: GrammarLesson = r.lesson;
      setIntro(l.intro || '');
      setSteps((l.steps || []) as LessonStep[]);
      setByHand(!!r.hand_written);
      setLoaded(true);
      if (l.writing) toast.info?.('S’està escrivint ara mateix: desa quan hagi acabat.');
    }).catch((e: any) => { toast.error(e?.message || 'No s’ha pogut llegir la lliçó'); setLoaded(true); });
  }, [slug]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const change = (next: LessonStep[]) => { setSteps(next); setDirty(true); };
  const patch = (i: number, p: Record<string, unknown>) => change(steps.map((s, k) => (k === i ? { ...s, ...p } as LessonStep : s)));
  const move = (i: number, by: number) => {
    const j = i + by;
    if (j < 0 || j >= steps.length) return;
    const copy = [...steps]; [copy[i], copy[j]] = [copy[j], copy[i]]; change(copy);
  };
  const duplicate = (i: number) => { const copy = [...steps]; copy.splice(i + 1, 0, JSON.parse(JSON.stringify(steps[i]))); change(copy); };
  const remove = (i: number) => change(steps.filter((_, k) => k !== i));
  const add = (kind: Kind) => {
    const blank: Record<Kind, LessonStep> = {
      explain: { type: 'explain', title: '', text: '', examples: [] },
      tip: { type: 'tip', text: '' },
      dialect: { type: 'dialect', text: '' },
      quiz: { type: 'quiz', kind: 'meaning', question: '', options: ['', ''], answer: 0, example: null as never },
      pattern: { type: 'pattern', title: '', rows: [['', '']] },
      end: { type: 'end' },
    };
    // the end card closes the unit, so anything new goes before it
    const endAt = steps.findIndex((s) => s.type === 'end');
    const copy = [...steps];
    copy.splice(endAt === -1 ? copy.length : endAt, 0, blank[kind]);
    change(copy);
  };

  // What would stop a learner: an empty card, or a question with no right answer.
  const problems = useMemo(() => {
    const out: string[] = [];
    steps.forEach((s, i) => {
      const n = i + 1;
      if (s.type === 'explain' && !(s.title || '').trim() && !(s.text || '').trim()) out.push(`${n}: l’explicació és buida`);
      if ((s.type === 'tip' || s.type === 'dialect') && !(s.text || '').trim()) out.push(`${n}: la nota és buida`);
      if (s.type === 'quiz') {
        if (!(s.question || '').trim()) out.push(`${n}: la pregunta no diu res`);
        const opts = (s.options || []).filter((o) => (o || '').trim());
        if (opts.length < 2) out.push(`${n}: la pregunta necessita almenys dues respostes`);
        if (typeof s.answer !== 'number' || s.answer < 0 || s.answer >= (s.options || []).length) out.push(`${n}: no has marcat quina és la bona`);
      }
    });
    if (!steps.some((s) => s.type === 'end')) out.push('falta el pas final que tanca la unitat');
    return out;
  }, [steps]);

  const save = async () => {
    if (problems.length) { toast.error('Hi ha coses per acabar abans de desar'); return; }
    setSaving(true);
    try {
      await api.putGrammarLesson(slug, { intro, steps });
      setByHand(true); setDirty(false);
      toast.success('Desada. A partir d’ara la màquina no la tocarà.');
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut desar'); }
    finally { setSaving(false); }
  };
  const release = async () => {
    if (!window.confirm('La tornes a la màquina? La pròxima vegada que s’obri, l’escriurà de nou i es perdrà el que hi has escrit.')) return;
    try { await api.releaseGrammarLesson(slug); setByHand(false); toast.success('Tornada a la màquina'); }
    catch (e: any) { toast.error(e?.message || 'No s’ha pogut fer'); }
  };

  if (!loaded) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant la lliçó…</div>;

  return (
    <div style={{ padding: '18px 16px 60px', maxWidth: 820, margin: '0 auto' }}>
      <button onClick={() => navigate(`/grammar/${slug}`)} style={back}>← La unitat</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: '6px 0 2px' }}>Edita la lliçó</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13, margin: '0 0 14px', lineHeight: 1.5 }}>
        {byHand
          ? 'Aquesta lliçó l’ha escrita una persona: la màquina no la tocarà.'
          : 'Ara mateix l’escriu la màquina, i la torna a escriure quan canvia la unitat. En desar-la, deixarà de fer-ho.'}
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <button onClick={save} disabled={saving || !dirty} style={{ ...primary, opacity: saving || !dirty ? 0.5 : 1 }}>
          <FaSave /> {saving ? 'Desant…' : 'Desa la lliçó'}
        </button>
        <button onClick={() => navigate(`/grammar/${slug}`)} style={secondary}><FaEye /> Mira la unitat</button>
        {byHand && <button onClick={release} style={{ ...secondary, color: 'var(--text-soft)' }}><FaRobot /> Torna-la a la màquina</button>}
      </div>

      {problems.length > 0 && (
        <div style={{ padding: '10px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', marginBottom: 14, fontSize: 13.5, lineHeight: 1.6 }}>
          <strong>Per acabar:</strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>{problems.map((p) => <li key={p}>{p}</li>)}</ul>
        </div>
      )}

      <label style={lbl}>Com comença la unitat</label>
      <textarea value={intro} onChange={(e) => { setIntro(e.target.value); setDirty(true); }} rows={3}
                placeholder="La primera cosa que llegeix qui obre la unitat" style={{ ...input, marginBottom: 18 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {steps.map((s, i) => (
          <div key={i} style={card}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--text-muted)', fontWeight: 800, fontSize: 12, minWidth: 18 }}>{i + 1}</span>
              <strong style={{ fontSize: 13 }}>{KINDS.find((k) => k.kind === s.type)?.label || s.type}</strong>
              <span style={{ flex: 1, fontSize: 12, color: 'var(--text-muted)' }}>{helpOf(s.type)}</span>
              <button onClick={() => duplicate(i)} title="Duplica’l" style={icon}><FaClone size={11} /></button>
              <button onClick={() => move(i, -1)} title="Amunt" style={icon}><FaArrowUp size={11} /></button>
              <button onClick={() => move(i, 1)} title="Avall" style={icon}><FaArrowDown size={11} /></button>
              <button onClick={() => remove(i)} title="Treu-lo" style={{ ...icon, color: 'var(--rose)' }}><FaTrash size={11} /></button>
            </div>

            {s.type === 'explain' && (
              <>
                <input value={s.title || ''} onChange={(e) => patch(i, { title: e.target.value })} placeholder="títol" style={{ ...input, fontWeight: 800, marginBottom: 6 }} />
                <textarea value={s.text || ''} onChange={(e) => patch(i, { text: e.target.value })} rows={4} placeholder="què s’hi ensenya" style={{ ...input, resize: 'vertical' }} />
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0' }}>
                  {(s.examples || []).length} {(s.examples || []).length === 1 ? 'frase' : 'frases'} de la biblioteca.
                  Les frases no s’editen aquí: porten qui les diu, la seva glossa i el «per què és aquí».
                </p>
              </>
            )}

            {(s.type === 'tip' || s.type === 'dialect') && (
              <textarea value={s.text || ''} onChange={(e) => patch(i, { text: e.target.value })} rows={3}
                        placeholder={s.type === 'tip' ? 'el consell' : 'com canvia segons la varietat'} style={{ ...input, resize: 'vertical' }} />
            )}

            {s.type === 'quiz' && (
              <>
                <input value={s.question || ''} onChange={(e) => patch(i, { question: e.target.value })} placeholder="la pregunta" style={{ ...input, marginBottom: 8 }} />
                {(s.options || []).map((o, j) => (
                  <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <input type="radio" name={`answer-${i}`} checked={s.answer === j} onChange={() => patch(i, { answer: j })} title="aquesta és la bona" />
                    <input value={o} onChange={(e) => patch(i, { options: (s.options || []).map((x, k) => (k === j ? e.target.value : x)) })}
                           placeholder={`resposta ${j + 1}`} style={{ ...input, flex: 1 }} />
                    {(s.options || []).length > 2 && (
                      <button onClick={() => patch(i, {
                        options: (s.options || []).filter((_, k) => k !== j),
                        answer: s.answer > j ? s.answer - 1 : Math.min(s.answer, (s.options || []).length - 2),
                      })} style={{ ...icon, color: 'var(--rose)' }}><FaTrash size={10} /></button>
                    )}
                  </div>
                ))}
                <button onClick={() => patch(i, { options: [...(s.options || []), ''] })} style={tiny}>+ una resposta més</button>
              </>
            )}

            {s.type === 'pattern' && (
              <>
                <input value={s.title || ''} onChange={(e) => patch(i, { title: e.target.value })} placeholder="títol de la taula" style={{ ...input, fontWeight: 800, marginBottom: 8 }} />
                {(s.rows || []).map((row, r) => (
                  <div key={r} style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    {row.map((cell, c) => (
                      <input key={c} value={cell} onChange={(e) => patch(i, {
                        rows: (s.rows || []).map((rr, k) => (k === r ? rr.map((cc, kk) => (kk === c ? e.target.value : cc)) : rr)),
                      })} placeholder={r === 0 ? 'capçalera' : 'cel·la'} style={{ ...input, flex: 1 }} />
                    ))}
                    <button onClick={() => patch(i, { rows: (s.rows || []).filter((_, k) => k !== r) })} style={{ ...icon, color: 'var(--rose)' }}><FaTrash size={10} /></button>
                  </div>
                ))}
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={() => patch(i, { rows: [...(s.rows || []), new Array((s.rows?.[0] || ['', '']).length).fill('')] })} style={tiny}>+ fila</button>
                  <button onClick={() => patch(i, { rows: (s.rows || []).map((rr) => [...rr, '']) })} style={tiny}>+ columna</button>
                </div>
              </>
            )}

            {s.type === 'end' && <p style={{ margin: 0, fontSize: 13, color: 'var(--text-soft)' }}>Aquí s’acaba la unitat.</p>}
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
        {KINDS.filter((k) => k.kind !== 'end' || !steps.some((s) => s.type === 'end')).map((k) => (
          <button key={k.kind} onClick={() => add(k.kind)} style={secondary}>+ {k.label}</button>
        ))}
      </div>
    </div>
  );
}

const card: React.CSSProperties = { padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' };
const input: React.CSSProperties = { padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: 14, width: '100%', boxSizing: 'border-box' };
const lbl: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 };
const primary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const secondary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const tiny: React.CSSProperties = { padding: '5px 10px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' };
const icon: React.CSSProperties = { width: 28, height: 28, flexShrink: 0, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' };
const back: React.CSSProperties = { padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
