from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Customer, EngineerProfile, IssueOption, Item, Replacement, ReplacementLineItem, Ticket, TicketServiceType, TicketStatus


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
    model_choice = forms.ChoiceField(label="Product", required=False)
    model_custom = forms.CharField(label="Other product", required=False)

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
        model_choices = [("", "Select product")]
        model_choices.extend((item.name, item.name) for item in Item.objects.filter(active=True))
        model_choices.append(("__other__", "Other"))
        self.fields["model_choice"].choices = model_choices

    def clean(self):
        cleaned_data = super().clean()
        issue_choice = (cleaned_data.get("issue_choice") or "").strip()
        issue_custom = _capfirst(cleaned_data.get("issue_custom", ""))
        model_choice = (cleaned_data.get("model_choice") or "").strip()
        model_custom = _capfirst(cleaned_data.get("model_custom", ""))
        service_type = cleaned_data.get("service_type")
        assigned_engineer = cleaned_data.get("assigned_engineer")

        if issue_choice == "__other__":
            if not issue_custom:
                self.add_error("issue_choice", "Add the issue using Add Issue.")
            cleaned_data["resolved_issue"] = issue_custom
        elif issue_choice:
            cleaned_data["resolved_issue"] = issue_choice
        elif issue_custom:
            cleaned_data["resolved_issue"] = issue_custom
        else:
            self.add_error("issue_choice", "Select an issue or enter a custom one.")

        if model_choice == "__other__":
            if not model_custom:
                self.add_error("model_choice", "Add the product using Add Product.")
            cleaned_data["resolved_model"] = model_custom
        elif model_choice:
            cleaned_data["resolved_model"] = model_choice
        elif model_custom:
            cleaned_data["resolved_model"] = model_custom
        else:
            self.add_error("model_choice", "Select a product or enter a custom one.")

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
        self.instance.model = self.cleaned_data.get("resolved_model", "")
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
    SPARE_PART_CHOICES = (
        "Full Product",
        "Motor",
        "PCB Board",
        "Blade Set",
        "Remote",
        "Accessories",
    )

    class Meta:
        model = Replacement
        fields = (
            "ref_date",
            "client_ref_date",
            "ref_number",
            "custom_challan_number",
            "client_ref_number",
            "contact_name",
            "contact_phone",
            "billing_city",
            "billing_state",
            "billing_country",
            "billing_address",
            "billing_postal_code",
        )
        widgets = {
            "ref_date": forms.DateInput(attrs={"type": "date"}),
            "client_ref_date": forms.DateInput(attrs={"type": "date"}),
            "billing_address": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop("created_by", None)
        self.ticket = kwargs.pop("ticket")
        super().__init__(*args, **kwargs)
        replacement = self.instance
        customer = getattr(self.ticket, "customer", None)
        if not replacement.pk:
            self.fields["contact_name"].initial = (customer.contact_name or customer.name) if customer else ""
            self.fields["contact_phone"].initial = customer.contact_phone if customer else ""
            self.fields["billing_address"].initial = customer.address if customer else ""
            self.fields["ref_number"].initial = self.ticket.ticket_id
            default_name = self.ticket.model or "Full Product"
            default_description = self.ticket.issue or ""
            self.line_item_rows = [
                {
                    "item_name": default_name,
                    "item_description": default_description,
                    "quantity": 1,
                    "serial_number": self.ticket.serial_number or "",
                }
            ]
        else:
            self.line_item_rows = [
                {
                    "item_name": line.item_name,
                    "item_description": line.item_description,
                    "quantity": line.quantity,
                    "serial_number": line.serial_number,
                }
                for line in replacement.line_items.all()
            ]
            if not self.line_item_rows:
                fallback_name = replacement.item_name or self.ticket.model or "Full Product"
                self.line_item_rows = [
                    {
                        "item_name": fallback_name,
                        "item_description": replacement.item_description or self.ticket.issue or "",
                        "quantity": replacement.quantity or 1,
                        "serial_number": self.ticket.serial_number or "",
                    }
                ]

        if self.is_bound:
            self.line_item_rows = self.extract_line_items(self.data)

        self.spare_part_choices = list(self.SPARE_PART_CHOICES)
        for row in self.line_item_rows:
            name = row.get("item_name", "")
            if name and name not in self.spare_part_choices:
                self.spare_part_choices.append(name)

    @staticmethod
    def extract_line_items(data):
        names = data.getlist("line_item_name")
        descriptions = data.getlist("line_item_description")
        quantities = data.getlist("line_item_quantity")
        serial_numbers = data.getlist("line_item_serial_number")
        row_count = max(len(names), len(descriptions), len(quantities), len(serial_numbers), 1)
        rows = []
        for index in range(row_count):
            rows.append(
                {
                    "item_name": (names[index] if index < len(names) else "").strip(),
                    "item_description": (descriptions[index] if index < len(descriptions) else "").strip(),
                    "quantity": (quantities[index] if index < len(quantities) else "").strip(),
                    "serial_number": (serial_numbers[index] if index < len(serial_numbers) else "").strip(),
                }
            )
        return rows

    def clean(self):
        cleaned_data = super().clean()
        cleaned_items = []
        has_line_item = False

        for index, row in enumerate(self.extract_line_items(self.data), start=1):
            name = _capfirst(row.get("item_name", ""))
            description = _capfirst(row.get("item_description", ""))
            quantity_raw = (row.get("quantity", "") or "").strip()
            serial_number = row.get("serial_number", "").strip()
            has_meaningful_value = any([name, description, serial_number]) or (quantity_raw not in ("", "1"))
            if not has_meaningful_value:
                continue

            has_line_item = True
            if not name:
                raise forms.ValidationError(f"Line item {index}: item name is required.")

            try:
                quantity = int(quantity_raw or 1)
            except (TypeError, ValueError):
                raise forms.ValidationError(f"Line item {index}: quantity must be a whole number.")

            if quantity < 1:
                raise forms.ValidationError(f"Line item {index}: quantity must be at least 1.")

            cleaned_items.append(
                {
                    "item_name": name,
                    "item_description": description,
                    "quantity": quantity,
                    "serial_number": serial_number,
                }
            )

        if not has_line_item:
            raise forms.ValidationError("Add at least one replacement item.")

        cleaned_data["line_items"] = cleaned_items
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.ticket = self.ticket
        if not instance.pk and self.created_by and not instance.created_by_id:
            instance.created_by = self.created_by
        if not instance.subject:
            instance.subject = f"Replacement - {self.ticket.ticket_id}"
        if not instance.organization_name:
            customer = getattr(self.ticket, "customer", None)
            instance.organization_name = _capfirst(customer.name) if customer and customer.name else ""
        instance.contact_name = _capfirst(self.cleaned_data.get("contact_name", ""))
        instance.contact_phone = self.cleaned_data.get("contact_phone", "").strip()
        instance.billing_city = _capfirst(self.cleaned_data.get("billing_city", ""))
        instance.billing_state = _capfirst(self.cleaned_data.get("billing_state", ""))
        instance.billing_country = _capfirst(self.cleaned_data.get("billing_country", ""))
        instance.billing_address = _capfirst(self.cleaned_data.get("billing_address", ""))
        line_items = self.cleaned_data.get("line_items", [])
        first_item = line_items[0] if line_items else {}
        instance.item_name = first_item.get("item_name", "")
        instance.item_description = first_item.get("item_description", "")
        instance.quantity = sum(item.get("quantity", 0) for item in line_items) or 1
        if commit:
            instance.save()
            instance.line_items.all().delete()
            ReplacementLineItem.objects.bulk_create(
                [
                    ReplacementLineItem(
                        replacement=instance,
                        sort_order=index,
                        **line_item,
                    )
                    for index, line_item in enumerate(line_items)
                ]
            )
        return instance


class PanelEngineerForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    name = forms.CharField(label="Name")
    phone = forms.CharField(required=False)

    def clean_password(self):
        password = self.cleaned_data["password"]
        username = self.cleaned_data.get("username", "")
        full_name = self.cleaned_data.get("name", "")
        user = User(username=username, first_name=full_name)
        try:
            password_validation.validate_password(password, user=user)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return password

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
