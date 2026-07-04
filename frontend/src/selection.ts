// Tiny shared store for the currently-selected drill ids, so the AI copilot
// dock (mounted at the app root) knows what the grid has selected without
// prop-drilling. Same pattern as toast.ts.
let ids: number[] = [];
const listeners = new Set<(ids: number[]) => void>();

export function setSelectedDrillIds(next: number[]) {
  ids = next;
  listeners.forEach((l) => l(ids));
}
export function getSelectedDrillIds() {
  return ids;
}
export function subscribeSelection(l: (ids: number[]) => void) {
  listeners.add(l);
  l(ids);
  return () => { listeners.delete(l); };
}

// Fired by the copilot after it creates/edits drills so lists can refresh.
export function notifyDrillsChanged() {
  window.dispatchEvent(new Event('drills-changed'));
}
