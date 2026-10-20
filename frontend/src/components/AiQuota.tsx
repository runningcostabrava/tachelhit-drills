import { useEffect, useState } from 'react';
import { api, type AiUsage } from '../api';

/** One quiet line under an AI panel: how many AI questions the person has left today and how
 *  much of the month's Gemini budget is spent. `refreshKey` bumps after every call. */
export default function AiQuota({ refreshKey }: { refreshKey: number }) {
  const [u, setU] = useState<AiUsage | null>(null);
  useEffect(() => {
    let alive = true;
    api.aiUsage().then((r) => { if (alive) setU(r); }).catch(() => { /* the line is optional */ });
    return () => { alive = false; };
  }, [refreshKey]);
  if (!u) return null;
  const today = u.today.limit == null
    ? `${u.today.used} consultes avui (sense límit)`
    : `${u.today.remaining} de ${u.today.limit} consultes d'IA per avui`;
  const month = `${u.month.spent_eur.toFixed(2)} € de ${u.month.budget_eur.toFixed(0)} € aquest mes`;
  const out = !u.available;
  return (
    <div style={{ padding: '0 14px 8px', fontSize: '11.5px', color: out ? 'var(--rose)' : 'var(--text-muted)', display: 'flex', gap: '6px', flexWrap: 'wrap' }} aria-live="polite">
      <span>{out ? 'Pressupost mensual d’IA esgotat' : today}</span>
      <span>·</span>
      <span>{month}</span>
    </div>
  );
}

/** Admin only: this month's Gemini spend by feature (tutor, copilot, captures, pictures…). */
export function AiSpendAdmin() {
  const [u, setU] = useState<AiUsage | null>(null);
  useEffect(() => { api.aiUsage().then(setU).catch(() => {}); }, []);
  const by = u?.month.by_feature;
  if (!u || !by) return null;
  const rows = Object.entries(by).sort((a, b) => b[1].eur - a[1].eur);
  const labels: Record<string, string> = { ask: 'Tutor (preguntes)', agent: 'Copilot', explain: 'Explica’m', analyze: 'Anàlisi', suggest: 'Traducció suggerida', review: 'Revisió', pipeline: 'Captures, temes, veus i imatges' };
  return (
    <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
      <div style={{ fontWeight: 700, marginBottom: '4px' }}>IA aquest mes</div>
      <div style={{ fontSize: '13px', color: u.available ? 'var(--text-soft)' : 'var(--rose)', marginBottom: '6px' }}>
        {u.month.spent_eur.toFixed(2)} € de {u.month.budget_eur.toFixed(0)} € · es reinicia l’1 del mes que ve{u.available ? '' : ' · pressupost esgotat'}
      </div>
      <table style={{ fontSize: '12.5px', borderCollapse: 'collapse' }}>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td style={{ padding: '2px 10px 2px 0', color: 'var(--text-soft)' }}>{labels[k] || k}</td>
              <td style={{ padding: '2px 10px 2px 0', textAlign: 'right' }}>{v.calls} crides</td>
              <td style={{ padding: '2px 0', textAlign: 'right' }}>{v.eur.toFixed(3)} €</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
