import { cloneElement, useState } from 'react';
import type { ButtonHTMLAttributes, ReactElement } from 'react';
import { FaCheck, FaDownload } from 'react-icons/fa';
import { isNativeApp } from '../config';
import { baixaAudio, useAudioSrc } from '../services/audioLocal';
import type { Drill } from '../types';
import { toast } from '../toast';

const AVIS = 'sense baixar';

/**
 * El botó d'escoltar, apagat si el so no es pot sentir (#506, pas 2).
 *
 * Embolcalla el botó en lloc de ser un hook perquè la majoria viuen dins d'un `.map` o d'una cel·la
 * de la graella. Un `title` sol no serviria: al telèfon no es veu, i el botó ho ha de dir.
 *
 * `dins` posa l'avís al lloc del contingut: per als botons grans o els que floten sobre una foto.
 */
export default function AmbSo({ url, dins, children }: {
  url?: string | null;
  dins?: boolean;
  children: ReactElement<ButtonHTMLAttributes<HTMLButtonElement>>;
}) {
  const { disponible } = useAudioSrc(url);
  if (!url?.trim() || disponible) return children;
  const { style, 'aria-label': nom } = children.props;
  const apagat = {
    disabled: true,
    title: AVIS,
    'aria-label': nom ? `${nom}, ${AVIS}` : AVIS,
    style: { ...style, opacity: 0.45, cursor: 'default' },
  };
  if (dins) return cloneElement(children, apagat, <span style={{ fontSize: 11, lineHeight: 1.1 }}>{AVIS}</span>);
  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 2, flexShrink: 0 }}>
      {cloneElement(children, apagat)}
      <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{AVIS}</span>
    </span>
  );
}

/** Demanar la veu d'un drill per tenir-la sense connexió. Només a l'app: al web no hi ha disc. */
export function BaixaAudio({ drill, style }: { drill: Drill; style?: React.CSSProperties }) {
  const { baixat } = useAudioSrc(drill);
  const [baixant, setBaixant] = useState(false);
  if (!isNativeApp() || !drill.audio_url) return null;
  const baixa = async () => {
    setBaixant(true);
    const fet = await baixaAudio(drill);
    setBaixant(false);
    if (!fet) toast.error("No s'ha pogut baixar l'àudio.");
  };
  const nom = baixat ? 'Àudio baixat' : "Baixa l'àudio per escoltar-lo sense connexió";
  return (
    <button onClick={baixa} disabled={baixat || baixant} aria-label={nom} title={nom} style={style}>
      {baixant ? '…' : baixat ? <FaCheck size={15} /> : <FaDownload size={15} />}
    </button>
  );
}
