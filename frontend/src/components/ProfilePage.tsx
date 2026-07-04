import { useState, useEffect } from 'react';
import { getUserToken, setUserIdentity, clearUserIdentity } from '../config';
import { api, type Me } from '../api';

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
  const hasToken = !!getUserToken();

  useEffect(() => {
    if (!hasToken) return;
    api.me()
      .then((data) => {
        if (data) setMe(data);
        else clearUserIdentity(); // token no longer valid
      })
      .catch(() => {});
    api.reviewStreak().then(setStreak).catch(() => {});
  }, [hasToken]);

  const register = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await api.register(username.trim(), displayName.trim() || null);
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

  const logout = () => {
    clearUserIdentity();
    window.location.reload();
  };

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
          <div style={{ padding: '12px 16px', background: 'var(--rose-soft)', border: '1px solid var(--rose)', borderRadius: 'var(--r-md)', marginBottom: '16px', color: 'var(--rose)', fontWeight: 600 }}>
            {error}
          </div>
        )}

        {newToken && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>✅ Compte creat!</h3>
            <p style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
              Aquest és el teu <strong>token personal</strong>. Guarda&apos;l en un lloc segur —
              és l&apos;única manera d&apos;iniciar sessió en altres dispositius i només es mostra ara.
            </p>
            <code style={{ display: 'block', padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', fontSize: '14px', wordBreak: 'break-all', border: '1px solid var(--border)' }}>
              {newToken}
            </code>
            <button
              onClick={() => window.location.reload()}
              style={{ marginTop: '16px', padding: '12px 24px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer' }}
            >
              L&apos;he guardat — continua
            </button>
          </div>
        )}

        {!newToken && hasToken && me && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0, fontSize: '22px' }}>{me.display_name || me.username}</h3>
            <p style={{ color: 'var(--text-muted)', margin: '0 0 16px', fontSize: '14px' }}>@{me.username}</p>
            <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '18px' }}>
              <div style={{ padding: '12px 18px', background: 'var(--brand-gradient-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--brand-1)' }}>
                📚 {me.drills_contributed} drills aportats
              </div>
              <div style={{ padding: '12px 18px', background: 'var(--emerald-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--emerald)' }}>
                🧠 {me.cards_learning} targetes en aprenentatge
              </div>
              {streak && streak.streak_days > 0 && (
                <div style={{ padding: '12px 18px', background: 'var(--amber-soft)', borderRadius: 'var(--r-lg)', fontWeight: 700, color: 'var(--amber-strong)' }}>
                  🔥 {streak.streak_days} {streak.streak_days === 1 ? 'dia' : 'dies'} seguits · {streak.reviews_week} repassos aquesta setmana
                </div>
              )}
            </div>
            <button
              onClick={logout}
              style={{ padding: '10px 20px', background: 'var(--rose-soft)', color: 'var(--rose)', border: '1px solid var(--rose)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer' }}
            >
              Tanca la sessió en aquest dispositiu
            </button>
          </div>
        )}

        {!newToken && !hasToken && (
          <>
            <div style={cardStyle}>
              <h3 style={{ marginTop: 0 }}>Crea el teu compte</h3>
              <p style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
                Amb un compte, el teu repàs (SRS) és només teu i els drills que creïs
                porten el teu nom com a contribuïdor.
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.5 }}>
                En registrar-te dónes el teu consentiment perquè les gravacions i textos
                que aportis es conservin al corpus per documentar i ensenyar la llengua.
                Pots indicar la llicència de cada contribució al camp «license».
              </p>
              <input style={inputStyle} placeholder="Nom d'usuari (a-z, 0-9, _-.)" value={username} onChange={(e) => setUsername(e.target.value)} />
              <input style={inputStyle} placeholder="Nom per mostrar (opcional)" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
              <button
                onClick={register}
                disabled={busy || username.trim().length < 3}
                style={{ padding: '12px 26px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: busy ? 'wait' : 'pointer', opacity: username.trim().length < 3 ? 0.6 : 1 }}
              >
                {busy ? 'Creant…' : 'Registra\'m'}
              </button>
            </div>

            <div style={cardStyle}>
              <h3 style={{ marginTop: 0 }}>Ja tens un token?</h3>
              <input style={inputStyle} placeholder="Enganxa el teu token personal" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} />
              <button
                onClick={loginWithToken}
                disabled={!tokenInput.trim()}
                style={{ padding: '10px 22px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: 'pointer' }}
              >
                Inicia sessió
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
