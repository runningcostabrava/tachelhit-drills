import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaChevronLeft } from 'react-icons/fa';
import { api } from '../api';

// Credits, read from the project's own docs/CREDITS.md so there is only ever one of them.
//
// The grammar of this app comes from a compendium two people wrote, the vocabulary from IRCAM's
// dictionaries, the transcriber from somebody who trained it and gave it away, and the corpora
// from people who recorded their own voices. Some of those licences REQUIRE that this be said
// where the work is used — and the only place a learner ever looks is inside the app.
//
// Rendered by hand, as React elements, because the project carries no Markdown library and no
// `dangerouslySetInnerHTML` anywhere: text that came from a file never becomes markup here.

type Block =
  | { t: 'h'; level: number; text: string }
  | { t: 'p'; text: string }
  | { t: 'li'; text: string }
  | { t: 'quote'; text: string }
  | { t: 'rule' };

// The small part of Markdown that CREDITS.md actually uses.
function parse(md: string): Block[] {
  const out: Block[] = [];
  let para: string[] = [];
  const flush = () => { if (para.length) { out.push({ t: 'p', text: para.join(' ') }); para = []; } };
  for (const raw of md.split('\n')) {
    const line = raw.trimEnd();
    if (!line.trim()) { flush(); continue; }
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) { flush(); out.push({ t: 'h', level: h[1].length, text: h[2] }); continue; }
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) { flush(); out.push({ t: 'rule' }); continue; }
    if (/^>\s?/.test(line)) { flush(); out.push({ t: 'quote', text: line.replace(/^>\s?/, '') }); continue; }
    const li = /^\s*[-*]\s+(.*)$/.exec(line) || /^\s*\d+\.\s+(.*)$/.exec(line);
    if (li) { flush(); out.push({ t: 'li', text: li[1] }); continue; }
    para.push(line.trim());
  }
  flush();
  return out;
}

// **bold**, `code` and [text](link) — as elements, never as HTML.
function rich(text: string, key: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g).filter(Boolean);
  return parts.map((p, i) => {
    const k = `${key}-${i}`;
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={k}>{p.slice(2, -2)}</strong>;
    if (/^`[^`]+`$/.test(p)) return <code key={k} style={{ background: 'var(--surface-2)', padding: '1px 5px', borderRadius: 4, fontSize: '0.92em' }}>{p.slice(1, -1)}</code>;
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(p);
    if (link) {
      const href = link[2];
      const external = /^https?:\/\//.test(href);
      return external
        ? <a key={k} href={href} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 600 }}>{link[1]}</a>
        : <span key={k} style={{ fontWeight: 600 }}>{link[1]}</span>;   // repo paths: nothing to open from here
    }
    return <span key={k}>{p}</span>;
  });
}

export default function CreditsPage() {
  const navigate = useNavigate();
  const [md, setMd] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    document.title = 'Crèdits i fonts · Tamazight';
    api.credits().then((r) => setMd(r.markdown)).catch(() => setFailed(true));
  }, []);

  const blocks = md ? parse(md) : [];
  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 720, margin: '0 auto' }}>
      <button onClick={() => navigate(-1)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: 'none', color: 'var(--brand-1)', fontWeight: 700, cursor: 'pointer', padding: '4px 0', marginBottom: 8 }}>
        <FaChevronLeft /> Enrere
      </button>

      {failed && (
        <p style={{ color: 'var(--text-soft)', lineHeight: 1.6 }}>
          Ara mateix no s’han pogut llegir els crèdits. Són a <strong>docs/CREDITS.md</strong> del
          repositori del projecte, amb cada font, la seva llicència i la citació que demana.
        </p>
      )}
      {!md && !failed && <p style={{ color: 'var(--text-muted)' }}>Carregant…</p>}

      {blocks.map((b, i) => {
        const key = `b${i}`;
        if (b.t === 'rule') return <hr key={key} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '22px 0' }} />;
        if (b.t === 'h') {
          const size = b.level === 1 ? 26 : b.level === 2 ? 19 : 16;
          return (
            <h2 key={key} style={{ fontFamily: 'var(--font-display)', fontSize: size, lineHeight: 1.25, margin: b.level === 1 ? '0 0 10px' : '24px 0 8px' }}>
              {rich(b.text, key)}
            </h2>
          );
        }
        if (b.t === 'quote') {
          return (
            <blockquote key={key} style={{ margin: '10px 0', padding: '10px 14px', borderLeft: '3px solid var(--brand-1)', background: 'var(--surface-2)', borderRadius: '0 var(--r-md) var(--r-md) 0', fontSize: 14, lineHeight: 1.6 }}>
              {rich(b.text, key)}
            </blockquote>
          );
        }
        if (b.t === 'li') {
          return (
            <div key={key} style={{ display: 'flex', gap: 10, margin: '4px 0', fontSize: 14.5, lineHeight: 1.6 }}>
              <span style={{ color: 'var(--brand-1)', flexShrink: 0 }}>·</span>
              <span>{rich(b.text, key)}</span>
            </div>
          );
        }
        return <p key={key} style={{ margin: '8px 0', fontSize: 14.5, lineHeight: 1.65 }}>{rich(b.text, key)}</p>;
      })}
    </div>
  );
}
