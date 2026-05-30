import { apiUrl } from "./api";
import {
  buildAuthHeaders,
  ensureSessionForApi,
  refreshSession,
} from "./auth";

type ApiFetchOptions = RequestInit & {
  /** Attach Bearer token (default true). */
  auth?: boolean;
  /** Set Content-Type: application/json */
  json?: boolean;
};

/**
 * Fetch Django API with auth, one refresh+retry on 401, clearer errors on network/CORS failures.
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
    throw new Error(
      "Could not reach the API (network or timeout). Sign in again, or retry with a smaller payroll file.",
      { cause: err },
    );
  }
}
