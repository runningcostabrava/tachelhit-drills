import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaArrowDown, FaArrowUp, FaMicrophone, FaPlay, FaPlus, FaSave, FaTrash } from 'react-icons/fa';
import { api, type PracticeList, type PracticeStep } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import RecordAudioModal from './RecordAudioModal';
import type { Drill } from '../types';

// The practice workbench (issue #199, ADR 0002). A practice is an ordered sequence of steps, each
// with its own tool — so the library on the left, the sequence on the right, and on every step
// the things you actually want there: hear it, see that it has no voice, record it, change what
// it asks of the learner.

const TOOLS: { kind: PracticeStep['kind']; label: string; needsDrill: boolean }[] = [
  { kind: 'listen_pick', label: 'escolta i tria', needsDrill: true },
  { kind: 'write_heard', label: 'escriu el que sents', needsDrill: true },
  { kind: 'say_it', label: 'digues-ho i compara', needsDrill: true },
  { kind: 'look_say', label: 'mira i digues-ho', needsDrill: true },
  { kind: 'fill_gap', label: 'omple el buit', needsDrill: true },
  { kind: 'word_by_word', label: 'paraula per paraula', needsDrill: true },
  { kind: 'script_swap', label: 'tifinag o llatí', needsDrill: true },
  { kind: 'pick_spelling', label: 'quina és la bona', needsDrill: true },
  { kind: 'note', label: 'nota que ensenya', needsDrill: false },
];

export default function PracticeEditor() {
  const { testId } = useParams<{ testId: string }>();
  const id = Number(testId);
  const navigate = useNavigate();
  const [practice, setPractice] = useState<PracticeList | null>(null);
  const [steps, setSteps] = useState<PracticeStep[]>([]);
  const [drills, setDrills] = useState<Record<number, Drill>>({});   // the sentences the steps use
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Drill[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [recording, setRecording] = useState<Drill | null>(null);

  const remember = useCallback((list: Drill[]) => {
    setDrills((d) => ({ ...d, ...Object.fromEntries(list.map((x) => [x.id, x])) }));
  }, []);

  useEffect(() => {
    if (!id) return;
    api.practices().then((all) => setPractice(all.find((p) => p.id === id) || null)).catch(() => {});
    api.practiceSteps(id).then(async (r) => {
      setSteps(r.steps);
      const ids = Array.from(new Set(r.steps.map((s) => s.drill_id).filter(Boolean))) as number[];
      if (ids.length) {
        const got = await api.drillsByIds(ids).catch(() => [] as Drill[]);
        remember(got);
      }
    }).catch(() => toast.error('No s’han pogut llegir els passos'));
  }, [id, remember]);

  const search = async () => {
    if (q.trim().length < 2) { setHits(null); return; }
    try { const got = await api.searchDrills(q.trim()); remember(got); setHits(got); }
    catch { toast.error('No s’ha pogut cercar'); }
  };

  const add = (drill: Drill) => {
    remember([drill]);
    setSteps((s) => [...s, { kind: drill.audio_url ? 'listen_pick' : 'fill_gap', drill_id: drill.id }]);
    setDirty(true);
  };
  const addNote = () => { setSteps((s) => [...s, { kind: 'note', payload: { text: '' } }]); setDirty(true); };
  const move = (i: number, by: number) => {
    setSteps((s) => {
      const j = i + by;
      if (j < 0 || j >= s.length) return s;
      const copy = [...s]; [copy[i], copy[j]] = [copy[j], copy[i]]; return copy;
    });
    setDirty(true);
  };
  const update = (i: number, patch: Partial<PracticeStep>) => {
    setSteps((s) => s.map((x, k) => (k === i ? { ...x, ...patch } : x)));
    setDirty(true);
  };
  const remove = (i: number) => { setSteps((s) => s.filter((_, k) => k !== i)); setDirty(true); };

  const save = async () => {
    setBusy(true);
    try {
      const clean = steps.map(({ kind, drill_id, payload }) => ({ kind, drill_id, payload }));
      const r = await api.savePracticeSteps(id, clean);
      setSteps(r.steps); setDirty(false);
      toast.success(`Desada: ${r.steps.length} passos`);
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut desar'); }
    finally { setBusy(false); }
  };

  // What the person needs to know before handing this to anybody: how many sentences have no voice
  const voiceless = useMemo(
    () => steps.filter((s) => s.drill_id && !drills[s.drill_id]?.audio_url).length,
    [steps, drills],
  );

  if (!id) return null;
  return (
    <div style={{ padding: '18px 16px 40px', maxWidth: 1100, margin: '0 auto' }}>
      <button onClick={() => navigate('/tests')} style={back}>← Pràctiques</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, margin: '6px 0 2px' }}>
        {practice?.title || 'Pràctica'}
      </h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13, margin: '0 0 14px' }}>
        {steps.length} passos{voiceless > 0 ? ` · ${voiceless} sense veu` : ''}
        {dirty ? ' · hi ha canvis sense desar' : ''}
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <button onClick={save} disabled={busy || !dirty} style={{ ...primary, opacity: busy || !dirty ? 0.5 : 1 }}>
          <FaSave /> {busy ? 'Desant…' : 'Desa la pràctica'}
        </button>
        <button onClick={addNote} style={secondary}><FaPlus /> Afegeix una nota</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 18 }}>
        {/* the sequence */}
        <section>
          <h2 style={h2}>Els passos</h2>
          {steps.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Encara no n’hi ha cap. Busca una frase aquí sota i afegeix-la, o comença amb una nota.
            </p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map((s, i) => {
              const drill = s.drill_id ? drills[s.drill_id] : undefined;
              return (
                <div key={`${s.id ?? 'new'}-${i}`} style={card}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 800, fontSize: 12, minWidth: 22 }}>{i + 1}</span>
                    <select value={s.kind} onChange={(e) => update(i, { kind: e.target.value as PracticeStep['kind'] })} style={select}>
                      {TOOLS.map((t) => <option key={t.kind} value={t.kind}>{t.label}</option>)}
                    </select>
                    <div style={{ flex: 1, minWidth: 160 }}>
                      {s.kind === 'note' ? (
                        <input value={s.payload?.text || ''} onChange={(e) => update(i, { payload: { text: e.target.value } })}
                               placeholder="què vols explicar aquí" style={input} />
                      ) : drill ? (
                        <>
                          <div style={{ fontWeight: 700, fontSize: 15 }}>{drill.text_tachelhit}</div>
                          <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{drill.text_catalan}</div>
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>frase #{s.drill_id}</span>
                      )}
                    </div>
                    {drill?.audio_url && (
                      <button onClick={() => new Audio(getMediaUrl(drill.audio_url!)).play().catch(() => {})}
                              title="Escolta" style={icon}><FaPlay size={11} /></button>
                    )}
                    {drill && !drill.audio_url && (
                      <button onClick={() => setRecording(drill)} title="Grava-la ara" style={{ ...icon, color: 'var(--rose)' }}>
                        <FaMicrophone size={12} />
                      </button>
                    )}
                    <button onClick={() => move(i, -1)} title="Amunt" style={icon}><FaArrowUp size={11} /></button>
                    <button onClick={() => move(i, 1)} title="Avall" style={icon}><FaArrowDown size={11} /></button>
                    <button onClick={() => remove(i)} title="Treu-lo" style={{ ...icon, color: 'var(--rose)' }}><FaTrash size={11} /></button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* the library */}
        <section>
          <h2 style={h2}>Afegeix frases</h2>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
                   placeholder="busca al català, a l’amazic o a l’etiqueta" style={{ ...input, flex: 1 }} />
            <button onClick={search} style={secondary}>Busca</button>
          </div>
          {hits && hits.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Cap frase amb això.</p>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(hits || []).map((d) => (
              <div key={d.id} style={{ ...card, display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{d.text_tachelhit}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-soft)' }}>
                    {d.text_catalan}{d.audio_url ? '' : ' · sense veu'}
                  </div>
                </div>
                <button onClick={() => add(d)} style={secondary}><FaPlus size={11} /> Afegeix</button>
              </div>
            ))}
          </div>
        </section>
      </div>

      {recording && (
        <RecordAudioModal drill={recording} onClose={() => setRecording(null)}
                          onSaved={() => { setRecording(null); toast.success('Gravada. Gràcies per la teva veu.'); }} />
      )}
    </div>
  );
}

const h2: React.CSSProperties = { fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px' };
const card: React.CSSProperties = { padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' };
const input: React.CSSProperties = { padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: 14, width: '100%' };
const select: React.CSSProperties = { ...input, width: 'auto', minWidth: 150, fontWeight: 700 };
const primary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const secondary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const icon: React.CSSProperties = { width: 30, height: 30, flexShrink: 0, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' };
const back: React.CSSProperties = { padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
