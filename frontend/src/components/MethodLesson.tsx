import { useEffect, useRef, useState, type ReactNode } from 'react';
import { FaPlay, FaStop, FaCommentDots, FaMicrophone, FaPen, FaCheck, FaTags, FaBookOpen, FaHandPointer } from 'react-icons/fa';
import { api, type MethodContent, type MethodExample, type MethodGloss } from '../api';
import type { Drill } from '../types';
import { getMediaUrl, hasIdentity } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import RecordAudioModal from './RecordAudioModal';
import { GlossWords } from './WordGloss';
import SentenceVariants from './SentenceVariants';

// La lliçó d'un capítol: l'explicació, el diàleg i el vocabulari.
//
// El text ve del manual d'El Mountassir, traduït i adaptat (ADR 0004), i viu a la base de dades
// perquè es pugui corregir sense desplegar res.
//
// Tres coses acompanyen cada línia, i cap no és decoració:
//
//   · la TIFINAGH a sota, petita. El capítol s'escriu en llatí perquè així és el manual i així
//     escriu qui grava, però l'escriptura de la llengua va amb la llengua.
//   · el PARAULA PER PARAULA, igual que al curs de gramàtica. Una frase que s'ensenya i no es
//     pot desmuntar és una frase que només es pot repetir. A més, cada paraula es pot escoltar:
//     l'alineació sap on es diu dins de les gravacions que ja tenim.
//   · el MICRÒFON. Un capítol no està acabat fins que les seves línies es poden escoltar, i una
//     línia del manual no és encara una frase de la biblioteca: és text dins del capítol.
//     Prémer el micròfon la converteix en una frase nostra i obre la gravadora, on qui parla hi
//     posa la seva veu, la seva manera d'escriure-ho i el seu poble.
//
// Aquest és el camí pel qual un capítol adaptat del Souss es torna una recollida de l'Atles.

type Where = { kind: 'example' | 'turn' | 'vocabulary'; index: number; section?: string };

/** La mateixa línia en tifinagh, a sota i petita: l'escriptura de la llengua va amb la llengua. */
function Tif({ t, size = 12.5 }: { t?: string | null; size?: number }) {
  if (!t) return null;
  return (
    <div lang="shi" aria-label="En tifinagh"
         style={{ fontFamily: 'var(--font-tifinagh)', fontSize: size, color: 'var(--text-muted)', opacity: 0.85, lineHeight: 1.35 }}>
      {t}
    </div>
  );
}

/** El text d'una secció: el llapis per a qui administra, i «proposa un canvi» per a tothom.
 *
 *  Una secció és una explicació, i una explicació es pot millorar: una errada, una paraula que
 *  al teu poble no es diu així, una frase que no s'entén. Qui administra ho canvia allà mateix;
 *  qui no, ho proposa i va a la mateixa cua que les propostes del curs de gramàtica.
 */
function SectionText({
  slug, index, title, text, deep, ours, canEdit, signedIn, onSave,
}: {
  slug: string; index: number;
  title: string; text?: string; deep?: string; ours?: string;
  canEdit: boolean; signedIn: boolean;
  onSave: (p: { title: string; text: string; deep: string; ours: string }) => Promise<void>;
}) {
  const [edit, setEdit] = useState<{ title: string; text: string; deep: string; ours: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [propose, setPropose] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  if (edit) {
    return (
      <div style={{ padding: '10px 0 14px' }}>
        <label style={lbl}>El títol de la secció</label>
        <input value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} style={field} />
        <label style={lbl}>L’explicació</label>
        <textarea value={edit.text} onChange={(e) => setEdit({ ...edit, text: e.target.value })} rows={5} style={{ ...field, resize: 'vertical' }} />
        <label style={lbl}>A fons <span style={{ fontWeight: 400 }}>— el que el manual dóna per sabut</span></label>
        <textarea value={edit.deep} onChange={(e) => setEdit({ ...edit, deep: e.target.value })} rows={5} style={{ ...field, resize: 'vertical' }} />
        <label style={lbl}>A l’Atles central <span style={{ fontWeight: 400 }}>— el que la nostra varietat fa d’una altra manera</span></label>
        <textarea value={edit.ours} onChange={(e) => setEdit({ ...edit, ours: e.target.value })} rows={3} style={{ ...field, resize: 'vertical' }} />
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <button disabled={saving} onClick={async () => {
            setSaving(true);
            try { await onSave({ title: edit.title.trim(), text: edit.text.trim(), deep: edit.deep.trim(), ours: edit.ours.trim() }); setEdit(null); }
            finally { setSaving(false); }
          }} style={{ ...pill, borderColor: 'var(--brand-1)', color: 'var(--brand-1)' }}>
            <FaCheck size={10} /> {saving ? 'Desant…' : 'Desa'}
          </button>
          <button onClick={() => setEdit(null)} style={pill}>Deixa-ho</button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: '0 0 6px', flex: 1 }}>{title}</h3>
        {canEdit && (
          <button onClick={() => setEdit({ title, text: text || '', deep: deep || '', ours: ours || '' })}
                  aria-label="Corregeix aquesta secció" title="Corregeix-la" style={iconBtn}>
            <FaPen size={10} />
          </button>
        )}
      </div>
      {text && <p style={{ fontSize: 14.5, lineHeight: 1.65, margin: '0 0 6px', whiteSpace: 'pre-line' }}>{text}</p>}
      {deep && <Deep text={deep} />}
      {!canEdit && (
        propose === null ? (
          <button onClick={() => { if (!signedIn) { toast.error('Per proposar un canvi et cal un nom: fes-te’n un al perfil.'); return; } setPropose(text || ''); }}
                  style={glossBtn}>Proposa un canvi en aquesta explicació</button>
        ) : (
          <div style={{ margin: '6px 0 10px' }}>
            <textarea value={propose} onChange={(e) => setPropose(e.target.value)} rows={4} style={{ ...field, resize: 'vertical' }}
                      placeholder="Com ho diries tu" />
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <button disabled={sending} onClick={async () => {
                setSending(true);
                try {
                  await api.proposeLessonChange(`metode:${slug}`, index, propose.trim());
                  setPropose(null);
                  toast.success('Enviada. Qui administra la veurà.');
                } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut enviar')); }
                finally { setSending(false); }
              }} style={{ ...pill, borderColor: 'var(--brand-1)', color: 'var(--brand-1)' }}>
                {sending ? 'Enviant…' : 'Envia la proposta'}
              </button>
              <button onClick={() => setPropose(null)} style={pill}>Deixa-ho</button>
            </div>
          </div>
        )
      )}
    </>
  );
}

/** El que el manual dóna per sabut, explicat. Tancat, perquè qui només vol la frase la té. */
function Deep({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ margin: '2px 0 6px' }}>
      <button onClick={() => setOpen((v) => !v)} style={glossBtn}>
        {open ? 'Tanca' : 'A fons'}
      </button>
      {open && (
        <p style={{ fontSize: 13.5, lineHeight: 1.7, margin: '4px 0 0', padding: '10px 12px',
                    borderRadius: 'var(--r-md)', background: 'var(--surface-2)',
                    border: '1px solid var(--border)', whiteSpace: 'pre-line' }}>
          {text}
        </p>
      )}
    </div>
  );
}

/** El micròfon d'una línia, i el llapis per a qui administra. */
function LineTools({
  slug, where, shi, drillId, canEdit, onRecorded, onEdit,
}: {
  slug: string;
  where: Where;
  shi: string;
  drillId?: number;
  canEdit: boolean;
  onRecorded: (drillId: number) => void;
  onEdit?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState<Drill | null>(null);

  const record = async () => {
    if (!hasIdentity()) { toast.error('Per gravar et cal un nom: fes-te’n un al perfil.'); return; }
    if (!shi.trim()) { toast.error('Aquesta línia no té text amazic per dir.'); return; }
    setBusy(true);
    try {
      // La primera vegada, la línia es torna una frase de la biblioteca; les següents, se li
      // afegeix una veu més.
      const r = await api.methodLineDrill(slug, where.kind, where.index, where.section);
      setRecording(r.drill);
      onRecorded(r.drill_id);
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut preparar la gravació')); }
    finally { setBusy(false); }
  };

  return (
    <>
      <span style={{ marginInlineStart: 'auto', display: 'inline-flex', gap: 4, flexShrink: 0 }}>
        {canEdit && onEdit && (
          <button onClick={onEdit} aria-label="Corregeix aquesta línia" title="Corregeix-la"
                  style={iconBtn}><FaPen size={10} /></button>
        )}
        <button onClick={record} disabled={busy}
                aria-label={drillId ? 'Afegeix-hi la teva veu' : 'Grava aquesta línia'}
                title={drillId ? 'Afegeix-hi la teva veu' : 'Grava-la: la farà nostra'}
                style={{ ...iconBtn, color: drillId ? 'var(--emerald)' : 'var(--brand-1)', borderColor: drillId ? 'var(--emerald)' : 'var(--border)' }}>
          {busy ? '…' : <FaMicrophone size={11} />}
        </button>
      </span>
      {recording && (
        <RecordAudioModal drill={recording} onClose={() => setRecording(null)}
                          onSaved={() => { setRecording(null); toast.success('Gravada. Gràcies per la teva veu.'); }} />
      )}
    </>
  );
}

/** Una línia del llibre: el text, la tifinagh, el paraula per paraula i les seves eines.
 *
 *  El llapis és el mateix a tot arreu —exemples, rèpliques del diàleg i vocabulari— perquè una
 *  errada és una errada visqui on visqui: no tenia sentit poder corregir un exemple i no poder
 *  corregir la rèplica que hi ha tres dits més avall.
 */
function BookLine({
  slug, where, look, who, shi, ca, note, tif, gloss, drillId, canEdit, extra, audio, image,
  speaker, playing, onPlay, onSave, onRecorded,
}: {
  slug: string; where: Where; look: 'row' | 'turn' | 'word';
  who?: string; shi: string; ca?: string; note?: string; tif?: string | null; gloss?: MethodGloss[];
  drillId?: number; canEdit: boolean; extra?: ReactNode;
  /** El que la biblioteca ja en té: la veu d'algú, la seva imatge, i qui la diu. */
  audio?: string | null; image?: string | null; speaker?: string | null;
  playing?: boolean; onPlay?: () => void;
  onSave: (shi: string, ca: string) => Promise<void>;
  onRecorded: (drillId: number) => void;
}) {
  const [edit, setEdit] = useState<{ shi: string; ca: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [openGloss, setOpenGloss] = useState(false);

  if (edit) {
    return (
      <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
        <input value={edit.shi} onChange={(e) => setEdit({ ...edit, shi: e.target.value })}
               lang="shi" autoCapitalize="off" autoCorrect="off" spellCheck={false}
               aria-label="Text amazic" style={{ ...field, fontWeight: 700, color: 'var(--brand-1)' }} />
        <input value={edit.ca} onChange={(e) => setEdit({ ...edit, ca: e.target.value })}
               lang="ca" aria-label="Català" style={{ ...field, marginTop: 5 }} />
        {/* Si la línia ja s'ha gravat, el text del capítol i el de la gravació poden separar-se:
            la frase de la biblioteca es queda com la va dir qui la va dir, i això no es toca. */}
        {drillId && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>
            Aquesta línia ja és una frase de la biblioteca i algú hi pot haver posat la veu. El
            text de la gravació no canviarà: es queda com la va dir qui la va dir.
          </p>
        )}
        <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
          <button disabled={saving} onClick={async () => {
            setSaving(true);
            try { await onSave(edit.shi.trim(), edit.ca.trim()); setEdit(null); }
            finally { setSaving(false); }
          }} style={{ ...pill, borderColor: 'var(--brand-1)', color: 'var(--brand-1)' }}>
            <FaCheck size={10} /> {saving ? 'Desant…' : 'Desa'}
          </button>
          <button onClick={() => setEdit(null)} style={pill}>Deixa-ho</button>
        </div>
      </div>
    );
  }

  const tools = (
    <span style={{ marginInlineStart: 'auto', display: 'inline-flex', gap: 4, flexShrink: 0, alignItems: 'center' }}>
      {audio && onPlay && (
        <button onClick={onPlay} aria-label={`Escolta «${shi}»`} title={speaker ? `Ho diu ${speaker}` : 'Escolta-la'}
                style={{ ...iconBtn, border: 'none', background: playing ? 'var(--brand-1)' : 'var(--brand-gradient)', color: '#fff' }}>
          <FaPlay size={9} />
        </button>
      )}
      <LineTools slug={slug} where={where} shi={shi} drillId={drillId} canEdit={canEdit}
                 onRecorded={onRecorded} onEdit={() => setEdit({ shi, ca: ca || '' })} />
    </span>
  );
  const words = gloss && gloss.length > 0 ? (
    <div style={{ flexBasis: '100%' }}>
      <button onClick={() => setOpenGloss((v) => !v)} style={glossBtn}>
        {openGloss ? 'Amaga el paraula per paraula' : 'Paraula per paraula'}
      </button>
      {openGloss && <GlossWords words={gloss} size="sm" />}
    </div>
  ) : null;

  if (look === 'turn') {
    return (
      <div style={{ padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)',
                    background: playing ? 'var(--brand-gradient-soft)' : 'var(--surface)',
                    borderColor: playing ? 'var(--brand-1)' : 'var(--border)' }}>
        {who && <div style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{who}</div>}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <div lang="shi" style={{ fontSize: 16.5, fontWeight: 700, color: 'var(--brand-1)', lineHeight: 1.35, marginTop: 2 }}>{shi}</div>
            <Tif t={tif} size={13} />
            <div style={{ fontSize: 14, color: 'var(--text-soft)' }}>{ca}</div>
          </div>
          {tools}
          {words}
        </div>
      </div>
    );
  }

  if (look === 'word') {
    return (
      <div style={{ borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', overflow: 'hidden',
                    background: playing ? 'var(--brand-gradient-soft)' : 'var(--surface)' }}>
        {image && (
          <img src={getMediaUrl(image)} alt="" loading="lazy"
               style={{ width: '100%', aspectRatio: '4 / 3', objectFit: 'cover', display: 'block' }}
               onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
        )}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '7px 10px', fontSize: 13.5 }}>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span lang="shi" style={{ fontWeight: 800, color: 'var(--brand-1)' }}>{shi}</span>
            <Tif t={tif} size={11.5} />
            <span style={{ display: 'block', color: 'var(--text-soft)' }}>{ca}</span>
          </span>
          {extra}
          {tools}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ minWidth: 160 }}>
        <span lang="shi" style={{ fontWeight: 700, fontSize: 15.5, color: 'var(--brand-1)' }}>{shi}</span>
        <Tif t={tif} />
      </span>
      {ca && <span style={{ fontSize: 14, color: 'var(--text)' }}>{ca}</span>}
      {note && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>· {note}</span>}
      {tools}
      {words}
    </div>
  );
}

export default function MethodLesson({
  slug, content, canEdit, onChanged,
}: {
  slug: string;
  content: MethodContent;
  /** Qui administra pot corregir el text del capítol allà mateix. */
  canEdit: boolean;
  onChanged: () => void;
}) {
  const [openDialogue, setOpenDialogue] = useState(true);
  const [body, setBody] = useState<MethodContent>(content);
  const signedIn = hasIdentity();

  /** Canvia una línia i desa el capítol sencer: el cos és el format que l'endpoint torna. */
  const saveLine = async (where: Where, shi: string, ca: string) => {
    const next: MethodContent = JSON.parse(JSON.stringify(body));
    const target = whereIn(next, where);
    if (!target) return;
    target.shi = shi;
    if (ca) target.ca = ca; else delete (target as { ca?: string }).ca;
    try {
      await api.saveMethodContent(slug, next);
      setBody(next);
      toast.success('Corregit');
      onChanged();
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut desar')); }
  };

  /** Canvia el text d'una secció sencera i desa el capítol. El mateix camí que una línia. */
  const saveSection = async (i: number, p: { title: string; text: string; deep: string; ours: string }) => {
    const next: MethodContent = JSON.parse(JSON.stringify(body));
    const s = (next.sections || [])[i];
    if (!s) return;
    s.title = p.title;
    for (const [k, v] of [['text', p.text], ['deep', p.deep], ['ours', p.ours]] as const) {
      if (v) (s as Record<string, unknown>)[k] = v; else delete (s as Record<string, unknown>)[k];
    }
    try {
      await api.saveMethodContent(slug, next);
      setBody(next);
      toast.success('Corregida');
      onChanged();
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut desar')); }
  };

  /** Apunta localment el drill que acaba de néixer, perquè el micròfon canviï de color. */
  const noteDrill = (where: Where) => (drillId: number) => {
    setBody((b) => {
      const next: MethodContent = JSON.parse(JSON.stringify(b));
      const t = whereIn(next, where);
      if (t) (t as { drill_id?: number }).drill_id = drillId;
      return next;
    });
  };

  // ───────────────────────────────────────────────────────────────────────────────────────
  // El PLAY del capítol.
  //
  // L'amo: «recorda que haig de poder posar play a la lliçó». Un capítol és per escoltar-lo, no
  // per llegir-lo: això ajunta tot el que ja té veu —les rèpliques del diàleg, les paraules i
  // els exemples que algú ha gravat— i ho diu de dalt a baix, marcant la línia que sona. El que
  // encara no s'ha gravat no s'hi inventa: se salta, i el micròfon és allà per omplir-lo.
  const tracks: { key: string; url: string }[] = [];
  const push = (key: string, url?: string | null) => { if (url) tracks.push({ key, url: getMediaUrl(url) }); };
  (body.dialogue?.turns || []).forEach((t, k) => push(`turn:${k}`, t.audio_url));
  (body.vocabulary || []).forEach((v, k) => push(`vocabulary:${k}`, v.audio_url));
  (body.sections || []).forEach((sec) => {
    (sec.examples || []).forEach((e, k) => push(`example:${sec.id}:${k}`, e.audio_url));
  });
  // Les frases de la biblioteca NO entren al play del capítol, encara que siguin les que tenen
  // més veu. Un auditor pedagògic ho va comptar: de 24 talls que sonaven, 20 eren frases d'una
  // altra cosa —«La vaig agafar a casa del reparador de bicicletes», «Em vaig penedir»— i del
  // capítol se'n sentien quatre paraules soltes. El botó deia «escolta el capítol» i feia sonar
  // una altra cosa. Cada targeta nostra conserva el seu play, que és on té sentit.

  const [sounding, setSounding] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const chainRef = useRef(false);

  const stop = () => {
    chainRef.current = false;
    audioRef.current?.pause();
    audioRef.current = null;
    setSounding(null);
  };

  const playFrom = (i: number) => {
    const t = tracks[i];
    if (!t) { stop(); return; }
    audioRef.current?.pause();
    const a = new Audio(t.url);
    audioRef.current = a;
    setSounding(t.key);
    const next = () => { if (chainRef.current) playFrom(i + 1); else setSounding(null); };
    a.onended = next;
    a.onerror = next;
    a.play().catch(next);
  };

  const playAll = () => {
    if (sounding) { stop(); return; }
    chainRef.current = true;
    playFrom(0);
  };

  const playOne = (key: string) => {
    const i = tracks.findIndex((t) => t.key === key);
    if (i < 0) return;
    chainRef.current = false;
    if (sounding === key) { stop(); return; }
    playFrom(i);
  };

  useEffect(() => stop, []);

  return (
    <>
      {body.intro && <p style={{ fontSize: 15, lineHeight: 1.65, margin: '0 0 10px' }}>{body.intro}</p>}

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', margin: '0 0 22px' }}>
        <button onClick={playAll} disabled={tracks.length === 0}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 'var(--r-pill)', border: 'none', cursor: tracks.length ? 'pointer' : 'default', fontFamily: 'inherit', fontWeight: 800, fontSize: 14, color: '#fff', background: tracks.length ? 'var(--brand-gradient)' : 'var(--surface-2)', boxShadow: tracks.length ? 'var(--shadow-brand)' : 'none' }}>
          {sounding ? <FaStop size={12} /> : <FaPlay size={12} />}
          {sounding ? 'Atura' : 'Escolta el capítol'}
        </button>
        <span style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5, flex: '1 1 240px' }}>
          {tracks.length
            ? `${tracks.length} ${tracks.length === 1 ? 'línia del capítol es pot escoltar' : 'línies del capítol es poden escoltar'}. La resta espera una veu: prem el micròfon de qualsevol línia i la primera serà la teva.`
            : 'Cap línia del capítol no s’ha gravat encara. Prem el micròfon de qualsevol línia i la primera serà la teva.'}
        </span>
      </div>

      {/* La barra de dalt: on és cada cosa, i s'hi va amb un dit.
          L'amo: «crec que en els capítols a l'inici, en una barra horitzontal, hi hauria d'haver
          botons a les diferents seccions del capítol». Un capítol té quatre parts i vuit
          seccions: sense això, per tornar als datius s'ha de baixar mig quilòmetre. */}
      <nav aria-label="Les parts del capítol"
           style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 8, marginBottom: 18, scrollbarWidth: 'none' }}>
        {[
          ...(body.dialogue ? [{ id: 'part-dialeg', label: body.dialogue.title }] : []),
          ...((body.vocabulary || []).length ? [{ id: 'part-paraules', label: 'Les paraules' }] : []),
          ...(body.sections || []).map((s) => ({ id: `part-${s.id}`, label: s.title.split(':')[0] })),
          ...(body.practice ? [{ id: 'part-fes-ho-tu', label: 'Fes-ho tu' }] : []),
        ].map((x) => (
          <button key={x.id}
                  onClick={() => document.getElementById(x.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                  style={{ flexShrink: 0, padding: '6px 13px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}>
            {x.label}
          </button>
        ))}
      </nav>

      {/* 1 · EL DIÀLEG — l'escena sencera. Va primer perquè és el capítol: tot el que ve després
          explica el que aquí passa d'una tirada, i aquest és també l'ordre del manual. */}
      {body.dialogue && (
        <section id="part-dialeg" style={{ marginBottom: 30, scrollMarginTop: 'calc(var(--nav-h) + 10px)' }}>
          <Part n={1} title={body.dialogue.title} icon={<FaCommentDots size={13} />}
                what={body.dialogue.scene} onToggle={() => setOpenDialogue((v) => !v)} open={openDialogue} />
          {openDialogue && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {body.dialogue.turns.map((t, k) => {
                const where: Where = { kind: 'turn', index: k };
                return (
                  <BookLine key={k} slug={slug} where={where} look="turn" who={t.who}
                            shi={t.shi} ca={t.ca} tif={t.tif} gloss={t.gloss}
                            drillId={t.drill_id} canEdit={canEdit}
                            audio={t.audio_url} speaker={t.speaker}
                            playing={sounding === `turn:${k}`} onPlay={() => playOne(`turn:${k}`)}
                            onSave={(shi, ca) => saveLine(where, shi, ca)}
                            onRecorded={noteDrill(where)} />
                );
              })}
            </div>
          )}
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.55 }}>
            Aquest diàleg és del manual, i per tant en tachelhit del Souss. Grava’n una rèplica i
            hi anirà la teva manera de dir-la, amb el teu poble al costat.
          </p>
        </section>
      )}

      {/* 2 · LES PARAULES — amb la seva imatge i la seva veu quan la biblioteca ja en té. */}
      {body.vocabulary && body.vocabulary.length > 0 && (
        <section id="part-paraules" style={{ marginBottom: 30, scrollMarginTop: 'calc(var(--nav-h) + 10px)' }}>
          <Part n={2} title="Les paraules d’aquest capítol" icon={<FaTags size={12} />}
                what="Les que surten al diàleg i a les explicacions. Les que la biblioteca ja té surten amb la seva imatge i la seva veu." />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))', gap: 10 }}>
            {body.vocabulary.map((v, k) => {
              const where: Where = { kind: 'vocabulary', index: k };
              return (
                <BookLine key={k} slug={slug} where={where} look="word"
                          shi={v.shi} ca={v.ca} tif={v.tif}
                          drillId={v.drill_id} canEdit={canEdit}
                          audio={v.audio_url} image={v.image_url} speaker={v.speaker}
                          playing={sounding === `vocabulary:${k}`} onPlay={() => playOne(`vocabulary:${k}`)}
                          onSave={(shi, ca) => saveLine(where, shi, ca)}
                          onRecorded={noteDrill(where)} />
              );
            })}
          </div>
        </section>
      )}

      {/* 3 · COM FUNCIONA — les seccions numerades: el que el manual explica i, tot seguit, com
          ho diu la gent que coneixem. */}
      {(body.sections || []).length > 0 && (
        <Part n={3} title="Com funciona" icon={<FaBookOpen size={12} />}
              what="Una cosa per secció: el que el manual explica, i tot seguit com ho diu la gent que coneixem." />
      )}
      {(body.sections || []).map((s, si) => (
        <section key={s.id} id={`part-${s.id}`} style={{ marginBottom: 26, paddingInlineStart: 14, borderInlineStart: '3px solid var(--border)', scrollMarginTop: 'calc(var(--nav-h) + 10px)' }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--brand-1)', letterSpacing: '0.08em' }}>
            3.{si + 1}
          </div>
          <SectionText slug={slug} index={si} title={s.title} text={s.text} deep={s.deep} ours={s.ours}
                       canEdit={canEdit} signedIn={signedIn}
                       onSave={(p) => saveSection(si, p)} />

          {s.table && (
            <div style={{ marginTop: 8, border: '1px solid var(--border)', borderRadius: 'var(--r-md)', overflow: 'hidden' }}>
              <div style={{ padding: '6px 12px', background: 'var(--surface-2)', fontSize: 12, fontWeight: 800, color: 'var(--text-muted)' }}>{s.table.title}</div>
              {s.table.rows.map((r, k) => (
                <div key={k} style={{ display: 'flex', gap: 12, padding: '6px 12px', borderTop: '1px solid var(--border)', fontSize: 14 }}>
                  <span style={{ flex: 1, color: 'var(--text-soft)' }}>{r.p}</span>
                  <span style={{ textAlign: 'right' }}>
                    <span lang="shi" style={{ fontWeight: 800, color: 'var(--brand-1)' }}>{r.v}</span>
                    <Tif t={r.v_tif} size={11.5} />
                  </span>
                </div>
              ))}
            </div>
          )}

          {s.columns && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12, marginTop: 8 }}>
              {s.columns.map((col) => (
                <div key={col.title} style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-md)', overflow: 'hidden' }}>
                  <div style={{ padding: '6px 12px', background: 'var(--surface-2)', fontSize: 12, fontWeight: 800, color: 'var(--text-muted)' }}>{col.title}</div>
                  {col.rows.map((r, k) => (
                    <div key={k} style={{ display: 'flex', gap: 10, padding: '5px 12px', borderTop: '1px solid var(--border)', fontSize: 13.5 }}>
                      <span style={{ flex: 1 }}>
                        <span lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)' }}>{r.shi}</span>
                        <Tif t={r.tif} size={11.5} />
                      </span>
                      <span style={{ color: 'var(--text-soft)' }}>{r.ca}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {s.numbers && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))', gap: 6, marginTop: 8 }}>
              {s.numbers.map((n) => (
                <div key={n.n} style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', fontSize: 13 }}>
                  <div style={{ color: 'var(--text-muted)', fontWeight: 800, fontSize: 11.5 }}>{n.n}</div>
                  <div lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)' }}>{n.m}</div>
                  <Tif t={n.m_tif} size={11.5} />
                  {n.f && n.f !== n.m && (
                    <>
                      <div lang="shi" style={{ color: 'var(--text-soft)' }}>
                        {n.f} <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>f.</span>
                      </div>
                      <Tif t={n.f_tif} size={11.5} />
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {s.examples && s.examples.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: 8 }}>
              {s.examples.map((e: MethodExample, k) => {
                const where: Where = { kind: 'example', index: k, section: s.id };
                const key = `example:${s.id}:${k}`;
                return (
                  <BookLine key={k} slug={slug} where={where} look="row"
                            shi={e.shi} ca={e.ca} note={e.note} tif={e.tif} gloss={e.gloss}
                            drillId={e.drill_id} canEdit={canEdit}
                            audio={e.audio_url} speaker={e.speaker}
                            playing={sounding === key} onPlay={() => playOne(key)}
                            onSave={(shi, ca) => saveLine(where, shi, ca)}
                            onRecorded={noteDrill(where)} />
                );
              })}
            </div>
          )}

          {s.ours && (
            <p style={{ marginTop: 10, padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--brand-gradient-soft)', fontSize: 13.5, lineHeight: 1.6 }}>
              <strong>A l’Atles central:</strong> {s.ours}
            </p>
          )}

          {/* I com ho diu la gent que coneixem. Això és el que el llibre no té: la mateixa cosa
              dita per algú, amb la seva veu, el seu poble i la seva imatge. Cada targeta diu
              QUÈ HI FA: una frase que apareix sense dir què hi fa és soroll, per bona que sigui. */}
          {s.ours_drills && s.ours_drills.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 6 }}>
                Dit per les nostres veus
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 8 }}>
                {s.ours_drills.map((d) => (
                  <div key={d.id} style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', background: 'var(--surface)' }}>
                    {d.image_url && (
                      <img src={getMediaUrl(d.image_url)} alt="" loading="lazy"
                           style={{ width: '100%', aspectRatio: '16 / 10', objectFit: 'cover', display: 'block' }}
                           onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                    )}
                    <div style={{ padding: '8px 10px' }}>
                      <div lang="shi" style={{ fontWeight: 800, fontSize: 15, color: 'var(--brand-1)', lineHeight: 1.3 }}>{d.text_tachelhit}</div>
                      <Tif t={d.tif} size={12} />
                      <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                      {d.why && (
                        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 3, lineHeight: 1.4 }}>
                          És aquí perquè {d.why}
                        </div>
                      )}
                      {d.gloss && d.gloss.length > 0 && <GlossWords words={d.gloss} size="sm" />}
                      <SentenceVariants variants={d.variants} size="sm" />
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                        <span style={{ fontSize: 11.5, color: 'var(--text-muted)', flex: 1 }}>
                          {d.speaker || 'sense nom'}
                          {(d.variety || d.region) && (
                            <span style={{ fontSize: 10.5, opacity: 0.6 }}>
                              {d.variety ? ` · ${d.variety}` : ''}{d.region ? ` · ${d.region}` : ''}
                            </span>
                          )}
                        </span>
                        {d.audio_url && (
                          <button onClick={() => new Audio(getMediaUrl(d.audio_url as string)).play().catch(() => {})}
                                  aria-label="Escolta-la" title="Escolta-la"
                                  style={{ width: 30, height: 30, borderRadius: '50%', border: 'none', background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer', flexShrink: 0 }}>
                            <FaPlay size={10} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {typeof s.ours_total === 'number' && s.ours_total > s.ours_drills.length && (
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0' }}>
                  i {s.ours_total - s.ours_drills.length} més a la biblioteca
                </p>
              )}
            </div>
          )}
        </section>
      ))}

      {/* 4 · FES-HO TU — el mateix diàleg canviant el que compres: es tria, no es llegeix. */}
      {body.practice && (
        <div id="part-fes-ho-tu" style={{ scrollMarginTop: 'calc(var(--nav-h) + 10px)' }}>
          <Practice practice={body.practice} n={4} />
        </div>
      )}
    </>
  );
}

/** El títol d'una part del capítol: el número gros, el nom, i què hi fas.
 *
 *  L'amo: «s'ha de veure la jerarquia del document». Un capítol té quatre parts i vuit seccions,
 *  i fins ara tots els títols eren iguals: no es distingia una part d'una secció ni una secció
 *  d'un exemple, i el diàleg quedava enterrat al final com si fos un afegit.
 */
function Part({ n, title, what, icon, open, onToggle }: {
  n: number; title: string; what?: string; icon?: ReactNode; open?: boolean; onToggle?: () => void;
}) {
  const head = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span aria-hidden style={{ width: 28, height: 28, borderRadius: 9, background: 'var(--brand-gradient)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 14, flexShrink: 0 }}>{n}</span>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: 0, flex: 1, textAlign: 'start' }}>{title}</h2>
      {icon && <span style={{ color: 'var(--brand-1)' }}>{icon}</span>}
      {onToggle && <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{open ? '▾' : '▸'}</span>}
    </div>
  );
  return (
    <div style={{ margin: '0 0 10px', paddingTop: 12, borderTop: '1px solid var(--border)' }}>
      {onToggle
        ? <button onClick={onToggle} style={{ width: '100%', background: 'transparent', border: 'none', padding: 0, cursor: 'pointer', fontFamily: 'inherit', color: 'var(--text)' }}>{head}</button>
        : head}
      {what && <p style={{ fontSize: 13, color: 'var(--text-soft)', margin: '4px 0 10px', lineHeight: 1.55 }}>{what}</p>}
    </div>
  );
}

/** Fes-ho tu: el mateix diàleg canviant el que compres.
 *
 *  L'amo: «coses com aquestes poden ser interactives». Una llista de productes al costat d'un
 *  patró és una cosa per MIRAR; triar el producte i veure com queda la frase sencera és una cosa
 *  per FER, que és el que un mètode demana.
 */
function Practice({ practice, n }: { practice: NonNullable<MethodContent['practice']>; n: number }) {
  const [pick, setPick] = useState(0);
  const f = practice.fills[pick];
  const put = (t: string, shi: boolean) => (t || '')
    .replace(/\{producte\}/g, (shi ? f?.shi : f?.ca) || '…')
    .replace(/\{quantitat\}/g, (shi ? f?.qty_shi : f?.qty_ca) || '…');

  return (
    <section style={{ marginBottom: 26 }}>
      <Part n={n} title={practice.title} icon={<FaHandPointer size={12} />} what={practice.scene} />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
        {practice.fills.map((x, k) => (
          <button key={k} onClick={() => setPick(k)}
                  style={{ padding: '7px 12px', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontFamily: 'inherit',
                           border: `1px solid ${k === pick ? 'var(--brand-1)' : 'var(--border)'}`,
                           background: k === pick ? 'var(--brand-gradient-soft)' : 'var(--surface)',
                           color: 'var(--text)', fontSize: 13 }}>
            <span lang="shi" style={{ fontWeight: 800, color: 'var(--brand-1)' }}>{x.shi}</span>
            <span style={{ color: 'var(--text-soft)' }}> {x.ca}</span>
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
        {practice.pattern.map((t, k) => (
          <div key={k}>
            <div style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{t.who}</div>
            <div lang="shi" style={{ fontSize: 16.5, fontWeight: 700, color: 'var(--brand-1)', lineHeight: 1.35 }}>{put(t.shi, true)}</div>
            <div style={{ fontSize: 14, color: 'var(--text-soft)' }}>{put(t.ca, false)}</div>
          </div>
        ))}
        {f && (
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
            Ara compres <strong lang="shi">{f.shi}</strong> ({f.ca}) i en demanes{' '}
            <strong lang="shi">{f.qty_shi}</strong> ({f.qty_ca}). Tria’n un altre i torna-ho a dir.
          </p>
        )}
      </div>
    </section>
  );
}

/** La línia d'un cos, pel seu lloc. Igual que `method.line_at` al servidor. */
function whereIn(body: MethodContent, w: Where): { shi: string; ca?: string } | null {
  if (w.kind === 'example') {
    const s = (body.sections || []).find((x) => x.id === w.section);
    return s?.examples?.[w.index] ?? null;
  }
  if (w.kind === 'turn') return body.dialogue?.turns?.[w.index] ?? null;
  return body.vocabulary?.[w.index] ?? null;
}

const iconBtn: React.CSSProperties = {
  width: 28, height: 28, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--text-muted)', cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 0,
  fontFamily: 'inherit', fontSize: 11,
};
const pill: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 11px',
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text-soft)', fontWeight: 700, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
};
const glossBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', padding: '2px 0', margin: 0, cursor: 'pointer',
  color: 'var(--text-muted)', fontSize: 11.5, fontWeight: 700, fontFamily: 'inherit',
  textDecoration: 'underline', textUnderlineOffset: 3,
};
const lbl: React.CSSProperties = {
  display: 'block', fontSize: 11.5, fontWeight: 800, color: 'var(--text-muted)',
  textTransform: 'uppercase', letterSpacing: '0.05em', margin: '10px 0 3px',
};
const field: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '8px 10px', fontSize: 14.5,
  borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit',
};
