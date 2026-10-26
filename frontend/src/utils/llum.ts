// Com es veu la paraula que sona (#340). Viu a part perquè la fan servir el component compartit
// de la frase amaziga i la frase catalana, i un fitxer de components no pot exportar constants
// sense trencar la recàrrega en calent.
export const llum: React.CSSProperties = {
  background: 'var(--brand-1)', color: '#fff', borderRadius: 4,
  padding: '0 2px', margin: '0 -2px',
};
