/**
 * API URLs for the Django backend.
 *
 * Production (Vercel): browser calls same-origin `/api/...` → Next.js rewrites
 * proxy to Render (see next.config.ts). No CORS issues.
 *
 * Local dev: set in admin-dash/.env.local (optional if using rewrites):
 *   NEXT_PUBLIC_API_URL=http://localhost:8000
 *
 * To call Render directly from the browser (not recommended on Vercel):
 *   NEXT_PUBLIC_API_DIRECT=true
 *   NEXT_PUBLIC_API_URL=https://toyota-assessment.onrender.com
 */

export const API_PATH_PREFIX = "/api";

const RENDER_API = "https://toyota-assessment.onrender.com";

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

/** Upstream Django origin (for error messages and direct mode). */
export function resolveUpstreamUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeBackendUrl(fromEnv);
  if (process.env.NODE_ENV === "production") return RENDER_API;
  return "http://localhost:8000";
}

/**
 * Base URL for fetch(). Empty string = same-origin `/api/*` (Vercel rewrite proxy).
 */
export function resolveBackendUrl(): string {
  const direct = process.env.NEXT_PUBLIC_API_DIRECT === "true";
  if (direct) {
    return resolveUpstreamUrl();
  }
  // Default: relative /api paths (works on Vercel + local `next dev` via rewrites)
  return "";
}

export const UPSTREAM_URL = resolveUpstreamUrl();
export const BACKEND_URL = resolveBackendUrl();

/** @deprecated Use BACKEND_URL / UPSTREAM_URL */
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
