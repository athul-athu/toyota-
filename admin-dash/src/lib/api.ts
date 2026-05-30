/**
 * Django API base URL.
 * - Local dev: http://localhost:8000 (or NEXT_PUBLIC_API_URL)
 * - Vercel production: "" (same-origin) so /api/* is proxied via next.config rewrites (no CORS)
 */
function resolveApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    // Same-origin /api proxy (next.config rewrites) — avoids CORS on Render
    if (host.endsWith(".vercel.app")) {
      return "";
    }
  }

  const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "");
  if (configured) return configured;

  return "http://localhost:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();
