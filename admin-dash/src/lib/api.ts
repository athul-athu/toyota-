/**
 * API URLs for the Django backend.
 *
 * Default: call Render directly (CORS_ALLOW_ALL_ORIGINS on Django).
 * Set in admin-dash/.env.local or Vercel env at build time:
 *   NEXT_PUBLIC_API_URL=https://toyota-assessment.onrender.com
 *
 * Optional same-origin proxy (if /api rewrites work on your Vercel project):
 *   NEXT_PUBLIC_API_PROXY=true
 */

export const API_PATH_PREFIX = "/api";

const RENDER_API = "https://toyota-assessment.onrender.com";

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

export function resolveUpstreamUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeBackendUrl(fromEnv);
  if (process.env.NODE_ENV === "production") return RENDER_API;
  return "http://localhost:8000";
}

/** Base URL for browser fetch(). */
export function resolveBackendUrl(): string {
  if (process.env.NEXT_PUBLIC_API_PROXY === "true") {
    return "";
  }
  return resolveUpstreamUrl();
}

export const UPSTREAM_URL = resolveUpstreamUrl();
export const BACKEND_URL = resolveBackendUrl();

/** @deprecated Use UPSTREAM_URL */
export const API_BASE_URL = UPSTREAM_URL;

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
