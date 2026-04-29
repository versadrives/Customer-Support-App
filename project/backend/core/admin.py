from django import forms
from django.contrib import admin, messages
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ValidationError
from django.urls import path, reverse
import csv

from .admin_site import admin_site
from .models import AdminProfile, Customer, EngineerProfile, IssueOption, Item, Replacement, ReplacementLineItem, Report, Ticket, TicketServiceType


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class AdminPasswordResetForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    superadmin_password = forms.CharField(widget=forms.PasswordInput, label="Your Superadmin Password")

    def __init__(self, *args, **kwargs):
        self.target_user = kwargs.pop("target_user", None)
        self.superadmin_user = kwargs.pop("superadmin_user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        new_pass = cleaned_data.get("new_password", "")
        confirm_pass = cleaned_data.get("confirm_password", "")
        superadmin_pass = cleaned_data.get("superadmin_password", "")

        if not self.superadmin_user.check_password(superadmin_pass):
            raise forms.ValidationError("Superadmin password is incorrect.")

        if new_pass != confirm_pass:
            raise forms.ValidationError("New passwords do not match.")

        if self.target_user:
            user = User(username=self.target_user.username)
            try:
                password_validation.validate_password(new_pass, user=user)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)

        return cleaned_data

    def save(self):
        self.target_user.set_password(self.cleaned_data["new_password"])
        self.target_user.save()


def _is_reset_locked_out(request, profile_type, profile_id):
    from django.core.cache import cache
    from django.utils import timezone
    key = f"pwd_reset_fail:{profile_type}:{profile_id}:{_get_client_ip(request)}"
    locked_until = cache.get(key)
    if locked_until:
        seconds = max(1, int((locked_until - timezone.now()).total_seconds()))
        minutes = (seconds + 59) // 60
        messages.error(request, f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.")
        return True
    return False


def _record_reset_failure(request, profile_type, profile_id):
    from django.core.cache import cache
    from django.utils import timezone
    from datetime import timedelta
    key = f"pwd_reset_fail:{profile_type}:{profile_id}:{_get_client_ip(request)}"
    attempts = cache.get(key.replace("pwd_reset_fail:", "pwd_reset_attempt:"), 0) + 1
    cache.set(key.replace("pwd_reset_fail:", "pwd_reset_attempt:"), attempts, 900)
    if attempts >= 3:
        cache.set(key, timezone.now() + timedelta(minutes=5), 300)
        return True
    return False


def _clear_reset_failures(request, profile_type, profile_id):
    from django.core.cache import cache
    ip = _get_client_ip(request)
    cache.delete(f"pwd_reset_fail:{profile_type}:{profile_id}:{ip}")
    cache.delete(f"pwd_reset_attempt:{profile_type}:{profile_id}:{ip}")


def admin_password_reset(request, profile_type, profile_id):
    if not request.user.is_superuser:
        messages.error(request, "Only superadmins can reset passwords.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

    if request.method == "POST" and _is_reset_locked_out(request, profile_type, profile_id):
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

    if profile_type == "engineer":
        profile = get_object_or_404(EngineerProfile, id=profile_id)
        target_user = profile.user
        profile_name = profile.user.get_full_name() or profile.user.username
        change_list_url = reverse("admin:core_engineerprofile_changelist")
    elif profile_type == "admin":
        profile = get_object_or_404(AdminProfile, id=profile_id)
        target_user = profile.user
        profile_name = profile.user.get_full_name() or profile.user.username
        change_list_url = reverse("admin:core_adminprofile_changelist")
    else:
        messages.error(request, "Invalid profile type.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

    form = AdminPasswordResetForm(request.POST or None, target_user=target_user, superadmin_user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()
        _clear_reset_failures(request, profile_type, profile_id)
        messages.success(request, f"Password for {profile_name} has been reset.")
        return HttpResponseRedirect(change_list_url)

    if request.method == "POST" and form.errors:
        _record_reset_failure(request, profile_type, profile_id)

    context = {
        "form": form,
        "profile_name": profile_name,
        "profile_type": profile_type,
        "profile_id": profile_id,
        "change_list_url": change_list_url,
        "title": f"Reset Password — {profile_name}",
    }
    return render(request, "admin/password_reset.html", context)


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
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
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

    def clean_password(self):
        password = self.cleaned_data['password']
        username = self.cleaned_data.get('username', '')
        user = User(
            username=username,
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            email=self.cleaned_data.get('email', ''),
        )
        password_validation.validate_password(password, user=user)
        return password

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
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
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

    def clean_password(self):
        password = self.cleaned_data['password']
        username = self.cleaned_data.get('username', '')
        user = User(
            username=username,
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            email=self.cleaned_data.get('email', ''),
        )
        password_validation.validate_password(password, user=user)
        return password

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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("password-reset/admin/<int:profile_id>/", self.admin_site.admin_view(self.password_reset_view), name="core_adminprofile_password_reset"),
        ]
        return custom + urls

    def password_reset_view(self, request, profile_id):
        return admin_password_reset(request, "admin", profile_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_reset_password'] = request.user.is_superuser
        return super().changeform_view(request, object_id, form_url, extra_context)

    def submit_row(self, context, context_variable_name='change'):
        ctx = super().submit_row(context, context_variable_name)
        show_reset = context.get('show_reset_password', False)
        original = context.get('original')
        if show_reset and original:
            profile_id = original.id
            ctx['reset_password_url'] = f"/admin/core/adminprofile/password-reset/admin/{profile_id}/"
        return ctx


class EngineerProfileAdmin(admin.ModelAdmin):
    form = EngineerProfileForm
    list_display = ('id', 'user', 'phone', 'active')
    search_fields = ('user__username', 'phone')
    list_filter = ('active',)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("password-reset/engineer/<int:profile_id>/", self.admin_site.admin_view(self.password_reset_view), name="core_engineerprofile_password_reset"),
        ]
        return custom + urls

    def password_reset_view(self, request, profile_id):
        return admin_password_reset(request, "engineer", profile_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_reset_password'] = request.user.is_superuser
        return super().changeform_view(request, object_id, form_url, extra_context)

    def submit_row(self, context, context_variable_name='change'):
        ctx = super().submit_row(context, context_variable_name)
        show_reset = context.get('show_reset_password', False)
        original = context.get('original')
        if show_reset and original:
            profile_id = original.id
            ctx['reset_password_url'] = f"/admin/core/engineerprofile/password-reset/engineer/{profile_id}/"
        return ctx


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
        if self.cleaned_data.get('service_type') == TicketServiceType.REPLACEMENT:
            self.instance.assigned_engineer = None
        return super().save(commit=commit)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('service_type') == TicketServiceType.REPLACEMENT and cleaned.get('assigned_engineer'):
            raise ValidationError('Replacement tickets cannot be assigned to an engineer.')
        return cleaned


class TicketAdmin(admin.ModelAdmin):
    form = TicketAdminForm
    list_display = ('ticket_id', 'customer', 'service_type', 'model', 'serial_number', 'mfg_date', 'status', 'assigned_engineer', 'created_by', 'created_at')
    search_fields = ('ticket_id', 'customer__name', 'assigned_engineer__user__username')
    list_filter = ('service_type', 'status', 'assigned_engineer', 'customer', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'qr_code')
    fields = (
        'ticket_id',
        'customer_name',
        'customer_phone',
        'customer_address',
        'location',
        'issue',
        'service_type',
        'model',
        'serial_number',
        'mfg_date',
        'status',
        'assigned_engineer',
    )


class IssueOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    search_fields = ('name',)
    list_filter = ('active',)


class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'active', 'created_at')
    search_fields = ('name',)
    list_filter = ('active',)


class ReplacementLineItemInline(admin.TabularInline):
    model = ReplacementLineItem
    extra = 0
    fields = ('sort_order', 'item_name', 'serial_number', 'quantity', 'item_description')


class ReplacementAdmin(admin.ModelAdmin):
    inlines = (ReplacementLineItemInline,)
    list_display = ('ticket', 'created_by', 'contact_name', 'contact_phone', 'items_summary', 'total_quantity', 'status', 'updated_at')
    search_fields = ('ticket__ticket_id', 'contact_name', 'contact_phone', 'organization_name', 'line_items__item_name')
    list_filter = ('status', 'currency', 'tax_mode', 'updated_at')


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
admin_site.register(IssueOption, IssueOptionAdmin)
admin_site.register(Item, ItemAdmin)
admin_site.register(Replacement, ReplacementAdmin)
admin_site.register(Report, ReportAdmin)
