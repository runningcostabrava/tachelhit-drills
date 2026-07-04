// Lightweight, provider-free toast system. A module-level store emits to a
// single mounted <ToastHost/>; anywhere in the app calls toast.success/error/
// info(...) without prop-drilling or context. Replaces blocking alert().
export type ToastKind = 'success' | 'error' | 'info';
export interface ToastItem { id: number; kind: ToastKind; message: string; }
type Listener = (items: ToastItem[]) => void;

let items: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<Listener>();

function emit() { listeners.forEach((l) => l(items)); }

function push(kind: ToastKind, message: string) {
  const id = nextId++;
  items = [...items, { id, kind, message }];
  emit();
  window.setTimeout(() => {
    items = items.filter((i) => i.id !== id);
    emit();
  }, 4200);
}

export const toast = {
  success: (m: string) => push('success', m),
  error: (m: string) => push('error', m),
  info: (m: string) => push('info', m),
};

export function dismissToast(id: number) {
  items = items.filter((i) => i.id !== id);
  emit();
}

export function subscribeToasts(l: Listener) {
  listeners.add(l);
  l(items);
  return () => { listeners.delete(l); };
}
