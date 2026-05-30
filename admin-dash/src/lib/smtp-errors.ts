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
    "Email failed. Render blocks Gmail SMTP (port 587). " +
    "On Render, set RESEND_API_KEY + RESEND_FROM (free at resend.com). " +
    "For local dev only, use SMTP_* in .env.";
  return detail ? `${base}\n\n${detail}` : base;
}
