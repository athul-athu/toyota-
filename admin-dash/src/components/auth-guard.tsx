"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchMe } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetchMe().then((user) => {
      if (cancelled) return;
      if (!user) {
        router.replace("/login");
        return;
      }
      setReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!ready) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-zinc-500">Loading…</p>
      </div>
    );
  }

  return <>{children}</>;
}
