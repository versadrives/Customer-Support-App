from django.contrib.admin import AdminSite
from django.urls import reverse
from django.shortcuts import redirect
from django.utils import timezone

from .models import Customer, EngineerProfile, Report, Ticket, TicketStatus


class SupportAdminSite(AdminSite):
    site_header = 'Admin'
    site_title = 'Admin'
    index_title = 'Operations Dashboard'

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        tickets = Ticket.objects.all()
        extra_context['stats'] = {
            'total': tickets.count(),
            'open': tickets.filter(status=TicketStatus.OPEN).count(),
            'assigned': tickets.filter(status=TicketStatus.ASSIGNED).count(),
            'in_progress': tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
            'completed': tickets.filter(status=TicketStatus.COMPLETED).count(),
            'engineers': EngineerProfile.objects.count(),
            'customers': Customer.objects.count(),
            'reports': Report.objects.count(),
        }
        extra_context['recent_tickets'] = tickets.select_related('customer').order_by('-created_at')[:5]
        extra_context['quick_links'] = [
            {'label': 'Create Ticket', 'url': reverse('admin:core_ticket_add')},
            {'label': 'Assign Tickets', 'url': reverse('admin:core_ticket_changelist')},
            {'label': 'Engineers', 'url': reverse('admin:core_engineerprofile_changelist')},
            {'label': 'Reports', 'url': reverse('admin:core_report_changelist')},
        ]
        extra_context['server_time'] = timezone.now()
        return super().index(request, extra_context=extra_context)

    def app_index(self, request, app_label, extra_context=None):
        return redirect(reverse(f'{self.name}:index'))


admin_site = SupportAdminSite(name='support_admin')
