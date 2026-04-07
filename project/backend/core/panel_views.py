from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
import csv

from .models import AdminProfile, Customer, EngineerProfile, Report, Ticket, TicketStatus
from .panel_forms import PanelEngineerForm, PanelLoginForm, PanelTicketForm, PanelTicketStatusForm


def _require_staff(user):
    return user.is_authenticated and user.is_staff


def panel_login(request):
    if _require_staff(request.user):
        return redirect("panel:panel_index")
    form = PanelLoginForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        user = authenticate(username=form.cleaned_data["username"], password=form.cleaned_data["password"])
        if user and user.is_staff:
            login(request, user)
            return redirect("panel:panel_index")
        error = "Invalid credentials or not an admin."
    return render(request, "panel/login.html", {"form": form, "error": error, "page_title": "Login"})


def panel_logout(request):
    logout(request)
    return redirect("panel:panel_login")


@login_required(login_url="/panel/login/")
def panel_index(request):
    if not request.user.is_staff:
        return redirect("panel:panel_login")
    tickets = Ticket.objects.select_related("customer").all()
    today = timezone.localdate()
    tickets_today = tickets.filter(created_at__date=today)
    context = {
        "stats": {
            "total": tickets_today.count(),
            "open": tickets_today.filter(status=TicketStatus.OPEN).count(),
            "assigned": tickets_today.filter(status=TicketStatus.ASSIGNED).count(),
            "in_progress": tickets_today.filter(status=TicketStatus.IN_PROGRESS).count(),
            "completed": tickets_today.filter(status=TicketStatus.COMPLETED).count(),
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
    tickets = Ticket.objects.select_related("customer", "assigned_engineer", "assigned_engineer__user").all()
    status = request.GET.get("status", "").strip()
    engineer_id = request.GET.get("engineer", "").strip()
    customer_id = request.GET.get("customer", "").strip()
    search = request.GET.get("search", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if status:
        tickets = tickets.filter(status=status)
    if engineer_id:
        tickets = tickets.filter(assigned_engineer_id=engineer_id)
    if customer_id:
        tickets = tickets.filter(customer_id=customer_id)
    if search:
        tickets = tickets.filter(ticket_id__icontains=search)
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            tickets = tickets.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            tickets = tickets.filter(created_at__date__lte=parsed)
    if not any([status, engineer_id, customer_id, search, date_from, date_to]):
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
    ticket = Ticket.objects.select_related("customer", "assigned_engineer").get(id=ticket_id)
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
        form.save()
        return redirect("panel:panel_tickets")
    return render(request, "panel/ticket_form.html", {"form": form, "page_title": "Create Ticket"})


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
    reports = Report.objects.select_related("ticket", "engineer", "engineer__user", "ticket__customer").all()
    engineer_id = request.GET.get("engineer", "").strip()
    status = request.GET.get("status", "").strip()
    ticket_search = request.GET.get("ticket", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if engineer_id:
        reports = reports.filter(engineer_id=engineer_id)
    if status:
        reports = reports.filter(ticket__status=status)
    if ticket_search:
        reports = reports.filter(ticket__ticket_id__icontains=ticket_search)
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            reports = reports.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            reports = reports.filter(created_at__date__lte=parsed)
    if not any([engineer_id, status, ticket_search, date_from, date_to]):
        today = timezone.localdate()
        reports = reports.filter(created_at__date=today)
        date_from = date_to = today.isoformat()

    reports = reports.order_by("-created_at")

    filters_applied = any([engineer_id, status, ticket_search, date_from, date_to])
    if request.GET.get("export") == "csv" and filters_applied:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="service_reports.csv"'
        writer = csv.writer(response)
        writer.writerow([
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
            "Number Of Fans",
            "Serial Number",
            "Problem Identified",
            "Action Taken",
            "PCB Board Number",
            "Comments",
            "Charges Collected",
            "KMs Driven",
            "Customer Polite",
            "Difficult To Attend",
        ])
        for report in reports:
            ticket = report.ticket
            engineer_user = report.engineer.user if report.engineer else None
            customer = ticket.customer if ticket else None
            writer.writerow([
                ticket.ticket_id if ticket else "",
                engineer_user.username if engineer_user else "",
                customer.name if customer else "",
                ticket.location if ticket else "",
                ticket.status if ticket else "",
                ticket.created_at if ticket else "",
                ticket.started_at if ticket else "",
                ticket.completed_at if ticket else "",
                report.created_at,
                report.service_provider_code,
                report.number_of_fans,
                report.serial_number,
                report.problem_identified,
                report.action_taken,
                report.pcb_board_number,
                report.comments,
                report.charges_collected,
                report.kms_driven,
                "Yes" if report.is_customer_polite else "No",
                "Yes" if report.difficult_to_attend else "No",
            ])
        return response

    engineers = EngineerProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "panel/reports.html",
        {
            "reports": reports,
            "page_title": "Reports",
            "engineers": engineers,
            "filters": {
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
