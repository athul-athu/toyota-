from __future__ import annotations

import json
import logging
import zipfile
from decimal import Decimal
from io import BytesIO

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from payroll.email_service import email_configured, email_provider
from payroll.models import Employee, SalaryRecord
from payroll.parsers import parse_payroll_file
from payroll.pdf_generator import generate_salary_slip_pdf
from payroll.services import (
    generate_and_upload_period,
    import_payroll_rows,
    process_period,
    run_full_pipeline,
    run_pipeline_from_file,
    send_period_emails,
)
from payroll.supabase_storage import (
    list_slip_files,
    upload_salary_slip_pdf,
    get_supabase_clients,
    make_in_memory_salary_record,
)

from server.auth_utils import require_auth

logger = logging.getLogger(__name__)


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def preview_upload(request):
    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        result = parse_payroll_file(uploaded.name, uploaded.read())
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(result)


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def import_payroll(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    rows = body.get("rows") or []
    if not rows:
        return JsonResponse({"error": "No rows to import"}, status=400)

    result = import_payroll_rows(rows)
    return JsonResponse({"saved": result["saved"], "errors": result["errors"]})


@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def list_employees(request):
    clients = get_supabase_clients()
    res = clients.service.table("employees").select("*").order("employee_id").execute()
    employees = res.data or []
    data = [
        {
            "employee_id": e["employee_id"],
            "name": e["name"],
            "email": e["email"],
            "designation": e.get("designation") or "",
        }
        for e in employees
    ]
    return JsonResponse({"employees": data, "count": len(data)})



@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def list_salaries(request):
    month = request.GET.get("month")
    year = request.GET.get("year")
    clients = get_supabase_clients()
    query = clients.service.table("salary_records").select("*, employees(*)")
    if month:
        query = query.eq("month", int(month))
    if year:
        query = query.eq("year", int(year))
    res = query.execute()
    records = res.data or []

    data = []
    for r in records:
        emp = r.get("employees") or {}
        data.append({
            "employee_id": r["employee_id"],
            "name": emp.get("name", "Unknown"),
            "email": emp.get("email", ""),
            "designation": emp.get("designation", ""),
            "base_salary": float(r["base_salary"]),
            "hra": float(r["hra"]),
            "allowances": float(r["allowances"]),
            "deductions": float(r["deductions"]),
            "net_salary": float(r["net_salary"]),
            "month": r["month"],
            "year": r["year"],
        })
    return JsonResponse({"salaries": data, "count": len(data)})



@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def list_stored_slips(request):
    month = request.GET.get("month")
    year = request.GET.get("year")
    try:
        slips = list_slip_files(
            month=int(month) if month else None,
            year=int(year) if year else None,
        )
        return JsonResponse({"slips": slips, "count": len(slips)})
    except Exception as exc:
        logger.exception("list_stored_slips failed: %s", exc)
        return JsonResponse(
            {"error": "Could not load slips. Run supabase/schema.sql first."},
            status=500,
        )


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def generate_pdfs(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    month = body.get("month")
    year = body.get("year")
    if not month or not year:
        return JsonResponse({"error": "month and year are required"}, status=400)

    month_int = int(month)
    year_int = int(year)

    clients = get_supabase_clients()
    res = clients.service.table("salary_records").select("*, employees(*)").eq("month", month_int).eq("year", year_int).execute()
    records = res.data or []
    if not records:
        return JsonResponse({"error": "No salary records for that period"}, status=404)

    salaries = [make_in_memory_salary_record(r) for r in records]


    uploaded: list[dict] = []
    upload_errors: list[str] = []
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for salary in salaries:
            employee = salary.employee
            pdf_bytes = generate_salary_slip_pdf(salary)
            zip_name = f"{employee.employee_id}_{employee.name.replace(' ', '_')}_{year_int}_{month_int:02d}.pdf"
            zf.writestr(zip_name, pdf_bytes)

            try:
                meta = upload_salary_slip_pdf(
                    pdf_bytes=pdf_bytes,
                    employee_id=employee.employee_id,
                    employee_name=employee.name,
                    email=employee.email,
                    designation=employee.designation,
                    month=month_int,
                    year=year_int,
                    net_salary=float(salary.net_salary),
                )
                uploaded.append(meta)
            except Exception as exc:
                logger.warning("Upload failed for %s: %s", employee.employee_id, exc)
                upload_errors.append(f"{employee.employee_id}: {exc}")

    if request.GET.get("download") == "zip" or body.get("download_zip"):
        zip_buffer.seek(0)
        response = FileResponse(
            zip_buffer,
            as_attachment=True,
            filename=f"salary_slips_{year_int}_{month_int:02d}.zip",
            content_type="application/zip",
        )
        response["X-Uploaded-Count"] = str(len(uploaded))
        return response

    return JsonResponse(
        {
            "uploaded": uploaded,
            "upload_errors": upload_errors,
            "count": len(uploaded),
            "bucket": "salary-slips",
            "message": "PDFs saved to Supabase Storage. Each file is named by Employee ID and name.",
        }
    )


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def process_period_api(request):
    """Generate PDFs and upload to Supabase only (emails via send-period-emails/)."""
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    month = body.get("month")
    year = body.get("year")
    if month is None or year is None:
        return JsonResponse({"error": "month and year are required"}, status=400)

    try:
        result = generate_and_upload_period(int(month), int(year))
        result["month"] = int(month)
        result["year"] = int(year)
        result["smtp_configured"] = email_configured()
        result["email_provider"] = email_provider()

        if result.get("error"):
            return JsonResponse(result, status=400)
        return JsonResponse(result)
    except Exception as exc:
        logger.exception("process_period_api failed: %s", exc)
        return JsonResponse(
            {"error": str(exc), "month": int(month), "year": int(year)},
            status=500,
        )


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def send_period_emails_api(request):
    """Send a small batch of salary slip emails (call until done=true)."""
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    month = body.get("month")
    year = body.get("year")
    if month is None or year is None:
        return JsonResponse({"error": "month and year are required"}, status=400)

    offset = int(body.get("offset", 0))
    limit = body.get("limit")
    limit_int = int(limit) if limit is not None else None
    employee_ids = body.get("employee_ids")
    if employee_ids is not None and not isinstance(employee_ids, list):
        return JsonResponse({"error": "employee_ids must be a list"}, status=400)

    try:
        result = send_period_emails(
            int(month),
            int(year),
            offset=offset,
            limit=limit_int,
            employee_ids=employee_ids,
        )
        result["smtp_configured"] = email_configured()
        result["email_provider"] = email_provider()

        if result.get("error") and result.get("done"):
            return JsonResponse(result, status=400)
        return JsonResponse(result)
    except Exception as exc:
        logger.exception("send_period_emails_api failed: %s", exc)
        return JsonResponse(
            {
                "error": str(exc),
                "month": int(month),
                "year": int(year),
                "done": False,
                "next_offset": offset,
            },
            status=500,
        )


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def process_and_send(request):
    """
    One-click pipeline: parse file → import DB → generate PDFs →
    upload to Supabase → email each employee their slip.
    """
    uploaded = request.FILES.get("file")
    send_emails = True

    if uploaded:
        send_emails = request.POST.get("send_emails", "true").lower() not in (
            "0",
            "false",
            "no",
        )
        try:
            result = run_pipeline_from_file(
                uploaded.name,
                uploaded.read(),
                send_emails=send_emails,
            )
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except Exception as exc:
            logger.exception("process_and_send failed: %s", exc)
            return JsonResponse({"error": str(exc)}, status=500)
    else:
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        send_emails = body.get("send_emails", True)
        rows = body.get("rows") or []
        if not rows:
            return JsonResponse(
                {"error": "Upload a file or provide rows in JSON body"},
                status=400,
            )
        try:
            result = run_full_pipeline(rows, send_emails=send_emails)
        except Exception as exc:
            logger.exception("process_and_send failed: %s", exc)
            return JsonResponse({"error": str(exc)}, status=500)

    if result.get("error") and not result.get("period_results"):
        return JsonResponse(result, status=400)

    result["smtp_configured"] = email_configured()
    result["email_provider"] = email_provider()
    return JsonResponse(result)
