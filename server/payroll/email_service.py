from __future__ import annotations

import base64
import json
import logging
import socket
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def resend_configured() -> bool:
    return bool(getattr(settings, "RESEND_API_KEY", ""))


def smtp_configured() -> bool:
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
        and settings.DEFAULT_FROM_EMAIL
    )


def email_configured() -> bool:
    """True if Resend (Render) or SMTP (local) can send mail."""
    if resend_configured():
        from_addr = getattr(settings, "RESEND_FROM", "") or settings.DEFAULT_FROM_EMAIL
        return bool(from_addr)
    return smtp_configured()


def email_provider() -> str:
    if resend_configured():
        return "resend"
    if smtp_configured():
        return "smtp"
    return "none"


def format_smtp_error(exc: BaseException) -> str:
    """Actionable email errors for the admin UI."""
    text = str(exc).strip() or exc.__class__.__name__
    lower = text.lower()

    if not email_configured():
        return (
            "Email is not configured on the server. For Render, set RESEND_API_KEY and "
            "RESEND_FROM (HTTPS — works when SMTP port 587 is blocked). For local dev, "
            "use SMTP_* in .env instead."
        )

    if (
        "network is unreachable" in lower
        or "errno 101" in lower
        or "no route to host" in lower
        or "errno 113" in lower
        or "name or service not known" in lower
        or "getaddrinfo failed" in lower
    ):
        return (
            f"Cannot reach SMTP server ({settings.EMAIL_HOST}:{settings.EMAIL_PORT}). "
            "Render blocks outbound SMTP on port 587. Use Resend instead: set "
            "RESEND_API_KEY + RESEND_FROM on Render (see SETUP.md)."
        )

    if "timed out" in lower or "timeout" in lower:
        return (
            f"SMTP connection timed out ({settings.EMAIL_HOST}). "
            "On Render, use RESEND_API_KEY instead of Gmail SMTP."
        )

    if "authentication failed" in lower or "535" in lower or "534" in lower:
        return (
            "SMTP login failed. For Gmail use an App Password locally, or use "
            "RESEND_API_KEY on Render."
        )

    if "connection refused" in lower or "errno 111" in lower:
        return (
            f"SMTP server refused connection ({settings.EMAIL_HOST}:{settings.EMAIL_PORT}). "
            "On Render, switch to RESEND_API_KEY (HTTPS email API)."
        )

    return f"Email error: {text}"


def period_label(month: int, year: int) -> str:
    name = MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
    return f"{name} {year}"


def build_email_html(employee_name: str, month: int, year: int) -> str:
    period = period_label(month, year)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <tr>
            <td style="background:#EB0A1E;padding:20px 32px;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;">Toyota</h1>
              <p style="margin:6px 0 0;color:#ffe0e0;font-size:13px;">Salary Slip Notification</p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 16px;font-size:16px;color:#1a1a1a;">Dear <strong>{employee_name}</strong>,</p>
              <p style="margin:0 0 16px;font-size:15px;color:#404040;line-height:1.6;">
                Please find attached your salary slip for the pay period
                <strong style="color:#EB0A1E;">{period}</strong>.
              </p>
              <p style="margin:0 0 16px;font-size:15px;color:#404040;line-height:1.6;">
                Review the attached PDF for a detailed breakdown of your earnings, allowances,
                deductions, and net salary.
              </p>
              <p style="margin:0;font-size:15px;color:#404040;line-height:1.6;">
                If you have any questions, please contact the HR / payroll team.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px;background:#fafafa;border-top:1px solid #eee;">
              <p style="margin:0;font-size:12px;color:#888;">
                This is an automated message from Toyota Payroll. Please do not reply to this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_email_plain(employee_name: str, month: int, year: int) -> str:
    period = period_label(month, year)
    return (
        f"Dear {employee_name},\n\n"
        f"Please find attached your salary slip for {period}.\n\n"
        f"Review the PDF for your earnings, allowances, deductions, and net salary.\n\n"
        f"Toyota Payroll"
    )


def _send_via_resend(
    to_email: str,
    employee_name: str,
    month: int,
    year: int,
    pdf_bytes: bytes,
    attachment_filename: str,
) -> None:
    api_key = settings.RESEND_API_KEY
    from_email = getattr(settings, "RESEND_FROM", "") or settings.DEFAULT_FROM_EMAIL
    if not api_key or not from_email:
        raise RuntimeError(format_smtp_error(RuntimeError("Resend not configured")))

    period = period_label(month, year)
    subject = f"Your Salary Slip – {period} | Toyota"
    plain = build_email_plain(employee_name, month, year)
    html = build_email_html(employee_name, month, year)

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": plain,
        "attachments": [
            {
                "filename": attachment_filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Resend API HTTP {resp.status}: {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API error: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(format_smtp_error(exc)) from exc

    logger.info("Resend: salary slip sent to %s (%s)", to_email, employee_name)


def _send_via_smtp(
    to_email: str,
    employee_name: str,
    month: int,
    year: int,
    pdf_bytes: bytes,
    attachment_filename: str,
) -> None:
    if not smtp_configured():
        raise RuntimeError(format_smtp_error(RuntimeError("SMTP not configured")))

    period = period_label(month, year)
    subject = f"Your Salary Slip – {period} | Toyota"
    plain = build_email_plain(employee_name, month, year)
    html = build_email_html(employee_name, month, year)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html, "text/html")
    msg.attach(attachment_filename, pdf_bytes, "application/pdf")

    try:
        msg.send(fail_silently=False)
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(format_smtp_error(exc)) from exc
    except OSError as exc:
        raise RuntimeError(format_smtp_error(exc)) from exc
    except Exception as exc:
        raise RuntimeError(format_smtp_error(exc)) from exc

    logger.info("SMTP: salary slip sent to %s (%s)", to_email, employee_name)


def send_salary_slip_email(
    to_email: str,
    employee_name: str,
    month: int,
    year: int,
    pdf_bytes: bytes,
    attachment_filename: str,
) -> None:
    if not email_configured():
        raise RuntimeError(format_smtp_error(RuntimeError("not configured")))

    if resend_configured():
        _send_via_resend(
            to_email, employee_name, month, year, pdf_bytes, attachment_filename
        )
        return

    _send_via_smtp(to_email, employee_name, month, year, pdf_bytes, attachment_filename)
