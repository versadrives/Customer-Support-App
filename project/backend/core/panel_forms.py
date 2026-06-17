from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Customer, EngineerProfile, IssueOption, Item, Replacement, ReplacementLineItem, Ticket, TicketProduct, TicketServiceType, TicketStatus

TICKET_CLOSED_STATUSES = (
    TicketStatus.COMPLETED,
    TicketStatus.CANCELLED,
    TicketStatus.DUPLICATE,
    TicketStatus.CUSTOMER_SOLVED,
)


def format_ticket_products(product_rows):
    return ", ".join(
        f"{row.item.name} x {row.quantity}"
        for row in product_rows
    )


def parse_ticket_product_rows(data):
    product_names = data.getlist("product_item")
    quantities = data.getlist("product_quantity")
    serial_numbers = data.getlist("product_serial_number")
    rows_by_name = {}

    for index, raw_name in enumerate(product_names):
        name = (raw_name or "").strip()
        raw_quantity = quantities[index] if index < len(quantities) else ""
        raw_serial = serial_numbers[index] if index < len(serial_numbers) else ""
        if not name and not raw_quantity:
            continue
        if not name:
            raise ValidationError("Select a product for every product row.")
        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            raise ValidationError("Enter a valid quantity for every product.")
        if quantity < 1:
            raise ValidationError("Product quantity must be at least 1.")
        if name not in rows_by_name:
            rows_by_name[name] = {"quantity": 0, "serial_number": ""}
        # Sum quantities, keep the first serial number if multiple entries for same product
        rows_by_name[name]["quantity"] += quantity
        if not rows_by_name[name]["serial_number"] and raw_serial.strip():
            rows_by_name[name]["serial_number"] = raw_serial.strip()

    if not rows_by_name:
        raise ValidationError("Add at least one product.")

    items_by_name = Item.objects.filter(active=True, name__in=rows_by_name.keys()).in_bulk(field_name="name")
    missing = [name for name in rows_by_name if name not in items_by_name]
    if missing:
        raise ValidationError(f"Unknown product: {', '.join(missing)}.")

    return [
        {
            "item": items_by_name[name],
            "quantity": info["quantity"],
            "serial_number": info["serial_number"]
        }
        for name, info in rows_by_name.items()
    ]


def save_ticket_product_rows(ticket, product_rows):
    TicketProduct.objects.filter(ticket=ticket).delete()
    ticket_products = [
        TicketProduct(ticket=ticket, item=row["item"], quantity=row["quantity"], serial_number=row.get("serial_number", ""), sort_order=index)
        for index, row in enumerate(product_rows)
    ]
    TicketProduct.objects.bulk_create(ticket_products)
    ticket.model = format_ticket_products(ticket_products)
    ticket.save(update_fields=["model"])


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
    issue_notes = forms.CharField(label="Notes", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    issue_custom = forms.CharField(label="Other issue", required=False)
    new_fan_complaint = forms.ChoiceField(
        label="New fan complaint",
        required=True,
        choices=(("yes", "Yes"), ("no", "No")),
    )
    repeated_complaint_count = forms.IntegerField(label="Repeated complaint", required=False, min_value=1)

    class Meta:
        model = Ticket
        fields = (
            "location",
            "service_type",
            "model",
            "mfg_date",
            "purchase_date",
            "assigned_engineer",
        )
        widgets = {
            "mfg_date": forms.DateInput(attrs={"type": "date"}),
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_engineer"].queryset = EngineerProfile.objects.select_related("user").filter(active=True).order_by("user__username")
        self.fields["assigned_engineer"].required = False
        if self.instance and self.instance.pk:
            self.fields["new_fan_complaint"].initial = "yes" if self.instance.new_fan_complaint else "no"
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
        new_fan_complaint = cleaned_data.get("new_fan_complaint")

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

        if service_type == TicketServiceType.REPLACEMENT and assigned_engineer:
            self.add_error("assigned_engineer", "Replacement tickets cannot be assigned to an engineer.")

        if new_fan_complaint == "yes":
            cleaned_data["repeated_complaint_count"] = None

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
        self.instance.issue_notes = _capfirst(self.cleaned_data.get("issue_notes", ""))
        self.instance.purchase_date = self.cleaned_data.get("purchase_date")
        self.instance.new_fan_complaint = self.cleaned_data.get("new_fan_complaint") == "yes"
        self.instance.repeated_complaint_count = None if self.instance.new_fan_complaint else self.cleaned_data.get("repeated_complaint_count")
        self.instance.service_type = self.cleaned_data.get("service_type")
        if self.instance.service_type == TicketServiceType.REPLACEMENT:
            self.instance.assigned_engineer = None
        # Keep status in sync with assignment on create.
        if self.instance.assigned_engineer:
            self.instance.status = TicketStatus.ASSIGNED
        else:
            self.instance.status = TicketStatus.OPEN
        return super().save(commit=commit)

    def save_product_serial_numbers(self):
        """Save serial numbers for each product."""
        # Extract product serial numbers from form data
        product_serials = self.extract_product_serials(self.data if self.is_bound else {})

        # Update each product's serial number
        for product in self.instance.product_rows.all():
            # For existing tickets, try to match by item name
            # For new tickets, we'll match by position in the posted data
            serial_number = ""
            if self.is_bound and self.instance.pk:
                # Existing ticket - match by item name
                product_names = self.data.getlist("product_item")
                posted_serials = self.data.getlist("product_serial_number")
                for index, name in enumerate(product_names):
                    if index < len(posted_serials) and name.strip() == product.item.name:
                        serial_number = posted_serials[index].strip()
                        break
            else:
                # New ticket or when we can't match by name, use positional matching
                # This is less reliable but works for simple cases
                product_names = self.data.getlist("product_item")
                posted_serials = self.data.getlist("product_serial_number")
                # Find the position of this product in the list
                try:
                    product_names_list = list(self.instance.product_rows.values_list('item__name', flat=True))
                    index = product_names_list.index(product.item.name)
                    if index < len(posted_serials):
                        serial_number = posted_serials[index].strip()
                except (ValueError, IndexError):
                    # If we can't find it, leave serial_number empty
                    pass

            if product.serial_number != serial_number:
                product.serial_number = serial_number
                product.save(update_fields=["serial_number"])


class PanelTicketStatusForm(forms.ModelForm):
    report_problem_identified = forms.CharField(label="Problem identified", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    report_action_taken = forms.CharField(label="Action taken", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    report_pcb_board_number = forms.CharField(label="PCB board number", required=False)
    report_comments = forms.CharField(label="Comments", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    report_charges_collected = forms.DecimalField(label="Charges collected", required=False, min_value=0, decimal_places=2, max_digits=10)
    report_kms_driven = forms.IntegerField(label="KM's driven", required=False, min_value=0)
    report_is_customer_polite = forms.BooleanField(label="Customer polite", required=False)
    report_difficult_to_attend = forms.BooleanField(label="Difficult to attend", required=False)
    serial_number = forms.CharField(label="Serial Number", required=False)

    class Meta:
        model = Ticket
        fields = (
            "assigned_engineer",
            "status",
            "serial_number",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_engineer"].queryset = EngineerProfile.objects.select_related("user").filter(active=True).order_by("user__username")
        self.fields["assigned_engineer"].required = False
        # Set initial values for report fields from existing report
        try:
            report = self.instance.report
        except Exception:
            report = None
        if report:
            self.fields["report_problem_identified"].initial = report.problem_identified
            self.fields["report_action_taken"].initial = report.action_taken
            self.fields["report_pcb_board_number"].initial = report.pcb_board_number
            self.fields["report_comments"].initial = report.comments
            self.fields["report_charges_collected"].initial = report.charges_collected
            self.fields["report_kms_driven"].initial = report.kms_driven
            self.fields["report_is_customer_polite"].initial = report.is_customer_polite
            self.fields["report_difficult_to_attend"].initial = report.difficult_to_attend
        # Set initial serial_number from instance
        initial_serial = getattr(self.instance, "serial_number", "")
        if not initial_serial and self.instance and self.instance.product_rows.count() == 1:
            initial_serial = self.instance.product_rows.first().serial_number
        self.fields["serial_number"].initial = initial_serial or ""

    def clean(self):
        cleaned_data = super().clean()
        # Get values from cleaned_data or instance if not in cleaned_data
        service_type = cleaned_data.get("service_type") or getattr(self.instance, "service_type", None)
        status = cleaned_data.get("status") or getattr(self.instance, "status", None)
        assigned_engineer = cleaned_data.get("assigned_engineer") or getattr(self.instance, "assigned_engineer", None)
        serial_number = (cleaned_data.get("serial_number") or getattr(self.instance, "serial_number", "") or "").strip()
        report_problem_identified = (cleaned_data.get("report_problem_identified") or "").strip()

        # Import here to avoid circular imports
        from .models import TicketServiceType, TicketStatus

        if service_type == TicketServiceType.REPLACEMENT and assigned_engineer:
            self.add_error("assigned_engineer", "Replacement tickets cannot be assigned to an engineer.")
        if status in (TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS) and not assigned_engineer and service_type != TicketServiceType.REPLACEMENT:
            self.add_error("assigned_engineer", "Assign an engineer before using this status.")
        if status == TicketStatus.COMPLETED and service_type != TicketServiceType.REPLACEMENT:
            product_rows = self.instance.product_rows.all()
            if not product_rows.exists():
                if not serial_number:
                    self.add_error("serial_number", "Serial number is required to complete a ticket.")
            else:
                posted_serials = self.data.getlist("product_serial_number")
                if not posted_serials or any(not s.strip() for s in posted_serials):
                    self.add_error(None, "All product serial numbers are required to complete a ticket.")
            if not report_problem_identified:
                self.add_error("report_problem_identified", "Problem identified is required to complete a ticket.")
        return cleaned_data

    def save(self, commit=True):
        # Get the instance
        instance = super().save(commit=False)

        # Import here to avoid circular imports
        from .models import TicketServiceType, TicketStatus
        from django.utils import timezone

        # Handle service_type == REPLACEMENT logic
        if instance.service_type == TicketServiceType.REPLACEMENT:
            if instance.assigned_engineer:
                self.add_error("assigned_engineer", "Replacement tickets cannot be assigned to an engineer.")
                # Don't proceed with saving if there's an error
                if commit:
                    return None
                else:
                    return instance
            # If it's a replacement ticket and status is ASSIGNED or IN_PROGRESS, set to OPEN
            if instance.status in (TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS):
                instance.status = TicketStatus.OPEN

        # Set timestamp fields based on status changes
        # assigned_at: set when status changes to ASSIGNED and not already set
        if instance.status == TicketStatus.ASSIGNED and not instance.assigned_at:
            instance.assigned_at = timezone.now()
        # started_at: set when status changes to IN_PROGRESS and not already set
        if instance.status == TicketStatus.IN_PROGRESS and not instance.started_at:
            instance.started_at = timezone.now()
        # completed_at: set when status changes to a closed status and not already set
        if instance.status in TICKET_CLOSED_STATUSES and not instance.completed_at:
            instance.completed_at = timezone.now()

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
        default_contact_name = (customer.contact_name or customer.name) if customer else ""
        default_contact_phone = customer.contact_phone if customer else ""
        default_address = customer.address if customer else ""
        default_client_ref_number = self.ticket.ticket_id

        if not replacement.pk:
            self.initial["contact_name"] = default_contact_name
            self.initial["contact_phone"] = default_contact_phone
            self.initial["billing_address"] = default_address
            self.initial["client_ref_number"] = default_client_ref_number
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

        if replacement.pk:
            self.initial["contact_name"] = replacement.contact_name or default_contact_name
            self.initial["contact_phone"] = replacement.contact_phone or default_contact_phone
            self.initial["billing_address"] = replacement.billing_address or default_address
            self.initial["client_ref_number"] = replacement.client_ref_number or default_client_ref_number

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
        instance.ref_number = self.ticket.ticket_id
        if not instance.organization_name:
            customer = getattr(self.ticket, "customer", None)
            instance.organization_name = _capfirst(customer.name) if customer and customer.name else ""
        instance.client_ref_number = _capfirst(self.cleaned_data.get("client_ref_number", "")) or self.ticket.ticket_id
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
