import { useCallback, useEffect, useState } from 'react';
import { FaCheck, FaCloudDownloadAlt, FaStop, FaTrashAlt } from 'react-icons/fa';
import { Network } from '@capacitor/network';
import { isNativeApp } from '../config';
import { toast } from '../toast';
import { bibliotecaAlDia, drillsLocals } from '../services/biblioteca';
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
  const [disc, setDisc] = useState<{ fitxers: number; bytes: number; veus: number; extres: number } | null>(null);
  const [veus, setVeus] = useState<ProgresAudios | null>(null);
  const [curs, setCurs] = useState<ProgresCurs | null>(null);
  const [extres, setExtres] = useState<ProgresExtres | null>(null);
  const [wifi, setWifi] = useState<boolean | null>(null);
  const [netejant, setNetejant] = useState(false);

  const mesura = useCallback(async () => {
    const d = await drillsLocals().catch(() => [] as Awaited<ReturnType<typeof drillsLocals>>);
    setFrases({
      total: d.length,
      ambVeu: d.filter((x) => (x.audio_url || '').trim()).length,
      ambExtres: d.filter((x) => (x.audio_tts_url || '').trim()).length
        + d.filter((x) => (x.image_url || '').trim()).length,
    });
    setDisc(await resumAudios().catch(() => ({ fitxers: 0, bytes: 0, veus: 0, extres: 0 })));
  }, []);

  useEffect(() => {
    void mesura();
    Network.getStatus().then((s) => setWifi(s.connectionType === 'wifi')).catch(() => setWifi(null));
  }, [mesura]);

  const baixaVeus = async () => {
    if (baixantAudios()) { aturaBaixada(); return; }
    const d = await bibliotecaAlDia().catch(() => drillsLocals());
    await baixaTotsElsAudios(d, setVeus);
    await mesura();
    toast.success('Les veus ja són al telèfon.');
  };

  const baixaCurs = async () => {
    if (baixantCurs()) { aturaCurs(); return; }
    await baixaElCurs(setCurs);
    toast.success('El curs ja es pot obrir sense connexió.');
  };

  const baixaExtres = async () => {
    if (baixantExtres()) { aturaExtres(); return; }
    const d = await bibliotecaAlDia().catch(() => drillsLocals());
    await baixaExtresDeTot(d, setExtres);
    await mesura();
    toast.success('El català llegit i les imatges ja són al telèfon.');
  };

  /**
   * Posa-ho tot al dia, i només el que ha canviat.
   *
   * L'amo (31-10): «si hi ha actualització de l'app, no cal perdre tota la info descarregada
   * offline, excepte la info que hagi estat actualitzada; cal poder sincronitzar les dades
   * offline». Actualitzar l'app no esborra res —els fitxers i la còpia viuen a la carpeta de
   * dades, no dins de l'app—, però fins ara per posar-ho al dia calia prémer tres botons i
   * saber quin.
   *
   * Això és un de sol, i cada pas ja sap saltar-se el que té: les frases es demanen per
   * `since=` i només arriben les que han canviat (i les mortes, per treure-les); una veu que ja
   * és a disc no es torna a baixar, i si algú ha tornat a gravar-la l'adreça canvia i llavors
   * sí. Es pot aturar i reprendre.
   */
  const posaAlDia = async () => {
    if (baixantAudios() || baixantExtres() || baixantCurs()) {
      aturaBaixada(); aturaExtres(); aturaCurs();
      return;
    }
    const d = await bibliotecaAlDia().catch(() => drillsLocals());
    await baixaTotsElsAudios(d, setVeus);
    await baixaExtresDeTot(d, setExtres);
    await baixaElCurs(setCurs);
    await mesura();
    toast.success('Tot al dia al telèfon.');
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

  const faltenVeus = Math.max(0, (frases?.ambVeu || 0) - (veus?.fetes ?? disc?.veus ?? 0));
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

      {/* El botó que fa falta quan surt una versió nova: un de sol, i només el que ha canviat. */}
      <Bloc
        titol="Posa-ho tot al dia"
        ara={corrent || extresCorrent || cursCorrent ? 'anant-hi…' : ''}
        peu="Actualitzar l’app no esborra res del que tens baixat. Això demana només el que ha canviat des de l’últim cop: les frases noves o retocades, les veus que encara no tens i les pantalles del curs."
      >
        <button type="button" onClick={posaAlDia}
                style={corrent || extresCorrent || cursCorrent ? boto.atura : boto.gran}>
          {corrent || extresCorrent || cursCorrent
            ? <><FaStop size={14} /> Atura</>
            : <><FaCloudDownloadAlt size={16} /> Posa-ho tot al dia</>}
        </button>
      </Bloc>

      <Bloc titol="Les frases" ara={frases ? `${frases.total.toLocaleString('ca')} al telèfon` : '…'}
            peu="Es posen al dia soles quan hi ha connexió." />

      <Bloc
        titol="Les veus"
        ara={disc ? `${disc.veus.toLocaleString('ca')} de ${(frases?.ambVeu || 0).toLocaleString('ca')} · ${mida(disc.bytes)} en total` : '…'}
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
        ara={disc && frases ? `${disc.extres.toLocaleString('ca')} de ${frases.ambExtres.toLocaleString('ca')}` : '…'}
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
                 text={curs.corrent ? `${curs.ara} (${curs.fetes}/${curs.total})` : `${curs.fetes} pantalles${curs.fallades ? ` · ${curs.fallades} han fallat` : ''}`} />
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
