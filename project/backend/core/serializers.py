from django.contrib.auth.models import User
from rest_framework import serializers

from .models import AdminProfile, Customer, EngineerProfile, Report, Ticket


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active')


class EngineerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=4)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)

    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = EngineerProfile
        fields = ('id', 'user', 'username', 'password', 'first_name', 'last_name', 'email', 'phone', 'active')

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')

        user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name, email=email)
        return EngineerProfile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user = instance.user
        for field in ('first_name', 'last_name', 'email'):
            if field in validated_data:
                setattr(user, field, validated_data.pop(field))
        if 'password' in validated_data:
            user.set_password(validated_data.pop('password'))
        user.save()
        return super().update(instance, validated_data)


class AdminProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = AdminProfile
        fields = ('id', 'user', 'active')


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class TicketSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.contact_phone', read_only=True)
    customer_address = serializers.CharField(source='customer.address', read_only=True)
    assigned_engineer_name = serializers.CharField(source='assigned_engineer.user.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Ticket
        fields = (
            'id',
            'ticket_id',
            'customer',
            'customer_name',
            'customer_phone',
            'customer_address',
            'model',
            'serial_number',
            'mfg_date',
            'location',
            'issue',
            'status',
            'assigned_engineer',
            'assigned_engineer_name',
            'created_by',
            'created_by_name',
            'created_at',
            'assigned_at',
            'started_at',
            'completed_at',
            'qr_code',
        )
        read_only_fields = ('created_by', 'created_at', 'assigned_at', 'started_at', 'completed_at')


class ReportSerializer(serializers.ModelSerializer):
    ticket_id = serializers.CharField(source='ticket.ticket_id', read_only=True)
    engineer_name = serializers.CharField(source='engineer.user.username', read_only=True)
    ticket_created_at = serializers.DateTimeField(source='ticket.created_at', read_only=True)
    ticket_started_at = serializers.DateTimeField(source='ticket.started_at', read_only=True)
    ticket_completed_at = serializers.DateTimeField(source='ticket.completed_at', read_only=True)

    class Meta:
        model = Report
        fields = (
            'id',
            'ticket',
            'ticket_id',
            'engineer',
            'engineer_name',
            'ticket_created_at',
            'ticket_started_at',
            'ticket_completed_at',
            'service_provider_code',
            'number_of_fans',
            'serial_number',
            'problem_identified',
            'action_taken',
            'pcb_board_number',
            'comments',
            'charges_collected',
            'kms_driven',
            'is_customer_polite',
            'difficult_to_attend',
            'created_at',
        )
        read_only_fields = ('created_at',)
