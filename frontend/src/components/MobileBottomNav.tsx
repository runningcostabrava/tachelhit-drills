import { useNavigate, useLocation } from 'react-router-dom';

export default function MobileBottomNav({}: {}) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const items: { path: string; icon: string; label: string }[] = [
    { path: '/', icon: '📚', label: 'Drills' },
    { path: '/video-creator', icon: '🎬', label: 'Captura' },
    { path: '/corpus', icon: '📖', label: 'Corpus' },
    { path: '/tests', icon: '📝', label: 'Tests' },
    { path: '/profile', icon: '👤', label: 'Perfil' },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 'calc(64px + env(safe-area-inset-bottom, 0px))',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(16px)',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        boxShadow: '0 -4px 20px rgba(15,23,42,0.06)',
        zIndex: 1000,
      }}
    >
      {items.map((item) => {
        const active = isActive(item.path);
        return (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            style={{
              flex: 1,
              height: '100%',
              padding: '6px 0',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '3px',
              color: active ? 'var(--brand-1)' : 'var(--text-muted)',
              fontWeight: active ? 800 : 600,
              fontSize: '11px',
              position: 'relative',
            }}
          >
            <span
              style={{
                fontSize: '20px',
                transform: active ? 'translateY(-1px) scale(1.08)' : 'none',
                transition: 'transform var(--t-fast)',
                filter: active ? 'none' : 'grayscale(0.3) opacity(0.85)',
              }}
            >
              {item.icon}
            </span>
            <span>{item.label}</span>
            {active && (
              <span
                style={{
                  position: 'absolute',
                  top: '6px',
                  width: '28px',
                  height: '3px',
                  borderRadius: '999px',
                  background: 'var(--brand-gradient)',
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
