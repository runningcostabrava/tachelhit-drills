// Remove trailing slash if present to avoid double slashes in URLs
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_BASE = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
