import { apiUrl, BACKEND_URL, UPSTREAM_URL } from "./api";
import {
  buildAuthHeaders,
  ensureSessionForApi,
  refreshSession,
} from "./auth";
import {
  isPayrollEmailApiPath,
  looksLikeSmtpError,
  smtpErrorMessage,
} from "./smtp-errors";

type ApiFetchOptions = RequestInit & {
  auth?: boolean;
  json?: boolean;
};

async function parseJsonSafe(res: Response): Promise<Record<string, unknown>> {
  try {
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export function apiErrorFromResponse(
  res: Response,
  data: Record<string, unknown>,
  fallback: string,
): string {
  if (res.status === 404) {
    return (
      `API not found (${res.url}). Set NEXT_PUBLIC_API_URL in admin-dash/.env.local ` +
      `(API base: ${BACKEND_URL || UPSTREAM_URL}). Redeploy Vercel after env changes.`
    );
  }
  if (res.status === 401) {
    return String(data.error ?? "Session expired. Please sign in again.");
  }
  const msg = String(data.error ?? fallback);
  if (looksLikeSmtpError(msg)) {
    return smtpErrorMessage(msg);
  }
  if (res.status >= 500 && isPayrollEmailApiPath(res.url)) {
    return smtpErrorMessage(msg);
  }
  return msg;
}

/**
 * Fetch Django API with auth, refresh+retry on 401, clear errors on 404/CORS/network.
 */
export async function apiFetch(
  path: string,
  options: ApiFetchOptions = {},
): Promise<Response> {
  const { auth = true, json = false, headers: initHeaders, ...rest } = options;

  async function run(tryRefresh: boolean): Promise<Response> {
    const headers = new Headers(initHeaders);

    if (auth) {
      if (tryRefresh) {
        await ensureSessionForApi();
      }
      const authHeader = buildAuthHeaders(json ? "application/json" : undefined);
      for (const [key, value] of Object.entries(authHeader)) {
        headers.set(key, value);
      }
    } else if (json) {
      headers.set("Content-Type", "application/json");
    }

    return fetch(apiUrl(path), { ...rest, headers });
  }

  const maxAttempts = 2;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      let res = await run(true);

      if (auth && res.status === 401) {
        const refreshed = await refreshSession();
        if (refreshed) {
          res = await run(false);
        }
      }

      return res;
    } catch (err) {
      if (err instanceof Error && err.message.includes("not signed in")) {
        throw err;
      }
      const isNetwork =
        err instanceof TypeError ||
        (err instanceof Error && err.message === "Failed to fetch");
      if (isNetwork && attempt < maxAttempts) {
        await new Promise((r) => setTimeout(r, 2000));
        continue;
      }
      if (isPayrollEmailApiPath(path)) {
        throw new Error(smtpErrorMessage(), { cause: err });
      }
      throw new Error(
        `Cannot reach API (upstream ${UPSTREAM_URL}). ` +
          `If Render was sleeping, wait ~30s and refresh. ` +
          `If this happened while sending emails, it is usually an SMTP error on Render—` +
          `check SMTP_* environment variables, not CORS.`,
        { cause: err },
      );
    }
  }

  throw new Error(`Cannot reach API (upstream ${UPSTREAM_URL}).`);
}

export async function apiFetchJson<T extends Record<string, unknown>>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<{ res: Response; data: T }> {
  const res = await apiFetch(path, options);
  const data = (await parseJsonSafe(res)) as T;
  return { res, data };
}
