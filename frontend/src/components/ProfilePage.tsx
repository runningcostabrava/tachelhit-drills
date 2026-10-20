import { useState, useEffect } from 'react';
import { getUserToken, isNativeApp, setUserIdentity, clearUserIdentity } from '../config';
import { Share } from '@capacitor/share';
import { syncManager } from '../services/OfflineSyncManager';
import { api, type Me } from '../api';
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

export default function ProfilePage() {
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
        if (e?.status === 401 || /401|invalid token/i.test(e?.message || '')) {
          clearUserIdentity();
          setError('El token ja no és vàlid. Torna a iniciar sessió.');
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
            <p style={{ color: 'var(--text-muted)', margin: '0 0 16px', fontSize: '14px' }}>@{me.username}</p>
            <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '18px' }}>
              <div style={{ padding: '12px 18px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--brand-1)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}><FaLayerGroup /> {me.drills_contributed} drills aportats</span>
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
                  <button type="button" onClick={() => Share.share({ title: 'Tachelhit Drills · token', text: getUserToken() }).catch(() => {})} style={{ padding: '10px 16px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer', minHeight: '44px' }}>
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
    </div>
  );
}
