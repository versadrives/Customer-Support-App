from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape


DEFAULT_COMPANY_NAME = "VERSA DRIVES PRIVATE LIMITED"
DEFAULT_COMPANY_CLOSING = "With best regards"
DEFAULT_PURPOSE_NOTE = (
    "The following material are sent only for servicing / replacement / trial / "
    "after service / rework / job work purpose and not for sale."
)


def _clean_text(value):
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _format_date(value):
    if not value:
        return "-"
    return timezone.localtime(value).strftime("%d-%m-%Y") if hasattr(value, "hour") else value.strftime("%d-%m-%Y")


def _display_user(user):
    if not user:
        return "-"
    full_name = user.get_full_name().strip()
    return full_name or user.get_username()


def _resolve_header_image_path():
    configured_path = getattr(settings, "REPLACEMENT_INVOICE_HEADER_IMAGE", None)
    if configured_path:
        configured_path = Path(configured_path)
        if configured_path.exists():
            return configured_path

    logo_dir = Path(getattr(settings, "REPLACEMENT_INVOICE_LOGO_DIR", Path.cwd()))
    candidates = [
        "invoice_header.png",
        "invoice_header.jpg",
        "invoice_header.jpeg",
        "invoice_header.webp",
        "header.png",
        "header.jpg",
        "header.jpeg",
        "header.webp",
        "logo.png",
        "logo.jpg",
        "logo.jpeg",
        "logo.webp",
    ]
    for name in candidates:
        candidate = logo_dir / name
        if candidate.exists():
            return candidate
    return None


def _build_header_image():
    image_path = _resolve_header_image_path()
    if not image_path:
        return None

    header = RLImage(str(image_path))
    max_width = 170 * mm
    if header.imageWidth > max_width:
        scale = max_width / float(header.imageWidth)
        header.drawWidth = header.imageWidth * scale
        header.drawHeight = header.imageHeight * scale
    header.hAlign = "CENTER"
    return header


def _recipient_lines(replacement):
    ticket = replacement.ticket
    customer = getattr(ticket, "customer", None)
    lines = []

    organization_name = _clean_text(replacement.organization_name)
    contact_name = _clean_text(replacement.contact_name or (customer.name if customer else ""))
    billing_address = _clean_text(replacement.billing_address or (customer.address if customer else ""))
    location = _clean_text(ticket.location)

    city = _clean_text(replacement.billing_city)
    state = _clean_text(replacement.billing_state)
    country = _clean_text(replacement.billing_country)
    postal_code = _clean_text(replacement.billing_postal_code)
    phone = _clean_text(replacement.contact_phone or (customer.contact_phone if customer else ""))

    if organization_name and organization_name.lower() != contact_name.lower():
        lines.append(organization_name)
    if contact_name:
        lines.append(contact_name)
    if billing_address:
        lines.append(billing_address)

    locality_parts = [part for part in [location, city, state, country] if part]
    if locality_parts or postal_code:
        locality_line = ", ".join(locality_parts)
        if postal_code:
            locality_line = f"{locality_line}, Pin Code - {postal_code}" if locality_line else f"Pin Code - {postal_code}"
        lines.append(locality_line)

    if phone:
        lines.append(phone)

    return lines or ["-"]


def _build_story(replacement):
    company_name = getattr(settings, "REPLACEMENT_INVOICE_COMPANY_NAME", DEFAULT_COMPANY_NAME)
    closing = getattr(settings, "REPLACEMENT_INVOICE_CLOSING", DEFAULT_COMPANY_CLOSING)
    purpose_note = getattr(settings, "REPLACEMENT_INVOICE_NOTE", DEFAULT_PURPOSE_NOTE)

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "ReplacementNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceAfter=0,
    )
    bold = ParagraphStyle(
        "ReplacementBold",
        parent=normal,
        fontName="Helvetica-Bold",
    )
    heading = ParagraphStyle(
        "ReplacementHeading",
        parent=bold,
        fontSize=12,
        leading=16,
        spaceAfter=4,
    )
    right = ParagraphStyle(
        "ReplacementRight",
        parent=normal,
        alignment=2,
    )

    story = []
    header_image = _build_header_image()
    if header_image:
        story.extend([header_image, Spacer(1, 6 * mm)])

    story.extend(
        [
            Paragraph(escape("To whom so ever it may concern"), heading),
            Spacer(1, 2 * mm),
            Paragraph(escape("To"), bold),
        ]
    )

    for line in _recipient_lines(replacement):
        story.append(Paragraph(escape(line), normal))

    story.append(Spacer(1, 6 * mm))

    ref_table = Table(
        [
            [
                Paragraph(f"<b>Our Ref. No.:</b> {escape(_clean_text(replacement.custom_challan_number or replacement.ref_number or replacement.ticket.ticket_id))}", normal),
                Paragraph(f"<b>Date:</b> {escape(_format_date(replacement.ref_date or replacement.updated_at))}", right),
            ],
            [
                Paragraph(f"<b>Your Ref. No.:</b> {escape(_clean_text(replacement.client_ref_number or replacement.ticket.ticket_id))}", normal),
                Paragraph(f"<b>Date:</b> {escape(_format_date(replacement.client_ref_date or replacement.ticket.created_at))}", right),
            ],
            [
                Paragraph(f"<b>Prepared By:</b> {escape(_display_user(replacement.created_by or replacement.ticket.created_by))}", normal),
                "",
            ],
        ],
        colWidths=[95 * mm, 75 * mm],
    )
    ref_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([ref_table, Spacer(1, 6 * mm), Paragraph(escape(purpose_note), normal), Spacer(1, 6 * mm)])

    line_items = list(replacement.line_items.all())
    if not line_items and replacement.item_name:
        line_items = [replacement]
    table_rows = [[
        Paragraph("<b>S.No#</b>", normal),
        Paragraph("<b>Description</b>", normal),
        Paragraph("<b>Qty</b>", normal),
        Paragraph("<b>Purpose</b>", normal),
    ]]

    for index, item in enumerate(line_items, start=1):
        serial_number = _clean_text(getattr(item, "serial_number", "") or replacement.ticket.serial_number)
        description_parts = [part for part in [_clean_text(item.item_name), serial_number] if part]
        description = " / ".join(description_parts) or "-"
        purpose = _clean_text(item.item_description) or "Replacement"
        table_rows.append([
            str(index),
            Paragraph(escape(description), normal),
            str(item.quantity),
            Paragraph(escape(purpose), normal),
        ])

    items_table = Table(table_rows, colWidths=[18 * mm, 82 * mm, 20 * mm, 50 * mm], repeatRows=1)
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#6b7280")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([items_table, Spacer(1, 18 * mm)])

    signature_table = Table(
        [
            [
                Paragraph(escape(closing), normal),
                "",
            ],
            [
                Paragraph(f"For <b>{escape(company_name)}</b>", normal),
            ],
            [
                Paragraph("Despatched through:", normal),
            ],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    signature_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(signature_table)
    return story


def build_replacement_invoice_response(replacement):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    doc.build(_build_story(replacement))

    filename_root = replacement.custom_challan_number or replacement.ref_number or replacement.ticket.ticket_id
    filename = f"replacement_invoice_{_clean_text(filename_root).replace(' ', '_')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
