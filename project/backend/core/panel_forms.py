from django import forms
from django.contrib.auth.models import User

from .models import Customer, EngineerProfile, Ticket, TicketStatus


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

    class Meta:
        model = Ticket
        fields = (
            "ticket_id",
            "location",
            "issue",
            "model",
            "serial_number",
            "mfg_date",
            "assigned_engineer",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.instance.issue = _capfirst(self.cleaned_data.get("issue", ""))
        self.instance.model = _capfirst(self.cleaned_data.get("model", ""))
        self.instance.serial_number = _capfirst(self.cleaned_data.get("serial_number", ""))
        self.instance.ticket_id = _capfirst(self.cleaned_data.get("ticket_id", ""))
        # Keep status in sync with assignment on create.
        if self.instance.assigned_engineer:
            self.instance.status = TicketStatus.ASSIGNED
        else:
            self.instance.status = TicketStatus.OPEN
        return super().save(commit=commit)


class PanelTicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("assigned_engineer",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-set to ASSIGNED if an engineer is selected and status is still OPEN.
        if instance.assigned_engineer and instance.status == TicketStatus.OPEN:
            instance.status = TicketStatus.ASSIGNED
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
