import axios from 'axios';
import { Preferences } from '@capacitor/preferences';

// Backend selection, in priority order:
// 1. VITE_API_URL (frontend/.env) always wins when set.
// 2. Native app builds (Capacitor APK/WebView) default to production.
// 3. The Vite dev server defaults to a local backend on the same host the
//    page was loaded from — so `npm run dev --host` tested from a phone hits
//    your dev backend over the LAN instead of silently writing to production.
// 4. Production web builds default to the Render API.
const PROD_API = 'https://tachelhit-drills-api.onrender.com';
const envApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
// Single source of truth for "are we inside the Capacitor shell?". Capacitor 8
// removed the old `Capacitor.isNative` boolean; only isNativePlatform() exists.
export const isNativeApp = (): boolean =>
  !!((window as any).Capacitor?.isNativePlatform?.() ?? (window as any).Capacitor?.isNative);

const rawApiBase =
  envApiUrl ||
  (import.meta.env.DEV && !isNativeApp() ? `http://${window.location.hostname}:8000` : PROD_API);

// Strip trailing slashes: a trailing slash in VITE_API_URL turns every
// `${API_BASE}/drills/` into a double-slash `//drills/`, which the backend
// 404s. This makes the base robust regardless of how the env var is written.
export const API_BASE = rawApiBase.replace(/\/+$/, '');

// ---- Identity & API-key header injection ----
// Components call axios and fetch directly all over the codebase, so until
// there is a shared API client both headers are injected globally here:
// - X-API-Key: must match the backend's API_KEY env var (bot lock)
// - X-User-Token: the personal token from /users/register (multi-tenancy);
//   read from localStorage on every request so login applies immediately.
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

// localStorage is the synchronous cache every request reads; on a device the
// same values are mirrored to Capacitor Preferences (UserDefaults on iOS),
// which survives WKWebView storage eviction. restoreUserIdentity() copies
// them back on boot (see main.tsx).
const NATIVE_TOKEN_KEY = 'user_token';
const NATIVE_NAME_KEY = 'user_name';

export const getUserToken = () => localStorage.getItem('user_token') || '';
/** Adding to the library needs a name (#184). A newcomer has none, and used to meet a bare 401. */
export const hasIdentity = () => !!getUserToken();
export const getUserName = () => localStorage.getItem('user_name') || '';
export const setUserIdentity = (token: string, username: string) => {
  localStorage.setItem('user_token', token);
  if (username) localStorage.setItem('user_name', username);
  Preferences.set({ key: NATIVE_TOKEN_KEY, value: token }).catch(() => {});
  if (username) Preferences.set({ key: NATIVE_NAME_KEY, value: username }).catch(() => {});
};
export const clearUserIdentity = () => {
  localStorage.removeItem('user_token');
  localStorage.removeItem('user_name');
  Preferences.remove({ key: NATIVE_TOKEN_KEY }).catch(() => {});
  Preferences.remove({ key: NATIVE_NAME_KEY }).catch(() => {});
};
export async function restoreUserIdentity(): Promise<void> {
  try {
    if (localStorage.getItem('user_token')) return;
    const { value: token } = await Preferences.get({ key: NATIVE_TOKEN_KEY });
    if (!token) return;
    const { value: name } = await Preferences.get({ key: NATIVE_NAME_KEY });
    localStorage.setItem('user_token', token);
    if (name) localStorage.setItem('user_name', name);
  } catch {
    /* storage unavailable (private mode): stay anonymous */
  }
}

axios.interceptors.request.use((cfg) => {
  const url = typeof cfg.url === 'string' ? cfg.url : '';
  if (url.startsWith(API_BASE) || url.startsWith('/')) {
    if (API_KEY) (cfg.headers as any)['X-API-Key'] = API_KEY;
    const t = getUserToken();
    if (t) (cfg.headers as any)['X-User-Token'] = t;
  }
  return cfg;
});

const originalFetch = window.fetch.bind(window);
window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
  const url =
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  if (url.startsWith(API_BASE)) {
    const headers = new Headers(
      init?.headers ?? (input instanceof Request ? input.headers : undefined)
    );
    if (API_KEY) headers.set('X-API-Key', API_KEY);
    const t = getUserToken();
    if (t) headers.set('X-User-Token', t);
    init = { ...init, headers };
  }
  return originalFetch(input, init);
};

if (import.meta.env.DEV) {
  console.log('[config] API_BASE:', API_BASE, '| mode:', import.meta.env.MODE);
}

// Test fetching drills - error handling updated (commented out for now to prevent startup errors)
/*
(async () => {
  try {
    console.log('🔍 Testing drills fetch...');
    console.log('🔍 API_BASE:', API_BASE);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    const response = await fetch(`${API_BASE}/drills/`, {
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });
    clearTimeout(timeoutId);
    console.log('🔍 Response status:', response.status, response.statusText);
    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Drills fetch successful, count: ${data.length}`);
      // Log first drill if exists
      if (data.length > 0) {
        console.log('🔍 First drill sample:', JSON.stringify(data[0], null, 2));
      }
    } else {
      const text = await response.text();
      console.error('❌ Drills fetch failed:', response.status, response.statusText, text);
    }
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.error('❌ Drills fetch timeout after 15 seconds.');
    } else {
      console.error('❌ Drills fetch error:', error.message);
    }
  }
})();
*/

/**
 * Get the full URL for a media file
 * - If URL is already absolute (Cloudinary), return as-is
 * - If URL is relative (local storage), prepend API_BASE
 */
export function getMediaUrl(url: string | null | undefined): string {
  if (!url) return '';

  let corrected = url;

  // Caso especial: URL que comienza con el dominio del backend pegado a https// (sin dos puntos)
  // Ejemplo: tachelhit-drills-api.onrender.comhttps//res.cloudinary.com/...
  // Convertir directamente a https://res.cloudinary.com/...
  const malformedPattern = /^(https?:\/\/)?tachelhit-drills-api\.onrender\.comhttps\/\//i;
  if (malformedPattern.test(corrected)) {
    // Eliminar todo hasta después de https//
    corrected = corrected.replace(malformedPattern, 'https://');
  }

  // Fix malformed protocol (https// -> https://, http// -> http://) anywhere in the string
  corrected = corrected.replace(/https\/\//g, 'https://').replace(/http\/\//g, 'http://');

  // Remove duplicate API_BASE prefix if accidentally included
  const apiBaseWithoutProtocol = API_BASE.replace(/^https?:\/\//, '');
  const prefixesToRemove = [
    `https://${apiBaseWithoutProtocol}`,
    `http://${apiBaseWithoutProtocol}`,
    apiBaseWithoutProtocol,
  ];
  for (const prefix of prefixesToRemove) {
    if (corrected.startsWith(prefix) && corrected.includes('res.cloudinary.com')) {
      corrected = corrected.substring(prefix.length);
      // Ensure corrected starts with https:// or http://
      if (corrected.startsWith('https//')) corrected = 'https://' + corrected.substring(7);
      if (corrected.startsWith('http//')) corrected = 'http://' + corrected.substring(6);
      break;
    }
  }

  // Check if URL is already absolute (starts with http:// or https:// or blob:)
  if (corrected.startsWith('http://') || corrected.startsWith('https://') || corrected.startsWith('blob:') || corrected.startsWith('data:')) {
    // If it's already a full URL (like Cloudinary), return it directly without any more processing
    return corrected;
  }

  // Relative URL - prepend API_BASE
  return `${API_BASE}${corrected}`;
}
