/** Detect SMTP / mail failures (including misleading browser "network" errors). */

export function looksLikeSmtpError(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("smtp") ||
    lower.includes("network is unreachable") ||
    lower.includes("cannot reach smtp") ||
    lower.includes("mail") ||
    lower.includes("timed out") && lower.includes("smtp")
  );
}

export function isPayrollEmailApiPath(path: string): boolean {
  return (
    path.includes("send-period-emails") ||
    path.includes("process-period") ||
    path.includes("process-and-send")
  );
}

export function smtpErrorMessage(detail?: string): string {
  const base =
    "Email failed (SMTP). Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM " +
    "in Render → your service → Environment (not only local .env). " +
    "Gmail needs an App Password on port 587.";
  return detail ? `${base}\n\n${detail}` : base;
}
