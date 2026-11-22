/**
 * «rix» i «riɣ» són la mateixa paraula (#364).
 *
 * Qui obre la biblioteca llegeix «rix» en una frase i «riɣ» en una altra i es pensa que són dues
 * paraules. No ho són: és la mateixa, escrita per dues mans amb dues convencions. Qui ho sap no
 * hi ensopega; qui no ho sap aprèn una lletra que no hi és, perquè el transliterador escriu el
 * que té i pinta ⵅ on hi va ⵖ.
 *
 * Va als dos llocs on algú hi topa —la unitat dels sons de la Gramàtica i el capítol dels sons
 * del Mètode— i no a cada frase: seria soroll, i la frase ja està escrita com la va escriure qui
 * la va escriure.
 *
 * El text i els números vénen del servidor (`ortografia.py`), que els té comptats. Aquí només es
 * pinten: si algun dia es tornen a comptar i canvien, aquesta pantalla no s'ha de tocar.
 */
import { FaPenNib } from 'react-icons/fa6';
import type { NotaOrtografia as Nota } from '../api';

export default function NotaOrtografia({ nota }: { nota?: Nota | null }) {
  if (!nota) return null;
  return (
    <section style={{
      margin: '18px 0', padding: '16px 18px', borderRadius: 'var(--r-lg)',
      border: '1px solid var(--amber)', background: 'var(--amber-soft)',
    }}>
      <h3 style={{
        margin: '0 0 8px', fontSize: 15.5, fontWeight: 800, color: 'var(--amber-strong)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <FaPenNib size={13} /> {nota.titol}
      </h3>
      {nota.cos.map((p, i) => (
        <p key={i} style={{ margin: '0 0 8px', fontSize: 14, lineHeight: 1.55, color: 'var(--text)' }}>{p}</p>
      ))}

      {/* Les parelles no són un exemple inventat: són les que hi ha a la biblioteca, amb el
          compte de quantes vegades surt cadascuna. */}
      <div style={{ overflowX: 'auto', marginTop: 10 }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 13.5, minWidth: 320 }}>
          <thead>
            <tr>
              {['amb x', 'amb ɣ', 'vol dir'].map((h) => (
                <th key={h} style={{
                  textAlign: 'left', padding: '5px 14px 5px 0', fontSize: 11.5, fontWeight: 800,
                  letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--amber-strong)',
                  borderBottom: '1px solid var(--amber)',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {nota.parelles.map((p) => (
              <tr key={p.x}>
                <td style={cel}><span lang="shi" style={{ fontWeight: 700 }}>{p.x}</span>
                  <span style={compte}> {p.x_n}</span></td>
                <td style={cel}><span lang="shi" style={{ fontWeight: 700 }}>{p.g}</span>
                  <span style={compte}> {p.g_n}</span></td>
                <td style={{ ...cel, color: 'var(--text-soft)' }}>{p.ca}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p style={{ margin: '10px 0 0', fontSize: 12.5, color: 'var(--text-muted)' }}>
        Comptat a la biblioteca: {nota.quantes} frases de {nota.de_quantes} porten alguna paraula
        acabada en -x.
      </p>
    </section>
  );
}

const cel: React.CSSProperties = {
  padding: '5px 14px 5px 0', borderBottom: '1px solid var(--amber)', whiteSpace: 'nowrap',
};
const compte: React.CSSProperties = {
  color: 'var(--text-muted)', fontSize: 12, fontVariantNumeric: 'tabular-nums',
};
