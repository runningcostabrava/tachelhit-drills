import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaMicrophone, FaPaperPlane, FaVolumeUp } from 'react-icons/fa';
import { api, type PetitionItem, type Me } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import type { Drill } from '../types';
import RecordAudioModal from './RecordAudioModal';

// «Posa-hi veu»: the two halves of the same act. A learner asks how to say something (a petition,
// in Catalan); somebody who speaks the language answers with their voice and their own spelling,
// and says where they are from.
//
// It used to be called «Veus», which named a thing instead of what you do here, and the tabs were
// named after how the server groups the rows (#200). The route stays /veus so links keep working.

type Kind = 'open' | 'synthetic' | 'aitmraw';
const TABS: { kind: Kind; label: string; blurb: string }[] = [
  { kind: 'open', label: 'Algú ho ha demanat', blurb: 'Algú vol saber dir això i espera una veu. Si ho saps dir, grava-ho: la teva manera de dir-ho i d’escriure-ho és la bona.' },
  { kind: 'synthetic', label: 'Només hi parla una màquina', blurb: 'Aquestes frases només tenen una veu sintètica, i una llengua no s’aprèn d’una màquina. Les primeres unitats del curs van al davant.' },
  { kind: 'aitmraw', label: 'Dites a Aït Mraw', blurb: 'Frases d’altres llocs que valdria la pena sentir dites a Aït Mraw, com les diuen la Halima i en Driss.' },
];

export default function VeusPage() {
  const navigate = useNavigate();
  const [kind, setKind] = useState<Kind>('open');
  const [items, setItems] = useState<PetitionItem[] | null>(null);
  const [listFailed, setListFailed] = useState(false);
  const [total, setTotal] = useState(0);
  const [me, setMe] = useState<Me | null>(null);
  const [recording, setRecording] = useState<Drill | null>(null);
  const [asking, setAsking] = useState(false);
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => { api.me().then(setMe).catch(() => setMe(null)); }, []);
  useEffect(() => {
    setItems(null); setListFailed(false);
    api.petitions(kind)
      .then((r) => { setItems(r.items); setTotal(r.total); })
      .catch((e) => { setListFailed(true); toast.error(whyItFailed(e, 'No s’ha pogut carregar la llista')); });
  }, [kind, tick]);

  const play = (url?: string | null) => { if (url) new Audio(getMediaUrl(url)).play().catch(() => {}); };
  const ask = async () => {
    if (!me) { navigate('/profile'); return; }
    if (text.trim().length < 2) { toast.error('Escriu què vols saber dir'); return; }
    setAsking(true);
    try { await api.addPetition(text.trim(), note.trim() || null); setText(''); setNote(''); toast.success('Demanat. Quan algú ho gravi, ho veuràs aquí.'); setKind('open'); setTick((t) => t + 1); }
    catch (e: any) { toast.error(e?.message || 'No s’ha pogut demanar'); }
    finally { setAsking(false); }
  };
  const [opening, setOpening] = useState(false);
  // Admin: everything the library cannot say out loud becomes a request, in one pass inside the
  // server. 581 sentences outside the Beni Mellal deck and some 246 inside it, "yan", "Azul!" and
  // "nkk" among them: the first hour of the course has no voice.
  const askEverything = async () => {
    setOpening(true);
    try {
      const r = await api.askForEveryMissingVoice();
      toast.success(`${r.asked} frases demanades a les nostres veus`);
      setTick((t) => t + 1);
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut demanar'); }
    finally { setOpening(false); }
  };
  const tab = TABS.find((t) => t.kind === kind)!;

  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Si us plau, necessitem la teva veu</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: '14.5px', margin: '0 0 10px', lineHeight: 1.6 }}>
        Aquesta biblioteca només té el que la gent hi ha posat. Una frase escrita i muda ensenya a
        llegir-la, no a dir-la, i una veu de màquina no ensenya a parlar amb ningú: per això una
        frase no està acabada fins que algú la diu.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 10, margin: '0 0 16px' }}>
        {[
          ['Grava’n una que sàpigues dir', 'Prem el micròfon de qualsevol frase. Trenta segons i ja està.'],
          ['Digue-la com la dius tu', 'Amb les teves paraules i la teva manera d’escriure-la: no cal seguir cap ortografia, i si al teu poble es diu d’una altra manera, aquesta és la bona.'],
          ['Queda amb el teu nom', 'Cada veu porta qui parla i de quin poble és. Qui l’escolti sabrà de qui està aprenent.'],
          ['Demana el que vols saber dir', 'Si no saps com es diu una cosa, escriu-la en català aquí sota i algú que ho sàpiga la gravarà.'],
        ].map(([t, w]) => (
          <div key={t} style={{ padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
            <div style={{ fontWeight: 800, fontSize: 13.5, marginBottom: 2 }}>{t}</div>
            <div style={{ fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.5 }}>{w}</div>
          </div>
        ))}
      </div>

      {me?.is_admin && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
          <button onClick={askEverything} disabled={opening} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit', opacity: opening ? 0.6 : 1 }}>
            {opening ? 'Demanant…' : 'Demana veu per a tot el que no en té'}
          </button>
        </div>
      )}

      <div style={{ padding: 14, borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', marginBottom: 18 }}>
        <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Demana com es diu</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="En català: p. ex. «Bon profit!»" style={{ padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', fontSize: 15, fontFamily: 'inherit', background: 'var(--surface-2)', color: 'var(--text)' }} />
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Context (opcional): a qui ho diries, quan…" style={{ padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', fontSize: 14, fontFamily: 'inherit', background: 'var(--surface-2)', color: 'var(--text)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{me ? `Ho demanes com a ${me.display_name || me.username}` : 'Cal identificar-se per demanar'}</span>
            <button onClick={ask} disabled={asking} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}><FaPaperPlane size={12} /> {me ? 'Demana-ho' : 'Identifica’t'}</button>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        {TABS.map((t) => <button key={t.kind} onClick={() => setKind(t.kind)} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: kind === t.kind ? 'var(--brand-1)' : 'var(--surface)', color: kind === t.kind ? '#fff' : 'var(--text)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 }}>{t.label}</button>)}
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-soft)', margin: '0 0 12px' }}>{tab.blurb}{items ? ` · ${total}` : ''}</p>

      {/* Una llista que no s'ha pogut portar no pot semblar una llista buida. */}
      {!items && listFailed
        ? <div style={{ color: 'var(--text-soft)', fontSize: 14 }}>
            No s’ha pogut portar la llista.{' '}
            <button onClick={() => setTick((t) => t + 1)} style={{ background: 'transparent', border: 'none', padding: 0, color: 'var(--brand-1)', fontWeight: 700, fontSize: 'inherit', cursor: 'pointer', fontFamily: 'inherit' }}>Torna-ho a provar</button>
          </div>
        : !items && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
      {items && items.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Res pendent aquí.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items?.map((it) => {
          const d = it.drill;
          return (
            <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}>
              {d.image_url && <img src={getMediaUrl(d.image_url)} alt="" style={{ width: 56, height: 42, objectFit: 'cover', borderRadius: 'var(--r-sm)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 800, color: 'var(--text)', fontSize: 15 }}>{d.text_tachelhit || <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>encara sense amazic</span>}</div>
                <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {it.requested_by ? `Ho demana ${it.requested_by}` : d.region ? d.region : 'sense lloc'}{it.note ? ` · ${it.note}` : ''}{it.units.length ? ` · ${it.units.join(', ')}` : ''}
                </div>
              </div>
              {(d.audio_url || d.audio_tts_shi_url) && <button onClick={() => play(d.audio_url || d.audio_tts_shi_url)} aria-label="Escolta" title={d.audio_url ? 'Veu gravada' : 'Veu sintètica'} style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : 'var(--sky)', color: '#fff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={12} /></button>}
              <button onClick={() => setRecording(d)} aria-label="Grava-ho tu" title="Grava-ho a la teva manera" style={{ flexShrink: 0, width: 38, height: 38, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaMicrophone size={15} /></button>
            </div>
          );
        })}
      </div>
      {recording && <RecordAudioModal drill={recording} onClose={() => setRecording(null)} onSaved={() => { setRecording(null); setTick((t) => t + 1); }} />}
    </div>
  );
}
