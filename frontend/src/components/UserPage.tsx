import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaChevronLeft, FaMapMarkerAlt, FaMicrophone, FaVolumeUp } from 'react-icons/fa';
import { api, type UserPublicPage, type ContributionDrill } from '../api';
import { getMediaUrl } from '../config';
import { varietyLabel } from '../varieties';

// A person's page («fitxa»): who they are and what they gave the library — the drills they
// created (petitions and variants among them), their takes with their own words, the lesson
// changes accepted. Public: no e-mail.

export default function UserPage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState<UserPublicPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (username) api.userPage(username).then(setPage).catch((e) => setError(e?.message || 'Error')); }, [username]);
  const play = (url?: string | null) => { if (url) new Audio(getMediaUrl(url)).play().catch(() => {}); };
  if (error) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>{error === 'User not found' ? 'No hi ha cap persona amb aquest nom.' : error}</div>;
  if (!page) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Carregant…</div>;
  const c = page.counts;
  const row = (d: ContributionDrill, extra?: string | null) => (
    <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
      {d.image_url && <img src={getMediaUrl(d.image_url)} alt="" style={{ width: 44, height: 33, objectFit: 'cover', borderRadius: 'var(--r-sm)', flexShrink: 0 }} onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, color: 'var(--text)', fontSize: 14 }}>{d.text_tachelhit || <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>encara sense amazic</span>}{d.variant_of ? <span style={{ marginLeft: 6, fontSize: 11, fontWeight: 800, color: 'var(--saffron-strong)' }}>variant</span> : null}</div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>{d.text_catalan}{d.region ? <span style={{ color: 'var(--text-muted)' }}> · {d.region}</span> : null}{extra ? <span style={{ color: 'var(--brand-1)', fontWeight: 600 }}> · {extra}</span> : null}</div>
      </div>
      <button onClick={() => play(d.audio_url)} disabled={!d.audio_url} aria-label="Escolta" style={{ flexShrink: 0, width: 30, height: 30, borderRadius: 'var(--r-pill)', border: 'none', background: d.audio_url ? 'var(--brand-1)' : 'var(--surface)', color: d.audio_url ? '#fff' : 'var(--text-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><FaVolumeUp size={12} /></button>
    </div>
  );
  return (
    <div style={{ padding: '20px 16px 32px', maxWidth: 900, margin: '0 auto' }}>
      <button onClick={() => navigate(-1)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: 6 }}><FaChevronLeft /> Enrere</button>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: '0 0 2px' }}>{page.display_name}</h1>
      <div style={{ fontSize: 13, color: 'var(--text-soft)', marginBottom: 14, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <span>@{page.username}</span>
        {page.region && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><FaMapMarkerAlt size={11} /> {page.region}</span>}
        {page.variety && <span>{varietyLabel(page.variety)}</span>}
        {page.since && <span>des de {new Date(page.since).toLocaleDateString('ca-ES', { month: 'short', year: 'numeric' })}</span>}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8, marginBottom: 20 }}>
        {[[c.drills, 'drills aportats'], [c.takes, 'veus gravades'], [c.variants, 'variants pròpies'], [c.petitions, 'peticions'], [c.proposals_accepted, 'canvis al curs acceptats']].map(([n, l]) => (
          <div key={String(l)} style={{ padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}><div style={{ fontSize: 22, fontWeight: 800 }}>{n}</div><div style={{ fontSize: 12, color: 'var(--text-soft)' }}>{l}</div></div>
        ))}
      </div>
      {page.takes.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 6 }}><FaMicrophone size={11} /> Veus gravades</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {page.takes.map((t) => row({ ...t.drill, audio_url: t.audio_url, region: t.region || t.drill.region }, t.text && t.text !== t.drill.text_tachelhit ? `ho diu: «${t.text}»` : null))}
          </div>
        </section>
      )}
      {page.drills.length > 0 && (
        <section>
          <h2 style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>Drills aportats</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{page.drills.map((d) => row(d))}</div>
        </section>
      )}
      {page.takes.length === 0 && page.drills.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Encara no ha aportat res.</div>}
    </div>
  );
}
