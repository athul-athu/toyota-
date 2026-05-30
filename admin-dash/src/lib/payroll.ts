import { API_BASE_URL } from "./api";
import { getAccessToken } from "./auth";

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
  error?: string;
};

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function authHeadersJson(): HeadersInit {
  return { ...authHeaders(), "Content-Type": "application/json" };
}

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

  const res = await fetch(`${API_BASE_URL}/api/payroll/preview/`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(res, data, "Preview failed"));
  return data as { rows: PayrollRow[]; errors: string[]; count: number };
}

/** One-click: import → PDFs → Supabase → email all employees */
export async function processAndSendPayroll(
  file: File,
  sendEmails = true,
): Promise<ProcessAndSendResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("send_emails", sendEmails ? "true" : "false");

  const res = await fetch(`${API_BASE_URL}/api/payroll/process-and-send/`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(res, data, "Processing failed"));
  return data as ProcessAndSendResult;
}

export async function processAndSendFromRows(
  rows: PayrollRow[],
  sendEmails = true,
): Promise<ProcessAndSendResult> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/process-and-send/`, {
    method: "POST",
    headers: authHeadersJson(),
    body: JSON.stringify({ rows, send_emails: sendEmails }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(res, data, "Processing failed"));
  return data as ProcessAndSendResult;
}

export async function importPayrollRows(rows: PayrollRow[]) {
  const res = await fetch(`${API_BASE_URL}/api/payroll/import/`, {
    method: "POST",
    headers: authHeadersJson(),
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

  const res = await fetch(
    `${API_BASE_URL}/api/payroll/salaries/?${params.toString()}`,
    { headers: authHeaders() },
  );

  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "Failed to load salaries");
  return data.salaries as PayrollRow[];
}

export async function generateAndStoreSlips(month: number, year: number) {
  const res = await fetch(`${API_BASE_URL}/api/payroll/generate-pdfs/`, {
    method: "POST",
    headers: authHeadersJson(),
    body: JSON.stringify({ month, year }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "PDF generation failed");
  return data;
}

export async function downloadSalaryPdfsZip(month: number, year: number) {
  const res = await fetch(
    `${API_BASE_URL}/api/payroll/generate-pdfs/?download=zip`,
    {
      method: "POST",
      headers: authHeadersJson(),
      body: JSON.stringify({ month, year, download_zip: true }),
    },
  );

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
