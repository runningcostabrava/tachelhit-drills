// Controlled variety vocabulary (mirrors the backend GET /varieties). ISO 639-3
// codes kept DISTINCT so a speaker's variety is never collapsed into the
// standard. Tarifit (rif) is first-class — the Catalan diaspora is largely Rif.
export interface Variety { code: string; label: string }

export const VARIETIES: Variety[] = [
  { code: 'shi', label: 'Taixelhit (Tashelhit)' },
  { code: 'tzm', label: "Tamazight de l'Atles Central" },
  { code: 'rif', label: 'Tarifit (Rif)' },
  { code: 'zgh', label: 'Amazic estàndard marroquí (IRCAM)' },
  { code: 'kab', label: 'Cabilenc (Kabyle)' },
  { code: 'other', label: 'Altra / no ho sé' },
];

export function varietyLabel(code?: string | null): string {
  if (!code) return '';
  return VARIETIES.find((v) => v.code === code)?.label ?? code;
}

// Short chip label — the ISO code uppercased (e.g. RIF), or the raw value.
export function varietyShort(code?: string | null): string {
  if (!code) return '';
  const known = VARIETIES.find((v) => v.code === code);
  return known && known.code !== 'other' ? known.code.toUpperCase() : code;
}
