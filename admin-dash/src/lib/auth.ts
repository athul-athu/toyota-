import { apiUrl } from "./api";

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

/** Throws if there is no access token (call before protected API requests). */
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

/** Refresh Supabase session before long payroll / email jobs. */
export async function refreshSession(): Promise<boolean> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  const res = await fetch(apiUrl("auth/refresh/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    clearAuth();
    return false;
  }

  const data = (await res.json()) as LoginResponse;
  saveSession(data);
  return true;
}

/** Ensure access token exists; refresh if possible before multi-step API work. */
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
  const res = await fetch(apiUrl("auth/signup/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName || undefined,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error ?? "Sign up failed");
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
  const res = await fetch(apiUrl("auth/login/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error ?? "Login failed");
  }

  saveSession(data);
  return data;
}

export async function fetchMe(): Promise<AuthUser | null> {
  const token = getAccessToken();
  if (!token) return null;

  const res = await fetch(apiUrl("auth/me/"), {
    headers: { Authorization: `Bearer ${token}` },
  });

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
      await fetch(apiUrl("auth/logout/"), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // ignore network errors on logout
    }
  }
  clearAuth();
}
