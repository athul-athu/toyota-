from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from payroll.logo_utils import find_toyota_logo_path
from payroll.models import SalaryRecord

# Toyota salary slip palette
C_PRIMARY = colors.HexColor("#EB0A1E")
C_TEXT = colors.HexColor("#1F2937")
C_LABEL = colors.HexColor("#6B7280")
C_NET = colors.HexColor("#047857")
C_DEDUCT = colors.HexColor("#B91C1C")
C_HEADER_BG = colors.HexColor("#EB0A1E")
C_ROW_ALT = colors.HexColor("#F3F4F6")
C_NET_ROW_BG = colors.HexColor("#ECFDF5")


def _money(value: Decimal | float) -> str:
    return f"₹ {Decimal(value):,.2f}"


def _logo_flowable() -> RLImage | Paragraph | None:
    logo_path = find_toyota_logo_path()
    if not logo_path:
        return None
    try:
        img = RLImage(str(logo_path))
        max_w = 45 * mm
        max_h = 18 * mm
        scale = min(max_w / img.drawWidth, max_h / img.drawHeight, 1.0)
        img.drawWidth *= scale
        img.drawHeight *= scale
        return img
    except Exception:
        return None


def generate_salary_slip_pdf(salary: SalaryRecord) -> bytes:
    employee = salary.employee
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SlipTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=C_PRIMARY,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "SlipSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=C_LABEL,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "SlipBody",
        parent=styles["Normal"],
        fontSize=11,
        textColor=C_TEXT,
        leading=16,
    )
    footer_style = ParagraphStyle(
        "SlipFooter",
        parent=styles["Normal"],
        fontSize=9,
        textColor=C_LABEL,
        fontName="Helvetica-Oblique",
    )

    month_names = [
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
    period = f"{month_names[salary.month]} {salary.year}"
    pay_period_short = f"{salary.month}/{salary.year}"

    story: list = []
    logo = _logo_flowable()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("TOYOTA", title_style))

    story.extend(
        [
            Paragraph("Salary Slip", title_style),
            Paragraph("Official pay statement", subtitle_style),
            Paragraph(
                f'<font color="#EB0A1E"><b>Pay Period: {pay_period_short}</b></font>',
                body_style,
            ),
            Spacer(1, 14),
            Paragraph(
                f'<font color="#1F2937"><b>{employee.name}</b></font><br/>'
                f'<font color="#6B7280">Employee ID:</font> <font color="#1F2937">{employee.employee_id}</font><br/>'
                f'<font color="#6B7280">Email:</font> <font color="#1F2937">{employee.email}</font><br/>'
                f'<font color="#6B7280">Designation:</font> <font color="#1F2937">{employee.designation or "—"}</font><br/>'
                f'<font color="#6B7280">Period:</font> <font color="#1F2937">{period}</font>',
                body_style,
            ),
            Spacer(1, 18),
        ]
    )

    data = [
        ["Component", "Amount (INR)"],
        ["Base Salary", _money(salary.base_salary)],
        ["HRA", _money(salary.hra)],
        ["Allowances", _money(salary.allowances)],
        ["Deductions", f"- {_money(salary.deductions)[2:]}"],
        ["Net Salary", _money(salary.net_salary)],
    ]

    table = Table(data, colWidths=[100 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("TEXTCOLOR", (0, 1), (0, -2), C_TEXT),
                ("TEXTCOLOR", (1, 1), (1, -2), C_TEXT),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, C_ROW_ALT]),
                ("TEXTCOLOR", (0, 4), (-1, 4), C_DEDUCT),
                ("TEXTCOLOR", (1, 4), (1, 4), C_DEDUCT),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
                ("TEXTCOLOR", (0, -1), (-1, -1), C_NET),
                ("TEXTCOLOR", (1, -1), (1, -1), C_NET),
                ("BACKGROUND", (0, -1), (-1, -1), C_NET_ROW_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            "Net Salary = (Base Salary + HRA + Allowances) − Deductions",
            footer_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
