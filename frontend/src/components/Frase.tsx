// Com es veu una frase amaziga, a tot arreu igual (#339).
//
// Regla del propietari: **una transcripció va sempre en tifinag i en llatí, i el tifinag té el
// lloc de més importància.** Fins ara el projecte feia el contrari sense pensar-hi —el camp del
// Mètode es diu literalment «la frase en tifinag per posar-la SOTA la llatina»— i cada pantalla
// s'ho pintava a la seva manera: dinou components toquen els dos alfabets, cadascun amb els seus
// estils. Mentre no hi hagués un sol lloc que digués com es veu una frase, la regla no es podia
// complir «a tot arreu»: s'hauria d'escriure dinou vegades i es trencaria a la vintena pantalla.
//
// Això és aquell lloc. Tifinag a dalt i gran; el llatí a sota, més petit, perquè el curs d'avui
// encara ensenya amb llatí (#302) i treure'l deixaria mig curs il·legible.
//
// Transliterar no és traduir: és determinista, no va a `*_suggested` i no toca mai el text del
// parlant. La cara que el parlant va escriure es torna **tal com la va escriure**; només l'altra
// es calcula.

import { duesCares, formes } from '../utils/tifinag';
import type { WordTime } from '../api';
import { llum } from '../utils/llum';

export interface FraseProps {
  /** El text tal com el va escriure qui el va escriure, en l'alfabet que fos. */
  text: string;
  /** La forma llatina desada, si la frase original és en tifinag i algú ja l'havia escrita. */
  latin?: string | null;
  /** Els temps de cada paraula, per encendre la que sona (#340). */
  mots?: WordTime[];
  /** Quina paraula sona ara; `null` quan no en sona cap. */
  encesa?: number | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const MIDES = {
  sm: { tif: 15, lat: 12.5 },
  md: { tif: 18, lat: 14 },
  lg: { tif: 22, lat: 15.5 },
  // Per a la pantalla d'escoltar corrent (#449): es mira de lluny, un segon, amb el braç
  // estirat i movent-se. Vint-i-dos píxels no s'hi llegeixen.
  xl: { tif: 34, lat: 21 },
};

export default function Frase({ text, latin, mots, encesa = null, size = 'md' }: FraseProps) {
  const net = (text || '').trim();
  if (!net) return null;
  const m = MIDES[size];

  // Paraula per paraula, perquè el tifinag i el llatí quedin alineats i se'n pugui encendre una
  // de sola. Transliterar la frase sencera donaria el mateix text, però llavors no se sabria on
  // comença i on acaba cada paraula a cada cara.
  const paraules = net.split(/\s+/).filter(Boolean);
  const llatines = (latin || '').trim().split(/\s+/).filter(Boolean);
  const cares = paraules.map((p, i) =>
    duesCares(p, llatines.length === paraules.length ? llatines[i] : null));

  // Quina paraula s'encén. Els temps vénen de l'alineament, fet sobre aquest mateix text, de
  // manera que la paraula i del rellotge és la i de la frase. Quan els comptes no quadren
  // —l'alineament n'ha ajuntat dues, o algú ha reescrit la frase— no s'endevina: s'encén la que
  // diu el mateix, mirant les dues cares, i si no n'hi ha cap, cap.
  const quadren = !!mots && mots.length === paraules.length;
  const diu = encesa != null && mots && mots[encesa] ? formes(mots[encesa].w) : null;
  const es_encesa = (i: number) => {
    if (encesa == null) return false;
    if (quadren) return i === encesa;
    if (!diu) return false;
    return cares[i].tif === diu.tif || cares[i].lat === diu.lat;
  };

  return (
    <div>
      {/* El tifinag primer i gran: és la llengua escrita amb el seu alfabet. */}
      <div lang="zgh" style={{ fontSize: m.tif, fontWeight: 800, lineHeight: 1.45, wordBreak: 'break-word' }}>
        {cares.map((c, i) => (
          <span key={i} style={es_encesa(i) ? llum : undefined}>{c.tif}{i < cares.length - 1 ? ' ' : ''}</span>
        ))}
      </div>
      {/* I el llatí a sota, que és amb el que el curs ensenya avui. */}
      <div style={{ fontSize: m.lat, fontWeight: 600, lineHeight: 1.4, color: 'var(--text-soft)', wordBreak: 'break-word' }}>
        {cares.map((c, i) => (
          <span key={i} style={es_encesa(i) ? llum : undefined}>{c.lat}{i < cares.length - 1 ? ' ' : ''}</span>
        ))}
      </div>
    </div>
  );
}
