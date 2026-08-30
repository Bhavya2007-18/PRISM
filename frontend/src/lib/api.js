/**
 * Centralized API utility for PRISM frontend.
 * Reads base API URL from VITE_API_URL environment variable.
 * Defaults to relative paths (which use Vite dev proxy in local development).
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export function getApiUrl(path) {
  if (!path.startsWith('/')) {
    path = '/' + path;
  }
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

export async function apiFetch(path, options = {}) {
  const url = getApiUrl(path);
  return fetch(url, options);
}

/**
 * Safely fetches JSON from an API endpoint.
 * Ensures response is 200 OK and content-type is application/json before parsing.
 * Prevents "Unexpected token '<', '<!DOCTYPE '... is not valid JSON" errors when backend is offline or serving HTML fallback pages.
 */
export async function safeFetchJson(path, options = {}) {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    throw new Error(`HTTP error ${res.status}`);
  }
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('Backend server returned non-JSON response (ensure Python backend is running on port 8001)');
  }
  return res.json();
}
