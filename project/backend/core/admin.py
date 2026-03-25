from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.core.exceptions import ValidationError
import csv

from .admin_site import admin_site
from .models import AdminProfile, Customer, EngineerProfile, Report, Ticket


def export_reports_pdf(modeladmin, request, queryset):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    def _fmt_dt(value):
        if not value:
            return '-'
        return value.strftime('%Y-%m-%d %H:%M')

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="service_reports.pdf"'
    p = canvas.Canvas(response, pagesize=letter)

    for report in queryset.select_related('ticket', 'engineer', 'engineer__user'):
        ticket = report.ticket
        engineer_user = report.engineer.user if report.engineer else None
        customer = ticket.customer if ticket else None
        y = 760
        p.setFont('Helvetica-Bold', 14)
        p.drawString(40, y, f"Service Report - {ticket.ticket_id if ticket else '-'}")
        y -= 24
        p.setFont('Helvetica', 11)
        lines = [
            f"Engineer: {engineer_user.username if engineer_user else '-'}",
            f"Customer: {customer.name if customer else '-'}",
            f"Location: {ticket.location if ticket else '-'}",
            f"Status: {ticket.status if ticket else '-'}",
            f"Ticket Created: {_fmt_dt(ticket.created_at if ticket else None)}",
            f"Ticket Started: {_fmt_dt(ticket.started_at if ticket else None)}",
            f"Ticket Completed: {_fmt_dt(ticket.completed_at if ticket else None)}",
            f"Log Date: {_fmt_dt(report.created_at)}",
            f"Service Provider Code: {report.service_provider_code}",
            f"Number Of Fans: {report.number_of_fans}",
            f"Serial Number: {report.serial_number}",
            f"Problem Identified: {report.problem_identified}",
            f"Action Taken: {report.action_taken}",
            f"PCB Board Number: {report.pcb_board_number}",
            f"Comments: {report.comments}",
            f"Charges Collected: {report.charges_collected}",
            f"KMs Driven: {report.kms_driven}",
            f"Customer Polite: {'Yes' if report.is_customer_polite else 'No'}",
            f"Difficult To Attend: {'Yes' if report.difficult_to_attend else 'No'}",
        ]
        for line in lines:
            if y < 60:
                p.showPage()
                y = 760
            p.drawString(40, y, line[:120])
            y -= 16
        p.showPage()

    p.save()
    return response


export_reports_pdf.short_description = 'Export selected reports as PDF'


def export_reports_csv(modeladmin, request, queryset):
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
    for report in queryset.select_related('ticket', 'engineer', 'engineer__user', 'ticket__customer'):
        ticket = report.ticket
        engineer_user = report.engineer.user if report.engineer else None
        customer = ticket.customer if ticket else None
        writer.writerow([
            ticket.ticket_id if ticket else '',
            engineer_user.username if engineer_user else '',
            customer.name if customer else '',
            ticket.location if ticket else '',
            ticket.status if ticket else '',
            ticket.created_at if ticket else '',
            ticket.started_at if ticket else '',
            ticket.completed_at if ticket else '',
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


export_reports_csv.short_description = 'Export selected reports as CSV'


class AdminProfileForm(forms.ModelForm):
    username = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = AdminProfile
        fields = ('username', 'password', 'first_name', 'last_name', 'email', 'active')

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        if not username:
            return cleaned
        user = User.objects.filter(username=username).first()
        if user and AdminProfile.objects.filter(user=user).exists():
            raise ValidationError('Admin profile with this user already exists.')
        return cleaned

    def save(self, commit=True):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        user = User.objects.filter(username=username).first()
        if user:
            if password:
                user.set_password(password)
            user.first_name = self.cleaned_data.get('first_name', user.first_name)
            user.last_name = self.cleaned_data.get('last_name', user.last_name)
            user.email = self.cleaned_data.get('email', user.email)
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                email=self.cleaned_data.get('email', ''),
            )
        user.is_staff = True
        user.save()
        self.instance.user = user
        return super().save(commit=commit)


class EngineerProfileForm(forms.ModelForm):
    username = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = EngineerProfile
        fields = ('username', 'password', 'first_name', 'last_name', 'email', 'phone', 'active')

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        if not username:
            return cleaned
        user = User.objects.filter(username=username).first()
        if user and EngineerProfile.objects.filter(user=user).exists():
            raise ValidationError('Engineer profile with this user already exists.')
        return cleaned

    def save(self, commit=True):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        user = User.objects.filter(username=username).first()
        if user:
            if password:
                user.set_password(password)
            user.first_name = self.cleaned_data.get('first_name', user.first_name)
            user.last_name = self.cleaned_data.get('last_name', user.last_name)
            user.email = self.cleaned_data.get('email', user.email)
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                email=self.cleaned_data.get('email', ''),
            )
        user.save()
        self.instance.user = user
        return super().save(commit=commit)


class AdminProfileAdmin(admin.ModelAdmin):
    form = AdminProfileForm
    list_display = ('id', 'user', 'active')
    search_fields = ('user__username',)
    list_filter = ('active',)


class EngineerProfileAdmin(admin.ModelAdmin):
    form = EngineerProfileForm
    list_display = ('id', 'user', 'phone', 'active')
    search_fields = ('user__username', 'phone')
    list_filter = ('active',)


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contact_name', 'contact_phone', 'active')
    search_fields = ('name', 'contact_name', 'contact_phone')
    list_filter = ('active',)


class TicketAdminForm(forms.ModelForm):
    customer_name = forms.CharField(label='Customer', required=False)
    customer_phone = forms.CharField(label='Phone number', required=False)
    customer_address = forms.CharField(label='Address', required=False)

    class Meta:
        model = Ticket
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.customer_id:
            self.fields['customer_name'].initial = self.instance.customer.name
            self.fields['customer_phone'].initial = self.instance.customer.contact_phone
            self.fields['customer_address'].initial = self.instance.customer.address

    def save(self, commit=True):
        customer_name = self.cleaned_data.get('customer_name', '').strip()
        customer_phone = self.cleaned_data.get('customer_phone', '').strip()
        customer_address = self.cleaned_data.get('customer_address', '').strip()
        if customer_name:
            customer, _ = Customer.objects.get_or_create(name=customer_name)
            if customer_phone:
                customer.contact_phone = customer_phone
            if customer_address:
                customer.address = customer_address
            customer.save()
            self.instance.customer = customer
        return super().save(commit=commit)


class TicketAdmin(admin.ModelAdmin):
    form = TicketAdminForm
    list_display = ('ticket_id', 'customer', 'model', 'serial_number', 'mfg_date', 'status', 'assigned_engineer', 'created_by', 'created_at')
    search_fields = ('ticket_id', 'customer__name', 'assigned_engineer__user__username')
    list_filter = ('status', 'assigned_engineer', 'customer', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'qr_code')
    fields = (
        'ticket_id',
        'customer_name',
        'customer_phone',
        'customer_address',
        'location',
        'issue',
        'model',
        'serial_number',
        'mfg_date',
        'status',
        'assigned_engineer',
    )


class ReportAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'engineer', 'ticket_created_at', 'ticket_started_at', 'ticket_completed_at')
    search_fields = ('ticket__ticket_id', 'engineer__user__username')
    list_filter = ('ticket__status', 'engineer', 'created_at', 'ticket__created_at')
    date_hierarchy = 'created_at'
    actions = [export_reports_pdf, export_reports_csv]

    def ticket_created_at(self, obj):
        return obj.ticket.created_at

    def ticket_started_at(self, obj):
        return obj.ticket.started_at

    def ticket_completed_at(self, obj):
        return obj.ticket.completed_at

    ticket_created_at.admin_order_field = 'ticket__created_at'
    ticket_started_at.admin_order_field = 'ticket__started_at'
    ticket_completed_at.admin_order_field = 'ticket__completed_at'


admin_site.register(AdminProfile, AdminProfileAdmin)
admin_site.register(EngineerProfile, EngineerProfileAdmin)
admin_site.register(Ticket, TicketAdmin)
admin_site.register(Report, ReportAdmin)
