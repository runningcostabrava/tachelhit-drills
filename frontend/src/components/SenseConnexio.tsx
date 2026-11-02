import { useCallback, useEffect, useState } from 'react';
import { FaCheck, FaCloudDownloadAlt, FaCloudUploadAlt, FaRedo, FaStop, FaTrashAlt } from 'react-icons/fa';
import { Network } from '@capacitor/network';
import { isNativeApp } from '../config';
import { toast } from '../toast';
import { bibliotecaAlDia, drillsLocals } from '../services/biblioteca';
import { syncManager } from '../services/OfflineSyncManager';
import {
  alliberaAudios, aturaBaixada, aturaExtres, baixaExtresDeTot, baixaTotsElsAudios,
  baixantAudios, baixantExtres, resumAudios,
  type ProgresAudios, type ProgresExtres,
} from '../services/audioLocal';
import { aturaCurs, baixaElCurs, baixantCurs, type ProgresCurs } from '../services/cursOffline';

/**
 * «Al telèfon»: què hi ha baixat i què falta (#506, ADR 0008, passos 3 i 4).
 *
 * En Pablo (31-10): «I need a system that have the audios, I should be able to download them all
 * to the phone; the gramatica, metode and histories should work».
 *
 * Tres coses, i cadascuna diu quant ocupa ABANS de baixar-se: les frases (text, uns megabytes),
 * les veus (centenars de megabytes) i el curs (poc). Res no es baixa sol: fins ara l'app es
 * descarregava els àudios en segon pla a cada obertura i gairebé cap pantalla no els feia servir.
 */

const mida = (b: number) => (b >= 1 << 30 ? `${(b / (1 << 30)).toFixed(2)} GB` : b >= 1 << 20 ? `${Math.round(b / (1 << 20))} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

/** Mitjana mesurada el 30-10 sobre 24 fitxers de la biblioteca: serveix per dir-ho abans de baixar. */
const BYTES_PER_VEU = 42 * 1024;

export default function SenseConnexio() {
  const [frases, setFrases] = useState<{ total: number; ambVeu: number; ambExtres: number } | null>(null);
  const [disc, setDisc] = useState<{ fitxers: number; bytes: number } | null>(null);
  const [veus, setVeus] = useState<ProgresAudios | null>(null);
  const [curs, setCurs] = useState<ProgresCurs | null>(null);
  const [extres, setExtres] = useState<ProgresExtres | null>(null);
  const [wifi, setWifi] = useState<boolean | null>(null);
  const [netejant, setNetejant] = useState(false);
  // El que s'ha fet al telèfon i encara no és al servidor (#568).
  const [cua, setCua] = useState<{ frases: number; fitxers: number; canvis: number; mortes: number } | null>(null);
  const [pujant, setPujant] = useState(false);

  const miraLaCua = useCallback(async () => {
    const [q, mortes] = await Promise.all([
      syncManager.getQueue().catch(() => []),
      syncManager.getDeadLetters().catch(() => []),
    ]);
    setCua({
      frases: q.filter((a) => a.type === 'CREATE').length,
      fitxers: q.filter((a) => a.type === 'UPLOAD_MEDIA').length,
      canvis: q.filter((a) => a.type === 'UPDATE' || a.type === 'DELETE').length,
      mortes: mortes.length,
    });
  }, []);

  const mesura = useCallback(async () => {
    const d = await drillsLocals().catch(() => [] as Awaited<ReturnType<typeof drillsLocals>>);
    setFrases({
      total: d.length,
      ambVeu: d.filter((x) => (x.audio_url || '').trim()).length,
      ambExtres: d.filter((x) => (x.audio_tts_url || '').trim()).length
        + d.filter((x) => (x.image_url || '').trim()).length,
    });
    setDisc(await resumAudios().catch(() => ({ fitxers: 0, bytes: 0 })));
  }, []);

  useEffect(() => {
    void mesura();
    void miraLaCua();
    Network.getStatus().then((s) => setWifi(s.connectionType === 'wifi')).catch(() => setWifi(null));
    // La cua es mou sola quan torna el senyal: mirar-la de tant en tant és el que fa que el
    // número baixi davant dels teus ulls en comptes de quedar-se encallat a la pantalla.
    const t = window.setInterval(() => { void miraLaCua(); }, 4000);
    return () => window.clearInterval(t);
  }, [mesura, miraLaCua]);

  /** «Prova-ho ara»: empeny la cua sense esperar que l'app se n'adoni. */
  const pujaAra = async () => {
    if (!(await Network.getStatus()).connected) {
      toast.error('Ara no hi ha connexió. Quan en torni, pujarà sol.');
      return;
    }
    setPujant(true);
    try {
      await syncManager.sync();
      await Promise.all([miraLaCua(), mesura()]);
      const q = await syncManager.getQueue().catch(() => []);
      toast.success(q.length ? `${q.length} encara esperen; s’hi tornarà.` : 'Tot pujat.');
    } finally { setPujant(false); }
  };

  /** Les que han fallat cinc vegades i s'han apartat: tornar-ho a provar o descartar-les. */
  const tornaHiAmbLesMortes = async () => {
    setPujant(true);
    try { await syncManager.retryDeadLetters(); await Promise.all([miraLaCua(), mesura()]); }
    finally { setPujant(false); }
  };

  /**
   * Treu-les de la cua, i prou.
   *
   * No esborra res del telèfon: la frase es queda a la biblioteca marcada «Al telèfon» i la
   * gravació es queda al disc. L'únic que es perd és que l'app ho torni a intentar sola. Una
   * gravació que algú ha fet amb una persona al davant no s'esborra per un botó d'aquesta
   * pantalla.
   */
  const descartaLesMortes = async () => {
    if (!window.confirm('Deixar d’intentar pujar-les?\n\nEs queden al telèfon —la frase a la '
      + 'biblioteca i la gravació al disc—, però l’app no hi tornarà sola.')) return;
    await syncManager.discardDeadLetters();
    await miraLaCua();
    toast.info('Fora de la cua. Segueixen al telèfon.');
  };

  const baixaVeus = async () => {
    if (baixantAudios()) { aturaBaixada(); return; }
    const d = await bibliotecaAlDia().catch(() => drillsLocals());
    await baixaTotsElsAudios(d, setVeus);
    await mesura();
    toast.success('Les veus ja són al telèfon.');
  };

  const baixaCurs = async () => {
    if (baixantCurs()) { aturaCurs(); return; }
    const r = await baixaElCurs(setCurs);
    // Una baixada a mitges s'ha de dir. Si el servidor no ha contestat quan es demanava la
    // llista d'una part, aquella part NO és al telèfon, i abans això passava en silenci.
    if (r.sense.length) {
      toast.error(`El servidor no ha contestat per ${r.sense.join(', ')}: això no s’ha baixat. Torna-ho a provar.`);
    } else if (r.fallades) {
      toast.error(`${r.fallades} ${r.fallades === 1 ? 'pantalla no s’ha' : 'pantalles no s’han'} pogut baixar. Torna-ho a provar.`);
    } else {
      toast.success('El curs ja es pot obrir sense connexió.');
    }
  };

  const baixaExtres = async () => {
    if (baixantExtres()) { aturaExtres(); return; }
    const d = await bibliotecaAlDia().catch(() => drillsLocals());
    await baixaExtresDeTot(d, setExtres);
    await mesura();
    toast.success('El català llegit i les imatges ja són al telèfon.');
  };

  const allibera = async () => {
    if (!window.confirm('Esborrar totes les veus baixades? Les tornaràs a poder baixar quan vulguis.')) return;
    setNetejant(true);
    try { await alliberaAudios(); await mesura(); } finally { setNetejant(false); }
  };

  if (!isNativeApp()) {
    return (
      <p style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.6, margin: 0 }}>
        Això és per a l’app del telèfon: al navegador no hi ha disc on desar les veus.
      </p>
    );
  }

  const faltenVeus = Math.max(0, (frases?.ambVeu || 0) - (veus?.fetes ?? disc?.fitxers ?? 0));
  const corrent = veus?.corrent || baixantAudios();
  const cursCorrent = curs?.corrent || baixantCurs();
  const extresCorrent = extres?.corrent || baixantExtres();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.6, margin: 0 }}>
        El que baixis es queda al telèfon i funciona en mode avió. Només la intel·ligència
        artificial —transcriure, traduir, el copilot, la captura de vídeos— necessita connexió
        sempre.
      </p>

      {/* Quina versió portes. Sense això, una app antiga i una de nova es veuen igual, i un dia
          sencer es va perdre buscant per què «ja està fet» no es veia a la pantalla. */}
      <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: '-6px 0 0' }}>
        Aquesta app és del <strong>{__VERSIO__}</strong>
      </p>

      {/* El que va cap amunt, no cap avall (#568).
          L'amo: «vull poder crear drills offline i després que aquests drills es processin quan
          hi hagi connexió». La cua ja ho feia sola, però no es veia enlloc: una frase gravada
          pel camp i una de pujada s'assemblaven, i no hi havia manera de saber si s'havia
          perdut. Aquí es veu, i es pot empènyer. */}
      {cua && (cua.frases + cua.fitxers + cua.canvis + cua.mortes) > 0 && (
        <Bloc
          titol="El que espera per pujar"
          ara={[cua.frases && `${cua.frases} ${cua.frases === 1 ? 'frase' : 'frases'}`,
               cua.fitxers && `${cua.fitxers} ${cua.fitxers === 1 ? 'gravació' : 'gravacions'}`,
               cua.canvis && `${cua.canvis} ${cua.canvis === 1 ? 'canvi' : 'canvis'}`]
               .filter(Boolean).join(' · ') || 'res'}
          peu={cua.mortes > 0
            ? `${cua.mortes} ${cua.mortes === 1 ? 'cosa no s’ha' : 'coses no s’han'} pogut pujar després de cinc intents i s’han apartat. Res no s’esborra del telèfon: la frase és a la biblioteca i la gravació al disc.`
            : 'Es puja sol quan hi ha senyal. Fins llavors és al telèfon i no es perd; les frases es veuen a la biblioteca marcades «Al telèfon».'}
        >
          <button type="button" onClick={pujaAra} disabled={pujant} style={pujant ? boto.atura : boto.gran}>
            <FaCloudUploadAlt size={16} /> {pujant ? 'Pujant…' : 'Prova-ho ara'}
          </button>
          {cua.mortes > 0 && (
            <>
              <button type="button" onClick={tornaHiAmbLesMortes} disabled={pujant} style={boto.petit}>
                <FaRedo size={12} /> Torna-ho a provar
              </button>
              <button type="button" onClick={descartaLesMortes} disabled={pujant} style={boto.petit}>
                <FaTrashAlt size={12} /> Deixa d’intentar-ho
              </button>
            </>
          )}
        </Bloc>
      )}

      <Bloc titol="Les frases" ara={frases ? `${frases.total.toLocaleString('ca')} al telèfon` : '…'}
            peu="Es posen al dia soles quan hi ha connexió." />

      <Bloc
        titol="Les veus"
        ara={disc ? `${disc.fitxers.toLocaleString('ca')} de ${(frases?.ambVeu || 0).toLocaleString('ca')} · ${mida(disc.bytes)}` : '…'}
        peu={faltenVeus > 0
          ? `En falten ${faltenVeus.toLocaleString('ca')}, uns ${mida(faltenVeus * BYTES_PER_VEU)}.${wifi === false ? ' Ara vas amb dades mòbils.' : ''}`
          : 'Totes les gravacions són al telèfon.'}
      >
        <button type="button" onClick={baixaVeus} style={corrent ? boto.atura : boto.gran}>
          {corrent ? <><FaStop size={14} /> Atura</> : faltenVeus > 0 ? <><FaCloudDownloadAlt size={16} /> Baixa totes les veus</> : <><FaCheck size={14} /> Ja hi són</>}
        </button>
        {disc && disc.fitxers > 0 && (
          <button type="button" onClick={allibera} disabled={netejant} style={boto.petit}>
            <FaTrashAlt size={12} /> {netejant ? 'Esborrant…' : 'Allibera l’espai'}
          </button>
        )}
        {veus && (veus.corrent || veus.fallades > 0) && (
          <Barra fet={veus.fetes} total={veus.total}
                 text={`${veus.fetes.toLocaleString('ca')} de ${veus.total.toLocaleString('ca')}${veus.fallades ? ` · ${veus.fallades} no s’han pogut baixar` : ''}`} />
        )}
      </Bloc>

      <Bloc
        titol="El català llegit i les imatges"
        ara={frases ? `${frases.ambExtres.toLocaleString('ca')} fitxers` : '…'}
        peu="El significat llegit en veu alta —el que sona a «Escolta-la amb el català» i a la primera passada de la Pràctica— i les fotos de les targetes. Sense això, sense xarxa el català calla i les fotos no es veuen."
      >
        <button type="button" onClick={baixaExtres} style={extresCorrent ? boto.atura : boto.gran}>
          {extresCorrent ? <><FaStop size={14} /> Atura</> : <><FaCloudDownloadAlt size={16} /> Baixa-ho</>}
        </button>
        {extres && (extres.corrent || extres.fetes > 0) && (
          <Barra fet={extres.fetes} total={extres.total || 1}
                 text={extres.corrent
                   ? `${extres.ara} · ${extres.fetes.toLocaleString('ca')} de ${extres.total.toLocaleString('ca')}`
                   : `${extres.fetes.toLocaleString('ca')} fitxers${extres.fallades ? ` · ${extres.fallades} no s’han pogut baixar` : ''}`} />
        )}
      </Bloc>

      <Bloc
        titol="El curs"
        ara="Gramàtica, Mètode, Històries, Sons i Pràctica"
        peu="Perquè s’obrin totes les unitats, tots els capítols i totes les llistes de pràctica sense connexió, no només els que ja hagis mirat."
      >
        <button type="button" onClick={baixaCurs} style={cursCorrent ? boto.atura : boto.gran}>
          {cursCorrent ? <><FaStop size={14} /> Atura</> : <><FaCloudDownloadAlt size={16} /> Baixa el curs</>}
        </button>
        {curs && (curs.corrent || curs.fetes > 0) && (
          <Barra fet={curs.fetes} total={curs.total || 1}
                 text={curs.corrent
                   ? `${curs.ara} (${curs.fetes}/${curs.total})`
                   : `${curs.fetes} pantalles${curs.fallades ? ` · ${curs.fallades} han fallat` : ''}`
                     + (curs.sense.length ? ` · sense ${curs.sense.join(', ')}` : '')} />
        )}
      </Bloc>
    </div>
  );
}

function Bloc({ titol, ara, peu, children }: { titol: string; ara: string; peu: string; children?: React.ReactNode }) {
  return (
    <section style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '14px 16px', background: 'var(--surface)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>{titol}</h3>
        <span style={{ fontSize: 13, color: 'var(--text-soft)', fontVariantNumeric: 'tabular-nums' }}>{ara}</span>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>{peu}</p>
      {children && <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginTop: 12 }}>{children}</div>}
    </section>
  );
}

function Barra({ fet, total, text }: { fet: number; total: number; text: string }) {
  return (
    <div style={{ flexBasis: '100%' }}>
      <div style={{ height: 6, background: 'var(--surface-2)', borderRadius: 3, overflow: 'hidden' }}>
        <i style={{ display: 'block', height: '100%', width: `${Math.min(100, (100 * fet) / Math.max(1, total))}%`, background: 'var(--brand-1)' }} />
      </div>
      <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: '5px 0 0' }}>{text}</p>
    </div>
  );
}

const base: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 'var(--r-pill)',
  cursor: 'pointer', fontWeight: 700, border: '1px solid transparent',
};
const boto = {
  gran: { ...base, padding: '12px 20px', minHeight: 48, fontSize: 15, background: 'var(--brand-1)', color: '#fff' },
  atura: { ...base, padding: '12px 20px', minHeight: 48, fontSize: 15, background: 'var(--amber-soft)', color: 'var(--amber-strong)', borderColor: 'var(--amber)' },
  petit: { ...base, padding: '8px 14px', fontSize: 13, background: 'var(--surface-2)', color: 'var(--text-soft)', borderColor: 'var(--border)' },
};
