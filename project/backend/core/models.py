from django.conf import settings
from django.db import models


class AdminProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile')
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f'Admin: {self.user.username}'


class EngineerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='engineer_profile')
    phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)

    @property
    def display_name(self) -> str:
        name = self.user.get_full_name().strip()
        if name:
            return f'{name} - {self.user.username}'
        return self.user.username

    def __str__(self) -> str:
        return self.display_name


class Customer(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class TicketStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'


class TicketServiceType(models.TextChoices):
    ONSITE = 'ONSITE', 'Onsite'
    REPLACEMENT = 'REPLACEMENT', 'Replacement'


class IssueOption(models.Model):
    name = models.CharField(max_length=120, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name',)

    def __str__(self) -> str:
        return self.name


class Ticket(models.Model):
    ticket_id = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='tickets')
    location = models.CharField(max_length=120)
    issue = models.TextField()
    model = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    mfg_date = models.DateField(null=True, blank=True)
    service_type = models.CharField(max_length=20, choices=TicketServiceType.choices, default=TicketServiceType.ONSITE)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    assigned_engineer = models.ForeignKey(EngineerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.CharField(max_length=120, blank=True)

    def __str__(self) -> str:
        return self.ticket_id


class ReplacementStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    READY = 'READY', 'Ready'
    DISPATCHED = 'DISPATCHED', 'Dispatched'
    COMPLETED = 'COMPLETED', 'Completed'


class Replacement(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='replacement')
    subject = models.CharField(max_length=150, blank=True)
    ref_date = models.DateField(null=True, blank=True)
    client_ref_date = models.DateField(null=True, blank=True)
    ref_number = models.CharField(max_length=80, blank=True)
    custom_challan_number = models.CharField(max_length=80, blank=True)
    client_ref_number = models.CharField(max_length=80, blank=True)
    organization_name = models.CharField(max_length=120, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    category = models.CharField(max_length=120, blank=True)
    billing_city = models.CharField(max_length=120, blank=True)
    billing_state = models.CharField(max_length=120, blank=True)
    billing_country = models.CharField(max_length=120, blank=True)
    billing_address = models.TextField(blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    item_name = models.CharField(max_length=150, blank=True)
    item_description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    currency = models.CharField(max_length=40, default='India, Rupees')
    tax_mode = models.CharField(max_length=40, default='Group')
    status = models.CharField(max_length=20, choices=ReplacementStatus.choices, default=ReplacementStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at', '-created_at')

    def __str__(self) -> str:
        return f'Replacement {self.ticket.ticket_id}'


class Report(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='report')
    engineer = models.ForeignKey(EngineerProfile, on_delete=models.PROTECT, related_name='reports')
    service_provider_code = models.CharField(max_length=60)
    serial_number = models.CharField(max_length=120)
    problem_identified = models.TextField()
    action_taken = models.TextField()
    pcb_board_number = models.CharField(max_length=120)
    comments = models.TextField()
    charges_collected = models.DecimalField(max_digits=10, decimal_places=2)
    kms_driven = models.PositiveIntegerField()
    is_customer_polite = models.BooleanField()
    difficult_to_attend = models.BooleanField()
    before_service_photo = models.ImageField(upload_to='reports/before/', null=True, blank=True)
    after_service_photo = models.ImageField(upload_to='reports/after/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Report {self.ticket.ticket_id}'
