from django.urls import path

from . import panel_views

urlpatterns = [
    path("login/", panel_views.panel_login, name="panel_login"),
    path("logout/", panel_views.panel_logout, name="panel_logout"),
    path("", panel_views.panel_index, name="panel_index"),
    path("tickets/", panel_views.panel_tickets, name="panel_tickets"),
    path("tickets/new/", panel_views.panel_ticket_create, name="panel_ticket_create"),
    path("tickets/<int:ticket_id>/edit/", panel_views.panel_ticket_edit, name="panel_ticket_edit"),
    path("engineers/", panel_views.panel_engineers, name="panel_engineers"),
    path("engineers/new/", panel_views.panel_engineer_create, name="panel_engineer_create"),
    path("reports/", panel_views.panel_reports, name="panel_reports"),
    path("reports/<int:report_id>/", panel_views.panel_report_detail, name="panel_report_detail"),
    path("admins/", panel_views.panel_admins, name="panel_admins"),
]

app_name = 'panel'
