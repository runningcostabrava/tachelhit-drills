import { useState } from 'react';
import { FaPlay, FaCommentDots, FaMicrophone, FaPen, FaCheck } from 'react-icons/fa';
import { api, type MethodContent, type MethodExample } from '../api';
import type { Drill } from '../types';
import { getMediaUrl, hasIdentity } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import RecordAudioModal from './RecordAudioModal';

// La lliçó d'un capítol: l'explicació, el diàleg i el vocabulari.
//
// El text ve del manual d'El Mountassir, traduït i adaptat (ADR 0004), i viu a la base de dades
// perquè es pugui corregir sense desplegar res.
//
// Però un capítol no està acabat fins que les seves línies es poden ESCOLTAR, i una línia del
// manual no és encara una frase de la biblioteca: és text dins del capítol. Per això cada línia
// porta un micròfon: prémer-lo la converteix en una frase nostra i obre la gravadora, on qui
// parla hi posa la seva veu, la seva manera d'escriure-ho i el seu poble.
//
// Aquest és el camí pel qual un capítol adaptat del Souss es torna una recollida de l'Atles.

type Where = { kind: 'example' | 'turn' | 'vocabulary'; index: number; section?: string };

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

/** Una línia, amb el seu micròfon i, per a qui administra, els seus dos camps de text. */
function Line({
  slug, where, shi, ca, note, drillId, canEdit, onSave, onRecorded,
}: {
  slug: string; where: Where; shi: string; ca?: string; note?: string;
  drillId?: number; canEdit: boolean;
  onSave: (shi: string, ca: string) => Promise<void>;
  onRecorded: (drillId: number) => void;
}) {
  const [edit, setEdit] = useState<{ shi: string; ca: string } | null>(null);
  const [saving, setSaving] = useState(false);

  if (edit) {
    return (
      <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
        <input value={edit.shi} onChange={(e) => setEdit({ ...edit, shi: e.target.value })}
               lang="shi" autoCapitalize="off" autoCorrect="off" spellCheck={false}
               aria-label="Text amazic" style={{ ...field, fontWeight: 700, color: 'var(--brand-1)' }} />
        <input value={edit.ca} onChange={(e) => setEdit({ ...edit, ca: e.target.value })}
               lang="ca" aria-label="Català" style={{ ...field, marginTop: 5 }} />
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

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span lang="shi" style={{ fontWeight: 700, fontSize: 15.5, color: 'var(--brand-1)', minWidth: 160 }}>{shi}</span>
      {ca && <span style={{ fontSize: 14, color: 'var(--text)' }}>{ca}</span>}
      {note && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>· {note}</span>}
      <LineTools slug={slug} where={where} shi={shi} drillId={drillId} canEdit={canEdit}
                 onRecorded={onRecorded}
                 onEdit={() => setEdit({ shi, ca: ca || '' })} />
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

  /** Apunta localment el drill que acaba de néixer, perquè el micròfon canviï de color. */
  const noteDrill = (where: Where) => (drillId: number) => {
    setBody((b) => {
      const next: MethodContent = JSON.parse(JSON.stringify(b));
      const t = whereIn(next, where);
      if (t) (t as { drill_id?: number }).drill_id = drillId;
      return next;
    });
  };

  return (
    <>
      {body.intro && <p style={{ fontSize: 15, lineHeight: 1.65, margin: '0 0 8px' }}>{body.intro}</p>}
      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 20px', lineHeight: 1.55 }}>
        <FaMicrophone size={10} /> Cada línia es pot gravar. La primera vegada que algú ho fa, la
        línia passa a ser una frase de la nostra biblioteca, amb la seva veu i el seu poble.
      </p>

      {(body.sections || []).map((s) => (
        <section key={s.id} style={{ marginBottom: 26 }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: '0 0 6px' }}>{s.title}</h3>
          {s.text && <p style={{ fontSize: 14.5, lineHeight: 1.65, margin: '0 0 6px', whiteSpace: 'pre-line' }}>{s.text}</p>}

          {s.table && (
            <div style={{ marginTop: 8, border: '1px solid var(--border)', borderRadius: 'var(--r-md)', overflow: 'hidden' }}>
              <div style={{ padding: '6px 12px', background: 'var(--surface-2)', fontSize: 12, fontWeight: 800, color: 'var(--text-muted)' }}>{s.table.title}</div>
              {s.table.rows.map((r, k) => (
                <div key={k} style={{ display: 'flex', gap: 12, padding: '6px 12px', borderTop: '1px solid var(--border)', fontSize: 14 }}>
                  <span style={{ flex: 1, color: 'var(--text-soft)' }}>{r.p}</span>
                  <span lang="shi" style={{ fontWeight: 800, color: 'var(--brand-1)' }}>{r.v}</span>
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
                      <span lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)', flex: 1 }}>{r.shi}</span>
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
                  {n.f && n.f !== n.m && (
                    <div lang="shi" style={{ color: 'var(--text-soft)' }}>
                      {n.f} <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>f.</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {s.examples && s.examples.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: 8 }}>
              {s.examples.map((e: MethodExample, k) => {
                const where: Where = { kind: 'example', index: k, section: s.id };
                return (
                  <Line key={k} slug={slug} where={where} shi={e.shi} ca={e.ca} note={e.note}
                        drillId={e.drill_id} canEdit={canEdit}
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
              dita per algú, amb la seva veu, el seu poble i la seva imatge. */}
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
                      <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                        <span style={{ fontSize: 11.5, color: 'var(--text-muted)', flex: 1 }}>
                          {d.speaker || 'sense nom'}{d.variety ? ` · ${d.variety}` : ''}{d.region ? ` · ${d.region}` : ''}
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

      {body.dialogue && (
        <section style={{ marginBottom: 26 }}>
          <button onClick={() => setOpenDialogue((v) => !v)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'transparent', border: 'none', padding: 0, cursor: 'pointer', fontFamily: 'inherit', color: 'var(--text)' }}>
            <FaCommentDots size={14} style={{ color: 'var(--brand-1)' }} />
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: 0 }}>{body.dialogue.title}</h3>
          </button>
          {body.dialogue.scene && (
            <p style={{ fontSize: 13.5, color: 'var(--text-soft)', margin: '4px 0 10px', lineHeight: 1.55 }}>{body.dialogue.scene}</p>
          )}
          {openDialogue && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {body.dialogue.turns.map((t, k) => {
                const where: Where = { kind: 'turn', index: k };
                return (
                  <div key={k} style={{ padding: '10px 12px', borderRadius: 'var(--r-lg)', background: k % 2 ? 'var(--surface-2)' : 'var(--surface)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{t.who}</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                      <div style={{ flex: 1, minWidth: 180 }}>
                        <div lang="shi" style={{ fontSize: 16.5, fontWeight: 700, color: 'var(--brand-1)', lineHeight: 1.35, marginTop: 2 }}>{t.shi}</div>
                        <div style={{ fontSize: 14, color: 'var(--text-soft)' }}>{t.ca}</div>
                      </div>
                      <LineTools slug={slug} where={where} shi={t.shi} drillId={t.drill_id}
                                 canEdit={false} onRecorded={noteDrill(where)} />
                    </div>
                  </div>
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

      {body.practice && (
        <section style={{ marginBottom: 26, padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 17, margin: '0 0 4px' }}>{body.practice.title}</h3>
          {body.practice.scene && <p style={{ fontSize: 13.5, color: 'var(--text-soft)', margin: '0 0 10px' }}>{body.practice.scene}</p>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginBottom: 10 }}>
            {body.practice.pattern.map((t, k) => (
              <div key={k} style={{ fontSize: 14 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12, marginRight: 6 }}>{t.who}</span>
                <span lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)' }}>{t.shi}</span>
                <span style={{ color: 'var(--text-soft)' }}> — {t.ca}</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 6 }}>
            {body.practice.fills.map((f, k) => (
              <div key={k} style={{ padding: '7px 10px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', fontSize: 13 }}>
                <span lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)' }}>{f.shi}</span>
                <span style={{ color: 'var(--text-soft)' }}> {f.ca}</span>
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  <span lang="shi">{f.qty_shi}</span> · {f.qty_ca}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {body.vocabulary && body.vocabulary.length > 0 && (
        <section style={{ marginBottom: 26 }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: '0 0 8px' }}>Les paraules d’aquest capítol</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 5 }}>
            {body.vocabulary.map((v, k) => {
              const where: Where = { kind: 'vocabulary', index: k };
              return (
                <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '5px 10px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', fontSize: 13.5 }}>
                  <span lang="shi" style={{ fontWeight: 700, color: 'var(--brand-1)' }}>{v.shi}</span>
                  <span style={{ color: 'var(--text-soft)' }}>{v.ca}</span>
                  {v.audio_url && (
                    <button onClick={() => new Audio(v.audio_url as string).play().catch(() => {})}
                            aria-label={`Escolta ${v.shi}`} style={{ ...iconBtn, border: 'none' }}>
                      <FaPlay size={9} />
                    </button>
                  )}
                  <LineTools slug={slug} where={where} shi={v.shi} drillId={v.drill_id}
                             canEdit={false} onRecorded={noteDrill(where)} />
                </div>
              );
            })}
          </div>
        </section>
      )}
    </>
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
const field: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '8px 10px', fontSize: 14.5,
  borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit',
};
