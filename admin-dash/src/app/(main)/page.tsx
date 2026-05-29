"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ToyotaLogo } from "@/components/toyota-logo";
import { UploadPortal } from "@/components/upload-portal";
import { AuthUser, fetchMe, logout } from "@/lib/auth";
import { fetchSalaries, PayrollRow } from "@/lib/payroll";

type Tab = "dashboard" | "upload";

const TOYOTA_RED = "#EB0A1E";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [salaries, setSalaries] = useState<PayrollRow[]>([]);

  useEffect(() => {
    fetchMe().then(setUser);
    fetchSalaries()
      .then(setSalaries)
      .catch(() => setSalaries([]));
  }, []);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-full flex-1 flex-col bg-[#f5f5f5]">
      <header className="border-b border-zinc-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-4">
            <ToyotaLogo width={120} height={48} className="h-8 w-auto max-w-[120px]" />
            <div>
              <h1 className="text-lg font-bold text-zinc-900">Toyota Admin</h1>
              {user && (
                <p className="text-xs text-zinc-500">
                  {user.full_name ?? user.email} · {user.role}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-50"
          >
            Log out
          </button>
        </div>

        <nav className="mx-auto flex max-w-6xl gap-1 px-6 pb-0">
          {(
            [
              ["dashboard", "Admin Dashboard"],
              ["upload", "Upload Portal"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className="border-b-2 px-4 py-3 text-sm font-semibold transition-colors"
              style={{
                borderColor: tab === id ? TOYOTA_RED : "transparent",
                color: tab === id ? TOYOTA_RED : "#71717a",
              }}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        {tab === "dashboard" ? (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label="Employees in DB" value={String(new Set(salaries.map((s) => s.employee_id)).size || "—")} />
              <StatCard label="Salary records" value={String(salaries.length)} />
              <StatCard label="Latest period" value={latestPeriod(salaries)} />
            </div>

            <section className="rounded-xl border border-zinc-200 bg-white shadow-sm">
              <h2 className="border-b border-zinc-200 px-6 py-4 font-semibold">
                Saved salary records
              </h2>
              {salaries.length === 0 ? (
                <p className="px-6 py-8 text-sm text-zinc-500">
                  No data yet. Use the Upload Portal to import payroll.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[800px] text-left text-sm">
                    <thead className="bg-[#EB0A1E] text-xs uppercase text-white">
                      <tr>
                        <th className="px-4 py-3">ID</th>
                        <th className="px-4 py-3">Name</th>
                        <th className="px-4 py-3 text-right">Net</th>
                        <th className="px-4 py-3">Period</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salaries.slice(0, 20).map((s, i) => (
                        <tr
                          key={`${s.employee_id}-${s.month}-${s.year}`}
                          className={`border-t ${i % 2 === 0 ? "bg-white" : "bg-zinc-50"}`}
                        >
                          <td className="px-4 py-2 font-medium text-zinc-800">
                            {s.employee_id}
                          </td>
                          <td className="px-4 py-2 text-zinc-700">{s.name}</td>
                          <td className="px-4 py-2 text-right font-semibold text-emerald-700">
                            ₹ {s.net_salary.toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-zinc-600">
                            {s.month}/{s.year}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        ) : (
          <UploadPortal />
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-zinc-900">{value}</p>
    </div>
  );
}

function latestPeriod(rows: PayrollRow[]): string {
  if (!rows.length) return "—";
  const s = rows[0];
  return `${s.month}/${s.year}`;
}
