from __future__ import annotations

import re
from typing import Any

from decimal import Decimal
from django.conf import settings
from payroll.models import Employee, SalaryRecord
from server.supabase_client import get_supabase_clients

BUCKET = getattr(settings, "SUPABASE_SALARY_BUCKET", "salary-slips")

def make_in_memory_salary_record(record_dict: dict) -> SalaryRecord:
    emp_data = record_dict.get("employees") or {}
    employee = Employee(
        employee_id=record_dict["employee_id"],
        name=emp_data.get("name", "Unknown"),
        email=emp_data.get("email", ""),
        designation=emp_data.get("designation", ""),
    )
    salary = SalaryRecord(
        employee=employee,
        month=record_dict["month"],
        year=record_dict["year"],
        base_salary=Decimal(str(record_dict["base_salary"])),
        hra=Decimal(str(record_dict["hra"])),
        allowances=Decimal(str(record_dict["allowances"])),
        deductions=Decimal(str(record_dict["deductions"])),
    )
    salary.net_salary = Decimal(str(record_dict["net_salary"]))
    return salary



def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip())
    return cleaned.strip("_") or "employee"


def build_slip_path(employee_id: str, employee_name: str, month: int, year: int) -> str:
    """Storage path: 2026/05/EMP001_Raj_Kumar.pdf"""
    safe_name = _slugify(employee_name)
    safe_id = _slugify(employee_id)
    return f"{year}/{month:02d}/{safe_id}_{safe_name}.pdf"


def build_file_name(employee_id: str, employee_name: str, month: int, year: int) -> str:
    safe_name = _slugify(employee_name)
    safe_id = _slugify(employee_id)
    return f"{safe_id}_{safe_name}_{year}_{month:02d}_salary_slip.pdf"


def sync_employee_to_supabase(
    employee_id: str,
    name: str,
    email: str,
    designation: str = "",
) -> None:
    clients = get_supabase_clients()
    clients.service.table("employees").upsert(
        {
            "employee_id": employee_id,
            "name": name,
            "email": email,
            "designation": designation or "",
        }
    ).execute()


def upload_salary_slip_pdf(
    pdf_bytes: bytes,
    employee_id: str,
    employee_name: str,
    email: str,
    designation: str,
    month: int,
    year: int,
    net_salary: float,
) -> dict[str, Any]:
    sync_employee_to_supabase(employee_id, employee_name, email, designation)

    clients = get_supabase_clients()
    storage_path = build_slip_path(employee_id, employee_name, month, year)
    file_name = build_file_name(employee_id, employee_name, month, year)

    clients.service.storage.from_(BUCKET).upload(
        storage_path,
        pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    signed = clients.service.storage.from_(BUCKET).create_signed_url(
        storage_path, 60 * 60 * 24 * 7
    )
    if isinstance(signed, dict):
        signed_url = signed.get("signedURL") or signed.get("signedUrl")
    else:
        signed_url = getattr(signed, "signed_url", None) or str(signed)

    row = {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "month": month,
        "year": year,
        "file_name": file_name,
        "storage_path": storage_path,
        "bucket_id": BUCKET,
        "net_salary": net_salary,
    }
    clients.service.table("salary_slip_files").upsert(
        row, on_conflict="employee_id,month,year"
    ).execute()

    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "file_name": file_name,
        "storage_path": storage_path,
        "bucket": BUCKET,
        "signed_url": signed_url,
        "month": month,
        "year": year,
    }


def list_slip_files(month: int | None = None, year: int | None = None) -> list[dict]:
    clients = get_supabase_clients()
    query = clients.service.table("salary_slip_files").select("*")
    if month:
        query = query.eq("month", month)
    if year:
        query = query.eq("year", year)
    res = query.order("year", desc=True).order("month", desc=True).execute()
    return res.data or []
