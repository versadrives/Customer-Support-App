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
            "status",
            "assigned_engineer",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide "Assigned" from manual selection; it should be derived from assignment.
        filtered_choices = [
            choice for choice in self.fields["status"].choices if choice[0] != TicketStatus.ASSIGNED
        ]
        self.fields["status"].choices = filtered_choices
        self.fields["status"].widget.choices = filtered_choices

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
        # Auto-set to ASSIGNED if an engineer is selected and status is still OPEN.
        if self.instance.assigned_engineer and self.instance.status == TicketStatus.OPEN:
            self.instance.status = TicketStatus.ASSIGNED
        return super().save(commit=commit)


class PanelTicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("status", "assigned_engineer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide "Assigned" from manual selection; it should be derived from assignment.
        filtered_choices = [
            choice for choice in self.fields["status"].choices if choice[0] != TicketStatus.ASSIGNED
        ]
        self.fields["status"].choices = filtered_choices
        self.fields["status"].widget.choices = filtered_choices

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
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False)
    active = forms.BooleanField(required=False, initial=True)

    def save(self):
        first_name = _capfirst(self.cleaned_data.get('first_name', ''))
        last_name = _capfirst(self.cleaned_data.get('last_name', ''))
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
            email=self.cleaned_data.get("email", ""),
        )
        profile = EngineerProfile.objects.create(
            user=user,
            phone=self.cleaned_data.get("phone", ""),
            active=self.cleaned_data.get("active", True),
        )
        return profile
