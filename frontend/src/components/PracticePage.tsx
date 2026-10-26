import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaListUl, FaPlay, FaPlus, FaVideo, FaUser, FaTag, FaPen, FaTrash } from 'react-icons/fa';
import { api, type PracticeCollections } from '../api';
import { getMediaUrl, hasIdentity } from '../config';
import { toast } from '../toast';

// Pràctica: the library offered as short pronunciation sessions, four ways — by recording day
// (one of our speakers' sessions), by subject, by grammar unit, and the hand-made lists (the old
// tests). Every entry opens a session (PracticeSession) of up to 10 sentences.

const MONTHS = ['gen.', 'febr.', 'març', 'abr.', 'maig', 'juny', 'jul.', 'ag.', 'set.', 'oct.', 'nov.', 'des.'];
function dayLabel(day: string): string {
  const [y, m, d] = day.split('-').map(Number);
  return `${d} ${MONTHS[(m || 1) - 1]} ${y}`;
}

type Done = Record<string, { right: number; total: number; at: string }>;
const DONE_KEY = 'practice_done';
export function loadDone(): Done { try { return JSON.parse(localStorage.getItem(DONE_KEY) || '{}'); } catch { return {}; } }
export function saveDone(key: string, right: number, total: number) {
  try { localStorage.setItem(DONE_KEY, JSON.stringify({ ...loadDone(), [key]: { right, total, at: new Date().toISOString() } })); } catch { /* private mode */ }
}

const cardStyle: React.CSSProperties = { textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4, padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', color: 'var(--text)', fontFamily: 'inherit' };
const h2Style: React.CSSProperties = { margin: '0 0 8px', fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' };

export default function PracticePage() {
  const navigate = useNavigate();
  // A practice starts empty and opens in the workbench: you put the sentences in there, in the
  // order you want, and every step can ask for something different (ADR 0002).
  const [making, setMaking] = useState(false);
  const newPractice = async () => {
    // A name first. A practice belongs to whoever made it, and one made without a name belonged
    // to nobody: the editor opened, everything you put in it came back 403 on saving, and it
    // could not even be thrown away. Asking here costs a click; the other way cost the work.
    if (!hasIdentity()) {
      toast.error('Per fer-te una pràctica et cal un nom: fes-te’n un al perfil i torna-hi.');
      navigate('/profile');
      return;
    }
    setMaking(true);
    try {
      const made = await api.createPractice('Pràctica nova');
      navigate(`/tests/${made.id}/editor`);
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut crear'); }
    finally { setMaking(false); }
  };
  const [col, setCol] = useState<PracticeCollections | null>(null);
  // Throwing a practice away asks twice, in the button itself: a browser dialog stops the whole
  // page and hides WHICH one you are about to lose.
  // La graella ensenyava dotze pràctiques i amagava la resta sense dir-ho: les que tenies de
  // més senzillament no existien.
  const PER_PAGE = 12;
  const [showing, setShowing] = useState(PER_PAGE);
  const [confirming, setConfirming] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const removePractice = async (id: number, title: string) => {
    if (confirming !== id) { setConfirming(id); window.setTimeout(() => setConfirming((c) => (c === id ? null : c)), 4000); return; }
    setConfirming(null); setDeleting(id);
    try {
      await api.deletePractice(id);
      setCol((c) => (c ? { ...c, lists: c.lists.filter((x) => x.id !== id) } : c));
      toast.success(`«${title}» llençada`);
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut esborrar'); }
    finally { setDeleting(null); }
  };
  const [done] = useState<Done>(loadDone);
  const [allTopics, setAllTopics] = useState(false);
  const [allVideos, setAllVideos] = useState(false);
  const [allTags, setAllTags] = useState(false);
  useEffect(() => { api.practiceCollections().then(setCol).catch(() => toast.error('No s’ha pogut carregar la pràctica')); }, []);
  const topics = useMemo(() => (col ? (allTopics ? col.topics : col.topics.slice(0, 8)) : []), [col, allTopics]);
  const go = (q: string) => navigate(`/tests/sessio?${q}`);
  const grid = (q: string) => navigate(`/tests/grup?${q}`);
  // a chip with two doors: the grid (see and play the drills) and the spoken session
  const chip = (label: string, count: number, q: string, key: string) => (
    <div key={key} style={{ display: 'inline-flex', alignItems: 'stretch', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', overflow: 'hidden', background: 'var(--surface)' }}>
      <button onClick={() => grid(q)} title="Obre la llista" style={{ padding: '8px 12px', border: 'none', background: 'transparent', color: 'var(--text)', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label} <span style={{ color: 'var(--text-muted)' }}>{count}</span></button>
      <button onClick={() => go(q)} title="Fes la sessió" aria-label={`Practica ${label}`} style={{ padding: '8px 10px', border: 'none', borderLeft: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}><FaPlay size={11} /></button>
    </div>
  );
  const doneLine = (key: string) => done[key] ? `${done[key].right}/${done[key].total} bé` : null;
  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Pràctica</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: '14px', margin: '0 0 16px' }}>Sessions curtes amb les veus d’en Driss i la Halima: escolta-les, repeteix-les tu, i digues si ja te’n surts.</p>

      <button onClick={() => go('daily=1')} style={{ ...cardStyle, width: '100%', background: 'var(--brand-gradient)', color: '#fff', border: 'none', marginBottom: 20, gap: 6 }}>
        <span style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', opacity: 0.85 }}>Sessió d’avui</span>
        <span style={{ fontSize: '18px', fontWeight: 800 }}>Repàs: les frases que toca repetir avui</span>
        <span style={{ fontSize: '13px', opacity: 0.9 }}>10 frases · uns 6 minuts · <FaPlay size={11} /> cal el micròfon</span>
      </button>

      {/* Entendre quan algú ho diu és una altra cosa que llegir-ho, i fins ara no s'entrenava
          enlloc (#333). A més, és l'únic exercici que funciona amb les gravacions que tenen veu
          i cap paraula escrita, que són 644. */}
      <button onClick={() => navigate('/listen')} style={{ ...cardStyle, width: '100%', marginBottom: 20, gap: 6, textAlign: 'left' }}>
        <span style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--brand-1)' }}>Escoltar</span>
        <span style={{ fontSize: '17px', fontWeight: 800 }}>Escolta i tria què vol dir</span>
        <span style={{ fontSize: '13px', color: 'var(--text-soft)' }}>Sona una frase, no es veu el text, i tries entre quatre significats. Sense micròfon.</span>
      </button>

      {/* What you made yourself comes first: the automatic slices of the library are below. */}
      {col && (
        <section style={{ marginBottom: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <h2 style={h2Style}>Les meves llistes</h2>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button onClick={newPractice} disabled={making} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', opacity: making ? 0.6 : 1 }}>
                <FaPlus size={11} /> {making ? 'Creant…' : 'Nova pràctica'}
              </button>
              <button onClick={() => navigate('/tests/llistes')} style={{ background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 4 }}><FaListUl size={11} /> Gestiona-les</button>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 12 }}>
            {col.lists.slice(0, showing).map((t) => (
              <div key={t.id} style={{ ...cardStyle, padding: 0, overflow: 'hidden', cursor: 'default', gap: 0 }}>
                {/* the picture of its first illustrated sentence, so a practice is something you recognise */}
                <button
                  onClick={() => grid(`test_id=${t.id}&title=${encodeURIComponent(t.title)}`)}
                  title="Obre la llista"
                  style={{ border: 'none', padding: 0, cursor: 'pointer', background: t.cover ? 'var(--surface-2)' : 'var(--brand-gradient-soft)', height: 104, display: 'block', width: '100%' }}
                >
                  {t.cover
                    ? <img src={getMediaUrl(t.cover)} alt="" loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    : <span style={{ display: 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--brand-1)', opacity: 0.5 }}><FaListUl size={22} /></span>}
                </button>
                <div style={{ padding: '10px 12px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <button onClick={() => grid(`test_id=${t.id}&title=${encodeURIComponent(t.title)}`)} style={{ textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '14px', fontWeight: 700, color: 'var(--text)', padding: 0, lineHeight: 1.3 }}>{t.title}</button>
                  <span style={{ fontSize: '12px', color: 'var(--text-soft)', fontWeight: 700 }}>
                    {t.count === 0 ? 'encara buida' : `${t.count} ${t.count === 1 ? 'pas' : 'passos'}`}
                  </span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <button onClick={() => go(`test_id=${t.id}`)} disabled={t.count === 0} aria-label={`Practica ${t.title}`} title={t.count === 0 ? 'Encara no hi ha res per practicar' : 'Fes la sessió'} style={{ flex: 1, padding: '6px 10px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 12, cursor: t.count === 0 ? 'not-allowed' : 'pointer', fontFamily: 'inherit', opacity: t.count === 0 ? 0.45 : 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}><FaPlay size={10} /> Fes-la</button>
                    <button onClick={() => navigate(`/tests/${t.id}/editor`)} aria-label={`Edita ${t.title}`} title="Obre el taller" style={{ padding: '6px 10px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 5 }}><FaPen size={10} /> Edita</button>
                    <button
                      onClick={() => removePractice(t.id, t.title)}
                      disabled={deleting === t.id}
                      aria-label={confirming === t.id ? `Confirma esborrar ${t.title}` : `Esborra ${t.title}`}
                      title={confirming === t.id ? 'Prem un altre cop per llençar-la' : 'Llença la pràctica'}
                      style={{ padding: '6px 9px', borderRadius: 'var(--r-pill)', border: `1px solid ${confirming === t.id ? 'var(--rose, #b3261e)' : 'var(--border)'}`, background: confirming === t.id ? 'var(--rose-soft, #fdecea)' : 'var(--surface)', color: confirming === t.id ? 'var(--rose, #b3261e)' : 'var(--text-muted)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}
                    >
                      {deleting === t.id ? '…' : confirming === t.id ? 'Segur?' : <FaTrash size={10} />}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {col.lists.length > showing && (
            <button
              onClick={() => setShowing((n) => n + PER_PAGE)}
              style={{ marginTop: 12, padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 800, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', width: '100%' }}
            >
              Ensenya&apos;n més ({col.lists.length - showing} {col.lists.length - showing === 1 ? 'pràctica' : 'pràctiques'} més)
            </button>
          )}
          <div>
            {col.lists.length === 0 && (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Encara no en tens cap. «Nova pràctica» obre el taller: hi poses les frases que vulguis, en l’ordre que vulguis, i cada pas pot demanar una cosa diferent.
              </div>
            )}
          </div>
        </section>
      )}

      {col && col.days.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per dia de gravació</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
            {col.days.map((d) => {
              const key = `day:${d.day}:${d.speaker}`;
              return (
                <button key={key} onClick={() => grid(`day=${d.day}&speaker=${encodeURIComponent(d.speaker)}&title=${encodeURIComponent(`${d.speaker} · ${dayLabel(d.day)}`)}`)} style={cardStyle}>
                  <span style={{ fontSize: '12px', color: 'var(--text-soft)' }}>{dayLabel(d.day)}</span>
                  <span style={{ fontSize: '15px', fontWeight: 800 }}>{d.speaker}</span>
                  <span style={{ fontSize: '12px', color: doneLine(key) ? 'var(--emerald)' : 'var(--text-soft)' }}>{d.count} frases{doneLine(key) ? ` · ${doneLine(key)}` : ''}</span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {col && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per tema</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {topics.map((t) => chip(t.label, t.count, `topic=${t.slug}&title=${encodeURIComponent(t.label)}`, t.slug))}
            {col.topics.length > 8 && <button onClick={() => setAllTopics((v) => !v)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allTopics ? 'Menys temes' : 'Tots els temes'}</button>}
          </div>
        </section>
      )}

      {col && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}>Per unitat de gramàtica</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {col.units.filter((u) => u.count > 0).map((u, i) => (
              <div key={u.slug} style={{ ...cardStyle, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', cursor: 'default' }}>
                <button onClick={() => grid(`unit=${u.slug}&title=${encodeURIComponent(u.title)}`)} style={{ flex: 1, textAlign: 'left', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '14px', fontWeight: 700, color: 'var(--text)', padding: 0 }}><span style={{ color: 'var(--text-muted)', marginRight: 8 }}>{i + 1}</span>{u.title}</button>
                <span style={{ fontSize: '12px', color: done[`unit:${u.slug}`] ? 'var(--emerald)' : 'var(--text-soft)', fontWeight: 700, whiteSpace: 'nowrap' }}>{done[`unit:${u.slug}`] ? `${done[`unit:${u.slug}`].right}/${done[`unit:${u.slug}`].total} bé` : `${u.count} frases`}</span>
                <button onClick={() => go(`unit=${u.slug}`)} aria-label={`Practica ${u.title}`} title="Fes la sessió" style={{ marginLeft: 10, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--brand-1)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaPlay size={11} /></button>
              </div>
            ))}
          </div>
        </section>
      )}

      {col && col.videos.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaVideo size={11} /> Per vídeo</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(allVideos ? col.videos : col.videos.slice(0, 10)).map((v) => chip(v.title, v.count, `video=${encodeURIComponent(v.title)}&title=${encodeURIComponent(v.title)}`, v.title))}
            {col.videos.length > 10 && <button onClick={() => setAllVideos((x) => !x)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 14, fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allVideos ? 'Menys vídeos' : `Tots els vídeos (${col.videos.length})`}</button>}
          </div>
        </section>
      )}

      {col && col.people.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaUser size={11} /> Per persona</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {col.people.map((p) => chip(p.name, p.count, `person=${encodeURIComponent(p.name)}&title=${encodeURIComponent(p.name)}`, p.name))}
          </div>
        </section>
      )}

      {col && col.tags.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={h2Style}><FaTag size={11} /> Per etiqueta</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(allTags ? col.tags : col.tags.slice(0, 12)).map((t) => chip(t.tag, t.count, `tag=${encodeURIComponent(t.tag)}&title=${encodeURIComponent(t.tag)}`, t.tag))}
            {col.tags.length > 12 && <button onClick={() => setAllTags((x) => !x)} style={{ padding: '9px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 14, fontWeight: 700, cursor: 'pointer', color: 'var(--brand-1)', fontFamily: 'inherit' }}>{allTags ? 'Menys etiquetes' : `Totes les etiquetes (${col.tags.length})`}</button>}
          </div>
        </section>
      )}

      {!col && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
    </div>
  );
}
