import { useCallback, useEffect, useState } from 'react';
import { FaChevronLeft, FaPlay, FaCheck } from 'react-icons/fa';
import { api } from '../api';
import { audioSrc } from '../services/audioLocal';
import Frase from './Frase';

/**
 * Les piles de revisió: una pregunta cada vegada (#454).
 *
 * Fins ara, per revisar, calia obrir `/drills`, prémer una etiqueta i llegir una graella de
 * 4.800 files decidint què fer amb cadascuna. **Això no es fa.** Una pila de cinc-centes
 * frases «per revisar» no la mira ningú, i les que més mal fan es queden allà any rere any.
 *
 * Les cinc etiquetes no són cinc graus de la mateixa cosa: són **cinc preguntes diferents**,
 * i cadascuna es respon amb dues o tres opcions. Aquí se'n serveix una cada vegada, amb els
 * botons que la resolen i res més.
 *
 * Tres decisions que fan que això funcioni:
 *
 * · **Marcar com a fet és treure l'etiqueta.** No hi ha cap taula nova: la pila s'encongeix
 *   sola i el compte de l'etiqueta és la barra de progrés.
 * · **Es pot sentir.** Decidir sobre una frase sense sentir-la és decidir a mitges.
 * · **«No ho sé» és una resposta.** Deixa la frase per a un altre dia i no toca res. És la
 *   regla de tot el projecte: el que no se sap, no s'inventa.
 */

interface Opcio { id: string; diu: string }
interface Pila { id: string; titol: string; pregunta: string; opcions: Opcio[]; queden: number }
interface Drill {
  id: number; text_tachelhit?: string | null; text_tachelhit_latin?: string | null;
  text_catalan?: string | null; text_arabic?: string | null; audio_url?: string | null;
  image_url?: string | null; text_tachelhit_suggested?: string | null;
  region?: string | null; variety?: string | null; speaker?: string | null;
}
/**
 * Un esborrany de màquina amb la seva procedència.
 *
 * `acord` és com de parescut és al que han llegit els altres models. És el número que de debò
 * importa: una lectura sola és una endevinalla, i tres que diuen el mateix és una altra cosa.
 */
interface Esborrany {
  text: string; model?: string | null; acord?: number | null;
  // La mateixa línia sense el que hi ha entre parèntesis, que al CD del Mètode no sona mai
  // («(dar)», «(afasi)» són indicacions de l'exercici). És el que es proposa per editar.
  text_net?: string | null; font?: string | null;
}
interface Seguent {
  pila: string; queden: number; titol?: string; pregunta?: string; opcions?: Opcio[];
  drill: Drill | null; companya?: Drill | null; esborranys?: Esborrany[];
}

export default function RevisaPage() {
  const [piles, setPiles] = useState<Pila[] | null>(null);
  const [pila, setPila] = useState<string | null>(null);
  const [item, setItem] = useState<Seguent | null>(null);
  const [saltats, setSaltats] = useState<number[]>([]);
  const [ocupat, setOcupat] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fet, setFet] = useState<string | null>(null);
  // La línia del llibre tal com la deixa la persona a la caixa; null = encara sense tocar.
  const [editat, setEditat] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ piles: Pila[] }>('/revisa')
      .then((r) => setPiles(r.piles))
      .catch(() => setError('Això és només per a qui administra la biblioteca.'));
  }, []);

  const seguent = useCallback(async (quina: string, fora: number[]) => {
    setOcupat(true);
    try {
      const q = fora.length ? `?saltats=${fora.join(',')}` : '';
      setEditat(null);
      setItem(await api.get<Seguent>(`/revisa/${quina}${q}`));
      setError(null);
    } catch {
      setError('No s’ha pogut carregar la següent.');
    } finally {
      setOcupat(false);
    }
  }, []);

  const obre = (quina: string) => { setPila(quina); setSaltats([]); setFet(null); seguent(quina, []); };

  const decideix = async (opcio: string, tria?: number, esborrany?: string) => {
    if (!item?.drill || !pila || ocupat) return;
    // «No ho sé» no toca res i no gasta cap crida: la treu d'avui i passa a la següent.
    if (opcio === 'no-ho-se') {
      const fora = [...saltats, item.drill.id];
      setSaltats(fora);
      setFet('deixada per a un altre dia');
      seguent(pila, fora);
      return;
    }
    setOcupat(true);
    try {
      const r = await api.post<{ canvis: string[]; queden: number }>(`/revisa/${pila}`, {
        drill_id: item.drill.id, opcio, tria, esborrany,
      });
      setFet(r.canvis.join(' · ') || 'fet');
      setPiles((p) => p && p.map((x) => (x.id === pila ? { ...x, queden: r.queden } : x)));
      await seguent(pila, saltats);
    } catch {
      setError('No s’ha pogut desar la decisió.');
      setOcupat(false);
    }
  };

  if (error && !piles) return <div style={cos}><p style={{ color: 'var(--text-soft)' }}>{error}</p></div>;
  if (!piles) return <div style={cos}><p style={{ color: 'var(--text-soft)' }}>Carregant…</p></div>;

  // La tria de pila: què hi ha per fer i quant en queda de cada cosa.
  if (!pila) {
    return (
      <div style={cos}>
        <h1 style={titol}>Què vols revisar</h1>
        <p style={{ color: 'var(--text-soft)', fontSize: 14, lineHeight: 1.6, margin: '0 0 20px' }}>
          Cada pila és <strong>una sola pregunta</strong>. Es respon prement, una frase cada
          vegada, i el que decideixes es desa a l’instant.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {piles.map((p) => (
            <button key={p.id} onClick={() => obre(p.id)} disabled={!p.queden}
                    style={{ ...fitxa, opacity: p.queden ? 1 : 0.5, cursor: p.queden ? 'pointer' : 'default' }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                <strong style={{ fontSize: 15.5 }}>{p.titol}</strong>
                <span style={{ fontSize: 13, fontWeight: 800, color: p.queden ? 'var(--brand-1)' : 'var(--text-muted)' }}>
                  {p.queden ? `${p.queden} per mirar` : 'cap'}
                </span>
              </span>
              <span style={{ fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.5 }}>{p.pregunta}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const d = item?.drill;
  const c = item?.companya;
  const opcions = item?.opcions || [];
  const esborranys = item?.esborranys || [];
  // Quants models han llegit aquesta gravació de la mateixa manera. Amb dos ja val la pena
  // mirar-la; amb tres, molt més.
  const coincideixen = esborranys.filter((e) => (e.acord ?? 0) >= 0.7).length;

  return (
    <div style={cos}>
      <button onClick={() => { setPila(null); setItem(null); }} style={enrere}>
        <FaChevronLeft size={11} /> Les piles
      </button>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap', marginBottom: 4 }}>
        <h1 style={{ ...titol, margin: 0 }}>{item?.titol || ''}</h1>
        <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)' }}>
          en queden {item?.queden ?? '…'}
        </span>
      </div>
      <p style={{ color: 'var(--text-soft)', fontSize: 14, margin: '0 0 16px' }}>{item?.pregunta}</p>

      {fet && (
        <p style={{ fontSize: 13, color: 'var(--emerald, #0a7)', margin: '0 0 12px', fontWeight: 700 }}>
          <FaCheck size={11} /> {fet}
        </p>
      )}

      {!d ? (
        <p style={{ fontSize: 15, lineHeight: 1.6 }}>
          <strong>No en queda cap.</strong> Aquesta pila està buida — o totes les que hi havia
          s’han deixat per a un altre dia.
        </p>
      ) : (
        <>
          <Targeta d={d} />
          {c && <><div style={separador}>i</div><Targeta d={c} /></>}

          {/* Els esborranys de màquina, amb de qui són i si coincideixen.
              Això no és decoració: és la raó per mirar-se aquesta frase i no una altra. */}
          {esborranys.length > 0 && (
            <div style={caixaEsborranys}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                <strong style={{ fontSize: 13.5 }}>
                  {esborranys.length === 1 ? 'Una màquina ho ha llegit així'
                    : `${esborranys.length} màquines ho han llegit`}
                </strong>
                {coincideixen >= 2 && (
                  <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--emerald, #0a7)' }}>
                    i {coincideixen} hi coincideixen
                  </span>
                )}
              </div>
              {esborranys.map((e, k) => (
                <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 15.5, lineHeight: 1.4 }}>{e.text}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {e.model || 'no sabem de quin model surt'}
                    {e.acord != null ? ` · acord ${e.acord.toFixed(2)}` : ''}
                  </span>
                </div>
              ))}
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-soft)', lineHeight: 1.5 }}>
                Cap d’aquests no és el text d’un parlant. El que triïs es desa com a
                <strong> proposta</strong>, perquè després algú que sàpiga la llengua el confirmi.
              </p>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginTop: 18 }}>
            {opcions.map((o) => (
              o.id === 'tria' && c ? (
                [d, c].map((quin) => (
                  <button key={`${o.id}-${quin.id}`} onClick={() => decideix('tria', quin.id)}
                          disabled={ocupat} style={boto}>
                    {o.diu}: <strong>«{(quin.text_catalan || quin.text_tachelhit || '').slice(0, 44)}»</strong>
                  </button>
                ))
              ) : o.id === 'tria' && pila === 'casa-amb-el-llibre' && esborranys.length ? (
                // Aquí el text és d'una persona (l'autor del llibre) i el que va fer la màquina
                // és l'aparellament. En Pablo va escoltar 30 talls (29/10): el CD sovint diu
                // només una PART de la línia (sense «yyih,», sense la segona frase) i el que
                // és entre parèntesis no sona mai. Un «sí» que escrivís la línia tal qual
                // posaria al camp del parlant coses que no sonen. Per això el «sí» porta la
                // línia en una caixa: el que es desa és el que la persona hi deixa.
                <div key={o.id} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <textarea id="revisa-linia-editada" value={editat ?? (esborranys[0].text_net || esborranys[0].text)}
                            onChange={(ev) => setEditat(ev.target.value)} rows={2} lang="zgh"
                            style={{ ...boto, fontSize: 17, lineHeight: 1.5, resize: 'vertical', textAlign: 'left' }} />
                  <button onClick={() => decideix('tria', undefined, (editat ?? (esborranys[0].text_net || esborranys[0].text)).trim())}
                          disabled={ocupat || !(editat ?? (esborranys[0].text_net || esborranys[0].text)).trim()} style={boto}>
                    {o.diu} <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>(es desa el que hi ha a la caixa)</span>
                  </button>
                </div>
              ) : o.id === 'tria' && esborranys.length ? (
                // Un botó per esborrany: triar-ne un és dir «aquest és el bo», i amb tres
                // lectures diferents al davant la tria és una decisió, no un sí o un no.
                esborranys.map((e, k) => (
                  <button key={`${o.id}-${k}`} onClick={() => decideix('tria', undefined, e.text)}
                          disabled={ocupat} style={boto}>
                    {o.diu}: <strong>«{e.text.slice(0, 60)}»</strong>
                  </button>
                ))
              ) : (
                <button key={o.id} onClick={() => decideix(o.id)} disabled={ocupat}
                        style={o.id === 'no-ho-se' ? botoFluix : boto}>{o.diu}</button>
              )
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/** Una frase, amb tot el que cal per decidir-ne: el so, la imatge, les dues escriptures. */
function Targeta({ d }: { d: Drill }) {
  return (
    <div style={targeta}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        {(d.audio_url || '').trim() && (
          <button onClick={() => { const a = new Audio(audioSrc(d.audio_url || '')); a.play().catch(() => {}); }}
                  aria-label="Escolta-la"
                  style={{ flexShrink: 0, width: 44, height: 44, borderRadius: '50%', border: 'none',
                           background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer',
                           display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <FaPlay size={15} />
          </button>
        )}
        <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontWeight: 700 }}>
          #{d.id}{d.region ? ` · ${d.region}` : ''}{d.speaker ? ` · ${d.speaker}` : ''}
        </span>
      </div>
      {(d.text_tachelhit || '').trim()
        ? <Frase text={d.text_tachelhit || ''} latin={d.text_tachelhit_latin} size="md" />
        : <div style={{ fontSize: 13.5, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>
            (ningú no ha escrit encara què diu)
          </div>}
      {(d.text_tachelhit_suggested || '').trim() && (
        <div style={{ marginTop: 6, opacity: 0.85 }}>
          <span style={{ fontSize: 10.5, fontWeight: 800, letterSpacing: '.04em', textTransform: 'uppercase',
                         color: 'var(--text-muted)' }}>esborrany de màquina</span>
          <Frase text={d.text_tachelhit_suggested || ''} size="sm" />
        </div>
      )}
      <div style={{ fontSize: 14.5, marginTop: 6, lineHeight: 1.5 }}>{d.text_catalan || '—'}</div>
      {(d.text_arabic || '').trim() && (
        <div dir="rtl" style={{ fontSize: 14.5, marginTop: 4, color: 'var(--text-soft)' }}>{d.text_arabic}</div>
      )}
    </div>
  );
}

const caixaEsborranys: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14,
  padding: '12px 14px', borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)', background: 'var(--surface-2)',
};

const cos: React.CSSProperties = {
  padding: '20px max(16px, env(safe-area-inset-left, 0px)) 80px max(16px, env(safe-area-inset-right, 0px))',
  maxWidth: 640, margin: '0 auto',
};
const titol: React.CSSProperties = { fontFamily: 'var(--font-display)', fontSize: 21, margin: '0 0 6px' };
const enrere: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 12, padding: '6px 10px',
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text-soft)', fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
};
const fitxa: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 5, textAlign: 'left', padding: '13px 15px',
  borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text)', fontFamily: 'inherit',
};
const targeta: React.CSSProperties = {
  padding: '13px 15px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)',
  background: 'var(--surface)',
};
const separador: React.CSSProperties = {
  textAlign: 'center', fontSize: 12.5, fontWeight: 800, color: 'var(--text-muted)', padding: '8px 0',
};
// Prou grans per prémer-los amb el dit sense mirar: això es fa al telèfon i de pressa.
const boto: React.CSSProperties = {
  padding: '15px 16px', minHeight: 52, borderRadius: 'var(--r-lg)', border: 'none',
  background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, fontSize: 14.5,
  cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', lineHeight: 1.4,
};
const botoFluix: React.CSSProperties = {
  ...boto, background: 'var(--surface)', color: 'var(--text-soft)',
  border: '1px solid var(--border)', fontWeight: 700,
};
