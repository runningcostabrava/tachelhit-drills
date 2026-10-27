import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { FaMicrophone, FaStop, FaSave, FaTrash, FaTimes, FaPlay } from 'react-icons/fa';
import { API_BASE, getMediaUrl } from '../config';
import { api, type Recording } from '../api';
import { toast } from '../toast';
import { varietyShort, varietyLabel, VARIETIES } from '../varieties';
import type { Drill } from '../types';

// Multi-speaker takes for one drill: the same phrase can carry recordings from
// different people/varieties. Lists every take (each tagged with its speaker's
// variety) and lets you add your own — the backend tags it with your declared
// variety automatically.
export default function RecordAudioModal({ drill, onClose, onSaved }: {
  drill: Drill;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [recs, setRecs] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);
  const [recording, setRecording] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // "Com ho dius tu?": the sentence in the recorder's own words (prefilled with the drill's),
  // their variety and their town. Only a different wording is kept by the server.
  const [ownText, setOwnText] = useState(drill.text_tachelhit || '');
  const [ownVariety, setOwnVariety] = useState('');
  const [ownTown, setOwnTown] = useState('');
  // the speaker's declared profile: a take without a place is not accepted (every voice carries its town)
  const [profile, setProfile] = useState<{ variety: string | null; region: string | null; is_native?: boolean | null } | null | undefined>(undefined);
  useEffect(() => { api.me().then((m) => setProfile(m ? { variety: m.variety ?? null, region: m.region ?? null } : null)).catch(() => setProfile(null)); }, []);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const load = () => {
    setLoading(true);
    api.drillRecordings(drill.id).then(setRecs).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(load, [drill.id]);
  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);

  const play = (url: string) => { const a = new Audio(getMediaUrl(url)); a.play().catch(() => {}); };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const b = new Blob(chunks.current, { type: mr.mimeType || 'audio/webm' });
        setBlob(b);
        setBlobUrl((p) => { if (p) URL.revokeObjectURL(p); return URL.createObjectURL(b); });
      };
      recRef.current = mr;
      mr.start();
      setRecording(true);
    } catch {
      toast.error('No s\'ha pogut accedir al micròfon. Comprova els permisos del navegador.');
    }
  };
  const stop = () => { recRef.current?.stop(); setRecording(false); };

  // Asked before the first take and then remembered: the library needs to know whether a voice is
  // a native speaker's. Nobody is kept out — a learner's take is welcome, it is just labelled.
  const [isNative, setIsNative] = useState<boolean | null>(null);
  const mustAsk = profile != null && (profile.is_native === undefined || profile.is_native === null) && isNative === null;

  const saveTake = async () => {
    if (!blob) return;
    setBusy(true);
    try {
      const ext = blob.type.includes('webm') ? 'webm' : blob.type.includes('mp4') ? 'mp4' : 'ogg';
      if (!ownTown.trim() && !profile?.region) { toast.error('Digues de quin poble o zona ets: cada veu porta el seu lloc.'); setBusy(false); return; }
      if (!ownVariety && !profile?.variety) { toast.error('Tria la teva varietat (o la més propera).'); setBusy(false); return; }
      const fd = new FormData();
      fd.append('file', blob, `take_${drill.id}.${ext}`);
      if (ownText.trim()) fd.append('text', ownText.trim());
      if (ownVariety) fd.append('variety', ownVariety);
      if (ownTown.trim()) fd.append('region', ownTown.trim());
      // whose voice this is: a learner's take must never pass for a model pronunciation
      const native = isNative ?? profile?.is_native;
      if (native !== undefined && native !== null) fd.append('is_native', String(native));
      const res = await fetch(`${API_BASE}/drills/${drill.id}/recordings`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'upload failed');
      const saved = await res.json().catch(() => null);
      toast.success(saved?.variant_id ? 'Veu afegida. Com que ho dius amb altres paraules, ara hi ha una targeta pròpia amb la teva versió, enllaçada a aquesta.' : 'Veu afegida');
      if (profile && isNative !== null && profile.is_native === undefined) api.updateMe({ is_native: isNative }).catch(() => {});
      if (profile !== undefined && profile !== null && (!profile.region || !profile.variety) && (ownTown.trim() || ownVariety)) {
        api.updateMe({ ...(ownTown.trim() && !profile.region ? { region: ownTown.trim() } : {}), ...(ownVariety && !profile.variety ? { variety: ownVariety } : {}) }).catch(() => {});
      }
      setBlob(null);
      setBlobUrl(null);
      load();
      onSaved();
    } catch (e: any) {
      toast.error(e.message || 'No s\'ha pogut desar la veu');
    } finally { setBusy(false); }
  };

  const del = async (id: number) => {
    setBusy(true);
    try { await api.deleteRecording(id); load(); onSaved(); }
    catch { toast.error('No s\'ha pogut esborrar'); }
    finally { setBusy(false); }
  };

  // the drill's primary audio, shown as a take if it isn't already in the list
  const primary = (drill.audio_url || '').trim();
  const inList = new Set(recs.map((r) => r.audio_url));
  const showPrimary = !!primary && !inList.has(primary);
  const varieties = new Set(recs.map((r) => r.variety).filter(Boolean));
  const takeCount = recs.length + (showPrimary ? 1 : 0);

  const badge = (v?: string | null) => v ? (
    <span title={varietyLabel(v)} style={{ fontSize: '10px', fontWeight: 800, letterSpacing: '0.03em', background: 'var(--saffron-soft)', color: 'var(--saffron-strong)', padding: '2px 7px', borderRadius: 'var(--r-pill)' }}>{varietyShort(v)}</span>
  ) : null;

  const takeRow = (key: string, label: string, url: string, v?: string | null, region?: string | null, onDelete?: () => void, ownWords?: string | null) => (
    <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
      <button onClick={() => play(url)} aria-label="Reprodueix" style={{ flexShrink: 0, width: 34, height: 34, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-1)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaPlay size={12} /></button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
          {badge(v)}
          {region && <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{region}</span>}
        </div>
        {ownWords && <div style={{ fontSize: '13px', color: 'var(--brand-1)', marginTop: '4px', fontWeight: 600 }} title="Com ho diu aquesta persona">{ownWords}</div>}
      </div>
      {onDelete && (
        <button onClick={onDelete} disabled={busy} aria-label="Esborra la veu" style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--rose)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaTrash size={12} /></button>
      )}
    </div>
  );

  return createPortal(
    <div role="dialog" aria-label="Veus d'aquest drill" style={{ position: 'fixed', inset: 0, zIndex: 30000, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(33,28,21,0.5)', padding: '16px' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(460px, 96vw)', maxHeight: '90vh', overflowY: 'auto', background: 'var(--surface)', borderRadius: 'var(--r-xl)', padding: '20px', boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text)' }}>Veus d&apos;aquest drill</h2>
          <button onClick={onClose} aria-label="Tanca" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', width: 34, height: 34, cursor: 'pointer', color: 'var(--text-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaTimes /></button>
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-soft)', marginBottom: '4px' }}>{drill.text_catalan || `Drill #${drill.id}`}</div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px' }}>
          {takeCount === 0 ? 'Encara no hi ha cap gravació.' : `${takeCount} ${takeCount === 1 ? 'veu' : 'veus'}${varieties.size > 1 ? ` · ${varieties.size} varietats` : ''}`}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
          {loading && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Carregant…</div>}
          {showPrimary && takeRow('primary', 'Àudio principal', primary, drill.variety, drill.region)}
          {/* La paperera només damunt de la teva presa: la veu d'un altre no l'has d'esborrar tu,
              i oferir-ho era convidar a fer-ho. El servidor ho impedeix igualment. */}
          {recs.map((r) => takeRow(`r${r.id}`, r.speaker || 'Anònim', r.audio_url, r.variety, r.region, r.mine ? () => del(r.id) : undefined, r.text))}
        </div>

        {/* record a new take */}
        <div style={{ paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>Afegeix la teva veu</div>
          <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-soft)', marginBottom: '8px' }}>
            Com ho dius tu? Si al teu poble es diu amb altres paraules, escriu-les.
            <textarea value={ownText} onChange={(e) => setOwnText(e.target.value)} rows={2} aria-label="La frase amb les teves paraules" style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: '4px', padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: '14px', fontFamily: 'inherit' }} />
          </label>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
            <select value={ownVariety} onChange={(e) => setOwnVariety(e.target.value)} aria-label="La teva varietat" style={{ flex: '1 1 160px', minWidth: 0, padding: '8px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: '13px' }}>
              <option value="">Varietat: la del meu perfil</option>
              {VARIETIES.map((v) => <option key={v.code} value={v.code}>{v.label}</option>)}
            </select>
            <input value={ownTown} onChange={(e) => setOwnTown(e.target.value)} placeholder="El teu poble (opcional)" aria-label="El teu poble" style={{ flex: '1 1 140px', minWidth: 0, padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: '13px' }} />
          </div>
          {blobUrl && <audio controls src={blobUrl} style={{ width: '100%', marginBottom: '10px' }} />}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {!recording ? (
              <button onClick={start} disabled={busy} style={btn('var(--rose)', '#fff')}><FaMicrophone /> {blob ? 'Torna a gravar' : 'Grava'}</button>
            ) : (
              <button onClick={stop} style={btn('var(--rose)', '#fff')}><FaStop /> Atura</button>
            )}
            {blob && !recording && (
              <button onClick={saveTake} disabled={busy || mustAsk} style={{ ...btn('var(--brand-1)', '#fff'), opacity: mustAsk ? 0.55 : 1 }}><FaSave /> {busy ? 'Desant…' : 'Desa aquesta veu'}</button>
            )}
          </div>
          {blob && !recording && mustAsk && (
            <div style={{ marginTop: '10px', padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>Parles amazic de tota la vida?</div>
              <div style={{ fontSize: '12px', color: 'var(--text-soft)', marginBottom: 8, lineHeight: 1.45 }}>Les dues veus hi tenen lloc; només cal saber quina és quina, perquè qui aprèn sàpiga a qui imitar.</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button onClick={() => setIsNative(true)} style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}>Sí, és la meva llengua</button>
                <button onClick={() => setIsNative(false)} style={{ padding: '7px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}>No, l&apos;estic aprenent</button>
              </div>
            </div>
          )}
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>La teva gravació es desa amb la teva varietat i les teves paraules, sense esborrar les altres veus ni el text del drill.</div>
        </div>
      </div>
    </div>,
    document.body
  );
}

function btn(bg: string, color: string): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', background: bg, color, border: '1px solid transparent' };
}
