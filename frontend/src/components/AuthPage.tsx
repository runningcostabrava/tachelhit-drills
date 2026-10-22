import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { setUserIdentity, getUserToken, isNativeApp } from '../config';
import { VARIETIES } from '../varieties';
import { toast } from '../toast';

type Mode = 'login' | 'signup' | 'forgot' | 'reset';

const card: React.CSSProperties = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-sm)', padding: '22px', maxWidth: '440px', margin: '24px auto' };
const input: React.CSSProperties = { width: '100%', padding: '11px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: '15px', marginBottom: '10px', boxSizing: 'border-box' };
const label: React.CSSProperties = { display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-soft)', marginBottom: '4px' };
const primary: React.CSSProperties = { width: '100%', minHeight: '46px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '15px', cursor: 'pointer', boxShadow: 'var(--shadow-brand)' };
const link: React.CSSProperties = { background: 'none', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', fontSize: '14px', padding: 0 };

const device = () => (isNativeApp() ? 'app' : 'web') + ' · ' + (navigator.platform || '').slice(0, 30);

export default function AuthPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mode, setMode] = useState<Mode>((params.get('mode') as Mode) || 'login');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [variety, setVariety] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  // the sign-in field already holds «e-mail or user name»: the code path reuses it, so whatever
  // the person typed to sign in is still there when they go to reset
  const [noMail, setNoMail] = useState(false); // this server sends no e-mail: ask for a code
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (getUserToken()) navigate('/profile', { replace: true }); }, [navigate]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError(null);
    try { await fn(); } catch (e: any) { setError(e?.message || 'Error'); } finally { setBusy(false); }
  };

  const doLogin = () => run(async () => {
    const r = await api.login(login.trim(), password, device());
    setUserIdentity(r.token, r.username);
    toast.success(`Hola, ${r.display_name || r.username}!`);
    navigate('/', { replace: true });
  });
  const doSignup = () => run(async () => {
    const r = await api.signup({ email: email.trim(), password, username: username.trim().toLowerCase(), display_name: displayName.trim() || null, variety: variety || null, device: device() });
    setUserIdentity(r.token, r.username);
    toast.success('Compte creat. Benvingut!');
    navigate('/', { replace: true });
  });
  const doForgot = () => run(async () => {
    const r = await api.forgotPassword(email.trim());
    if (r.mail === false) { setNoMail(true); toast.success('Aquest servidor no envia correu: demana el codi.'); }
    else toast.success('Si el correu existeix, hi rebràs un codi de 6 xifres.');
    setMode('reset');
  });
  const doReset = () => run(async () => {
    const r = await api.resetPassword((login || email).trim(), code.trim(), password, device());
    setUserIdentity(r.token, r.username);
    toast.success('Contrasenya canviada.');
    navigate('/', { replace: true });
  });

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '12px' }}>
      <div style={card}>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
          {(['login', 'signup'] as Mode[]).map((m) => (
            <button key={m} onClick={() => { setMode(m); setError(null); }} aria-pressed={mode === m || (m === 'login' && (mode === 'forgot' || mode === 'reset'))}
              style={{ flex: 1, padding: '9px', borderRadius: 'var(--r-pill)', border: `1px solid ${mode === m ? 'var(--brand-1)' : 'var(--border)'}`, background: mode === m ? 'var(--brand-gradient-soft)' : 'var(--surface)', color: mode === m ? 'var(--brand-1)' : 'var(--text-soft)', fontWeight: 700, cursor: 'pointer' }}>
              {m === 'login' ? 'Inicia sessió' : 'Crea un compte'}
            </button>
          ))}
        </div>

        {mode === 'login' && (
          <form onSubmit={(e) => { e.preventDefault(); doLogin(); }}>
            <label style={label} htmlFor="auth-login">Correu o nom d'usuari</label>
            <input id="auth-login" style={input} value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus />
            <label style={label} htmlFor="auth-pw">Contrasenya</label>
            <input id="auth-pw" style={input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            <button type="submit" disabled={busy || !login || !password} style={{ ...primary, opacity: busy || !login || !password ? 0.6 : 1 }}>{busy ? 'Entrant…' : 'Entra'}</button>
            <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <button type="button" style={link} onClick={() => setMode('forgot')}>He oblidat la contrasenya</button>
              <button type="button" style={link} onClick={() => navigate('/profile?token=1')}>Tinc un token personal</button>
            </div>
          </form>
        )}

        {mode === 'signup' && (
          <form onSubmit={(e) => { e.preventDefault(); doSignup(); }}>
            <label style={label} htmlFor="su-email">Correu electrònic</label>
            <input id="su-email" style={input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" autoFocus />
            <label style={label} htmlFor="su-pw">Contrasenya (mínim 8 caràcters)</label>
            <input id="su-pw" style={input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
            <label style={label} htmlFor="su-user">Nom d'usuari (a-z, 0-9, _ - .)</label>
            <input id="su-user" style={input} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
            <label style={label} htmlFor="su-name">Com et dius (opcional)</label>
            <input id="su-name" style={input} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            <label style={label} htmlFor="su-var">La teva varietat (opcional)</label>
            <select id="su-var" style={input} value={variety} onChange={(e) => setVariety(e.target.value)}>
              <option value="">— Tria la teva varietat —</option>
              {VARIETIES.map((v) => <option key={v.code} value={v.code}>{v.label}</option>)}
            </select>
            <button type="submit" disabled={busy || !email || password.length < 8 || username.length < 3} style={{ ...primary, opacity: busy || !email || password.length < 8 || username.length < 3 ? 0.6 : 1 }}>{busy ? 'Creant…' : 'Crea el compte'}</button>
          </form>
        )}

        {mode === 'forgot' && (
          <form onSubmit={(e) => { e.preventDefault(); doForgot(); }}>
            <p style={{ marginTop: 0, color: 'var(--text-soft)', fontSize: '14px' }}>T&apos;enviem un codi de 6 xifres al correu del compte. Si aquest servidor encara no envia correu, t&apos;ho dirà: llavors demana el codi a qui porta la biblioteca i fes servir «Ja tinc un codi».</p>
            <label style={label} htmlFor="fg-email">Correu electrònic</label>
            <input id="fg-email" style={input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
            <button type="submit" disabled={busy || !email} style={{ ...primary, opacity: busy || !email ? 0.6 : 1 }}>{busy ? 'Enviant…' : 'Envia el codi'}</button>
            <div style={{ marginTop: '12px' }}><button type="button" style={link} onClick={() => setMode('reset')}>Ja tinc un codi</button></div>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={(e) => { e.preventDefault(); doReset(); }}>
            {noMail && <p style={{ marginTop: 0, color: 'var(--text-soft)', fontSize: '14px' }}>Aquest servidor no envia correu. Demana el codi a qui porta la biblioteca (digues-li el teu nom d&apos;usuari) i escriu-lo aquí.</p>}
            <label style={label} htmlFor="rs-login">Correu electrònic o nom d&apos;usuari</label>
            <input id="rs-login" style={input} value={login || email} onChange={(e) => setLogin(e.target.value)} autoComplete="username" />
            <label style={label} htmlFor="rs-code">Codi de 6 xifres</label>
            <input id="rs-code" style={input} inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} />
            <label style={label} htmlFor="rs-pw">Contrasenya nova (mínim 8 caràcters)</label>
            <input id="rs-pw" style={input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
            <button type="submit" disabled={busy || !(login || email) || code.length < 6 || password.length < 8} style={{ ...primary, opacity: busy || !(login || email) || code.length < 6 || password.length < 8 ? 0.6 : 1 }}>{busy ? 'Canviant…' : 'Canvia la contrasenya'}</button>
          </form>
        )}

        {error && <div role="alert" style={{ marginTop: '12px', padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--rose-soft)', color: 'var(--rose)', fontSize: '14px', fontWeight: 600 }}>{error}</div>}
      </div>
    </div>
  );
}
