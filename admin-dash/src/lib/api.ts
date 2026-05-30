/**
 * Backend URL from admin-dash/.env.local → NEXT_PUBLIC_API_URL
 * Host only, no /api suffix (e.g. https://toyota-assessment.onrender.com)
 */

/** Django mounts routes under this prefix (see server/urls.py). */
export const API_PATH_PREFIX = "/api";

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

/** NEXT_PUBLIC_API_URL from .env.local (inlined at build time on Vercel). */
export function resolveBackendUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeBackendUrl(fromEnv);
  return "http://localhost:8000";
}

export const BACKEND_URL = resolveBackendUrl();

/** @deprecated Use BACKEND_URL */
export const API_BASE_URL = BACKEND_URL;

/**
 * Full URL for a Django API route.
 * @param path Route after /api, e.g. "auth/login/" or "/payroll/import/"
 */
export function apiUrl(path: string): string {
  const base = BACKEND_URL.replace(/\/$/, "");
  let route = path.trim();
  if (!route.startsWith("/")) {
    route = `/${route}`;
  }
  if (!route.startsWith(`${API_PATH_PREFIX}/`)) {
    route = `${API_PATH_PREFIX}${route}`;
  }
  return `${base}${route}`;
}
