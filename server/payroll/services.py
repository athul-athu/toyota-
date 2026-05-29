from __future__ import annotations

import logging
from decimal import Decimal

from payroll.email_service import send_salary_slip_email, smtp_configured
from payroll.models import Employee, SalaryRecord
from payroll.parsers import parse_payroll_file
from payroll.pdf_generator import generate_salary_slip_pdf
from payroll.supabase_storage import build_file_name, upload_salary_slip_pdf

logger = logging.getLogger(__name__)


def import_payroll_rows(rows: list[dict]) -> dict:
    saved = 0
    errors: list[str] = []

    for row in rows:
        try:
            emp_id = row["employee_id"]
            Employee.objects.update_or_create(
                employee_id=emp_id,
                defaults={
                    "name": row["name"],
                    "email": row["email"],
                    "designation": row.get("designation", ""),
                },
            )
            SalaryRecord.objects.update_or_create(
                employee_id=emp_id,
                month=int(row["month"]),
                year=int(row["year"]),
                defaults={
                    "base_salary": Decimal(str(row["base_salary"])),
                    "hra": Decimal(str(row["hra"])),
                    "allowances": Decimal(str(row["allowances"])),
                    "deductions": Decimal(str(row["deductions"])),
                },
            )
            saved += 1
        except Exception as exc:
            errors.append(f"{row.get('employee_id', '?')}: {exc}")

    return {"saved": saved, "errors": errors}


def _periods_from_rows(rows: list[dict]) -> list[tuple[int, int]]:
    periods = {(int(r["month"]), int(r["year"])) for r in rows}
    return sorted(periods)


def process_period(
    month: int,
    year: int,
    *,
    send_emails: bool = True,
) -> dict:
    if send_emails and not smtp_configured():
        return {
            "error": "SMTP not configured. Add SMTP_* variables to the repo root .env",
            "month": month,
            "year": year,
        }

    salaries = SalaryRecord.objects.select_related("employee").filter(
        month=month, year=year
    )
    if not salaries.exists():
        return {
            "error": f"No salary records for {month}/{year}",
            "month": month,
            "year": year,
        }

    uploaded: list[dict] = []
    upload_errors: list[str] = []
    emails_sent: list[dict] = []
    email_errors: list[dict] = []

    for salary in salaries:
        employee = salary.employee
        pdf_bytes = generate_salary_slip_pdf(salary)
        file_name = build_file_name(
            employee.employee_id, employee.name, month, year
        )

        try:
            meta = upload_salary_slip_pdf(
                pdf_bytes=pdf_bytes,
                employee_id=employee.employee_id,
                employee_name=employee.name,
                email=employee.email,
                designation=employee.designation,
                month=month,
                year=year,
                net_salary=float(salary.net_salary),
            )
            uploaded.append(meta)
        except Exception as exc:
            logger.warning("Supabase upload failed %s: %s", employee.employee_id, exc)
            upload_errors.append(f"{employee.employee_id}: {exc}")

        if send_emails:
            if not employee.email:
                email_errors.append(
                    {
                        "employee_id": employee.employee_id,
                        "email": "",
                        "error": "No email address",
                    }
                )
                continue
            try:
                send_salary_slip_email(
                    to_email=employee.email,
                    employee_name=employee.name,
                    month=month,
                    year=year,
                    pdf_bytes=pdf_bytes,
                    attachment_filename=file_name,
                )
                emails_sent.append(
                    {
                        "employee_id": employee.employee_id,
                        "name": employee.name,
                        "email": employee.email,
                    }
                )
            except Exception as exc:
                logger.warning("Email failed %s: %s", employee.employee_id, exc)
                email_errors.append(
                    {
                        "employee_id": employee.employee_id,
                        "email": employee.email,
                        "error": str(exc),
                    }
                )

    return {
        "month": month,
        "year": year,
        "pdfs_generated": salaries.count(),
        "uploaded": uploaded,
        "upload_errors": upload_errors,
        "emails_sent": emails_sent,
        "email_errors": email_errors,
    }


def run_full_pipeline(
    rows: list[dict],
    *,
    send_emails: bool = True,
) -> dict:
    parse_errors: list[str] = []
    if not rows:
        return {"error": "No payroll rows to process"}

    import_result = import_payroll_rows(rows)
    periods = _periods_from_rows(rows)

    period_results: list[dict] = []
    for month, year in periods:
        period_results.append(
            process_period(month, year, send_emails=send_emails)
        )

    total_emails = sum(len(p.get("emails_sent", [])) for p in period_results)
    total_uploaded = sum(len(p.get("uploaded", [])) for p in period_results)

    return {
        "message": "Payroll processed: imported, PDFs generated, stored, and emails sent.",
        "imported": import_result["saved"],
        "import_errors": import_result["errors"],
        "parse_errors": parse_errors,
        "periods": [{"month": m, "year": y} for m, y in periods],
        "period_results": period_results,
        "total_pdfs": sum(
            p.get("pdfs_generated", 0) for p in period_results if "pdfs_generated" in p
        ),
        "total_uploaded": total_uploaded,
        "total_emails_sent": total_emails,
    }


def run_pipeline_from_file(
    filename: str,
    content: bytes,
    *,
    send_emails: bool = True,
) -> dict:
    parsed = parse_payroll_file(filename, content)
    result = run_full_pipeline(parsed["rows"], send_emails=send_emails)
    result["parse_errors"] = parsed.get("errors", [])
    result["rows_parsed"] = parsed.get("count", 0)
    return result
