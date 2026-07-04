import { useEffect, useState } from 'react';
import { subscribeToasts, dismissToast, type ToastItem } from '../toast';

const STYLES: Record<ToastItem['kind'], { bg: string; color: string; icon: string }> = {
  success: { bg: 'var(--emerald)', color: '#fff', icon: '✓' },
  error: { bg: 'var(--rose)', color: '#fff', icon: '⚠' },
  info: { bg: 'var(--brand-1)', color: '#fff', icon: 'ℹ' },
};

// Mounted once in App; renders the toast stack fixed at the bottom-center.
export default function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);
  useEffect(() => subscribeToasts(setItems), []);

  if (!items.length) return null;

  return (
    <div style={{
      position: 'fixed', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
      zIndex: 20000, display: 'flex', flexDirection: 'column', gap: '10px',
      alignItems: 'center', maxWidth: '92vw', pointerEvents: 'none',
    }}>
      {items.map((t) => {
        const s = STYLES[t.kind];
        return (
          <div
            key={t.id}
            onClick={() => dismissToast(t.id)}
            style={{
              pointerEvents: 'auto', cursor: 'pointer',
              background: s.bg, color: s.color,
              padding: '12px 20px', borderRadius: 'var(--r-pill)',
              boxShadow: 'var(--shadow-lg)', fontSize: '14px', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: '10px', maxWidth: '480px',
            }}
          >
            <span style={{ fontWeight: 800 }}>{s.icon}</span>
            <span>{t.message}</span>
          </div>
        );
      })}
    </div>
  );
}
