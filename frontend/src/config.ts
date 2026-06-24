// 1. Default to your live production server
let API_BASE_TMP = 'https://tachelhit-drills-api.onrender.com';

// 2. ONLY use the local computer backend if we are explicitly running the Vite local dev server ('npm run dev')
// and we are NOT running inside a native mobile app wrapper.
const isDevServer = import.meta.env.DEV;
const isNativeApp = (window as any).Capacitor?.isNative || window.location.hostname !== 'localhost';

if (isDevServer && !isNativeApp) {
  API_BASE_TMP = 'http://localhost:8000';
} else {
  API_BASE_TMP = 'https://tachelhit-drills-api.onrender.com';
}

export const API_BASE = API_BASE_TMP;

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
