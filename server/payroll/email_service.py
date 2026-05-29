from __future__ import annotations

import logging

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


def smtp_configured() -> bool:
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
        and settings.DEFAULT_FROM_EMAIL
    )


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


def send_salary_slip_email(
    to_email: str,
    employee_name: str,
    month: int,
    year: int,
    pdf_bytes: bytes,
    attachment_filename: str,
) -> None:
    if not smtp_configured():
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM in the repo root .env"
        )

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
    msg.send(fail_silently=False)
    logger.info("Salary slip email sent to %s (%s)", to_email, employee_name)
