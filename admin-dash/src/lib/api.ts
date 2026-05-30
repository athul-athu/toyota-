/**
 * API routing:
 * - On Vercel (*.vercel.app): same-origin /api/* → proxied to Render (no CORS in browser)
 * - Local dev: NEXT_PUBLIC_API_URL from .env.local (e.g. http://localhost:8000)
 */

export const API_PATH_PREFIX = "/api";

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

export function resolveBackendUrl(): string {
  if (typeof window !== "undefined") {
    if (window.location.hostname.endsWith(".vercel.app")) {
      return "";
    }
  }

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
  return base ? `${base}${route}` : route;
}
