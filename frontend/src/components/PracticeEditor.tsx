import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  FaArrowDown, FaArrowUp, FaCheck, FaClone, FaEye, FaGripVertical, FaImage, FaMagic,
  FaDownload, FaFileAlt, FaMicrophone, FaPaperPlane, FaPen, FaPlay, FaPlus, FaPrint,
  FaRobot, FaTrash, FaVideo,
} from 'react-icons/fa';
import { api, type PracticeCollections, type PracticeList, type PracticeStep } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import MobileDrillCreator from './MobileDrillCreator';
import RecordAudioModal from './RecordAudioModal';
import type { Drill } from '../types';

// The practice workshop (issues #188 + #199, ADR 0002).
//
// A practice is an ordered sequence of steps, each with its own tool. Making one used to mean:
// type a word, search, add one sentence, press an arrow, press an arrow again, remember to save.
// Now the library comes to you — by grammar unit, by subject, by speaker, by recording day, by
// tag — you tick the ones you want and they go in together; the sequence is dragged into shape;
// and it saves itself.
//
// Two things it refuses to let you do quietly: build a practice out of sentences with no Amazigh
// text (that is how a group of nine empty «text» sentences came to exist), and ask a learner to
// listen to a sentence that has no voice. Neither is blocked — both are said out loud.

const TOOLS: { kind: PracticeStep['kind']; label: string; needsDrill: boolean; needsVoice: boolean }[] = [
  { kind: 'listen_pick', label: 'escolta i tria', needsDrill: true, needsVoice: true },
  { kind: 'write_heard', label: 'escriu el que sents', needsDrill: true, needsVoice: true },
  { kind: 'say_it', label: 'digues-ho i compara', needsDrill: true, needsVoice: true },
  { kind: 'look_say', label: 'mira i digues-ho', needsDrill: true, needsVoice: false },
  { kind: 'fill_gap', label: 'omple el buit', needsDrill: true, needsVoice: false },
  { kind: 'word_by_word', label: 'paraula per paraula', needsDrill: true, needsVoice: false },
  { kind: 'script_swap', label: 'tifinag o llatí', needsDrill: true, needsVoice: false },
  { kind: 'pick_spelling', label: 'quina és la bona', needsDrill: true, needsVoice: false },
  { kind: 'note', label: 'nota que ensenya', needsDrill: false, needsVoice: false },
];
const toolOf = (k: PracticeStep['kind']) => TOOLS.find((t) => t.kind === k);

// Where sentences come from. Everything but «cerca» is a collection the server already knows how
// to slice, so the workshop asks for it instead of making the person type a word and hope.
type SourceKind = 'cerca' | 'unit' | 'topic' | 'person' | 'day' | 'tag' | 'video';
const SOURCES: { kind: SourceKind; label: string }[] = [
  { kind: 'cerca', label: 'Cerca' },
  { kind: 'unit', label: 'Unitat' },
  { kind: 'topic', label: 'Tema' },
  { kind: 'person', label: 'Qui parla' },
  { kind: 'day', label: 'Dia' },
  { kind: 'tag', label: 'Etiqueta' },
  { kind: 'video', label: 'Vídeo' },
];

// A sentence is only usable if somebody has written what it says, in both languages.
const usable = (d?: Drill) => !!d && !!(d.text_tachelhit || '').trim() && !!(d.text_catalan || '').trim();
const hasVoice = (d?: Drill) => !!d && !!((d.audio_url || '').trim() || (d.audio_tts_shi_url || '').trim());
// Half-made sentences are never OFFERED. One with no voice, or with no words written down, is
// work waiting to happen (Veus, the editor) -- not something to put in front of a learner. The
// ones already in a practice still show, with their warning: hiding those would hide the problem.
const complete = (d: Drill) => usable(d) && hasVoice(d);

// Simplest first. Looking for «compra» should bring «compra pa» before a sentence that happens to
// contain the word halfway through a paragraph: fewer words wins, then fewer letters.
const simplicity = (d: Drill) => {
  const t = (d.text_tachelhit || '').trim();
  return [t.split(/\s+/).filter(Boolean).length, t.length];
};
const simplestFirst = (a: Drill, b: Drill) => {
  const [aw, ac] = simplicity(a), [bw, bc] = simplicity(b);
  return aw - bw || ac - bc;
};

export default function PracticeEditor() {
  const { testId } = useParams<{ testId: string }>();
  const id = Number(testId);
  const navigate = useNavigate();
  const [practice, setPractice] = useState<PracticeList | null>(null);
  const [title, setTitle] = useState('');
  const [steps, setSteps] = useState<PracticeStep[]>([]);
  const [drills, setDrills] = useState<Record<number, Drill>>({});
  const [collections, setCollections] = useState<PracticeCollections | null>(null);
  const [source, setSource] = useState<SourceKind>('cerca');
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Drill[] | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [loadingHits, setLoadingHits] = useState(false);
  const [hidden, setHidden] = useState(0);   // how many were left out for being half-made
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [view, setView] = useState<'edit' | 'preview' | 'document'>('edit');
  const preview = view === 'preview';
  const [about, setAbout] = useState('');
  const [recording, setRecording] = useState<Drill | null>(null);
  const [makingDrill, setMakingDrill] = useState(false);
  const [illustrating, setIllustrating] = useState<number | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  // The copilot, with its hands in this practice
  const [ask, setAsk] = useState('');
  const [talking, setTalking] = useState(false);
  const [chat, setChat] = useState<{ role: 'user' | 'model'; text: string }[]>([]);
  const firstLoad = useRef(true);

  const remember = useCallback((list: Drill[]) => {
    setDrills((d) => ({ ...d, ...Object.fromEntries(list.map((x) => [x.id, x])) }));
  }, []);

  useEffect(() => {
    if (!id) return;
    api.practices().then((all) => {
      const p = all.find((x) => x.id === id) || null;
      setPractice(p); setTitle(p?.title || ''); setAbout(p?.description || '');
    }).catch(() => {});
    api.practiceCollections().then(setCollections).catch(() => {});
    api.practiceSteps(id).then(async (r) => {
      setSteps(r.steps);
      const ids = Array.from(new Set(r.steps.map((s) => s.drill_id).filter(Boolean))) as number[];
      if (ids.length) remember(await api.drillsByIds(ids).catch(() => [] as Drill[]));
    }).catch(() => toast.error('No s’han pogut llegir els passos'));
  }, [id, remember]);

  // ---- saving itself ----------------------------------------------------------------
  const save = useCallback(async (next: PracticeStep[]) => {
    setSaving(true);
    try {
      const clean = next.map(({ kind, drill_id, payload }) => ({ kind, drill_id, payload }));
      const r = await api.savePracticeSteps(id, clean);
      setSteps(r.steps); setDirty(false);
      setSavedAt(new Date().toLocaleTimeString('ca-ES', { hour: '2-digit', minute: '2-digit' }));
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut desar'); }
    finally { setSaving(false); }
  }, [id]);

  useEffect(() => {
    if (firstLoad.current) { firstLoad.current = false; return; }
    if (!dirty) return;
    const t = window.setTimeout(() => { save(steps); }, 1200);
    return () => window.clearTimeout(t);
  }, [steps, dirty, save]);

  // leaving with work in the air should cost a confirmation, not the work
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const change = (next: PracticeStep[]) => { setSteps(next); setDirty(true); };

  // ---- the library ------------------------------------------------------------------
  const loadFrom = async (query: string) => {
    setLoadingHits(true); setPicked(new Set());
    try {
      const r = await api.practiceSession(`${query}&limit=120`);
      const good = r.drills.filter(complete).sort(simplestFirst);
      remember(good); setHits(good); setHidden(r.drills.length - good.length);
    } catch { toast.error('No s’han pogut portar les frases'); setHits([]); setHidden(0); }
    finally { setLoadingHits(false); }
  };
  const search = async () => {
    if (q.trim().length < 2) { setHits(null); return; }
    setLoadingHits(true); setPicked(new Set());
    try {
      const got = await api.searchDrills(q.trim(), 120);
      const good = got.filter(complete).sort(simplestFirst);
      remember(good); setHits(good); setHidden(got.length - good.length);
    } catch { toast.error('No s’ha pogut cercar'); }
    finally { setLoadingHits(false); }
  };

  const defaultKind = (d: Drill): PracticeStep['kind'] => (hasVoice(d) ? 'listen_pick' : 'fill_gap');
  // (anything the workshop offers has a voice; a voiceless one can only arrive from an old practice)
  const addDrills = (list: Drill[]) => {
    if (!list.length) return;
    remember(list);
    change([...steps, ...list.map((d) => ({ kind: defaultKind(d), drill_id: d.id }))]);
    setPicked(new Set());
    toast.success(list.length === 1 ? 'Afegida' : `${list.length} frases afegides`);
  };
  const addNote = () => change([...steps, { kind: 'note', payload: { heading: '', text: '' } }]);

  // A sentence that does not exist yet. The same sheet as everywhere else -- write the two texts,
  // let the AI translate one into the other, record it, attach media -- and when it comes back
  // with an id it goes straight into the sequence, so you never lose your place.
  const drillWasMade = async (drillId?: number) => {
    setMakingDrill(false);
    if (!drillId) { toast.success('Desada. Busca-la aquí sota per afegir-la.'); return; }
    const got = await api.drillsByIds([drillId]).catch(() => [] as Drill[]);
    if (!got.length) { toast.error('S’ha creat, però no s’ha pogut llegir'); return; }
    remember(got);
    change([...steps, { kind: defaultKind(got[0]), drill_id: got[0].id }]);
    toast.success('Frase nova afegida al final');
  };

  // Gemini draws the meaning of the Catalan sentence, in the deck's own style (backend/illustrate.py)
  const illustrate = async (d: Drill) => {
    setIllustrating(d.id);
    try {
      await api.illustrateDrill(d.id);
      const got = await api.drillsByIds([d.id]).catch(() => [] as Drill[]);
      remember(got);
      toast.success('Imatge feta');
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut fer la imatge'); }
    finally { setIllustrating(null); }
  };

  // ---- the sequence -----------------------------------------------------------------
  const move = (i: number, by: number) => {
    const j = i + by;
    if (j < 0 || j >= steps.length) return;
    const copy = [...steps]; [copy[i], copy[j]] = [copy[j], copy[i]]; change(copy);
  };
  const dropOn = (to: number) => {
    if (dragging === null || dragging === to) { setDragging(null); return; }
    const copy = [...steps];
    const [moved] = copy.splice(dragging, 1);
    copy.splice(to, 0, moved);
    change(copy); setDragging(null);
  };
  const update = (i: number, patch: Partial<PracticeStep>) => change(steps.map((x, k) => (k === i ? { ...x, ...patch } : x)));
  const duplicate = (i: number) => { const copy = [...steps]; copy.splice(i + 1, 0, { ...steps[i], id: undefined }); change(copy); };
  const remove = (i: number) => change(steps.filter((_, k) => k !== i));

  // The copilot may rewrite the sequence underneath us, so the steps are read back after each turn.
  const reloadSteps = async () => {
    const r = await api.practiceSteps(id).catch(() => null);
    if (!r) return;
    setSteps(r.steps); setDirty(false);
    const ids = Array.from(new Set(r.steps.map((x) => x.drill_id).filter(Boolean))) as number[];
    if (ids.length) remember(await api.drillsByIds(ids).catch(() => [] as Drill[]));
  };

  const askTheCopilot = async (text?: string) => {
    const message = (text ?? ask).trim();
    if (!message || talking) return;
    setAsk(''); setTalking(true);
    setChat((c) => [...c, { role: 'user', text: message }]);
    try {
      const r = await api.aiAgent(message, [], chat.slice(-8), id);
      setChat((c) => [...c, { role: 'model', text: r.answer || 'Fet.' }]);
      if ((r.actions || []).some((a) => a.name === 'build_practice')) await reloadSteps();
    } catch (e: any) {
      setChat((c) => [...c, { role: 'model', text: e?.message || 'No he pogut fer-ho.' }]);
    } finally { setTalking(false); }
  };

  const rename = async () => {
    const name = title.trim();
    if (!practice || !name || name === practice.title) return;
    try { const p = await api.updatePractice(id, { title: name }); setPractice(p); toast.success('Nom canviat'); }
    catch (e: any) { toast.error(e?.message || 'No s’ha pogut canviar el nom'); setTitle(practice.title); }
  };
  const saveAbout = async () => {
    if (!practice || about === (practice.description || '')) return;
    try { const p = await api.updatePractice(id, { description: about }); setPractice(p); }
    catch (e: any) { toast.error(e?.message || 'No s’ha pogut desar'); setAbout(practice.description || ''); }
  };

  // The practice as a text somebody can keep: the same thing the document view shows.
  const asMarkdown = () => {
    const out: string[] = [`# ${title || 'Pràctica'}`, ''];
    if (about.trim()) out.push(about.trim(), '');
    steps.forEach((s2, i) => {
      if (s2.kind === 'note') {
        if (s2.payload?.heading) out.push(`## ${s2.payload.heading}`, '');
        if (s2.payload?.text) out.push(s2.payload.text, '');
        return;
      }
      const d = s2.drill_id ? drills[s2.drill_id] : undefined;
      out.push(`**${i + 1}. ${toolOf(s2.kind)?.label}**`, '');
      if (d) {
        out.push(`> ${d.text_tachelhit || ''}`, `> ${d.text_catalan || ''}`, '');
        if (d.speaker || d.author) out.push(`*Ho diu ${d.speaker || d.author}.*`, '');
      }
    });
    out.push('', `_${steps.length} passos · tamazight-drills_`);
    return out.join('\n');
  };
  const download = () => {
    const blob = new Blob([asMarkdown()], { type: 'text/markdown;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${(title || 'practica').replace(/[^\p{L}\p{N}]+/gu, '-').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  // ---- what is wrong with this practice ---------------------------------------------
  const problems = useMemo(() => {
    const noText: number[] = [], noVoice: number[] = [], missing: number[] = [];
    steps.forEach((s, i) => {
      if (!s.drill_id) return;
      const d = drills[s.drill_id];
      if (!d) { missing.push(i); return; }
      if (!usable(d)) noText.push(i);
      else if (toolOf(s.kind)?.needsVoice && !hasVoice(d)) noVoice.push(i);
    });
    return { noText, noVoice, missing };
  }, [steps, drills]);

  if (!id) return null;
  const sourceList = () => {
    if (!collections) return null;
    const chip = (label: string, count: number, query: string, key: string) => (
      <button key={key} onClick={() => loadFrom(query)} style={pill}>
        {label} <span style={{ color: 'var(--text-muted)' }}>{count}</span>
      </button>
    );
    if (source === 'unit') return collections.units.filter((u) => u.count).map((u) => chip(u.title, u.count, `unit=${u.slug}`, u.slug));
    if (source === 'topic') return collections.topics.map((t) => chip(t.label, t.count, `topic=${t.slug}`, t.slug));
    if (source === 'person') return collections.people.map((p) => chip(p.name, p.count, `person=${encodeURIComponent(p.name)}`, p.name));
    if (source === 'day') return collections.days.map((d) => chip(`${d.speaker} · ${d.day}`, d.count, `day=${d.day}&speaker=${encodeURIComponent(d.speaker)}`, `${d.day}${d.speaker}`));
    if (source === 'tag') return collections.tags.map((t) => chip(t.tag, t.count, `tag=${encodeURIComponent(t.tag)}`, t.tag));
    if (source === 'video') return collections.videos.map((v) => chip(v.title, v.count, `video=${encodeURIComponent(v.title)}`, v.title));
    return null;
  };

  return (
    <div style={{ padding: '18px 16px 60px', maxWidth: 1180, margin: '0 auto' }}>
      <button onClick={() => navigate('/tests')} style={back}>← Pràctiques</button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', margin: '6px 0 4px' }}>
        <input
          value={title} onChange={(e) => setTitle(e.target.value)} onBlur={rename}
          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
          placeholder="Com es diu aquesta pràctica"
          aria-label="Nom de la pràctica"
          style={{ flex: 1, minWidth: 220, fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, padding: '4px 8px', border: '1px solid transparent', borderRadius: 'var(--r-md)', background: 'transparent', color: 'var(--text)' }}
          onFocus={(e) => { e.target.style.border = '1px solid var(--border)'; e.target.style.background = 'var(--surface)'; }}
        />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: saving ? 'var(--text-muted)' : dirty ? 'var(--saffron-dark, #7A4A12)' : 'var(--emerald)' }}>
          {saving ? 'Desant…' : dirty ? 'canvis sense desar' : savedAt ? <><FaCheck size={10} /> desat a les {savedAt}</> : 'desat'}
        </span>
      </div>
      <p style={{ color: 'var(--text-soft)', fontSize: 13, margin: '0 0 12px' }}>
        {steps.length} {steps.length === 1 ? 'pas' : 'passos'} · es desa sol
      </p>

      {(problems.noText.length > 0 || problems.noVoice.length > 0) && (
        <div style={{ padding: '10px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', marginBottom: 14, fontSize: 13.5, lineHeight: 1.5 }}>
          {problems.noText.length > 0 && (
            <div><strong>{problems.noText.length} {problems.noText.length === 1 ? 'frase no té text amazic' : 'frases no tenen text amazic'}</strong> (passos {problems.noText.map((i) => i + 1).join(', ')}). Qui aprengui no hi veurà res a llegir.</div>
          )}
          {problems.noVoice.length > 0 && (
            <div>{problems.noVoice.length} {problems.noVoice.length === 1 ? 'demana escoltar una frase sense veu' : 'demanen escoltar frases sense veu'} (passos {problems.noVoice.map((i) => i + 1).join(', ')}). Grava-la, o tria una altra eina.</div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <button onClick={() => setMakingDrill(true)} style={primary}><FaPlus /> Crea una frase nova</button>
        <button onClick={addNote} style={secondary}><FaPlus /> Afegeix una nota</button>
        <button onClick={() => window.open('/video-creator', '_blank')} style={secondary}
                title="Captura: porta un vídeo de YouTube o d'on sigui, talla'l i fes-ne frases">
          <FaVideo /> Porta-les d’un vídeo
        </button>
        <div style={{ display: 'inline-flex', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', overflow: 'hidden' }}>
          {([['edit', 'Edita', <FaPen key="e" size={11} />], ['preview', 'Mira-ho', <FaEye key="p" size={11} />], ['document', 'Document', <FaFileAlt key="d" size={11} />]] as const).map(([v, label, ico]) => (
            <button key={v} onClick={() => setView(v as typeof view)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 700, fontSize: 13, background: view === v ? 'var(--brand-1)' : 'var(--surface)', color: view === v ? '#fff' : 'var(--text)' }}>
              {ico} {label}
            </button>
          ))}
        </div>
      </div>

      {/* The copilot, with its hands in this practice */}
      {view !== 'document' && <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface)', padding: '12px 14px', marginBottom: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <FaRobot style={{ color: 'var(--brand-1)' }} />
          <strong style={{ fontSize: 14 }}>Digues-li què vols i t’ho munta</strong>
        </div>
        {chat.length > 0 && (
          <div style={{ maxHeight: 220, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
            {chat.map((m, k) => (
              <div key={k} style={{
                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%',
                padding: '8px 12px', borderRadius: 'var(--r-lg)', fontSize: 13.5, lineHeight: 1.5,
                background: m.role === 'user' ? 'var(--brand-gradient-soft)' : 'var(--surface-2)',
              }}>{m.text}</div>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={ask} onChange={(e) => setAsk(e.target.value)}
                 onKeyDown={(e) => { if (e.key === 'Enter') askTheCopilot(); }}
                 placeholder="p. ex. «munta’n una dels possessius amb 8 frases, de la més fàcil a la més difícil»"
                 disabled={talking} style={{ ...input, flex: 1 }} />
          <button onClick={() => askTheCopilot()} disabled={talking || !ask.trim()} style={{ ...primary, opacity: talking || !ask.trim() ? 0.5 : 1 }}>
            <FaPaperPlane size={12} /> {talking ? 'Pensant…' : 'Envia'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          {[
            'Munta-la tu: tria el tema que vulguis i fes 8 passos variats',
            'Afegeix-hi 5 frases més, més curtes que les que hi ha',
            'Escriu una nota al principi que digui què s’hi aprèn',
            'Canvia les eines perquè no es repeteixin tant',
          ].map((t) => (
            <button key={t} onClick={() => askTheCopilot(t)} disabled={talking} style={tiny}>{t}</button>
          ))}
        </div>
        <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: '8px 0 0', lineHeight: 1.45 }}>
          Només pot fer servir frases senceres de la biblioteca, i només pot tocar les pràctiques teves.
        </p>
      </div>}

      {view === 'document' ? (
        <article className="practice-document" style={{ maxWidth: 720, margin: '0 auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '28px 30px 36px' }}>
          <div className="no-print" style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginBottom: 14 }}>
            <button onClick={() => window.print()} style={secondary}><FaPrint size={12} /> Imprimeix o desa en PDF</button>
            <button onClick={download} style={secondary}><FaDownload size={12} /> Baixa’l en text</button>
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, margin: '0 0 6px' }}>{title || 'Pràctica'}</h1>
          <textarea className="no-print" value={about} onChange={(e) => setAbout(e.target.value)} onBlur={saveAbout}
                    placeholder="Una línia que digui de què va i per a qui és (surt al document)"
                    rows={2} style={{ ...input, resize: 'vertical', marginBottom: 18, color: 'var(--text-soft)' }} />
          {about.trim() && <p className="only-print" style={{ color: 'var(--text-soft)', fontSize: 15, margin: '0 0 18px' }}>{about}</p>}

          {steps.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Encara no hi ha res a llegir.</p>}
          {steps.map((s2, i) => {
            const d = s2.drill_id ? drills[s2.drill_id] : undefined;
            if (s2.kind === 'note') {
              return (
                <section key={`doc-${i}`} style={{ margin: '0 0 20px' }}>
                  {s2.payload?.heading && <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 19, margin: '0 0 6px' }}>{s2.payload.heading}</h2>}
                  {s2.payload?.text && <p style={{ margin: 0, lineHeight: 1.6, fontSize: 15 }}>{s2.payload.text}</p>}
                  {s2.payload?.image_url && <img src={getMediaUrl(s2.payload.image_url)} alt="" style={{ width: '100%', borderRadius: 'var(--r-md)', marginTop: 10 }} />}
                </section>
              );
            }
            return (
              <section key={`doc-${i}`} style={{ margin: '0 0 18px', paddingLeft: 14, borderLeft: '3px solid var(--border)' }}>
                <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 4 }}>
                  {i + 1} · {toolOf(s2.kind)?.label}
                </div>
                {d ? (
                  <>
                    <div style={{ fontSize: 19, fontWeight: 800, lineHeight: 1.3 }}>{d.text_tachelhit}</div>
                    <div style={{ fontSize: 15, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                    {(d.speaker || d.author) && <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 2 }}>Ho diu {d.speaker || d.author}.</div>}
                  </>
                ) : <em style={{ color: 'var(--text-muted)' }}>frase #{s2.drill_id}</em>}
              </section>
            );
          })}
          <p style={{ marginTop: 26, fontSize: 12, color: 'var(--text-muted)' }}>{steps.length} passos · tamazight-drills</p>
        </article>
      ) : (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(330px, 1fr))', gap: 20, alignItems: 'start' }}>
        {/* ---------- the sequence ---------- */}
        <section>
          <h2 style={h2}>Els passos</h2>
          {steps.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.5 }}>
              Encara no n’hi ha cap. Tria d’on vols les frases aquí al costat —per unitat, per tema,
              per qui parla— marca les que vulguis i afegeix-les totes de cop. O comença amb una nota.
            </p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map((s, i) => {
              const drill = s.drill_id ? drills[s.drill_id] : undefined;
              const tool = toolOf(s.kind);
              const badText = !!s.drill_id && !!drill && !usable(drill);
              const badVoice = !!drill && !!tool?.needsVoice && !hasVoice(drill);
              if (preview) {
                return (
                  <div key={`p-${i}`} style={{ ...card, borderLeft: '3px solid var(--brand-1)' }}>
                    <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 4 }}>
                      {i + 1} · {tool?.label}
                    </div>
                    {s.kind === 'note' ? (
                      <>
                        {s.payload?.heading && <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 2 }}>{s.payload.heading}</div>}
                        <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-soft)' }}>{s.payload?.text || <em>nota buida</em>}</div>
                      </>
                    ) : drill ? (
                      <>
                        <div style={{ fontSize: 17, fontWeight: 800 }}>
                          {s.kind === 'listen_pick' || s.kind === 'write_heard' ? '🔊 …' : drill.text_tachelhit}
                        </div>
                        <div style={{ fontSize: 13.5, color: 'var(--text-soft)' }}>
                          {s.kind === 'write_heard' ? 'escriu el que sents' : drill.text_catalan}
                        </div>
                      </>
                    ) : <em style={{ fontSize: 13, color: 'var(--text-muted)' }}>frase #{s.drill_id}</em>}
                  </div>
                );
              }
              return (
                <div
                  key={`${s.id ?? 'new'}-${i}`}
                  draggable onDragStart={() => setDragging(i)} onDragOver={(e) => e.preventDefault()}
                  onDrop={() => dropOn(i)} onDragEnd={() => setDragging(null)}
                  style={{
                    ...card,
                    opacity: dragging === i ? 0.4 : 1,
                    borderColor: badText ? 'var(--rose)' : badVoice ? 'var(--saffron)' : 'var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span title="Arrossega per moure'l" style={{ cursor: 'grab', color: 'var(--text-muted)', display: 'inline-flex' }}><FaGripVertical size={12} /></span>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 800, fontSize: 12, minWidth: 18 }}>{i + 1}</span>
                    <select value={s.kind} onChange={(e) => update(i, { kind: e.target.value as PracticeStep['kind'] })} style={select}>
                      {TOOLS.filter((t) => (s.drill_id ? t.needsDrill : !t.needsDrill)).map((t) => (
                        <option key={t.kind} value={t.kind}>{t.label}</option>
                      ))}
                    </select>
                    <div style={{ flex: 1, minWidth: 170 }}>
                      {s.kind === 'note' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <input value={s.payload?.heading || ''} onChange={(e) => update(i, { payload: { ...s.payload, heading: e.target.value } })}
                                 placeholder="títol (opcional)" style={{ ...input, fontWeight: 800 }} />
                          <textarea value={s.payload?.text || ''} onChange={(e) => update(i, { payload: { ...s.payload, text: e.target.value } })}
                                    placeholder="què vols explicar aquí" rows={2} style={{ ...input, resize: 'vertical', lineHeight: 1.45 }} />
                          {s.payload?.image_url ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <img src={getMediaUrl(s.payload.image_url)} alt="" style={{ width: 54, height: 36, objectFit: 'cover', borderRadius: 'var(--r-sm)' }} />
                              <button onClick={() => update(i, { payload: { ...s.payload, image_url: '' } })} style={{ ...tiny, color: 'var(--rose)' }}>treu la imatge</button>
                            </div>
                          ) : (
                            <input value={s.payload?.image_url || ''} onChange={(e) => update(i, { payload: { ...s.payload, image_url: e.target.value } })}
                                   placeholder="enllaç d’una imatge (opcional)" style={{ ...input, fontSize: 12.5 }} />
                          )}
                        </div>
                      ) : drill ? (
                        <>
                          <div style={{ fontWeight: 700, fontSize: 15 }}>{drill.text_tachelhit || <span style={{ color: 'var(--rose)' }}>sense text amazic</span>}</div>
                          <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{drill.text_catalan}</div>
                          {badVoice && <div style={{ fontSize: 12, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>aquesta eina demana escoltar, i no té veu</div>}
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>frase #{s.drill_id}</span>
                      )}
                    </div>
                    {drill && hasVoice(drill) && (
                      <button onClick={() => new Audio(getMediaUrl(drill.audio_url || drill.audio_tts_shi_url || '')).play().catch(() => {})}
                              title="Escolta" style={icon}><FaPlay size={11} /></button>
                    )}
                    {drill && !hasVoice(drill) && (
                      <button onClick={() => setRecording(drill)} title="Grava-la ara" style={{ ...icon, color: 'var(--rose)' }}><FaMicrophone size={12} /></button>
                    )}
                    {drill && !(drill.image_url || '').trim() && (drill.text_catalan || '').trim() && (
                      <button onClick={() => illustrate(drill)} disabled={illustrating === drill.id}
                              title="Fes-ne una imatge amb la IA" style={{ ...icon, color: 'var(--sky)' }}>
                        {illustrating === drill.id ? '…' : <FaMagic size={11} />}
                      </button>
                    )}
                    <button onClick={() => duplicate(i)} title="Duplica’l" style={icon}><FaClone size={11} /></button>
                    <button onClick={() => move(i, -1)} title="Amunt" style={icon}><FaArrowUp size={11} /></button>
                    <button onClick={() => move(i, 1)} title="Avall" style={icon}><FaArrowDown size={11} /></button>
                    <button onClick={() => remove(i)} title="Treu-lo" style={{ ...icon, color: 'var(--rose)' }}><FaTrash size={11} /></button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ---------- the library ---------- */}
        <section>
          <h2 style={h2}>D’on surten les frases</h2>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
            {SOURCES.map((x) => (
              <button key={x.kind} onClick={() => { setSource(x.kind); setHits(null); setPicked(new Set()); }}
                      style={{ ...pill, background: source === x.kind ? 'var(--brand-1)' : 'var(--surface)', color: source === x.kind ? '#fff' : 'var(--text)', borderColor: source === x.kind ? 'var(--brand-1)' : 'var(--border)' }}>
                {x.label}
              </button>
            ))}
          </div>

          {source === 'cerca' ? (
            <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
              <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
                     placeholder="busca al català, a l’amazic o a l’etiqueta" style={{ ...input, flex: 1 }} />
              <button onClick={search} style={secondary}>Busca</button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10, maxHeight: 190, overflowY: 'auto' }}>
              {sourceList() || <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Carregant…</span>}
            </div>
          )}

          {loadingHits && <p style={{ fontSize: 13.5, color: 'var(--text-muted)' }}>Portant les frases…</p>}
          {hits && hits.length === 0 && !loadingHits && (
            <p style={{ color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.5 }}>
              Aquí no hi ha cap frase sencera{hidden > 0 ? `: n’hi havia ${hidden}, però els falta la veu o les paraules escrites` : ''}.
            </p>
          )}
          {hits && hits.length > 0 && hidden > 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 12.5, margin: '0 0 8px', lineHeight: 1.45 }}>
              {hidden} {hidden === 1 ? 'frase no surt' : 'frases no surten'} perquè els falta la veu o les paraules escrites.
              Les trobaràs a Veus i a Drills; aquí no s’ofereixen a mitges.
            </p>
          )}

          {hits && hits.length > 0 && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
                <button onClick={() => setPicked(picked.size === hits.length ? new Set() : new Set(hits.map((d) => d.id)))} style={tiny}>
                  {picked.size === hits.length ? 'Desmarca-les totes' : `Marca-les totes (${hits.length})`}
                </button>
                <button onClick={() => addDrills(hits.filter((d) => picked.has(d.id)))} disabled={!picked.size}
                        style={{ ...primary, opacity: picked.size ? 1 : 0.45 }}>
                  <FaPlus /> Afegeix {picked.size || ''} {picked.size === 1 ? 'frase' : 'frases'}
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 520, overflowY: 'auto' }}>
                {hits.map((d) => {
                  const already = steps.some((s) => s.drill_id === d.id);
                  return (
                    <label key={d.id} style={{ ...card, display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', opacity: already ? 0.55 : 1 }}>
                      <input type="checkbox" checked={picked.has(d.id)} onChange={(e) => {
                        const n = new Set(picked); if (e.target.checked) n.add(d.id); else n.delete(d.id); setPicked(n);
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 14 }}>{d.text_tachelhit}</div>
                        <div style={{ fontSize: 12.5, color: 'var(--text-soft)' }}>
                          {d.text_catalan}
                          {d.image_url && <FaImage size={10} style={{ marginLeft: 6, color: 'var(--text-muted)' }} />}
                          {already && <span style={{ color: 'var(--text-muted)' }}> · ja hi és</span>}
                        </div>
                      </div>
                      <button onClick={(e) => { e.preventDefault(); addDrills([d]); }} style={tiny}><FaPlus size={10} /> afegeix</button>
                    </label>
                  );
                })}
              </div>
            </>
          )}
        </section>
      </div>

      )}

      {makingDrill && (
        <MobileDrillCreator onClose={() => setMakingDrill(false)} onDrillCreated={drillWasMade} />
      )}

      {recording && (
        <RecordAudioModal drill={recording} onClose={() => setRecording(null)}
                          onSaved={async () => {
                            const got = await api.drillsByIds([recording.id]).catch(() => [] as Drill[]);
                            remember(got); setRecording(null);
                            toast.success('Gravada. Gràcies per la teva veu.');
                          }} />
      )}
    </div>
  );
}

const h2: React.CSSProperties = { fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px' };
const card: React.CSSProperties = { padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' };
const input: React.CSSProperties = { padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: 14, width: '100%', boxSizing: 'border-box' };
const select: React.CSSProperties = { ...input, width: 'auto', minWidth: 148, fontWeight: 700 };
const primary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const secondary: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
const pill: React.CSSProperties = { ...secondary, padding: '6px 12px', fontSize: 12.5 };
const tiny: React.CSSProperties = { padding: '5px 10px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 5 };
const icon: React.CSSProperties = { width: 30, height: 30, flexShrink: 0, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' };
const back: React.CSSProperties = { padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' };
