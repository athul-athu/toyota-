/** Django API on Render (production). */
export const PRODUCTION_API_URL = "https://toyota-assessment.onrender.com";

/**
 * Normalize API base URL (no trailing slash, no trailing /api).
 * Wrong: https://example.onrender.com/api → https://example.onrender.com
 */
export function normalizeApiBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

/**
 * Django API base URL.
 * - Local: http://localhost:8000 or NEXT_PUBLIC_API_URL
 * - Vercel: NEXT_PUBLIC_API_URL or PRODUCTION_API_URL (CORS allowed on Django)
 */
export function resolveApiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeApiBaseUrl(fromEnv);

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host.endsWith(".vercel.app")) {
      return PRODUCTION_API_URL;
    }
  }

  return "http://localhost:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();
