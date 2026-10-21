import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaMicrophone, FaPaperPlane, FaVolumeUp } from 'react-icons/fa';
import { api, type PetitionItem, type Me } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';
import RecordAudioModal from './RecordAudioModal';

// Veus: what the community can record. A learner asks how to say something (a petition: Catalan
// only); a native speaker answers with their voice and their own spelling, and says where they are
// from. Drills that only have a synthetic voice are listed too, the basic units first, and the
// sentences our Aït Mraw speakers could say in their words.

type Kind = 'open' | 'synthetic' | 'aitmraw';
const TABS: { kind: Kind; label: string; blurb: string }[] = [
  { kind: 'open', label: 'Demanades', blurb: 'Frases que algú vol saber dir. Si les saps, grava-les: la teva manera de dir-ho i d’escriure-ho és la bona.' },
  { kind: 'synthetic', label: 'Sense veu humana', blurb: 'Frases que de moment només tenen una veu sintètica. Les unitats bàsiques del curs van primer.' },
  { kind: 'aitmraw', label: 'Per a Aït Mraw', blurb: 'Frases d’altres llocs que valdria la pena sentir dites a Aït Mraw (Halima, Driss).' },
];

export default function VeusPage() {
  const navigate = useNavigate();
  const [kind, setKind] = useState<Kind>('open');
  const [items, setItems] = useState<PetitionItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [me, setMe] = useState<Me | null>(null);
  const [recording, setRecording] = useState<Drill | null>(null);
  const [asking, setAsking] = useState(false);
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => { api.me().then(setMe).catch(() => setMe(null)); }, []);
  useEffect(() => {
    setItems(null);
    api.petitions(kind).then((r) => { setItems(r.items); setTotal(r.total); }).catch(() => toast.error('No s’ha pogut carregar la llista'));
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
  const tab = TABS.find((t) => t.kind === kind)!;

  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: '0 0 4px' }}>Veus</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: '14px', margin: '0 0 14px', lineHeight: 1.5 }}>
        La biblioteca creix amb les veus de qui parla amazic. Demana una frase, o grava les que saps dir: pots fer servir l’escriptura que ja hi ha o escriure-ho com ho dius tu. Digue’ns de quin poble ets: cada veu porta el seu lloc.
      </p>

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

      {!items && <div style={{ color: 'var(--text-muted)' }}>Carregant…</div>}
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
