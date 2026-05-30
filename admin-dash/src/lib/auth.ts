import { UPSTREAM_URL } from "./api";
import { apiFetch, apiFetchJson, apiErrorFromResponse } from "./api-request";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "staff";
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: AuthUser;
};

export type SignupResponse =
  | LoginResponse
  | {
      message: string;
      requires_email_confirmation?: boolean;
    };

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function clearAuth(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function saveSession(data: LoginResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  if (data.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  }
}

/** After Supabase email confirmation, tokens arrive in the URL hash on /login. */
export function saveSessionFromAuthHash(): boolean {
  if (typeof window === "undefined") return false;

  const raw = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : "";
  if (!raw) return false;

  const params = new URLSearchParams(raw);
  const accessToken = params.get("access_token");
  if (!accessToken) return false;

  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  const refreshToken = params.get("refresh_token");
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  window.history.replaceState(
    null,
    "",
    window.location.pathname + window.location.search,
  );
  return true;
}

function emailConfirmRedirectUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return `${window.location.origin}/login`;
}

export function buildAuthHeaders(contentType?: string): Record<string, string> {
  const token = getAccessToken();
  if (!token) {
    throw new Error(
      "You are not signed in. Open the login page and sign in again.",
    );
  }
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  return headers;
}

export async function refreshSession(): Promise<boolean> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  const { res, data } = await apiFetchJson<LoginResponse & { error?: string }>(
    "auth/refresh/",
    {
      method: "POST",
      auth: false,
      json: true,
      body: JSON.stringify({ refresh_token: refreshToken }),
    },
  );

  if (!res.ok) {
    clearAuth();
    return false;
  }

  saveSession(data as LoginResponse);
  return true;
}

export async function ensureSessionForApi(): Promise<void> {
  if (getAccessToken()) return;
  const ok = await refreshSession();
  if (!ok) {
    throw new Error(
      "Session expired. Please sign in again before sending emails.",
    );
  }
}

export async function signup(
  email: string,
  password: string,
  fullName?: string,
): Promise<SignupResponse> {
  const { res, data } = await apiFetchJson<SignupResponse & { error?: string }>(
    "auth/signup/",
    {
      method: "POST",
      auth: false,
      json: true,
      body: JSON.stringify({
        email,
        password,
        full_name: fullName || undefined,
        redirect_to: emailConfirmRedirectUrl(),
      }),
    },
  );

  if (!res.ok) {
    throw new Error(apiErrorFromResponse(res, data, "Sign up failed"));
  }

  if ("access_token" in data) {
    saveSession(data as LoginResponse);
  }

  return data as SignupResponse;
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const { res, data } = await apiFetchJson<LoginResponse & { error?: string }>(
    "auth/login/",
    {
      method: "POST",
      auth: false,
      json: true,
      body: JSON.stringify({ email, password }),
    },
  );

  if (!res.ok) {
    throw new Error(apiErrorFromResponse(res, data, "Login failed"));
  }

  saveSession(data as LoginResponse);
  return data as LoginResponse;
}

export async function fetchMe(): Promise<AuthUser | null> {
  const token = getAccessToken();
  if (!token) return null;

  const res = await apiFetch("auth/me/", { method: "GET" });

  if (res.status === 401 || res.status === 403) {
    clearAuth();
    return null;
  }

  if (!res.ok) {
    return null;
  }

  const data = await res.json();
  return data.user as AuthUser;
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  if (token) {
    try {
      await apiFetch("auth/logout/", { method: "POST" });
    } catch {
      // ignore network errors on logout
    }
  }
  clearAuth();
}

/** For debugging in browser console: current API base */
export function getApiBaseUrl(): string {
  return UPSTREAM_URL;
}
