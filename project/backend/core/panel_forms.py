from django import forms
from django.contrib.auth.models import User

from .models import Customer, EngineerProfile, IssueOption, Replacement, Ticket, TicketServiceType, TicketStatus


class PanelLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

def _capfirst(value: str) -> str:
    if value is None:
        return value
    value = value.strip()
    if not value:
        return value
    return value[0].upper() + value[1:]


class PanelTicketForm(forms.ModelForm):
    customer_name = forms.CharField(label="Customer name")
    customer_phone = forms.CharField(label="Phone number")
    customer_address = forms.CharField(label="Address")
    issue_choice = forms.ChoiceField(label="Issue", required=False)
    issue_custom = forms.CharField(label="Other issue", required=False)

    class Meta:
        model = Ticket
        fields = (
            "ticket_id",
            "location",
            "service_type",
            "model",
            "serial_number",
            "mfg_date",
            "assigned_engineer",
        )
        widgets = {
            "mfg_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_engineer"].queryset = EngineerProfile.objects.select_related("user").filter(active=True).order_by("user__username")
        self.fields["assigned_engineer"].required = False
        issue_choices = [("", "Select issue")]
        issue_choices.extend((option.name, option.name) for option in IssueOption.objects.filter(active=True))
        issue_choices.append(("__other__", "Other"))
        self.fields["issue_choice"].choices = issue_choices

    def clean(self):
        cleaned_data = super().clean()
        issue_choice = (cleaned_data.get("issue_choice") or "").strip()
        issue_custom = _capfirst(cleaned_data.get("issue_custom", ""))
        service_type = cleaned_data.get("service_type")
        assigned_engineer = cleaned_data.get("assigned_engineer")

        if issue_choice == "__other__":
            if not issue_custom:
                self.add_error("issue_custom", "Enter the issue when Other is selected.")
            cleaned_data["resolved_issue"] = issue_custom
        elif issue_choice:
            cleaned_data["resolved_issue"] = issue_choice
        elif issue_custom:
            cleaned_data["resolved_issue"] = issue_custom
        else:
            self.add_error("issue_choice", "Select an issue or enter a custom one.")

        if service_type == TicketServiceType.REPLACEMENT and assigned_engineer:
            self.add_error("assigned_engineer", "Replacement tickets cannot be assigned to an engineer.")

        return cleaned_data

    def save(self, commit=True):
        customer_name = _capfirst(self.cleaned_data["customer_name"])
        customer_phone = self.cleaned_data["customer_phone"].strip()
        customer_address = _capfirst(self.cleaned_data["customer_address"])
        customer, _ = Customer.objects.get_or_create(name=customer_name)
        if customer_phone:
            customer.contact_phone = customer_phone
        if customer_address:
            customer.address = customer_address
        customer.save()
        self.instance.customer = customer
        self.instance.location = _capfirst(self.cleaned_data.get("location", ""))
        self.instance.issue = self.cleaned_data.get("resolved_issue", "")
        self.instance.model = _capfirst(self.cleaned_data.get("model", ""))
        self.instance.serial_number = _capfirst(self.cleaned_data.get("serial_number", ""))
        self.instance.ticket_id = _capfirst(self.cleaned_data.get("ticket_id", ""))
        self.instance.service_type = self.cleaned_data.get("service_type")
        if self.instance.service_type == TicketServiceType.REPLACEMENT:
            self.instance.assigned_engineer = None
        # Keep status in sync with assignment on create.
        if self.instance.assigned_engineer:
            self.instance.status = TicketStatus.ASSIGNED
        else:
            self.instance.status = TicketStatus.OPEN
        return super().save(commit=commit)


class PanelTicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("service_type", "assigned_engineer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_engineer"].queryset = EngineerProfile.objects.select_related("user").filter(active=True).order_by("user__username")

    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get("service_type")
        assigned_engineer = cleaned_data.get("assigned_engineer")
        if service_type == TicketServiceType.REPLACEMENT and assigned_engineer:
            self.add_error("assigned_engineer", "Replacement tickets cannot be assigned to an engineer.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.service_type == TicketServiceType.REPLACEMENT:
            instance.assigned_engineer = None
        # Auto-set to ASSIGNED if an engineer is selected and status is still OPEN.
        if instance.assigned_engineer and instance.status == TicketStatus.OPEN:
            instance.status = TicketStatus.ASSIGNED
        elif not instance.assigned_engineer and instance.status == TicketStatus.ASSIGNED:
            instance.status = TicketStatus.OPEN
        if commit:
            instance.save()
        return instance


class PanelReplacementForm(forms.ModelForm):
    class Meta:
        model = Replacement
        fields = (
            "subject",
            "ref_date",
            "client_ref_date",
            "ref_number",
            "custom_challan_number",
            "client_ref_number",
            "organization_name",
            "contact_name",
            "contact_phone",
            "status",
            "category",
            "billing_city",
            "billing_state",
            "billing_country",
            "billing_address",
            "billing_postal_code",
            "item_name",
            "item_description",
            "quantity",
            "currency",
            "tax_mode",
        )
        widgets = {
            "ref_date": forms.DateInput(attrs={"type": "date"}),
            "client_ref_date": forms.DateInput(attrs={"type": "date"}),
            "billing_address": forms.Textarea(attrs={"rows": 4}),
            "item_description": forms.Textarea(attrs={"rows": 4}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        self.ticket = kwargs.pop("ticket")
        super().__init__(*args, **kwargs)
        replacement = self.instance
        customer = getattr(self.ticket, "customer", None)
        if not replacement.pk:
            self.fields["subject"].initial = f"Replacement - {self.ticket.ticket_id}"
            self.fields["organization_name"].initial = customer.name if customer else ""
            self.fields["contact_name"].initial = (customer.contact_name or customer.name) if customer else ""
            self.fields["contact_phone"].initial = customer.contact_phone if customer else ""
            self.fields["billing_address"].initial = customer.address if customer else ""
            self.fields["item_name"].initial = self.ticket.model
            self.fields["item_description"].initial = self.ticket.issue
            self.fields["ref_number"].initial = self.ticket.ticket_id

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.ticket = self.ticket
        instance.subject = _capfirst(self.cleaned_data.get("subject", ""))
        instance.organization_name = _capfirst(self.cleaned_data.get("organization_name", ""))
        instance.contact_name = _capfirst(self.cleaned_data.get("contact_name", ""))
        instance.category = _capfirst(self.cleaned_data.get("category", ""))
        instance.billing_city = _capfirst(self.cleaned_data.get("billing_city", ""))
        instance.billing_state = _capfirst(self.cleaned_data.get("billing_state", ""))
        instance.billing_country = _capfirst(self.cleaned_data.get("billing_country", ""))
        instance.billing_address = _capfirst(self.cleaned_data.get("billing_address", ""))
        instance.item_name = _capfirst(self.cleaned_data.get("item_name", ""))
        instance.item_description = _capfirst(self.cleaned_data.get("item_description", ""))
        if commit:
            instance.save()
        return instance


class PanelEngineerForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    name = forms.CharField(label="Name")
    phone = forms.CharField(required=False)

    def save(self):
        full_name = _capfirst(self.cleaned_data.get('name', ''))
        parts = full_name.split()
        first_name = parts[0] if parts else ''
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
            email="",
        )
        profile = EngineerProfile.objects.create(
            user=user,
            phone=self.cleaned_data.get("phone", ""),
            active=True,
        )
        return profile
