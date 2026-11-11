import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaCheck, FaLayerGroup, FaMicrophone, FaPlus } from 'react-icons/fa';
import MobileDrillCreator from './MobileDrillCreator';
import RecordAudioModal from './RecordAudioModal';
import { api } from '../api';
import { hasIdentity } from '../config';
import { toast } from '../toast';
import type { Drill } from '../types';

// Afegir una frase a la biblioteca, des de qualsevol pantalla.
//
// L'amo: «falta un símbol + gran per crear un nou drill». El creador ja existia, però vivia a
// dins de la graella de drills, darrere d'un menú: qui obria l'app i volia posar-hi una frase
// que acabava de sentir havia de saber on era.
//
// Aquí és una pàgina seva (`/afegeix`), i el + de la portada i del menú hi porten.
//
// I quan la frase és feta, **es diu què ha passat i què ve després** (#284). Abans d'això,
// desar et deixava a la graella de mil sis-centes files amb un avís que marxava sol: ni sabies
// quina era la teva frase, ni que el pas següent natural és posar-hi la veu. Una frase escrita
// i muda ensenya a llegir-la, no a dir-la.

export default function AddSentencePage() {
  const navigate = useNavigate();
  const [feta, setFeta] = useState<Drill | null>(null);
  const [gravant, setGravant] = useState(false);
  const [teVeu, setTeVeu] = useState(false);
  // Quantes se n'han desat en aquesta estona, i el número de l'última.
  //
  // La fitxa «Afegida a la biblioteca» ara surt al PLEGAR, no després de cada frase (#569).
  // Abans sortia a la primera, i això treia del creador qui n'estava gravant una tirada: la
  // pantalla següent era aquesta, amb un botó «Fes-ne una altra» per tornar a començar.
  const [desades, setDesades] = useState(0);
  const [ultima, setUltima] = useState<number | null>(null);

  useEffect(() => {
    document.title = 'Afegeix una frase · Tamazight';
    if (!hasIdentity()) {
      toast.error('Per afegir una frase et cal un nom: fes-te’n un al perfil.');
      navigate('/signin');
    }
  }, [navigate]);

  if (!hasIdentity()) return null;

  if (feta) {
    const veu = teVeu || !!(feta.audio_url || '').trim();
    return (
      <div style={{ padding: '24px 16px 60px', maxWidth: 560, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--emerald)', fontWeight: 800, fontSize: 15 }}>
          <FaCheck size={14} /> Afegida a la biblioteca
        </div>

        <div style={{ marginTop: 12, padding: '14px 16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
          <div lang="shi" style={{ fontSize: 19, fontWeight: 800, color: 'var(--brand-1)', lineHeight: 1.35 }}>
            {(feta.text_tachelhit || '').trim() || <em style={{ color: 'var(--text-muted)' }}>sense amazic</em>}
          </div>
          <div style={{ fontSize: 14.5, color: 'var(--text-soft)', marginTop: 2 }}>
            {(feta.text_catalan || '').trim() || <em>sense català</em>}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
            Frase #{feta.id}{feta.author ? ` · hi consta ${feta.author}` : ''}
          </div>
        </div>

        {/* El pas següent natural. No és una altra pantalla: és el que falta perquè la frase
            serveixi per aprendre a dir-la. */}
        <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-soft)', margin: '14px 0 10px' }}>
          {veu
            ? 'Ja té veu. Si en vols una altra presa, torna-hi quan vulguis: no s’esborra cap.'
            : 'Ara li falta la veu. Una frase escrita i muda ensenya a llegir-la, no a dir-la: si la saps dir, digue-la tu.'}
        </p>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          <button onClick={() => setGravant(true)} style={primari}>
            <FaMicrophone size={13} /> {veu ? 'Posa-hi una altra veu' : 'Grava-la ara'}
          </button>
          <button onClick={() => { setFeta(null); setTeVeu(false); setDesades(0); setUltima(null); }} style={secundari}>
            <FaPlus size={12} /> Fes-ne una altra
          </button>
          <button onClick={() => navigate('/drills')} style={secundari}>
            <FaLayerGroup size={12} /> Ves a la biblioteca
          </button>
        </div>

        {gravant && (
          <RecordAudioModal drill={feta} onClose={() => setGravant(false)}
                            onSaved={() => { setGravant(false); setTeVeu(true); toast.success('Gràcies: la frase ja es pot escoltar.'); }} />
        )}
      </div>
    );
  }

  return (
    <MobileDrillCreator onClose={() => {
                          if (!desades) return navigate(-1);   // no s'ha fet res: enrere i prou
                          if (ultima == null) {                // sense connexió: encara no té número
                            toast.success(desades === 1 ? 'Afegida a la biblioteca'
                              : `${desades} frases afegides a la biblioteca`);
                            navigate('/drills');
                            return;
                          }
                          api.drill(ultima)
                            .then(setFeta)
                            .catch(() => { toast.success('Afegida a la biblioteca'); navigate('/drills'); });
                        }}
                        onDrillCreated={(drillId) => {
                          setDesades(n => n + 1);
                          if (drillId) setUltima(drillId);
                        }} />
  );
}

const primari: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 18px', minHeight: 48,
  borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff',
  fontWeight: 800, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit',
};
const secundari: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 18px', minHeight: 48,
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text)', fontWeight: 700, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit',
};
