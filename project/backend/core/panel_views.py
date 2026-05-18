def _escape_like_wildcards(value):
    """Escape SQL wildcard characters (%) and underscore (_) for literal LIKE matching."""
    if not value:
        return value
    # Escape % and _ by adding a backslash before them
    # Note: Different databases use different escape characters, but PostgreSQL and MySQL
    # both support \ as an escape character for LIKE when used with ESCAPE clause
    # However, Django's ORM doesn't easily support specifying the escape clause
    # So we'll use the standard SQL escape syntax by replacing the characters
    return value.replace('%', '\\%').replace('_', '\\_')


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import csv
from types import SimpleNamespace
import re
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from .models import AdminProfile, Customer, EngineerProfile, IssueOption, Item, Replacement, ReplacementStatus, Report, SavedView, SavedViewPageType, Ticket, TicketServiceType, TicketStatus
from .panel_forms import PanelEngineerForm, PanelLoginForm, PanelReplacementForm, PanelTicketForm, PanelTicketStatusForm
from .replacement_pdf import build_replacement_invoice_response


TICKET_COLUMN_CHOICES = (
    ("ticket_id", "Ticket"),
    ("customer", "Customer"),
    ("service_type", "Type"),
    ("complaint", "Complaint"),
    ("phone", "Phone"),
    ("location", "Location"),
    ("model", "Product"),
    ("purchase_date", "Purchase Date"),
    ("status", "Status"),
    ("assigned", "Assigned"),
    ("created", "Created"),
)
DEFAULT_TICKET_COLUMNS = [
    "ticket_id",
    "customer",
    "service_type",
    "complaint",
    "phone",
    "status",
    "assigned",
    "created",
]
TICKET_FILTER_KEYS = ("service_type", "status", "engineer", "search", "date_from", "date_to")
REPLACEMENT_COLUMN_CHOICES = (
    ("ticket_id", "Ticket"),
    ("customer", "Customer"),
    ("phone", "Phone"),
    ("purchase_date", "Purchase Date"),
    ("complaint", "Complaint"),
    ("item", "Item"),
    ("serial_number", "Serial Number"),
    ("challan", "Challan"),
    ("status", "Status"),
    ("created", "Created"),
)
DEFAULT_REPLACEMENT_COLUMNS = [column_id for column_id, _ in REPLACEMENT_COLUMN_CHOICES]
REPLACEMENT_FILTER_KEYS = ("status", "search", "date_from", "date_to")
REPORT_COLUMN_CHOICES = (
    ("ticket_id", "Ticket"),
    ("customer", "Customer"),
    ("type", "Type"),
    ("status", "Status"),
    ("engineer", "Engineer"),
    ("location", "Location"),
    ("provider_code", "Provider Code"),
    ("serial_number", "Serial Number"),
    ("charges", "Charges"),
    ("log_date", "Log Date"),
)
DEFAULT_REPORT_COLUMNS = [column_id for column_id, _ in REPORT_COLUMN_CHOICES]
REPORT_FILTER_KEYS = ("service_type", "status", "engineer", "search", "date_from", "date_to")
LIST_PAGE_CONFIG = {
    SavedViewPageType.TICKETS: {
        "label": "Tickets",
        "url_name": "panel:panel_tickets",
        "filter_keys": TICKET_FILTER_KEYS,
        "column_choices": TICKET_COLUMN_CHOICES,
        "default_columns": DEFAULT_TICKET_COLUMNS,
    },
    SavedViewPageType.REPLACEMENTS: {
        "label": "Replacements",
        "url_name": "panel:panel_replacements",
        "filter_keys": REPLACEMENT_FILTER_KEYS,
        "column_choices": REPLACEMENT_COLUMN_CHOICES,
        "default_columns": DEFAULT_REPLACEMENT_COLUMNS,
    },
    SavedViewPageType.REPORTS: {
        "label": "Reports",
        "url_name": "panel:panel_reports",
        "filter_keys": REPORT_FILTER_KEYS,
        "column_choices": REPORT_COLUMN_CHOICES,
        "default_columns": DEFAULT_REPORT_COLUMNS,
    },
}
TICKET_STATE_QUERY_KEYS = ("view", "service_type", "status", "engineer", "search", "date_from", "date_to", "page")
TICKET_LAST_QUERY_SESSION_KEY = "panel_tickets_last_query"


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


def _display_bool(value):
    return "Yes" if value else "No"


def _normalize_columns(page_type, columns):
    config = LIST_PAGE_CONFIG[page_type]
    allowed = {column_id for column_id, _ in config["column_choices"]}
    normalized = []
    for column in columns:
        if column in allowed and column not in normalized:
            normalized.append(column)
    return normalized or list(config["default_columns"])


def _build_filters_from_source(page_type, source):
    return {key: source.get(key, "").strip() for key in LIST_PAGE_CONFIG[page_type]["filter_keys"]}


def _get_columns_from_source(page_type, source):
    serialized = (source.get("selected_columns") or "").strip()
    if serialized:
        return _normalize_columns(page_type, [value.strip() for value in serialized.split(",") if value.strip()])
    getter = getattr(source, "getlist", None)
    if getter:
        return _normalize_columns(page_type, getter("columns"))
    raw_value = source.get("columns", [])
    if isinstance(raw_value, (list, tuple)):
        return _normalize_columns(page_type, raw_value)
    return _normalize_columns(page_type, [raw_value] if raw_value else [])


def _get_saved_views_for_page(user, page_type):
    return SavedView.objects.filter(user=user, page_type=page_type).order_by("name")


def _resolve_page_type(raw_page_type):
    if raw_page_type in LIST_PAGE_CONFIG:
        return raw_page_type
    return SavedViewPageType.TICKETS


def _build_lists_url(page_type, view_id="", mode=""):
    params = {"page_type": page_type}
    if view_id:
        params["view"] = str(view_id)
    if mode:
        params["mode"] = mode
    return f"{reverse('panel:panel_lists')}?{urlencode(params)}"


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
                    _display_datetime(report.ticket.purchase_date),
                    _display_bool(report.ticket.new_fan_complaint),
                    report.ticket.repeated_complaint_count or "",
                    _display_datetime(report.created_at),
                    report.service_provider_code,
                    report.serial_number,
                    report.problem_identified,
                    report.ticket.issue_notes,
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
                service_provider_code=replacement.custom_challan_number or ticket.ticket_id or "",
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
                    _display_datetime(ticket.purchase_date),
                    _display_bool(ticket.new_fan_complaint),
                    ticket.repeated_complaint_count or "",
                    _display_datetime(replacement.updated_at),
                    replacement.custom_challan_number or ticket.ticket_id or "",
                    ticket.serial_number,
                    ticket.issue,
                    ticket.issue_notes,
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
def panel_lists(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")

    saved_view_error = ""
    saved_view_success = ""
    current_page_type = _resolve_page_type((request.GET.get("page_type") or request.POST.get("page_type") or "").strip())
    selected_view_id = (request.GET.get("view") or "").strip()
    editor_mode = (request.GET.get("mode") or request.POST.get("editor_mode") or "").strip()
    all_saved_views = SavedView.objects.filter(user=request.user).order_by("page_type", "name")
    saved_views = all_saved_views.filter(page_type=current_page_type)
    active_saved_view = None
    if selected_view_id.isdigit():
        active_saved_view = all_saved_views.filter(id=int(selected_view_id)).first()
        if active_saved_view:
            current_page_type = active_saved_view.page_type
            saved_views = all_saved_views.filter(page_type=current_page_type)

    page_config = LIST_PAGE_CONFIG[current_page_type]
    initial_filters = {key: "" for key in page_config["filter_keys"]}
    visible_columns = list(page_config["default_columns"])
    view_name = ""
    is_default = False
    editing_view_id = ""
    if active_saved_view:
        initial_filters.update(active_saved_view.filters or {})
        visible_columns = _normalize_columns(current_page_type, active_saved_view.columns or [])
        view_name = active_saved_view.name
        is_default = active_saved_view.is_default
        editing_view_id = str(active_saved_view.id)
        if not editor_mode:
            editor_mode = "edit"

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_view":
            if editor_mode not in ("new", "edit"):
                editor_mode = "edit" if active_saved_view else "new"
            view_name = (request.POST.get("view_name") or "").strip()
            editing_view_id = (request.POST.get("editing_view_id") or "").strip()
            current_page_type = _resolve_page_type((request.POST.get("page_type") or "").strip())
            page_config = LIST_PAGE_CONFIG[current_page_type]
            initial_filters = _build_filters_from_source(current_page_type, request.POST)
            visible_columns = _get_columns_from_source(current_page_type, request.POST)
            is_default = request.POST.get("is_default") == "1"
            if not view_name:
                saved_view_error = "Enter a name to save this list."
            else:
                saved_view = None
                if editing_view_id.isdigit():
                    saved_view = SavedView.objects.filter(
                        id=int(editing_view_id),
                        user=request.user,
                    ).first()
                if saved_view:
                    saved_view.page_type = current_page_type
                    saved_view.name = view_name
                    saved_view.filters = dict(initial_filters)
                    saved_view.columns = visible_columns
                    saved_view.is_default = is_default
                    saved_view.save()
                else:
                    saved_view, _ = SavedView.objects.update_or_create(
                        user=request.user,
                        page_type=current_page_type,
                        name=view_name,
                        defaults={
                            "filters": dict(initial_filters),
                            "columns": visible_columns,
                            "is_default": is_default,
                        },
                    )
                if is_default:
                    SavedView.objects.filter(
                        user=request.user,
                        page_type=current_page_type,
                    ).exclude(id=saved_view.id).update(is_default=False)
                return redirect(_build_lists_url(current_page_type, saved_view.id, "edit"))
        elif action == "delete_view":
            delete_id = (request.POST.get("view_id") or "").strip()
            if delete_id.isdigit():
                target_view = all_saved_views.filter(id=int(delete_id)).first()
                deleted = all_saved_views.filter(id=int(delete_id)).delete()
                if deleted[0]:
                    if target_view:
                        current_page_type = target_view.page_type
                    return redirect(_build_lists_url(current_page_type))
        else:
            editor_mode = "new"

    editor_open = editor_mode in ("new", "edit")

    engineers = EngineerProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "panel/lists.html",
        {
            "page_title": "Lists",
            "page_type_choices": SavedViewPageType.choices,
            "current_page_type": current_page_type,
            "current_page_label": page_config["label"],
            "all_saved_views": all_saved_views,
            "saved_views": saved_views,
            "active_saved_view": active_saved_view,
            "selected_view_id": selected_view_id,
            "page_url_name": page_config["url_name"],
            "column_choices": page_config["column_choices"],
            "visible_columns": visible_columns,
            "filters": initial_filters,
            "engineers": engineers,
            "saved_view_error": saved_view_error,
            "saved_view_success": saved_view_success,
            "view_name": view_name,
            "is_default": is_default,
            "editing_view_id": editing_view_id,
            "editor_open": editor_open,
            "editor_mode": editor_mode,
        },
    )


@login_required(login_url="/panel/login/")
def panel_tickets(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    if request.GET.get("clear") == "1":
        request.session.pop(TICKET_LAST_QUERY_SESSION_KEY, None)
        return redirect("panel:panel_tickets")

    has_ticket_state = any(key in request.GET for key in TICKET_STATE_QUERY_KEYS)
    if not has_ticket_state:
        last_query = request.session.get(TICKET_LAST_QUERY_SESSION_KEY, "")
        if last_query:
            return redirect(f"{reverse('panel:panel_tickets')}?{last_query}")

    # Calculate today's date and count of tickets for today (unfiltered)
    today = timezone.localdate()
    today_tickets_count = Ticket.objects.filter(created_at__date=today).count()

    saved_views = _get_saved_views_for_page(request.user, SavedViewPageType.TICKETS)
    selected_view_id = (request.GET.get("view") or "").strip()
    active_saved_view = None
    if selected_view_id.isdigit():
        active_saved_view = saved_views.filter(id=int(selected_view_id)).first()
    elif request.method != "POST" and not any(key in request.GET for key in ("service_type", "status", "engineer", "search", "date_from", "date_to", "columns", "page")):
        active_saved_view = saved_views.filter(is_default=True).first()
        if active_saved_view:
            selected_view_id = str(active_saved_view.id)

    initial_filters = {key: "" for key in TICKET_FILTER_KEYS}
    visible_columns = list(DEFAULT_TICKET_COLUMNS)
    if active_saved_view:
        initial_filters.update(active_saved_view.filters or {})
        visible_columns = _normalize_columns(SavedViewPageType.TICKETS, active_saved_view.columns or [])
    else:
        for key in TICKET_FILTER_KEYS:
            if key in request.GET:
                initial_filters[key] = request.GET.get(key, "").strip()
        if "columns" in request.GET:
            visible_columns = _normalize_columns(SavedViewPageType.TICKETS, request.GET.getlist("columns"))

    tickets = Ticket.objects.select_related("customer", "created_by", "assigned_engineer", "assigned_engineer__user").all()
    service_type = initial_filters["service_type"]
    status = initial_filters["status"]
    engineer_id = initial_filters["engineer"]
    customer_id = request.GET.get("customer", "").strip()
    search = initial_filters["search"]
    date_from = initial_filters["date_from"]
    date_to = initial_filters["date_to"]

    if service_type:
        tickets = tickets.filter(service_type=service_type)
    if status:
        tickets = tickets.filter(status=status)
    if engineer_id:
        tickets = tickets.filter(assigned_engineer_id=engineer_id)
    if customer_id:
        tickets = tickets.filter(customer_id=customer_id)
    if search:
        # Escape special characters for literal search
        escaped_search = _escape_like_wildcards(search)
        tickets = tickets.filter(
            Q(ticket_id__icontains=escaped_search)
            | Q(customer__name__icontains=escaped_search)
            | Q(customer__contact_phone__icontains=escaped_search)
            | Q(issue__icontains=escaped_search)
            | Q(issue_notes__icontains=escaped_search)
        )
    if date_from and not search:
        parsed = parse_date(date_from)
        if parsed:
            tickets = tickets.filter(created_at__date__gte=parsed)
    if date_to and not search:
        parsed = parse_date(date_to)
        if parsed:
            tickets = tickets.filter(created_at__date__lte=parsed)
    # If no filters are applied, restrict to today's tickets
    if not any([service_type, status, engineer_id, customer_id, search, date_from, date_to]):
        tickets = tickets.filter(created_at__date=today)
        date_from = date_to = today.isoformat()

    # Calculate filtered count (after applying filters and today restriction if no filters)
    filtered_count = tickets.count()

    # Calculate statistics based on the filtered queryset
    non_replacement = tickets.exclude(service_type=TicketServiceType.REPLACEMENT)
    replacements = tickets.filter(service_type=TicketServiceType.REPLACEMENT)
    stats = {
        'total': tickets.count(),
        'open': non_replacement.filter(status=TicketStatus.OPEN).count(),
        'assigned': non_replacement.filter(status=TicketStatus.ASSIGNED).count(),
        'in_progress': non_replacement.filter(status=TicketStatus.IN_PROGRESS).count(),
        'completed': non_replacement.filter(status=TicketStatus.COMPLETED).count(),
        'replacements': replacements.count(),
        'engineers': EngineerProfile.objects.count(),
        'customers': Customer.objects.count(),
        'reports': Report.objects.count(),
        'admins': AdminProfile.objects.count(),
    }

    filters_applied = any([service_type, status, engineer_id, customer_id, search, date_from, date_to])
    tickets = tickets.order_by("-created_at")
    page_obj = None
    page_query = ""
    if filters_applied:
        paginator = Paginator(tickets, 10)
        page_obj = paginator.get_page(request.GET.get("page"))
        tickets = page_obj.object_list
        page_query_params = request.GET.copy()
        page_query_params.pop("page", None)
        page_query = page_query_params.urlencode()

    state_query = request.GET.copy()
    if "clear" in state_query:
        state_query.pop("clear", None)
    if any(state_query.get(key, "").strip() for key in TICKET_STATE_QUERY_KEYS if key != "page"):
        request.session[TICKET_LAST_QUERY_SESSION_KEY] = state_query.urlencode()
    elif state_query.get("view", "").strip():
        request.session[TICKET_LAST_QUERY_SESSION_KEY] = state_query.urlencode()
    else:
        request.session.pop(TICKET_LAST_QUERY_SESSION_KEY, None)

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
            "page_obj": page_obj,
            "page_query": page_query,
            "saved_views": saved_views,
            "active_saved_view": active_saved_view,
            "selected_view_id": selected_view_id,
            "ticket_column_choices": TICKET_COLUMN_CHOICES,
            "visible_columns": visible_columns,
            "empty_colspan": len(visible_columns) + 1,
            "filters": {
                "service_type": service_type,
                "status": status,
                "engineer": engineer_id,
                "customer": customer_id,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
            "stats": stats,
            "today_tickets_count": today_tickets_count,
            "filtered_count": filtered_count,
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

    saved_views = _get_saved_views_for_page(request.user, SavedViewPageType.REPLACEMENTS)
    selected_view_id = (request.GET.get("view") or "").strip()
    active_saved_view = None
    if selected_view_id.isdigit():
        active_saved_view = saved_views.filter(id=int(selected_view_id)).first()
    elif not any(key in request.GET for key in ("status", "search", "date_from", "date_to", "columns", "page")):
        active_saved_view = saved_views.filter(is_default=True).first()
        if active_saved_view:
            selected_view_id = str(active_saved_view.id)

    initial_filters = {key: "" for key in REPLACEMENT_FILTER_KEYS}
    visible_columns = list(DEFAULT_REPLACEMENT_COLUMNS)
    if active_saved_view:
        initial_filters.update(active_saved_view.filters or {})
        visible_columns = _normalize_columns(SavedViewPageType.REPLACEMENTS, active_saved_view.columns or [])
    else:
        for key in REPLACEMENT_FILTER_KEYS:
            if key in request.GET:
                initial_filters[key] = request.GET.get(key, "").strip()
        if "columns" in request.GET:
            visible_columns = _normalize_columns(SavedViewPageType.REPLACEMENTS, request.GET.getlist("columns"))

    status = initial_filters["status"]
    search = initial_filters["search"]
    date_from = initial_filters["date_from"]
    date_to = initial_filters["date_to"]

    if status:
        tickets = tickets.filter(replacement__status=status)
    if search:
        escaped_search = _escape_like_wildcards(search)
        tickets = tickets.filter(
            Q(ticket_id__icontains=escaped_search)
            | Q(customer__name__icontains=escaped_search)
            | Q(customer__contact_phone__icontains=escaped_search)
            | Q(issue__icontains=escaped_search)
            | Q(issue_notes__icontains=escaped_search)
        )
    if date_from and not search:
        parsed = parse_date(date_from)
        if parsed:
            tickets = tickets.filter(created_at__date__gte=parsed)
    if date_to and not search:
        parsed = parse_date(date_to)
        if parsed:
            tickets = tickets.filter(created_at__date__lte=parsed)
    if not any([status, search, date_from, date_to]):
        today = timezone.localdate()
        tickets = tickets.filter(created_at__date=today)
        date_from = date_to = today.isoformat()

    filters_applied = any([status, search, date_from, date_to])
    tickets = tickets.order_by("-created_at")
    page_obj = None
    page_query = ""
    if filters_applied:
        paginator = Paginator(tickets, 10)
        page_obj = paginator.get_page(request.GET.get("page"))
        tickets = page_obj.object_list
        page_query_params = request.GET.copy()
        page_query_params.pop("page", None)
        page_query = page_query_params.urlencode()

    replacements = [{"ticket": ticket, "replacement": _get_replacement(ticket)} for ticket in tickets]

    return render(
        request,
        "panel/replacements.html",
        {
            "replacements": replacements,
            "page_title": "Replacement",
            "page_obj": page_obj,
            "page_query": page_query,
            "active_saved_view": active_saved_view,
            "selected_view_id": selected_view_id,
            "visible_columns": visible_columns,
            "empty_colspan": len(visible_columns) + 1,
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
    # Calculate today's date and count of reports for today (unfiltered)
    today = timezone.localdate()
    today_reports_count = Report.objects.filter(created_at__date=today).count()

    saved_views = _get_saved_views_for_page(request.user, SavedViewPageType.REPORTS)
    selected_view_id = (request.GET.get("view") or "").strip()
    active_saved_view = None
    if selected_view_id.isdigit():
        active_saved_view = saved_views.filter(id=int(selected_view_id)).first()
    elif not any(key in request.GET for key in ("service_type", "status", "engineer", "search", "date_from", "date_to", "columns")):
        active_saved_view = saved_views.filter(is_default=True).first()
        if active_saved_view:
            selected_view_id = str(active_saved_view.id)

    initial_filters = {key: "" for key in REPORT_FILTER_KEYS}
    visible_columns = list(DEFAULT_REPORT_COLUMNS)
    if active_saved_view:
        initial_filters.update(active_saved_view.filters or {})
        visible_columns = _normalize_columns(SavedViewPageType.REPORTS, active_saved_view.columns or [])
    else:
        for key in REPORT_FILTER_KEYS:
            if key in request.GET:
                initial_filters[key] = request.GET.get(key, "").strip()
        if "columns" in request.GET:
            visible_columns = _normalize_columns(SavedViewPageType.REPORTS, request.GET.getlist("columns"))

    service_type = initial_filters["service_type"]
    engineer_id = initial_filters["engineer"]
    status = initial_filters["status"]
    search = initial_filters["search"]
    date_from = initial_filters["date_from"]
    date_to = initial_filters["date_to"]
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
    if search:
        # Escape special characters for literal search
        escaped_search = _escape_like_wildcards(search)
        service_reports = service_reports.filter(
            Q(ticket__ticket_id__icontains=escaped_search)
            | Q(ticket__customer__name__icontains=escaped_search)
            | Q(ticket__customer__contact_phone__icontains=escaped_search)
            | Q(ticket__issue__icontains=escaped_search)
            | Q(ticket__issue_notes__icontains=escaped_search)
        )
        replacement_reports = replacement_reports.filter(
            Q(ticket__ticket_id__icontains=escaped_search)
            | Q(ticket__customer__name__icontains=escaped_search)
            | Q(ticket__customer__contact_phone__icontains=escaped_search)
            | Q(ticket__issue__icontains=escaped_search)
            | Q(ticket__issue_notes__icontains=escaped_search)
        )
    if date_from and not search:
        parsed = parse_date(date_from)
        if parsed:
            service_reports = service_reports.filter(created_at__date__gte=parsed)
            replacement_reports = replacement_reports.filter(updated_at__date__gte=parsed)
    if date_to and not search:
        parsed = parse_date(date_to)
        if parsed:
            service_reports = service_reports.filter(created_at__date__lte=parsed)
            replacement_reports = replacement_reports.filter(updated_at__date__lte=parsed)
    # If no filters are applied, restrict to today's reports
    if not any([service_type, engineer_id, status, search, date_from, date_to]):
        today = timezone.localdate()
        service_reports = service_reports.filter(created_at__date=today)
        replacement_reports = replacement_reports.filter(updated_at__date=today)
        date_from = date_to = today.isoformat()

    report_rows = _build_report_rows(service_reports, replacement_reports)

    filters_applied = any([service_type, engineer_id, status, search, date_from, date_to])
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
            "Purchase Date",
            "New Fan Complaint",
            "Repeated Complaint Count",
            "Report Created",
            "Service Provider Code",
            "Serial Number",
            "Problem Identified",
            "Issue Notes",
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
            "active_saved_view": active_saved_view,
            "selected_view_id": selected_view_id,
            "visible_columns": visible_columns,
            "empty_colspan": len(visible_columns) + 1,
            "filters": {
                "service_type": service_type,
                "engineer": engineer_id,
                "status": status,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@login_required(login_url="/panel/login/")
def panel_report_detail(request, report_id):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    report = Report.objects.select_related(
        "ticket",
        "ticket__customer",
        "ticket__assigned_engineer",
        "ticket__assigned_engineer__user",
        "engineer",
        "engineer__user",
    ).get(id=report_id)
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
