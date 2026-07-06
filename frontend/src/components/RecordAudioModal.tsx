import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { FaMicrophone, FaStop, FaSave, FaTrash, FaTimes, FaPlay } from 'react-icons/fa';
import { API_BASE, getMediaUrl } from '../config';
import { api, type Recording } from '../api';
import { toast } from '../toast';
import { varietyShort, varietyLabel } from '../varieties';
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

  const saveTake = async () => {
    if (!blob) return;
    setBusy(true);
    try {
      const ext = blob.type.includes('webm') ? 'webm' : blob.type.includes('mp4') ? 'mp4' : 'ogg';
      const fd = new FormData();
      fd.append('file', blob, `take_${drill.id}.${ext}`);
      const res = await fetch(`${API_BASE}/drills/${drill.id}/recordings`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'upload failed');
      toast.success('Veu afegida');
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

  const takeRow = (key: string, label: string, url: string, v?: string | null, region?: string | null, onDelete?: () => void) => (
    <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
      <button onClick={() => play(url)} aria-label="Reprodueix" style={{ flexShrink: 0, width: 34, height: 34, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-1)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaPlay size={12} /></button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
          {badge(v)}
          {region && <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{region}</span>}
        </div>
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
          {recs.map((r) => takeRow(`r${r.id}`, r.speaker || 'Anònim', r.audio_url, r.variety, r.region, () => del(r.id)))}
        </div>

        {/* record a new take */}
        <div style={{ paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>Afegeix la teva veu</div>
          {blobUrl && <audio controls src={blobUrl} style={{ width: '100%', marginBottom: '10px' }} />}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {!recording ? (
              <button onClick={start} disabled={busy} style={btn('var(--rose)', '#fff')}><FaMicrophone /> {blob ? 'Torna a gravar' : 'Grava'}</button>
            ) : (
              <button onClick={stop} style={btn('var(--rose)', '#fff')}><FaStop /> Atura</button>
            )}
            {blob && !recording && (
              <button onClick={saveTake} disabled={busy} style={btn('var(--brand-1)', '#fff')}><FaSave /> {busy ? 'Desant…' : 'Desa aquesta veu'}</button>
            )}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>La teva gravació es desa amb la teva varietat (del teu perfil), sense esborrar les altres veus.</div>
        </div>
      </div>
    </div>,
    document.body
  );
}

function btn(bg: string, color: string): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', background: bg, color, border: '1px solid transparent' };
}
