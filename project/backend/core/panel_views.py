from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import timedelta
import csv
from types import SimpleNamespace

from django.db.models import Q
from .models import AdminProfile, Customer, EngineerProfile, IssueOption, Item, Replacement, ReplacementStatus, Report, Ticket, TicketServiceType, TicketStatus
from .panel_forms import PanelEngineerForm, PanelLoginForm, PanelReplacementForm, PanelTicketForm, PanelTicketStatusForm
from .replacement_pdf import build_replacement_invoice_response


def _require_staff(user):
    return user.is_authenticated and user.is_staff


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _login_cache_keys(request, username):
    safe_username = (username or "").strip().lower() or "anonymous"
    ip_address = _get_client_ip(request)
    return (
        f"panel_login_failures:{safe_username}:{ip_address}",
        f"panel_login_lockout:{safe_username}:{ip_address}",
    )


def _get_lockout_message(seconds_remaining):
    minutes = max(1, (seconds_remaining + 59) // 60)
    return f"Too many failed login attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}."


def _display_datetime(value):
    if not value:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M") if hasattr(value, "hour") else value.strftime("%Y-%m-%d")


def _build_report_rows(service_reports, replacements):
    rows = []

    for report in service_reports:
        rows.append(
            SimpleNamespace(
                kind="service",
                ticket=report.ticket,
                engineer=report.engineer,
                service_type=report.ticket.service_type,
                status=report.ticket.status,
                created_at=report.created_at,
                service_provider_code=report.service_provider_code,
                charges_collected=report.charges_collected,
                kms_driven=report.kms_driven,
                detail_url=f"/panel/reports/{report.id}/",
                export_row=[
                    report.ticket.get_service_type_display(),
                    report.ticket.ticket_id,
                    report.engineer.user.username if report.engineer else "",
                    report.ticket.customer.name if report.ticket.customer else "",
                    report.ticket.location,
                    report.ticket.status,
                    _display_datetime(report.ticket.created_at),
                    _display_datetime(report.ticket.started_at),
                    _display_datetime(report.ticket.completed_at),
                    _display_datetime(report.created_at),
                    report.service_provider_code,
                    report.serial_number,
                    report.problem_identified,
                    report.action_taken,
                    report.pcb_board_number,
                    report.comments,
                    report.charges_collected,
                    report.kms_driven,
                    "Yes" if report.is_customer_polite else "No",
                    "Yes" if report.difficult_to_attend else "No",
                    report.before_service_photo.url if report.before_service_photo else "",
                    report.after_service_photo.url if report.after_service_photo else "",
                ],
            )
        )

    for replacement in replacements:
        ticket = replacement.ticket
        rows.append(
            SimpleNamespace(
                kind="replacement",
                ticket=ticket,
                engineer=None,
                service_type=ticket.service_type,
                status=ticket.status,
                created_at=replacement.updated_at,
                service_provider_code=replacement.custom_challan_number or replacement.ref_number or "",
                charges_collected="",
                kms_driven="",
                detail_url=f"/panel/reports/replacement/{ticket.id}/",
                export_row=[
                    ticket.get_service_type_display(),
                    ticket.ticket_id,
                    "",
                    ticket.customer.name if ticket.customer else "",
                    ticket.location,
                    ticket.status,
                    _display_datetime(ticket.created_at),
                    _display_datetime(ticket.started_at),
                    _display_datetime(ticket.completed_at),
                    _display_datetime(replacement.updated_at),
                    replacement.custom_challan_number or replacement.ref_number or "",
                    ticket.serial_number,
                    ticket.issue,
                    replacement.items_summary,
                    "",
                    replacement.billing_address,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            )
        )

    return sorted(rows, key=lambda row: row.created_at or timezone.now(), reverse=True)


def panel_login(request):
    if _require_staff(request.user):
        return redirect("panel:panel_index")
    form = PanelLoginForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        failure_key, lockout_key = _login_cache_keys(request, username)
        lockout_expires_at = cache.get(lockout_key)
        if lockout_expires_at:
            seconds_remaining = max(1, int((lockout_expires_at - timezone.now()).total_seconds()))
            error = _get_lockout_message(seconds_remaining)
            return render(request, "panel/login.html", {"form": form, "error": error, "page_title": "Login"})

        user = authenticate(username=username, password=form.cleaned_data["password"])
        if user and user.is_staff:
            cache.delete(failure_key)
            cache.delete(lockout_key)
            login(request, user)
            return redirect("panel:panel_index")
        max_attempts = getattr(settings, "PANEL_LOGIN_MAX_FAILURES", 5)
        lockout_seconds = getattr(settings, "PANEL_LOGIN_LOCKOUT_SECONDS", 900)
        failure_window = getattr(settings, "PANEL_LOGIN_FAILURE_WINDOW_SECONDS", lockout_seconds)
        attempts = cache.get(failure_key, 0) + 1
        cache.set(failure_key, attempts, failure_window)
        if attempts >= max_attempts:
            lockout_expires_at = timezone.now() + timedelta(seconds=lockout_seconds)
            cache.set(lockout_key, lockout_expires_at, lockout_seconds)
            cache.delete(failure_key)
            error = _get_lockout_message(lockout_seconds)
        else:
            remaining = max_attempts - attempts
            error = f"Invalid credentials or not an admin. {remaining} attempt{'s' if remaining != 1 else ''} remaining before temporary lockout."
    return render(request, "panel/login.html", {"form": form, "error": error, "page_title": "Login"})


def panel_logout(request):
    logout(request)
    return redirect("panel:panel_login")


@login_required(login_url="/panel/login/")
def panel_index(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    tickets = Ticket.objects.select_related("customer", "created_by").all()
    today = timezone.localdate()
    tickets_today = tickets.filter(created_at__date=today)
    non_replacement_today = tickets_today.exclude(service_type=TicketServiceType.REPLACEMENT)
    context = {
        "stats": {
            "total": tickets_today.count(),
            "open": non_replacement_today.filter(status=TicketStatus.OPEN).count(),
            "assigned": non_replacement_today.filter(status=TicketStatus.ASSIGNED).count(),
            "in_progress": non_replacement_today.filter(status=TicketStatus.IN_PROGRESS).count(),
            "completed": non_replacement_today.filter(status=TicketStatus.COMPLETED).count(),
            "replacements": tickets_today.filter(service_type=TicketServiceType.REPLACEMENT).count(),
            "engineers": EngineerProfile.objects.count(),
            "customers": Customer.objects.count(),
            "reports": Report.objects.count(),
            "admins": AdminProfile.objects.count(),
        },
        "recent_tickets": tickets_today.order_by("-created_at")[:8],
        "page_title": "Dashboard",
    }
    return render(request, "panel/index.html", context)


@login_required(login_url="/panel/login/")
def panel_tickets(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    tickets = Ticket.objects.select_related("customer", "created_by", "assigned_engineer", "assigned_engineer__user").all()
    service_type = request.GET.get("service_type", "").strip()
    status = request.GET.get("status", "").strip()
    engineer_id = request.GET.get("engineer", "").strip()
    customer_id = request.GET.get("customer", "").strip()
    search = request.GET.get("search", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if service_type:
        tickets = tickets.filter(service_type=service_type)
    if status:
        tickets = tickets.filter(status=status)
    if engineer_id:
        tickets = tickets.filter(assigned_engineer_id=engineer_id)
    if customer_id:
        tickets = tickets.filter(customer_id=customer_id)
    if search:
        tickets = tickets.filter(
            Q(ticket_id__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(customer__contact_phone__icontains=search)
        )
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            tickets = tickets.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            tickets = tickets.filter(created_at__date__lte=parsed)
    if not any([service_type, status, engineer_id, customer_id, search, date_from, date_to]):
        today = timezone.localdate()
        tickets = tickets.filter(created_at__date=today)
        date_from = date_to = today.isoformat()

    tickets = tickets.order_by("-created_at")
    engineers = EngineerProfile.objects.select_related("user").order_by("user__username")
    customers = Customer.objects.order_by("name")
    return render(
        request,
        "panel/tickets.html",
        {
            "tickets": tickets,
            "page_title": "Tickets",
            "engineers": engineers,
            "customers": customers,
            "filters": {
                "service_type": service_type,
                "status": status,
                "engineer": engineer_id,
                "customer": customer_id,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@login_required(login_url="/panel/login/")
def panel_ticket_edit(request, ticket_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    ticket = Ticket.objects.select_related("customer", "created_by", "assigned_engineer").get(id=ticket_id)
    form = PanelTicketStatusForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:panel_tickets")
    return render(
        request,
        "panel/ticket_edit.html",
        {"form": form, "ticket": ticket, "page_title": f"Update {ticket.ticket_id}"},
    )


@login_required(login_url="/panel/login/")
def panel_ticket_create(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    form = PanelTicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        if request.user.is_authenticated and not ticket.created_by_id:
            ticket.created_by = request.user
        ticket.save()
        return redirect("panel:panel_tickets")
    return render(request, "panel/ticket_form.html", {"form": form, "page_title": "Create Ticket"})


@login_required(login_url="/panel/login/")
def panel_issue_option_create(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Issue name is required."}, status=400)
    name = name[0].upper() + name[1:] if name else name

    option, created = IssueOption.objects.get_or_create(name=name)
    if not created and not option.active:
        option.active = True
        option.save(update_fields=["active"])

    return JsonResponse(
        {
            "id": option.id,
            "name": option.name,
            "created": created,
        }
    )


@login_required(login_url="/panel/login/")
def panel_issue_option_delete(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Issue name is required."}, status=400)
    name = name[0].upper() + name[1:] if name else name

    option = get_object_or_404(IssueOption, name=name)
    option.active = False
    option.save(update_fields=["active"])
    return JsonResponse({"deleted": True, "id": option.id, "name": option.name})


@login_required(login_url="/panel/login/")
def panel_item_create(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Product name is required."}, status=400)
    name = name[0].upper() + name[1:] if name else name

    item, created = Item.objects.get_or_create(name=name)
    if not created and not item.active:
        item.active = True
        item.save(update_fields=["active"])

    return JsonResponse(
        {
            "id": item.id,
            "name": item.name,
            "created": created,
        }
    )


@login_required(login_url="/panel/login/")
def panel_item_delete(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Product name is required."}, status=400)
    name = name[0].upper() + name[1:] if name else name

    item = get_object_or_404(Item, name=name)
    item.active = False
    item.save(update_fields=["active"])
    return JsonResponse({"deleted": True, "id": item.id, "name": item.name})


@login_required(login_url="/panel/login/")
def panel_engineers(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    engineers = EngineerProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "panel/engineers.html",
        {
            "engineers": engineers,
            "page_title": "Engineers",
        },
    )


@login_required(login_url="/panel/login/")
def panel_engineer_create(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    form = PanelEngineerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:panel_engineers")
    return render(request, "panel/engineer_form.html", {"form": form, "page_title": "Add Engineer"})


@login_required(login_url="/panel/login/")
def panel_replacements(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")

    def _get_replacement(ticket):
        try:
            return ticket.replacement
        except Replacement.DoesNotExist:
            return None

    tickets = (
        Ticket.objects.select_related("customer")
        .select_related("created_by", "replacement__created_by")
        .prefetch_related("replacement__line_items")
        .filter(service_type=TicketServiceType.REPLACEMENT)
    )

    status = request.GET.get("status", "").strip()
    search = request.GET.get("search", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if status:
        tickets = tickets.filter(replacement__status=status)
    if search:
        tickets = tickets.filter(
            Q(ticket_id__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(customer__contact_phone__icontains=search)
        )
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            tickets = tickets.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            tickets = tickets.filter(created_at__date__lte=parsed)
    if not any([status, search, date_from, date_to]):
        today = timezone.localdate()
        tickets = tickets.filter(created_at__date=today)
        date_from = date_to = today.isoformat()

    tickets = tickets.order_by("-created_at")
    replacements = [{"ticket": ticket, "replacement": _get_replacement(ticket)} for ticket in tickets]

    return render(
        request,
        "panel/replacements.html",
        {
            "replacements": replacements,
            "page_title": "Replacement",
            "filters": {
                "status": status,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@login_required(login_url="/panel/login/")
def panel_replacement_edit(request, ticket_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    ticket = Ticket.objects.select_related("customer", "created_by", "replacement__created_by").prefetch_related("replacement__line_items").get(id=ticket_id, service_type=TicketServiceType.REPLACEMENT)
    try:
        replacement = ticket.replacement
    except Replacement.DoesNotExist:
        replacement = Replacement(ticket=ticket)
    form = PanelReplacementForm(request.POST or None, instance=replacement, ticket=ticket, created_by=request.user)
    if request.method == "POST" and form.is_valid():
        replacement = form.save()
        replacement.status = ReplacementStatus.COMPLETED
        replacement.save(update_fields=["status"])
        ticket.status = TicketStatus.COMPLETED
        ticket.save(update_fields=["status"])
        return redirect("panel:panel_replacements")
    items = Item.objects.filter(active=True).order_by("name")
    return render(
        request,
        "panel/replacement_form.html",
        {
            "form": form,
            "ticket": ticket,
            "replacement": replacement,
            "items": items,
            "page_title": "Replacement",
        },
    )


@login_required(login_url="/panel/login/")
def panel_replacement_invoice(request, ticket_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    replacement = get_object_or_404(
        Replacement.objects.select_related("created_by", "ticket", "ticket__customer", "ticket__created_by").prefetch_related("line_items"),
        ticket_id=ticket_id,
    )
    return build_replacement_invoice_response(replacement)


@login_required(login_url="/panel/login/")
def panel_customers(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    customers = Customer.objects.order_by("name")
    return render(
        request,
        "panel/customers.html",
        {
            "customers": customers,
            "page_title": "Customers",
        },
    )


@login_required(login_url="/panel/login/")
def panel_reports(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    service_type = request.GET.get("service_type", "").strip()
    engineer_id = request.GET.get("engineer", "").strip()
    status = request.GET.get("status", "").strip()
    ticket_search = request.GET.get("ticket", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    service_reports = Report.objects.select_related("ticket", "engineer", "engineer__user", "ticket__customer").all()
    replacement_reports = (
        Replacement.objects.select_related("ticket", "ticket__customer")
        .prefetch_related("line_items")
        .filter(status=ReplacementStatus.COMPLETED)
    )

    if service_type:
        service_reports = service_reports.filter(ticket__service_type=service_type)
        replacement_reports = replacement_reports.filter(ticket__service_type=service_type)
    if engineer_id:
        service_reports = service_reports.filter(engineer_id=engineer_id)
        replacement_reports = replacement_reports.none()
    if status:
        service_reports = service_reports.filter(ticket__status=status)
        replacement_reports = replacement_reports.filter(ticket__status=status)
    if ticket_search:
        service_reports = service_reports.filter(ticket__ticket_id__icontains=ticket_search)
        replacement_reports = replacement_reports.filter(ticket__ticket_id__icontains=ticket_search)
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            service_reports = service_reports.filter(created_at__date__gte=parsed)
            replacement_reports = replacement_reports.filter(updated_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            service_reports = service_reports.filter(created_at__date__lte=parsed)
            replacement_reports = replacement_reports.filter(updated_at__date__lte=parsed)
    if not any([service_type, engineer_id, status, ticket_search, date_from, date_to]):
        today = timezone.localdate()
        service_reports = service_reports.filter(created_at__date=today)
        replacement_reports = replacement_reports.filter(updated_at__date=today)
        date_from = date_to = today.isoformat()

    report_rows = _build_report_rows(service_reports, replacement_reports)

    filters_applied = any([service_type, engineer_id, status, ticket_search, date_from, date_to])
    if request.GET.get("export") == "csv" and filters_applied:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="reports.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Service Type",
            "Ticket ID",
            "Engineer",
            "Customer",
            "Location",
            "Status",
            "Ticket Created",
            "Ticket Started",
            "Ticket Completed",
            "Report Created",
            "Service Provider Code",
            "Serial Number",
            "Problem Identified",
            "Action Taken",
            "PCB Board Number",
            "Comments",
            "Charges Collected",
            "KMs Driven",
            "Customer Polite",
            "Difficult To Attend",
            "Before Service Photo",
            "After Service Photo",
        ])
        for row in report_rows:
            writer.writerow(row.export_row)
        return response

    engineers = EngineerProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "panel/reports.html",
        {
            "reports": report_rows,
            "page_title": "Reports",
            "engineers": engineers,
            "filters": {
                "service_type": service_type,
                "engineer": engineer_id,
                "status": status,
                "ticket": ticket_search,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@login_required(login_url="/panel/login/")
def panel_report_detail(request, report_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    report = Report.objects.select_related("ticket", "engineer", "engineer__user").get(id=report_id)
    return render(request, "panel/report_detail.html", {"report": report, "page_title": f"Report {report.ticket.ticket_id}"})


@login_required(login_url="/panel/login/")
def panel_replacement_report_detail(request, ticket_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    replacement = get_object_or_404(
        Replacement.objects.select_related("ticket", "ticket__customer").prefetch_related("line_items"),
        ticket_id=ticket_id,
        status=ReplacementStatus.COMPLETED,
    )
    return render(
        request,
        "panel/replacement_report_detail.html",
        {
            "replacement": replacement,
            "page_title": f"Replacement Report {replacement.ticket.ticket_id}",
        },
    )


@login_required(login_url="/panel/login/")
def panel_admins(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    admins = AdminProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "panel/admins.html",
        {
            "admins": admins,
            "page_title": "Admin Profiles",
        },
    )
