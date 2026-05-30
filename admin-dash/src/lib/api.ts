/**
 * API base URL — set in admin-dash/.env.local:
 *
 *   NEXT_PUBLIC_API_URL=https://toyota-assessment.onrender.com
 *
 * (host only, no /api suffix)
 *
 * Full URLs are built as: {BASE}/api/{path}
 * e.g. apiUrl("auth/login/") → https://toyota-assessment.onrender.com/api/auth/login/
 */

export const API_PATH_PREFIX = "/api";

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

/** Django backend origin from NEXT_PUBLIC_API_URL (inlined at `npm run build`). */
export function resolveBackendUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeBackendUrl(fromEnv);
  return "http://localhost:8000";
}

export const BACKEND_URL = resolveBackendUrl();

/** @deprecated Use BACKEND_URL */
export const API_BASE_URL = BACKEND_URL;

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
