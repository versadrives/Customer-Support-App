from django.urls import path

from . import panel_views

urlpatterns = [
    path("login/", panel_views.panel_login, name="panel_login"),
    path("logout/", panel_views.panel_logout, name="panel_logout"),
    path("", panel_views.panel_index, name="panel_index"),
    path("tickets/", panel_views.panel_tickets, name="panel_tickets"),
    path("tickets/new/", panel_views.panel_ticket_create, name="panel_ticket_create"),
    path("tickets/issues/add/", panel_views.panel_issue_option_create, name="panel_issue_option_create"),
    path("tickets/issues/remove/", panel_views.panel_issue_option_delete, name="panel_issue_option_delete"),
    path("tickets/items/add/", panel_views.panel_item_create, name="panel_item_create"),
    path("tickets/items/remove/", panel_views.panel_item_delete, name="panel_item_delete"),
    path("tickets/<int:ticket_id>/edit/", panel_views.panel_ticket_edit, name="panel_ticket_edit"),
    path("engineers/", panel_views.panel_engineers, name="panel_engineers"),
    path("engineers/new/", panel_views.panel_engineer_create, name="panel_engineer_create"),
    path("replacements/", panel_views.panel_replacements, name="panel_replacements"),
    path("replacements/<int:ticket_id>/", panel_views.panel_replacement_edit, name="panel_replacement_edit"),
    path("replacements/<int:ticket_id>/invoice/", panel_views.panel_replacement_invoice, name="panel_replacement_invoice"),
    path("reports/", panel_views.panel_reports, name="panel_reports"),
    path("reports/<int:report_id>/", panel_views.panel_report_detail, name="panel_report_detail"),
    path("reports/replacement/<int:ticket_id>/", panel_views.panel_replacement_report_detail, name="panel_replacement_report_detail"),
    path("admins/", panel_views.panel_admins, name="panel_admins"),
]

app_name = 'panel'
