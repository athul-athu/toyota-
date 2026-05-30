import { apiFetch } from "./api-request";
import { ensureSessionForApi, refreshSession } from "./auth";

export type PayrollRow = {
  employee_id: string;
  name: string;
  email: string;
  designation?: string;
  base_salary: number;
  hra: number;
  allowances: number;
  deductions: number;
  net_salary: number;
  month: number;
  year: number;
  period?: string;
  row?: number;
};

export type ProcessAndSendResult = {
  message: string;
  rows_parsed?: number;
  imported: number;
  import_errors: string[];
  parse_errors: string[];
  periods: { month: number; year: number }[];
  period_results: PeriodProcessResult[];
  total_pdfs: number;
  total_uploaded: number;
  total_emails_sent: number;
  smtp_configured: boolean;
  error?: string;
};

export type PeriodProcessResult = {
  month: number;
  year: number;
  pdfs_generated?: number;
  uploaded: StoredSlip[];
  upload_errors: string[];
  emails_sent: { employee_id: string; name: string; email: string }[];
  email_errors: { employee_id: string; email: string; error: string }[];
  smtp_configured?: boolean;
  error?: string;
};

function apiErrorMessage(
  res: Response,
  data: { error?: string } | null,
  fallback: string,
): string {
  if (res.status === 401) {
    return "Session expired or not signed in. Please log in again.";
  }
  return data?.error ?? fallback;
}

export async function previewPayrollFile(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await apiFetch("payroll/preview/", {
    method: "POST",
    body: form,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(res, data, "Preview failed"));
  return data as { rows: PayrollRow[]; errors: string[]; count: number };
}

function uniquePeriods(rows: PayrollRow[]): { month: number; year: number }[] {
  const seen = new Map<string, { month: number; year: number }>();
  for (const row of rows) {
    const key = `${row.year}-${row.month}`;
    if (!seen.has(key)) {
      seen.set(key, { month: row.month, year: row.year });
    }
  }
  return [...seen.values()].sort(
    (a, b) => a.year - b.year || a.month - b.month,
  );
}

export async function processPeriod(
  month: number,
  year: number,
  sendEmails = true,
): Promise<PeriodProcessResult> {
  const res = await apiFetch("payroll/process-period/", {
    method: "POST",
    json: true,
    body: JSON.stringify({ month, year, send_emails: sendEmails }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, data, "Period processing failed"));
  }
  return data as PeriodProcessResult;
}

/** Import + process each pay period separately (stays under Render request timeout). */
export async function processPayrollInSteps(
  rows: PayrollRow[],
  sendEmails = true,
  parseErrors: string[] = [],
): Promise<ProcessAndSendResult> {
  await ensureSessionForApi();
  await refreshSession();

  const importResult = await importPayrollRows(rows);
  const periods = uniquePeriods(rows);
  const period_results: PeriodProcessResult[] = [];

  for (const { month, year } of periods) {
    await refreshSession();
    period_results.push(await processPeriod(month, year, sendEmails));
  }

  const total_emails_sent = period_results.reduce(
    (n, p) => n + (p.emails_sent?.length ?? 0),
    0,
  );
  const total_uploaded = period_results.reduce(
    (n, p) => n + (p.uploaded?.length ?? 0),
    0,
  );
  const total_pdfs = period_results.reduce(
    (n, p) => n + (p.pdfs_generated ?? 0),
    0,
  );
  const smtpOk = !period_results.some((p) => p.smtp_configured === false);

  return {
    message:
      "Payroll processed: imported, PDFs generated, stored, and emails sent.",
    imported: importResult.saved,
    import_errors: importResult.errors,
    parse_errors: parseErrors,
    periods,
    period_results,
    total_pdfs,
    total_uploaded,
    total_emails_sent,
    smtp_configured: smtpOk,
  };
}

/** Parse file, then run stepped pipeline (import → each period). */
export async function processAndSendPayroll(
  file: File,
  sendEmails = true,
): Promise<ProcessAndSendResult> {
  const parsed = await previewPayrollFile(file);
  const result = await processPayrollInSteps(
    parsed.rows,
    sendEmails,
    parsed.errors,
  );
  return { ...result, rows_parsed: parsed.count };
}

export async function processAndSendFromRows(
  rows: PayrollRow[],
  sendEmails = true,
): Promise<ProcessAndSendResult> {
  return processPayrollInSteps(rows, sendEmails);
}

export async function importPayrollRows(rows: PayrollRow[]) {
  const res = await apiFetch("payroll/import/", {
    method: "POST",
    json: true,
    body: JSON.stringify({ rows }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(res, data, "Import failed"));
  return data as { saved: number; errors: string[] };
}

export type StoredSlip = {
  employee_id: string;
  employee_name: string;
  file_name: string;
  storage_path: string;
  bucket_id: string;
  month: number;
  year: number;
  net_salary?: number;
  signed_url?: string;
};

export async function fetchSalaries(month?: number, year?: number) {
  const params = new URLSearchParams();
  if (month) params.set("month", String(month));
  if (year) params.set("year", String(year));

  const res = await apiFetch(`payroll/salaries/?${params.toString()}`, {
    method: "GET",
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "Failed to load salaries");
  return data.salaries as PayrollRow[];
}

export async function generateAndStoreSlips(month: number, year: number) {
  const res = await apiFetch("payroll/generate-pdfs/", {
    method: "POST",
    json: true,
    body: JSON.stringify({ month, year }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "PDF generation failed");
  return data;
}

export async function downloadSalaryPdfsZip(month: number, year: number) {
  const res = await apiFetch("payroll/generate-pdfs/?download=zip", {
    method: "POST",
    json: true,
    body: JSON.stringify({ month, year, download_zip: true }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error ?? "ZIP download failed");
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `salary_slips_${year}_${String(month).padStart(2, "0")}.zip`;
  a.click();
  URL.revokeObjectURL(url);
}
