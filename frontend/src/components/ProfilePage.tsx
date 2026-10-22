import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserToken, isNativeApp, setUserIdentity, clearUserIdentity } from '../config';
import { Share } from '@capacitor/share';
import { syncManager } from '../services/OfflineSyncManager';
import { api, type AdminUser, type Me, type MailSettings } from '../api';
import { toast } from '../toast';
import { AiSpendAdmin } from './AiQuota';
import { VARIETIES } from '../varieties';
import { FaCheck, FaLayerGroup, FaRedo, FaFire } from 'react-icons/fa';

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-xl)',
  boxShadow: 'var(--shadow-sm)',
  padding: '24px',
  marginBottom: '20px',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 'var(--r-md)',
  border: '1px solid var(--border)',
  background: 'var(--surface-2)',
  fontSize: '15px',
  color: 'var(--text)',
  marginBottom: '12px',
};

// Admin: the mail sender, set from the app itself so nobody has to open the hosting dashboard.
// The password is stored on the server and never comes back to the browser.
function AdminMailSettings() {
  const [s, setS] = useState<MailSettings | null>(null);
  const [host, setHost] = useState(''); const [port, setPort] = useState(''); const [user, setUser] = useState('');
  const [pass, setPass] = useState(''); const [from, setFrom] = useState('');
  const [prov, setProv] = useState(''); const [apiKey, setApiKey] = useState('');
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState<string | null>(null); const [err, setErr] = useState<string | null>(null);
  const load = () => api.adminMailGet().then((r) => { setS(r); setHost(r.SMTP_HOST || ''); setPort(r.SMTP_PORT || '587'); setUser(r.SMTP_USER || ''); setFrom(r.SMTP_FROM || ''); setProv(r.MAIL_API_PROVIDER || ''); }).catch(() => {});
  useEffect(() => { load(); }, []);
  const save = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try {
      const r = await api.adminMailSet({ SMTP_HOST: host.trim(), SMTP_PORT: port.trim(), SMTP_USER: user.trim(), SMTP_FROM: (from.trim() || user.trim()), ...(pass.trim() ? { SMTP_PASS: pass.trim() } : {}), MAIL_API_PROVIDER: prov.trim() || '-', ...(apiKey.trim() ? { MAIL_API_KEY: apiKey.trim() } : {}) });
      setS(r); setPass(''); setApiKey(''); setMsg(r.ready ? 'Desat. Ja es poden enviar correus.' : 'Desat, però encara falten dades.');
    } catch (e: any) { setErr(e?.message || 'No s’ha pogut desar'); } finally { setBusy(false); }
  };
  const test = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try { const r = await api.adminMailTest(); setMsg(`Correu de prova enviat a ${r.sent_to}.`); }
    catch (e: any) { setErr(e?.message || 'No s’ha pogut enviar'); } finally { setBusy(false); }
  };
  const field = { padding: '9px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '14px', width: '100%', boxSizing: 'border-box' as const };
  return (
    <div style={{ marginTop: '18px', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)' }}>
      <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Correu de sortida {s ? (s.ready ? '· a punt' : '· incomplet') : ''}</div>
      <p style={{ margin: '0 0 10px', fontSize: '13px', color: 'var(--text-soft)', lineHeight: 1.45 }}>Amb un compte de Gmail dedicat: servidor smtp.gmail.com, port 587, l’adreça completa i una <strong>contrasenya d’aplicació</strong> de Google (no la del compte).</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '8px' }}>
        <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="smtp.gmail.com" style={field} />
        <input value={port} onChange={(e) => setPort(e.target.value)} placeholder="587" style={field} />
        <input value={user} onChange={(e) => setUser(e.target.value)} placeholder="adreça@gmail.com" style={field} />
        <input value={from} onChange={(e) => setFrom(e.target.value)} placeholder="remitent (per defecte, la mateixa)" style={field} />
        <input value={pass} onChange={(e) => setPass(e.target.value)} type="password" autoComplete="new-password" placeholder={s?.has_password ? 'contrasenya desada · escriu-ne una de nova per canviar-la' : 'contrasenya d’aplicació (16 lletres)'} style={field} />
      </div>
      <p style={{ margin: '10px 0 6px', fontSize: '13px', color: 'var(--text-soft)', lineHeight: 1.45 }}>Si el servidor no pot obrir connexions SMTP (error «Network is unreachable»), fes servir un proveïdor per HTTPS: escriu <strong>resend</strong> o <strong>brevo</strong> i la seva clau d’API. El remitent ha de ser una adreça verificada al proveïdor.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '8px' }}>
        <input value={prov} onChange={(e) => setProv(e.target.value)} placeholder="proveïdor: resend o brevo" style={field} />
        <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" autoComplete="new-password" placeholder={s?.has_api_key ? 'clau desada · escriu-ne una de nova' : 'clau d’API del proveïdor'} style={field} />
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
        <button onClick={save} disabled={busy} style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px' }}>{busy ? 'Desant…' : 'Desa'}</button>
        <button onClick={test} disabled={busy || !s?.ready} style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', opacity: busy || !s?.ready ? 0.6 : 1 }}>Envia’m una prova</button>
      </div>
      {msg && <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--emerald)' }}>{msg}</div>}
      {err && <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--rose)' }}>{err}</div>}
    </div>
  );
}

// The handle people see. It can be changed: nothing a person has given the library hangs on the
// name (takes, drills, proposals all hang on the account), and a handle typed in haste at sign-up
// should not follow somebody about for ever.
function Handle({ me, onChanged }: { me: Me; onChanged: (u: { username: string; display_name: string }) => void }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(me.username);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const u = await api.changeUsername(name.trim().toLowerCase());
      onChanged({ username: u.username, display_name: u.display_name });
      setUserIdentity(getUserToken() || '', u.username);
      setEditing(false);
    } catch (e: any) { setErr(e?.message || 'No s’ha pogut canviar'); }
    finally { setBusy(false); }
  };
  if (!editing) {
    return (
      <p style={{ color: 'var(--text-muted)', margin: '0 0 16px', fontSize: '14px' }}>
        @{me.username}
        <button onClick={() => { setName(me.username); setEditing(true); }} style={{ marginLeft: 8, padding: 0, border: 'none', background: 'none', color: 'var(--brand-1)', fontSize: '12px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>canvia’l</button>
      </p>
    );
  }
  return (
    <div style={{ margin: '0 0 16px' }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--text-muted)' }}>@</span>
        <input value={name} onChange={(e) => setName(e.target.value)} autoFocus maxLength={32} placeholder="pablo"
               style={{ flex: 1, minWidth: 140, padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '14px' }} />
        <button onClick={save} disabled={busy || name.trim().length < 3} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', opacity: busy || name.trim().length < 3 ? 0.6 : 1 }}>{busy ? 'Desant…' : 'Desa'}</button>
        <button onClick={() => { setEditing(false); setErr(null); }} style={{ padding: 0, border: 'none', background: 'none', color: 'var(--text-soft)', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}>deixa-ho</button>
      </div>
      <div style={{ fontSize: '12px', color: err ? 'var(--rose)' : 'var(--text-muted)', marginTop: 4 }}>{err || 'De 3 a 32 caràcters: lletres sense accent, xifres, _ - .'}</div>
    </div>
  );
}


// Admin: who is in this library, and who administers it. Being an administrator used to live in
// an environment variable on the host — now it is a row anyone with the keys can change, with the
// two guards the server keeps: you cannot demote yourself, and the last admin stays.
function AdminPeople() {
  const [people, setPeople] = useState<AdminUser[] | null>(null);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState<number | null>(null);
  const load = (needle?: string) => api.adminUsers(needle).then((r) => setPeople(r.users)).catch(() => setPeople([]));
  useEffect(() => { load(); }, []);
  const flip = async (u: AdminUser) => {
    setBusy(u.id);
    try {
      const r = await api.setAdmin(u.id, !u.is_admin);
      setPeople((ps) => (ps || []).map((p) => (p.id === u.id ? { ...p, is_admin: r.is_admin } : p)));
      toast.success(r.is_admin ? `@${r.username} ja pot administrar` : `@${r.username} ja no administra`);
    } catch (e: any) { toast.error(e?.message || 'No s’ha pogut canviar'); }
    finally { setBusy(null); }
  };
  return (
    <div style={{ marginTop: '18px', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)' }}>
      <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Qui hi ha i qui administra</div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') load(q.trim() || undefined); }}
               placeholder="busca per nom o correu"
               style={{ flex: 1, minWidth: 140, padding: '8px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '13px' }} />
        <button onClick={() => load(q.trim() || undefined)} style={{ padding: '8px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}>Busca</button>
      </div>
      {people === null && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Carregant…</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {(people || []).map((u) => (
          <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 'var(--r-md)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text)' }}>
                {u.display_name || u.username} <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>@{u.username}</span>
                {u.is_native === true && <span style={{ marginLeft: 6, fontSize: '11px', color: 'var(--emerald)', fontWeight: 700 }}>parla amazic</span>}
                {u.is_native === false && <span style={{ marginLeft: 6, fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700 }}>l’aprèn</span>}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {u.email || 'sense correu'} · {u.drills} drills · {u.takes} veus{u.region ? ` · ${u.region}` : ''}
              </div>
            </div>
            <button onClick={() => flip(u)} disabled={busy === u.id} style={{ flexShrink: 0, padding: '6px 12px', borderRadius: 'var(--r-pill)', border: `1px solid ${u.is_admin ? 'var(--brand-1)' : 'var(--border)'}`, background: u.is_admin ? 'var(--brand-1)' : 'var(--surface)', color: u.is_admin ? '#fff' : 'var(--text-soft)', fontWeight: 700, fontSize: '12px', cursor: 'pointer', fontFamily: 'inherit', opacity: busy === u.id ? 0.6 : 1 }}>
              {u.is_admin ? 'administra' : 'fes-lo administrador'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}


// Admin: a reset code for someone who cannot receive e-mail (no mail server configured yet).
// The admin passes the code on by hand; the person uses «Ja tinc un codi» on the sign-in page.
function AdminResetCode() {
  const [login, setLogin] = useState('');
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<{ username: string; email: string; code: string; expires_in_hours: number; mailed: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const go = async () => {
    setBusy(true); setErr(null); setOut(null);
    try { setOut(await api.adminResetCode(login.trim())); }
    catch (e: any) { setErr(e?.message || 'No s’ha pogut generar el codi'); }
    finally { setBusy(false); }
  };
  return (
    <div style={{ marginTop: '18px', padding: '14px', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)' }}>
      <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Codi per restablir una contrasenya</div>
      <p style={{ margin: '0 0 8px', fontSize: '13px', color: 'var(--text-soft)', lineHeight: 1.45 }}>Per a qui no pot rebre el correu. Dona-li el codi i que faci servir «Ja tinc un codi» a la pantalla d’entrada.</p>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <input value={login} onChange={(e) => setLogin(e.target.value)} placeholder="correu o nom d’usuari" style={{ flex: 1, minWidth: 180, padding: '9px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit', fontSize: '14px' }} />
        <button onClick={go} disabled={busy || login.trim().length < 3} style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', opacity: busy || login.trim().length < 3 ? 0.6 : 1 }}>{busy ? 'Generant…' : 'Genera el codi'}</button>
      </div>
      {err && <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--rose)' }}>{err}</div>}
      {out && (
        <div style={{ marginTop: '10px', padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '24px', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--brand-1)' }}>{out.code}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-soft)' }}>@{out.username} · {out.email} · caduca en {out.expires_in_hours} h{out.mailed ? ' · també enviat per correu' : ' · el servidor no envia correu: passa-l’hi tu'}</div>
        </div>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [streak, setStreak] = useState<{ streak_days: number; reviews_week: number } | null>(null);
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [tokenInput, setTokenInput] = useState('');
  const [newToken, setNewToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [variety, setVariety] = useState('');
  const [region, setRegion] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [savedProfile, setSavedProfile] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [tokenCopied, setTokenCopied] = useState(false);
  const [deadCount, setDeadCount] = useState(0);
  const [deadBusy, setDeadBusy] = useState(false);
  useEffect(() => { syncManager.getDeadLetters().then(d => setDeadCount(d.length)).catch(() => {}); }, []);
  const hasToken = !!getUserToken();
  const initialLoading = hasToken && !me && !newToken && !error;

  const copyToken = () => {
    if (!newToken) return;
    navigator.clipboard.writeText(newToken).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  useEffect(() => {
    if (!hasToken) return;
    api.me()
      .then((data) => {
        if (data) { setMe(data); setVariety(data.variety || ''); setRegion(data.region || ''); }
        else { clearUserIdentity(); setError('El token ja no és vàlid. Torna a iniciar sessió.'); }
      })
      .catch((e: any) => {
        if (e?.status === 401 || e?.code === 'unauthorized') {
          clearUserIdentity();
          // Happens more since changing a password closes every other session: the browser was
          // holding a token that no longer exists. Say that, instead of blaming the network.
          setError('La teva sessió s’ha acabat. Torna a entrar-hi.');
        } else {
          setError('No s\'ha pogut carregar el perfil (sense connexió?). Torna-ho a provar.');
        }
      });
    api.reviewStreak().then(setStreak).catch(() => {});
  }, [hasToken]);

  const register = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await api.register(username.trim(), displayName.trim() || null, variety || null, region.trim() || null);
      setUserIdentity(data.token, data.username);
      setNewToken(data.token);
      setMe(null); // will refetch via effect on next mount; show token first
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const loginWithToken = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setUserIdentity(t, '');
    window.location.reload();
  };

  const logout = async () => {
    const msg = me?.has_password
      ? 'Tancar la sessió en aquest dispositiu? Podràs tornar a entrar amb el correu i la contrasenya.'
      : 'Segur que vols tancar la sessió? Aquest compte no té contrasenya: necessitaràs el teu token per tornar a entrar.';
    if (!window.confirm(msg)) return;
    try { await api.logout(); } catch { /* the token may already be gone */ }
    clearUserIdentity();
    window.location.href = '/signin';
  };

  // Account: attach e-mail + password to a token identity, or change the password.
  const [accEmail, setAccEmail] = useState('');
  const [accPw, setAccPw] = useState('');
  const [accOld, setAccOld] = useState('');
  const [accBusy, setAccBusy] = useState(false);
  const [accMsg, setAccMsg] = useState<string | null>(null);
  const attach = async () => {
    setAccBusy(true); setAccMsg(null);
    try {
      const r = await api.attachCredentials(accEmail.trim(), accPw);
      setMe((m) => (m ? { ...m, email: r.email, has_password: true, is_admin: r.is_admin } : m));
      setAccMsg('Fet: ara pots entrar amb el correu i la contrasenya des de qualsevol dispositiu.');
      setAccPw('');
    } catch (e: any) { setAccMsg(e?.message || 'Error'); } finally { setAccBusy(false); }
  };
  const changePw = async () => {
    setAccBusy(true); setAccMsg(null);
    try {
      await api.changePassword(accOld, accPw);
      setAccMsg('Contrasenya canviada.'); setAccOld(''); setAccPw('');
    } catch (e: any) { setAccMsg(e?.message || 'Error'); } finally { setAccBusy(false); }
  };

  const saveProfile = async () => {
    setSavingProfile(true);
    setSavedProfile(false);
    try {
      const updated = await api.updateMe({ variety: variety || null, region: region.trim() || null });
      setMe((m) => (m ? { ...m, variety: updated.variety, region: updated.region } : m));
      setSavedProfile(true);
      setTimeout(() => setSavedProfile(false), 1800);
    } catch {
      /* transient */
    } finally {
      setSavingProfile(false);
    }
  };

  // A reusable "where you're from" editor (variety + region)
  const originFields = (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <div style={{ flex: 1, minWidth: '180px' }}>
        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' }}>La meva varietat</label>
        <select value={variety} onChange={(e) => setVariety(e.target.value)} style={{ ...inputStyle, marginBottom: 0 }}>
          <option value="">— Tria la teva varietat —</option>
          {VARIETIES.map((v) => <option key={v.code} value={v.code}>{v.label}</option>)}
        </select>
      </div>
      <div style={{ flex: 1, minWidth: '180px' }}>
        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' }}>Regió / origen</label>
        <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="p. ex. Nador, Souss, diàspora-BCN" style={{ ...inputStyle, marginBottom: 0 }} />
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <div style={{
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        padding: '18px 24px',
      }}>
        <div style={{ maxWidth: '560px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Perfil</h1>
        </div>
      </div>

      <div style={{ maxWidth: '560px', margin: '0 auto', padding: '24px' }}>
        {error && (
          <div role="alert" style={{ padding: '12px 16px', background: 'var(--rose-soft)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', marginBottom: '16px', color: 'var(--rose)', fontWeight: 600 }}>
            {error}
          </div>
        )}

        {newToken && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0, fontFamily: 'var(--font-display)', fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}><FaCheck /> Compte creat!</h3>
            <p style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
              Aquest és el teu <strong>token personal</strong>. Guarda&apos;l en un lloc segur —
              és l&apos;única manera d&apos;iniciar sessió en altres dispositius i només es mostra ara.
            </p>
            <code style={{ display: 'block', padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', fontSize: '14px', wordBreak: 'break-all', border: '1px solid var(--border)' }}>
              {newToken}
            </code>
            <button
              type="button"
              onClick={copyToken}
              style={{ marginTop: '12px', padding: '10px 20px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer' }}
            >
              {copied ? 'Copiat!' : 'Copia el token'}
            </button>
            <br />
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{ marginTop: '16px', padding: '12px 24px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer' }}
            >
              L&apos;he guardat — continua
            </button>
          </div>
        )}

        {initialLoading && (
          <div style={cardStyle}>
            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>Carregant el teu perfil…</p>
          </div>
        )}

        {!newToken && hasToken && me && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0, fontFamily: 'var(--font-display)', fontSize: '22px' }}>{me.display_name || me.username}</h3>
            <Handle me={me} onChanged={(u) => setMe((m) => (m ? { ...m, username: u.username, display_name: u.display_name } : m))} />
            <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '18px' }}>
              <div style={{ padding: '12px 18px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--brand-1)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaLayerGroup /> {me.drills_contributed} drills aportats</span>
                <a href={`/u/${me.username}`} style={{ color: 'var(--brand-1)', fontWeight: 700, textDecoration: 'none' }}>La meva fitxa: tot el que he aportat →</a>
              </div>
              <div style={{ padding: '12px 18px', background: 'var(--emerald-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--emerald)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaRedo /> {me.cards_learning} targetes en aprenentatge</span>
              </div>
              {streak && streak.streak_days > 0 && (
                <div style={{ padding: '12px 18px', background: 'var(--amber-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--amber-strong)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaFire /> {streak.streak_days} {streak.streak_days === 1 ? 'dia' : 'dies'} seguits · {streak.reviews_week} repassos aquesta setmana</span>
                </div>
              )}
            </div>
            <div style={{ marginBottom: '18px', paddingTop: '18px', borderTop: '1px solid var(--border)' }}>
              {originFields}
              <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 700, marginBottom: '6px' }}>Compte</div>
                {me.email ? (
                  <div style={{ fontSize: '14px', color: 'var(--text-soft)', marginBottom: '8px' }}>{me.email}{me.is_admin ? ' · administrador' : ''}</div>
                ) : (
                  <div style={{ fontSize: '14px', color: 'var(--text-soft)', marginBottom: '8px' }}>Aquest compte només té un token. Afegeix-hi un correu i una contrasenya per entrar des de qualsevol dispositiu.</div>
                )}
                <form onSubmit={(e) => { e.preventDefault(); me.has_password ? changePw() : attach(); }} style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '380px' }}>
                  {!me.has_password && <input type="email" placeholder="Correu electrònic" value={accEmail} onChange={(e) => setAccEmail(e.target.value)} style={inputStyle} autoComplete="email" />}
                  {me.has_password && <input type="password" placeholder="Contrasenya actual" value={accOld} onChange={(e) => setAccOld(e.target.value)} style={inputStyle} autoComplete="current-password" />}
                  <input type="password" placeholder={me.has_password ? 'Contrasenya nova (mínim 8)' : 'Contrasenya (mínim 8)'} value={accPw} onChange={(e) => setAccPw(e.target.value)} style={inputStyle} autoComplete="new-password" />
                  <button type="submit" disabled={accBusy || accPw.length < 8 || (!me.has_password && !accEmail)} style={{ padding: '10px 16px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px', opacity: accBusy || accPw.length < 8 ? 0.6 : 1 }}>
                    {accBusy ? '…' : me.has_password ? 'Canvia la contrasenya' : 'Afegeix correu i contrasenya'}
                  </button>
                  {accMsg && <div style={{ fontSize: '13px', color: 'var(--text-soft)' }}>{accMsg}</div>}
                </form>
                {me.is_admin && <AdminPeople />}
                {me.is_admin && <AdminMailSettings />}
                {me.is_admin && <AdminResetCode />}
                {me.is_admin && <AiSpendAdmin />}
              </div>
              <button onClick={saveProfile} disabled={savingProfile} style={{ marginTop: '12px', padding: '10px 20px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: savingProfile ? 'wait' : 'pointer' }}>
                {savingProfile ? 'Desant…' : savedProfile ? 'Desat ✓' : "Desa l'origen"}
              </button>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', marginBottom: 0 }}>
                Els drills que aportis prendran aquesta varietat i regió per defecte, així sabem com es parla.
              </p>
            </div>
            <div style={{ marginBottom: '18px', paddingTop: '18px', borderTop: '1px solid var(--border)' }}>
              <div style={{ fontWeight: 700, marginBottom: '6px' }}>El teu token personal</div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '0 0 10px' }}>
                És l&apos;única manera de recuperar el compte en un altre dispositiu o després de reinstal·lar l&apos;app. Guarda&apos;l en un lloc segur.
              </p>
              {showToken ? (
                <code style={{ display: 'block', padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', fontSize: '13px', wordBreak: 'break-all', border: '1px solid var(--border)', marginBottom: '10px' }}>{getUserToken()}</code>
              ) : null}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setShowToken(v => !v)} style={{ padding: '10px 16px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>
                  {showToken ? 'Amaga' : 'Mostra el token'}
                </button>
                <button type="button" onClick={() => { navigator.clipboard.writeText(getUserToken()).then(() => { setTokenCopied(true); setTimeout(() => setTokenCopied(false), 1500); }); }} style={{ padding: '10px 16px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>
                  {tokenCopied ? 'Copiat!' : 'Copia'}
                </button>
                {isNativeApp() && (
                  <button type="button" onClick={() => Share.share({ title: 'Tamazight Drills · token', text: getUserToken() }).catch(() => {})} style={{ padding: '10px 16px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>
                    Desa / comparteix
                  </button>
                )}
              </div>
            </div>
            {deadCount > 0 && (
              <div style={{ marginBottom: '18px', padding: '12px 14px', background: 'var(--amber-soft)', border: '1px solid var(--amber)', borderRadius: 'var(--r-md)' }}>
                <div style={{ fontWeight: 700, color: 'var(--amber-strong)', marginBottom: '6px' }}>{deadCount} canvis no s&apos;han pogut sincronitzar</div>
                <p style={{ fontSize: '12px', color: 'var(--text-soft)', margin: '0 0 10px' }}>Han fallat diverses vegades (per exemple, un drill esborrat o un fitxer no acceptat).</p>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="button" disabled={deadBusy} onClick={async () => { setDeadBusy(true); try { await syncManager.retryDeadLetters(); } finally { setDeadBusy(false); syncManager.getDeadLetters().then(d => setDeadCount(d.length)); } }} style={{ padding: '8px 14px', background: 'var(--brand-1)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '40px' }}>Reintenta</button>
                  <button type="button" disabled={deadBusy} onClick={async () => { if (!window.confirm('Descartar aquests canvis pendents?')) return; await syncManager.discardDeadLetters(); setDeadCount(0); }} style={{ padding: '8px 14px', background: 'var(--surface)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '40px' }}>Descarta</button>
                </div>
              </div>
            )}
            <button
              onClick={logout}
              style={{ padding: '10px 20px', background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}
            >
              Tanca la sessió en aquest dispositiu
            </button>
          </div>
        )}

        {!newToken && !hasToken && (
          <>
            <div style={cardStyle}>
              <div style={{ marginBottom: '16px', padding: '14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', border: '1px solid var(--brand-1)' }}>
                <div style={{ fontWeight: 800, fontFamily: 'var(--font-display)', fontSize: '18px', marginBottom: '6px' }}>Entra amb el teu compte</div>
                <div style={{ fontSize: '14px', color: 'var(--text-soft)', marginBottom: '10px' }}>Correu i contrasenya: el teu progrés et segueix a qualsevol dispositiu.</div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <a href="/signin" style={{ padding: '10px 18px', background: 'var(--brand-gradient)', color: '#fff', borderRadius: 'var(--r-pill)', fontWeight: 700, textDecoration: 'none' }}>Inicia sessió</a>
                  <a href="/signin?mode=signup" style={{ padding: '10px 18px', background: 'var(--surface)', color: 'var(--brand-1)', border: '1px solid var(--brand-1)', borderRadius: 'var(--r-pill)', fontWeight: 700, textDecoration: 'none' }}>Crea un compte</a>
                </div>
              </div>
              <h3 style={{ marginTop: 0, fontFamily: 'var(--font-display)', fontSize: '20px' }}>O crea només una identitat amb token</h3>
              <p style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
                Amb un compte, el teu repàs (SRS) és només teu i els drills que creïs
                porten el teu nom com a contribuïdor.
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.5 }}>
                En registrar-te dónes el teu consentiment perquè les gravacions i textos
                que aportis es conservin al corpus per documentar i ensenyar la llengua.
                Pots indicar la llicència de cada contribució al camp «license».
              </p>
              <form onSubmit={(e) => { e.preventDefault(); register(); }}>
                <label htmlFor="profile-username" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' }}>Nom d&apos;usuari</label>
                <input
                  id="profile-username"
                  style={inputStyle}
                  autoComplete="username"
                  placeholder="Nom d'usuari (a-z, 0-9, _-.)"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <p style={{ margin: '-8px 0 12px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  Mínim 3 caràcters · lletres, xifres, _ - .
                </p>
                <label htmlFor="profile-display-name" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' }}>Nom per mostrar (opcional)</label>
                <input
                  id="profile-display-name"
                  style={inputStyle}
                  autoComplete="nickname"
                  placeholder="Nom per mostrar (opcional)"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
                <div style={{ margin: '4px 0 16px' }}>{originFields}</div>
                <p style={{ margin: '-8px 0 14px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  D&apos;on ets ho fem servir per saber en quina varietat parles — mai per corregir-la.
                </p>
                <button
                  type="submit"
                  disabled={busy || username.trim().length < 3}
                  style={{ padding: '12px 26px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: busy ? 'wait' : (username.trim().length < 3 ? 'not-allowed' : 'pointer'), opacity: username.trim().length < 3 ? 0.6 : 1 }}
                >
                  {busy ? 'Creant…' : 'Registra\'m'}
                </button>
              </form>
            </div>

            <div style={cardStyle}>
              <h3 style={{ marginTop: 0, fontFamily: 'var(--font-display)', fontSize: '20px' }}>Ja tens un token?</h3>
              <form onSubmit={(e) => { e.preventDefault(); loginWithToken(); }}>
                <label htmlFor="profile-token" style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' }}>El teu token personal</label>
                <input
                  id="profile-token"
                  style={inputStyle}
                  autoComplete="off"
                  spellCheck={false}
                  autoCapitalize="none"
                  placeholder="Enganxa el teu token personal"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={!tokenInput.trim()}
                  style={{ padding: '10px 22px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: tokenInput.trim() ? 'pointer' : 'not-allowed' }}
                >
                  Inicia sessió
                </button>
              </form>
            </div>
          </>
        )}
      </div>

      {/* What this app is built on. Some of those licences ask to be named where the work is
          used, and the only place a learner looks is inside the app. */}
      <p style={{ textAlign: 'center', margin: '28px 0 0', fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
        Aquesta app s’aguanta en feina d’altra gent.{' '}
        <button onClick={() => navigate('/credits')} style={{ background: 'transparent', border: 'none', padding: 0, color: 'var(--brand-1)', fontWeight: 700, fontSize: '12.5px', cursor: 'pointer', fontFamily: 'inherit' }}>
          Crèdits i fonts
        </button>
      </p>
    </div>
  );
}
