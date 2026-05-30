"use client";

import { useCallback, useState } from "react";

import {
  ProcessAndSendResult,
  PayrollRow,
  previewPayrollFile,
  processAndSendFromRows,
  processAndSendPayroll,
} from "@/lib/payroll";

const TOYOTA_RED = "#EB0A1E";

export function UploadPortal() {
  const [rows, setRows] = useState<PayrollRow[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parseErrors, setParseErrors] = useState<string[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<ProcessAndSendResult | null>(
    null,
  );

  const onFile = useCallback(async (file: File | null) => {
    if (!file) return;
    setSelectedFile(file);
    setError(null);
    setStatus(null);
    setPipelineResult(null);
    setLoading(true);
    try {
      const result = await previewPayrollFile(file);
      setRows(result.rows);
      setParseErrors(result.errors);
      setStatus(
        `Parsed ${result.count} row(s). Click "Generate & Send All" to process and email slips.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleProcessAndSend() {
    if (!selectedFile && !rows.length) {
      setError("Upload an Excel or CSV file first");
      return;
    }
    setLoading(true);
    setError(null);
    setStatus("Processing payroll… importing, generating PDFs, uploading, sending emails.");
    try {
      const result = selectedFile
        ? await processAndSendPayroll(selectedFile)
        : await processAndSendFromRows(rows);

      setPipelineResult(result);
      setStatus(
        `Done: ${result.imported} imported · ${result.total_pdfs} PDFs · ${result.total_emails_sent} emails sent.`,
      );
      if (result.parse_errors?.length || result.import_errors?.length) {
        setParseErrors([
          ...result.parse_errors,
          ...result.import_errors,
        ]);
      }
      if (!result.smtp_configured) {
        setError(
          "SMTP is not configured on Render. PDFs were saved but emails were not sent. " +
            "Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM in Render → Environment.",
        );
      }
      const emailFails = result.period_results?.flatMap(
        (p) => p.email_errors ?? [],
      );
      if (emailFails.length && result.total_emails_sent === 0) {
        setError(emailFails[0]?.error ?? "All emails failed (check SMTP on Render).");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Processing failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-zinc-900">Upload payroll file</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Excel (.xlsx) or CSV with: Employee ID, Name, Email, Designation, Base
          Salary, HRA, Allowances, Deductions, Month/Year (e.g. 5/2026)
        </p>

        <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-300 bg-zinc-50 px-6 py-10 transition-colors hover:border-[#EB0A1E] hover:bg-red-50/30">
          <span className="text-sm font-medium text-zinc-700">
            {loading ? "Processing…" : "Click to upload or drag a file"}
          </span>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            disabled={loading}
            onChange={(e) => onFile(e.target.files?.[0] ?? null)}
          />
        </label>

        {rows.length > 0 && (
          <button
            type="button"
            disabled={loading}
            onClick={handleProcessAndSend}
            style={{ backgroundColor: TOYOTA_RED }}
            className="mt-6 w-full rounded-lg py-3.5 text-sm font-bold uppercase tracking-wide text-white shadow-md transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Working…" : "Generate PDFs & Send All Emails"}
          </button>
        )}
        <p className="mt-2 text-center text-xs text-zinc-500">
          One click: save data → create PDFs → upload to Supabase → email each employee
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {status && !error && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {status}
        </div>
      )}
      {parseErrors.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">Warnings</p>
          <ul className="mt-1 list-inside list-disc">
            {parseErrors.slice(0, 15).map((msg, i) => (
              <li key={`${msg}-${i}`}>{msg}</li>
            ))}
          </ul>
        </div>
      )}

      {rows.length > 0 && (
        <section className="rounded-xl border border-zinc-200 bg-white shadow-sm">
          <div className="border-b border-zinc-200 px-6 py-4">
            <h3 className="font-semibold text-zinc-900">Preview ({rows.length} rows)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-[#EB0A1E] text-xs uppercase text-white">
                <tr>
                  <th className="px-4 py-3">Emp ID</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Designation</th>
                  <th className="px-4 py-3 text-right">Net</th>
                  <th className="px-4 py-3">Period</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr
                    key={`${r.employee_id}-${r.month}-${r.year}`}
                    className={`border-t ${i % 2 === 0 ? "bg-white" : "bg-zinc-50"}`}
                  >
                    <td className="px-4 py-2 font-medium text-zinc-800">
                      {r.employee_id}
                    </td>
                    <td className="px-4 py-2 text-zinc-700">{r.name}</td>
                    <td className="px-4 py-2 text-zinc-600">{r.email}</td>
                    <td className="px-4 py-2 text-zinc-600">
                      {r.designation || "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-semibold text-emerald-700">
                      {r.net_salary.toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-zinc-600">
                      {r.period ?? `${r.month}/${r.year}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {pipelineResult && (
        <section className="rounded-xl border border-zinc-200 bg-white shadow-sm">
          <h3 className="border-b border-zinc-200 px-6 py-4 font-semibold text-zinc-900">
            Processing results
          </h3>
          <div className="grid gap-4 p-6 sm:grid-cols-3">
            <ResultCard label="Imported" value={String(pipelineResult.imported)} />
            <ResultCard label="PDFs generated" value={String(pipelineResult.total_pdfs)} />
            <ResultCard
              label="Emails sent"
              value={String(pipelineResult.total_emails_sent)}
            />
          </div>
          {pipelineResult.period_results?.map((period) => (
            <div key={`${period.month}-${period.year}`} className="border-t px-6 py-4">
              <p className="text-sm font-semibold text-zinc-800">
                Period {period.month}/{period.year}
              </p>
              {period.emails_sent?.length > 0 && (
                <ul className="mt-2 space-y-1 text-sm text-emerald-700">
                  {period.emails_sent.map((e) => (
                    <li key={e.employee_id}>
                      ✓ {e.name} — {e.email}
                    </li>
                  ))}
                </ul>
              )}
              {period.email_errors?.length > 0 && (
                <ul className="mt-2 space-y-1 text-sm text-red-600">
                  {period.email_errors.map((e) => (
                    <li key={e.employee_id}>
                      ✗ {e.employee_id}: {e.error}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function ResultCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-zinc-50 p-4 text-center">
      <p className="text-xs font-medium uppercase text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-zinc-900">{value}</p>
    </div>
  );
}
