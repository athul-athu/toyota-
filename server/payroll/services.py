from __future__ import annotations

import logging
from decimal import Decimal

from payroll.email_service import (
    email_configured,
    format_smtp_error,
    send_salary_slip_email,
)
from payroll.models import Employee, SalaryRecord
from payroll.parsers import parse_payroll_file
from payroll.pdf_generator import generate_salary_slip_pdf
from payroll.supabase_storage import (
    build_file_name,
    upload_salary_slip_pdf,
    get_supabase_clients,
    make_in_memory_salary_record,
)


logger = logging.getLogger(__name__)


def import_payroll_rows(rows: list[dict]) -> dict:
    saved = 0
    errors: list[str] = []
    clients = get_supabase_clients()

    for row in rows:
        try:
            emp_id = row["employee_id"]
            # 1) Upsert employee profile in Supabase
            clients.service.table("employees").upsert(
                {
                    "employee_id": emp_id,
                    "name": row["name"],
                    "email": row["email"],
                    "designation": row.get("designation", ""),
                }
            ).execute()

            # 2) Calculate net salary and upsert salary record in Supabase
            base = Decimal(str(row["base_salary"]))
            hra = Decimal(str(row["hra"]))
            allowances = Decimal(str(row["allowances"]))
            deductions = Decimal(str(row["deductions"]))
            net_salary = base + hra + allowances - deductions

            clients.service.table("salary_records").upsert(
                {
                    "employee_id": emp_id,
                    "month": int(row["month"]),
                    "year": int(row["year"]),
                    "base_salary": float(base),
                    "hra": float(hra),
                    "allowances": float(allowances),
                    "deductions": float(deductions),
                    "net_salary": float(net_salary),
                },
                on_conflict="employee_id,month,year",
            ).execute()

            saved += 1
        except Exception as exc:
            errors.append(f"{row.get('employee_id', '?')}: {exc}")

    return {"saved": saved, "errors": errors}



def _periods_from_rows(rows: list[dict]) -> list[tuple[int, int]]:
    periods = {(int(r["month"]), int(r["year"])) for r in rows}
    return sorted(periods)


def _salaries_for_period(month: int, year: int) -> list[SalaryRecord]:
    clients = get_supabase_clients()
    res = (
        clients.service.table("salary_records")
        .select("*, employees(*)")
        .eq("month", month)
        .eq("year", year)
        .execute()
    )
    records = res.data or []
    return [make_in_memory_salary_record(r) for r in records]


def _employee_ids_for_period(rows: list[dict], month: int, year: int) -> list[str]:
    return [
        str(r["employee_id"])
        for r in rows
        if int(r["month"]) == month and int(r["year"]) == year
    ]


def _filter_salaries_by_employee_ids(
    salaries: list[SalaryRecord],
    employee_ids: list[str] | None,
) -> list[SalaryRecord]:
    if employee_ids is None:
        return salaries
    allowed = set(employee_ids)
    return [s for s in salaries if s.employee.employee_id in allowed]


def generate_and_upload_period(month: int, year: int) -> dict:
    """Generate PDFs and upload to Supabase (no email — fast, fits Render timeout)."""
    try:
        salaries = _salaries_for_period(month, year)
    except Exception as exc:
        logger.exception("Failed to load salaries: %s", exc)
        return {
            "error": f"Could not load salary records: {exc}",
            "month": month,
            "year": year,
        }

    if not salaries:
        return {
            "error": f"No salary records for {month}/{year}",
            "month": month,
            "year": year,
        }

    uploaded: list[dict] = []
    upload_errors: list[str] = []

    for salary in salaries:
        employee = salary.employee
        pdf_bytes = generate_salary_slip_pdf(salary)
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

    return {
        "month": month,
        "year": year,
        "pdfs_generated": len(salaries),
        "uploaded": uploaded,
        "upload_errors": upload_errors,
        "emails_sent": [],
        "email_errors": [],
    }


def send_period_emails(
    month: int,
    year: int,
    *,
    offset: int = 0,
    limit: int | None = None,
    employee_ids: list[str] | None = None,
) -> dict:
    """Send salary slip emails in small batches (avoids worker timeout).

    When ``employee_ids`` is set, only those employees receive mail (e.g. current upload).
    """
    from django.conf import settings

    if not email_configured():
        return {
            "error": format_smtp_error(RuntimeError("not configured")),
            "month": month,
            "year": year,
            "done": True,
            "smtp_configured": False,
        }

    batch_size = limit or getattr(settings, "PAYROLL_EMAIL_BATCH_SIZE", 3)
    try:
        salaries = _filter_salaries_by_employee_ids(
            _salaries_for_period(month, year),
            employee_ids,
        )
    except Exception as exc:
        return {
            "error": f"Could not load salary records: {exc}",
            "month": month,
            "year": year,
            "done": True,
        }

    total = len(salaries)
    if total == 0:
        if employee_ids is not None:
            return {
                "month": month,
                "year": year,
                "emails_sent": [],
                "email_errors": [],
                "offset": 0,
                "next_offset": None,
                "total_employees": 0,
                "done": True,
                "smtp_configured": True,
            }
        return {
            "error": f"No salary records for {month}/{year}",
            "month": month,
            "year": year,
            "done": True,
        }

    batch = salaries[offset : offset + batch_size]
    emails_sent: list[dict] = []
    email_errors: list[dict] = []

    for salary in batch:
        employee = salary.employee
        file_name = build_file_name(
            employee.employee_id, employee.name, month, year
        )
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
            pdf_bytes = generate_salary_slip_pdf(salary)
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
                    "error": format_smtp_error(exc),
                }
            )

    next_offset = offset + len(batch)
    done = next_offset >= total

    result = {
        "month": month,
        "year": year,
        "emails_sent": emails_sent,
        "email_errors": email_errors,
        "offset": offset,
        "next_offset": next_offset if not done else None,
        "total_employees": total,
        "done": done,
        "smtp_configured": True,
    }
    if email_errors and not emails_sent and offset == 0:
        result["error"] = email_errors[0]["error"]
    return result


def process_period(
    month: int,
    year: int,
    *,
    send_emails: bool = True,
    employee_ids: list[str] | None = None,
) -> dict:
    """Full period: PDFs + optional batched emails (used by one-shot pipeline)."""
    doc_result = generate_and_upload_period(month, year)
    if doc_result.get("error"):
        return doc_result

    if not send_emails:
        return doc_result

    emails_sent: list[dict] = []
    email_errors: list[dict] = []
    offset = 0
    from django.conf import settings

    batch_size = getattr(settings, "PAYROLL_EMAIL_BATCH_SIZE", 3)
    while True:
        batch_result = send_period_emails(
            month,
            year,
            offset=offset,
            limit=batch_size,
            employee_ids=employee_ids,
        )
        if batch_result.get("error") and not emails_sent:
            doc_result["error"] = batch_result["error"]
            return doc_result
        emails_sent.extend(batch_result.get("emails_sent", []))
        email_errors.extend(batch_result.get("email_errors", []))
        if batch_result.get("done"):
            break
        offset = batch_result.get("next_offset") or offset + batch_size

    doc_result["emails_sent"] = emails_sent
    doc_result["email_errors"] = email_errors
    return doc_result


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
        period_employee_ids = _employee_ids_for_period(rows, month, year)
        period_results.append(
            process_period(
                month,
                year,
                send_emails=send_emails,
                employee_ids=period_employee_ids,
            )
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
