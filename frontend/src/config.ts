// Remove trailing slash if present to avoid double slashes in URLs
const apiUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000';
export const API_BASE = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;

console.log('🔧 Config loaded:');
console.log('   VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('   VITE_API_BASE:', import.meta.env.VITE_API_BASE);
console.log('   API_BASE:', API_BASE);
console.log('   NODE_ENV:', import.meta.env.MODE);

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
