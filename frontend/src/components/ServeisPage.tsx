import { useEffect, useState } from 'react';
import { FaCircle, FaSyncAlt } from 'react-icons/fa';
import { api, type Serveis } from '../api';

// Quina màquina fa cada feina, i si ara mateix contesta (#295).
//
// El 24-10-2026, en una sola jornada, tres serveis es van quedar sense: Gemini sense crèdit, la
// quota de FLUX esgotada i el traductor gratuït de Google tallant per excés de peticions. Qui
// feia servir l'app només veia que «no anava».
//
// Això ho posa per escrit a dins de l'app: què fa cada màquina, qui és el segon quan la primera
// no contesta, i què passa amb el que en surt —que va a «suggerit» i ho confirma una persona.

const COLOR: Record<string, string> = {
  viu: 'var(--emerald)',
  persona: 'var(--brand-1)',
  despertant: 'var(--amber-strong, #8a6100)',
  aturat: 'var(--rose)',
  sense_clau: 'var(--text-muted)',
  sense_pressupost: 'var(--amber-strong, #8a6100)',
  privat: 'var(--text-muted)',
  no_configurat: 'var(--text-muted)',
};

export default function ServeisPage() {
  const [d, setD] = useState<Serveis | null>(null);
  const [error, setError] = useState(false);
  const [carregant, setCarregant] = useState(true);

  const mira = () => {
    setCarregant(true);
    api.serveis().then((r) => { setD(r); setError(false); })
      .catch(() => setError(true))
      .finally(() => setCarregant(false));
  };

  useEffect(() => { document.title = 'Qui fa cada feina · Tamazight'; mira(); }, []);

  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 780, margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 25, margin: '0 0 6px', lineHeight: 1.25 }}>
        Qui fa cada feina
      </h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 14, margin: '0 0 18px', lineHeight: 1.6 }}>
        Aquesta app fa servir unes quantes màquines i cap no serveix per a tot. Aquí hi ha què fa
        cadascuna, qui ho fa quan la primera no contesta, i què passa amb el que en surt. Tots
        aquests serveis cauen de tant en tant: val més veure-ho que endevinar-ho.
      </p>

      <button onClick={mira} disabled={carregant} style={boto}>
        <FaSyncAlt size={12} /> {carregant ? 'Mirant…' : 'Torna-ho a mirar'}
      </button>

      {error && (
        <p style={{ marginTop: 16, fontSize: 14, color: 'var(--rose)' }}>
          No s’ha pogut parlar amb el servidor, de manera que d’aquestes màquines no en sabem res
          ara mateix.
        </p>
      )}

      {d && (
        <>
          {d.aturades.length > 0 && (
            <div style={{ margin: '16px 0 0', padding: '12px 14px', borderRadius: 'var(--r-lg)', border: '1px solid var(--rose)', background: 'var(--rose-soft)', fontSize: 13.5, lineHeight: 1.6 }}>
              <strong>Ara mateix hi ha {d.aturades.length} {d.aturades.length === 1 ? 'feina aturada' : 'feines aturades'}.</strong>{' '}
              No és que l’app estigui trencada: és que ningú no la pot fer fins que un d’aquests
              serveis torni.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 18 }}>
            {d.feines.map((f) => (
              <section key={f.id} style={{ padding: '14px 16px', borderRadius: 'var(--r-xl)', border: `1px solid ${f.funciona ? 'var(--border)' : 'var(--rose)'}`, background: 'var(--surface)' }}>
                <h2 style={{ fontSize: 16.5, margin: '0 0 6px' }}>{f.titol}</h2>
                <p style={{ margin: '0 0 10px', fontSize: 13.5, lineHeight: 1.6, color: 'var(--text-soft)' }}>{f.explica}</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {f.qui.map((q) => (
                    <div key={q.nom} style={{ display: 'flex', alignItems: 'baseline', gap: 8, fontSize: 13.5 }}>
                      <FaCircle size={8} color={COLOR[q.estat] || 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <strong>{q.nom}</strong>{' '}
                        <span style={{ color: 'var(--text-muted)' }}>— {q.diu}</span>
                        <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{q.paper}</span>
                      </span>
                    </div>
                  ))}
                </div>

                <p style={{ margin: '10px 0 0', fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.55 }}>
                  {f.regla}
                </p>
              </section>
            ))}
          </div>

          <p style={{ margin: '16px 0 0', fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6 }}>{d.avis}</p>

          <h2 style={{ fontSize: 16.5, margin: '22px 0 8px' }}>Les regles</h2>
          <ol style={{ margin: 0, paddingInlineStart: 20, fontSize: 13.5, lineHeight: 1.7, color: 'var(--text-soft)' }}>
            {d.regles.map((r) => <li key={r}>{r}</li>)}
          </ol>
        </>
      )}
    </div>
  );
}

const boto: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 16px', minHeight: 44,
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text)', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit',
};
