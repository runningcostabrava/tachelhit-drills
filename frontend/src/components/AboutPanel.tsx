import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaTimes } from 'react-icons/fa';

// Per què existeix això, dit per qui ho ha fet.
//
// Hi ha d'haver un lloc on es digui que això no és un producte: és algú que vol aprendre una
// llengua i la gent que l'hi ha ensenyada. Va al menú, perquè es pugui trobar des de qualsevol
// pantalla, i no a la portada, on seria un anunci.
//
// Tres llengües. El català és el de l'amo. L'anglès, perquè qui obri això des de fora l'entengui.
// I l'amazic, que és de qui parlem: la traducció la fa la màquina del projecte mateix (el nostre
// Space de NLLB) i es diu que la fa, perquè una traducció automàtica que es fa passar per la
// paraula d'algú és justament el que aquesta app no fa enlloc.

const CA = [
  'Aquest projecte va néixer de la meva necessitat i de les meves ganes d’aprendre la llengua que parla la gent més maca que conec: els imazighen.',
  'No hi ha cap ànim de lucre, ni n’hi haurà mai. Tothom hi és benvingut.',
  'Existeix gràcies a molts investigadors que he consultat per fer aquest treball d’antropologia lingüística. Gràcies a tots ells per la seva feina: els trobaràs tots a la pàgina de crèdits.',
  'I encara més gràcies als nostres amics imazighen, que han compartit la seva veu i el que saben de la seva llengua.',
];

const EN = [
  'This project was born from my own need, and my wish, to learn the language spoken by the kindest people I know: the Imazighen.',
  'It is not for profit, and it never will be. Everyone is welcome.',
  'It exists thanks to the many researchers whose work I consulted for this piece of linguistic anthropology. Thank you all: you will find every one of them on the credits page.',
  'And thank you even more to our Imazighen friends, who have shared their voice and what they know of their language.',
];

// Traducció del nostre Space de NLLB, sense revisar encara per cap parlant. Es diu a la pantalla.
const SHI = [
  'ⵉⵜⵜⵓⴼⴽⴰ ⵓⵙⵏⵜⵉ ⴰⴷ ⵙⴳ ⵜⵉⵔⵉⵡⵉⵏ ⵉⵏⵓ ⵏ ⵓⵍⵎⵎⵓⴷ ⵏ ⵜⵓⵜⵍⴰⵢⵜ ⵏ ⵉⵎⴰⵣⵉⵖⵏ.',
  'ⵓⵔ ⵉⴳⵉ ⴼⴰⴷ ⴰⴷ ⵔⵣⵓ ⵉⵇⴰⵔⵉⴹⵏ. ⴽⵓ ⵢⴰⵏ ⵉⵜⵜⵓⵙⵏⵓⴱⴳ.',
  'ⵜⴰⵏⵎⵎⵉⵔⵜ ⵉ ⵉⵎⵔⵣⴰ ⵍⵍⵉ ⵢⵓⵖⵔⴰⵏ ⵜⵓⵜⵍⴰⵢⵜ ⴰⴷ.',
  'ⵜⴰⵏⵎⵎⵉⵔⵜ ⵉ ⵉⵎⴷⴷⵓⴽⴽⴰⵍ ⵏⵏⵖ ⵉⵎⴰⵣⵉⵖⵏ, ⵏⵏⴰ ⴰⵖ ⴼⴽⴰⵏ ⵉⵎⵙⵍⵉ ⵏⵏⵙⵏ.',
];

export default function AboutPanel({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [onClose]);

  return (
    <div onClick={onClose} role="dialog" aria-modal="true" aria-label="Per què existeix això"
         style={{ position: 'fixed', inset: 0, zIndex: 2000, background: 'rgba(15,23,42,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()}
           style={{ width: 'min(620px, 100%)', maxHeight: '86vh', overflowY: 'auto', background: 'var(--surface)', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)', padding: '20px 22px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span aria-hidden style={{ width: 34, height: 34, borderRadius: 11, background: 'var(--brand-gradient)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff' }}>ⵣ</span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: 0, flex: 1 }}>Per què existeix això</h2>
          <button onClick={onClose} aria-label="Tanca"
                  style={{ width: 30, height: 30, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <FaTimes size={12} />
          </button>
        </div>

        {CA.map((p) => (
          <p key={p} style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--text)', margin: '0 0 10px' }}>{p}</p>
        ))}
        {/* Qui ho diu. Ho signa amb el seu nom i prou. */}
        <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--text)', margin: '0 0 12px', fontWeight: 700 }}>Pablo</p>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 2 }}>
          <button onClick={() => { onClose(); navigate('/credits'); }}
                  style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
            Els crèdits i les fonts
          </button>
          {/* I quines màquines ajuden, què fa cadascuna i què passa quan una no contesta (#295):
              qui fa servir l'app ha de poder saber-ho sense haver-ho de descobrir fallant. */}
          <button onClick={() => { onClose(); navigate('/serveis'); }}
                  style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
            Qui fa cada feina
          </button>
        </div>

        <div lang="shi" style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          {SHI.map((p) => (
            <p key={p} style={{ fontFamily: 'var(--font-tifinagh)', fontSize: 15, lineHeight: 1.8, color: 'var(--text)', margin: '0 0 8px' }}>{p}</p>
          ))}
          <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: '4px 0 0', lineHeight: 1.5 }}>
            Aquesta versió amaziga la fa el traductor automàtic del projecte i encara no l’ha
            revisada cap parlant. Si en parles, digue’ns com ho diries tu.
          </p>
        </div>

        <div lang="en" style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          {EN.map((p) => (
            <p key={p} style={{ fontSize: 13.5, lineHeight: 1.6, color: 'var(--text-soft)', margin: '0 0 8px' }}>{p}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
