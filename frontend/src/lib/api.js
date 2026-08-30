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
