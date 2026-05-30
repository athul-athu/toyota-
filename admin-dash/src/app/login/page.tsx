"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ToyotaLogo } from "@/components/toyota-logo";
import { fetchMe, login, saveSessionFromAuthHash, signup } from "@/lib/auth";

type Mode = "login" | "signup";

const TOYOTA_RED = "#EB0A1E";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setSuccess(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
        router.replace("/");
      } else {
        const result = await signup(email, password, fullName);
        if ("access_token" in result) {
          router.replace("/");
          return;
        }
        setSuccess(result.message);
        setMode("login");
        setPassword("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (saveSessionFromAuthHash()) {
      fetchMe().then((user) => {
        if (user) router.replace("/");
      });
      return;
    }
    fetchMe().then((user) => {
      if (user) router.replace("/");
    });
  }, [router]);

  const isSignup = mode === "signup";

  return (
    <div className="flex min-h-full flex-1">
      {/* Hero — automotive showroom */}
      <div className="relative hidden w-0 flex-1 overflow-hidden lg:block lg:w-[52%]">
        <Image
          src="https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?q=80&w=2070&auto=format&fit=crop"
          alt="Toyota vehicle"
          fill
          priority
          className="object-cover"
          sizes="52vw"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-black/85 via-black/60 to-[#EB0A1E]/40" />
        <div className="absolute inset-0 bg-[linear-gradient(105deg,transparent_40%,rgba(235,10,30,0.15)_100%)]" />

        <div className="relative z-10 flex h-full flex-col justify-between p-12 text-white">
          <ToyotaLogo variant="white" width={180} height={72} className="h-14 w-auto max-w-[180px]" />

          <div>
            <p
              className="text-xs font-semibold uppercase tracking-[0.35em] text-red-400"
              style={{ color: "#ff6b6b" }}
            >
              Admin Portal
            </p>
            <h2 className="mt-3 max-w-md text-4xl font-bold leading-tight tracking-tight">
              Let&apos;s Go Places
            </h2>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-zinc-300">
              Manage your Toyota fleet and operations from one secure dashboard.
            </p>
          </div>

          <p className="text-xs text-zinc-500">
            © {new Date().getFullYear()} Toyota. All rights reserved.
          </p>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col justify-center bg-[#f5f5f5] px-6 py-12 sm:px-10 lg:w-[48%] lg:px-16">
        <div className="mx-auto w-full max-w-md">
          <div className="mb-10 flex flex-col items-center lg:items-start">
            <ToyotaLogo width={160} height={64} className="mb-6 h-12 w-auto max-w-[160px]" />
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-[#1a1a1a]">
              {isSignup ? "Create your account" : "Welcome back"}
            </h1>
            <p className="mt-2 text-sm text-zinc-600">
              {isSignup
                ? "Join the admin dashboard in seconds"
                : "Sign in to continue to your dashboard"}
            </p>
          </div>

          <div className="rounded-xl border border-zinc-200/80 bg-white p-8 shadow-lg shadow-zinc-200/50">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div
                  role="alert"
                  className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                >
                  {error}
                </div>
              )}

              {success && (
                <div
                  role="status"
                  className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
                >
                  {success}
                </div>
              )}

              {isSignup && (
                <div>
                  <label
                    htmlFor="fullName"
                    className="mb-1.5 block text-sm font-semibold text-zinc-800"
                  >
                    Full name
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    autoComplete="name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full rounded-md border border-zinc-300 bg-zinc-50 px-3 py-2.5 text-zinc-900 transition-colors outline-none focus:border-[#EB0A1E] focus:bg-white focus:ring-2 focus:ring-[#EB0A1E]/20"
                    placeholder="Your name"
                  />
                </div>
              )}

              <div>
                <label
                  htmlFor="email"
                  className="mb-1.5 block text-sm font-semibold text-zinc-800"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-zinc-300 bg-zinc-50 px-3 py-2.5 text-zinc-900 transition-colors outline-none focus:border-[#EB0A1E] focus:bg-white focus:ring-2 focus:ring-[#EB0A1E]/20"
                  placeholder="you@email.com"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="mb-1.5 block text-sm font-semibold text-zinc-800"
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border border-zinc-300 bg-zinc-50 px-3 py-2.5 text-zinc-900 transition-colors outline-none focus:border-[#EB0A1E] focus:bg-white focus:ring-2 focus:ring-[#EB0A1E]/20"
                  placeholder="••••••••"
                />
                {isSignup && (
                  <p className="mt-1.5 text-xs text-zinc-500">
                    Minimum 8 characters
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{ backgroundColor: TOYOTA_RED }}
                className="w-full rounded-md py-3 text-sm font-bold uppercase tracking-wider text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading
                  ? isSignup
                    ? "Creating account…"
                    : "Signing in…"
                  : isSignup
                    ? "Create account"
                    : "Sign in"}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-zinc-600">
              {isSignup ? (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("login")}
                    className="font-semibold hover:underline"
                    style={{ color: TOYOTA_RED }}
                  >
                    Sign in
                  </button>
                </>
              ) : (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("signup")}
                    className="font-semibold hover:underline"
                    style={{ color: TOYOTA_RED }}
                  >
                    Sign up
                  </button>
                </>
              )}
            </p>
          </div>

          <p className="mt-8 text-center text-xs text-zinc-500 lg:hidden">
            Toyota Admin · Drive forward
          </p>
        </div>
      </div>
    </div>
  );
}
