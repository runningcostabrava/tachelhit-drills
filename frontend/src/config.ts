// Remove trailing slash if present to avoid double slashes in URLs
const apiUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000';
let API_BASE_TMP = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;

// Force production backend if we are in production (vercel)
if (import.meta.env.MODE === 'production' && !API_BASE_TMP.includes('render.com')) {
  API_BASE_TMP = 'https://tachelhit-drills-api.onrender.com';
}

export const API_BASE = API_BASE_TMP;

console.log('🔧 Config loaded - Audio fix v5:');
console.log('   VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('   VITE_API_BASE:', import.meta.env.VITE_API_BASE);
console.log('   API_BASE:', API_BASE);
console.log('   NODE_ENV:', import.meta.env.MODE);
console.log('   Production forced:', import.meta.env.MODE === 'production');
console.log('   Timestamp:', new Date().toISOString());
console.log('   Build version: 2026-02-11-connection-test');
console.log('   User agent:', navigator.userAgent);

// Test connection to backend
(async () => {
  try {
    console.log('🔌 Testing connection to backend...');
    const response = await fetch(`${API_BASE}/test-connection`);
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Backend connection successful:', data);
    } else {
      console.error('❌ Backend connection failed:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('❌ Backend connection error:', error);
  }
})();

/**
 * Get the full URL for a media file
 * - If URL is already absolute (Cloudinary), return as-is
 * - If URL is relative (local storage), prepend API_BASE
 */
export function getMediaUrl(url: string | null | undefined): string {
  if (!url) return '';

  // Check if URL is already absolute (starts with http:// or https://)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  // Relative URL - prepend API_BASE
  return `${API_BASE}${url}`;
}
