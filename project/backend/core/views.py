from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Customer, EngineerProfile, Report, Ticket, TicketStatus
from .permissions import IsAdmin, IsAdminOrEngineer, IsEngineer
from .serializers import CustomerSerializer, EngineerProfileSerializer, ReportSerializer, TicketSerializer


class EngineerProfileViewSet(viewsets.ModelViewSet):
    queryset = EngineerProfile.objects.select_related('user').all()
    serializer_class = EngineerProfileSerializer
    permission_classes = [IsAdmin]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdmin]


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related('customer', 'assigned_engineer', 'assigned_engineer__user').all()
    serializer_class = TicketSerializer

    def get_permissions(self):
        if self.action == 'start':
            return [IsAuthenticated()]
        if self.action == 'complete':
            return [IsEngineer()]
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated()]
        if self.request.method in ('PATCH', 'PUT'):
            if IsAdmin().has_permission(self.request, self):
                return [IsAdmin()]
            return [IsEngineer()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if IsAdmin().has_permission(self.request, self):
            return qs
        if self.request.user and self.request.user.is_authenticated:
            profile = EngineerProfile.objects.filter(user=self.request.user).first()
            profile_id = profile.id if profile else None
            return qs.filter(
                Q(assigned_engineer__user=self.request.user)
                | Q(assigned_engineer_id=profile_id)
                | Q(assigned_engineer__user__username__icontains=self.request.user.username)
                | Q(assigned_engineer__user__email=self.request.user.email)
            )
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        customer_id = data.get('customer')
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        customer_address = data.get('customer_address')
        if not customer_id and customer_name:
            customer, _ = Customer.objects.get_or_create(name=customer_name.strip())
            if customer_phone:
                customer.contact_phone = customer_phone
            if customer_address:
                customer.address = customer_address
            customer.save()
            data['customer'] = customer.id
        data.pop('customer_name', None)
        data.pop('customer_phone', None)
        data.pop('customer_address', None)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            ticket = self.get_object()
            if ticket.assigned_engineer != request.user.engineer_profile:
                return Response({'detail': 'Not your ticket.'}, status=status.HTTP_403_FORBIDDEN)
            allowed = {'status', 'qr_code'}
            for key in list(request.data.keys()):
                if key not in allowed:
                    request.data.pop(key, None)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        previous = self.get_object()
        updated = serializer.save()
        if previous.assigned_engineer != updated.assigned_engineer and updated.assigned_engineer and not updated.assigned_at:
            updated.assigned_at = timezone.now()
        if updated.status == TicketStatus.IN_PROGRESS and not updated.started_at:
            updated.started_at = timezone.now()
        if updated.status == TicketStatus.COMPLETED and not updated.completed_at:
            updated.completed_at = timezone.now()
        updated.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        ticket = self.get_object()
        is_admin = IsAdmin().has_permission(request, self)
        if not ticket.assigned_engineer:
            if is_admin:
                return Response({'detail': 'Ticket must be assigned before starting.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': 'Not your ticket.'}, status=status.HTTP_403_FORBIDDEN)
        if not is_admin and ticket.assigned_engineer.user != request.user:
            return Response({'detail': 'Not your ticket.'}, status=status.HTTP_403_FORBIDDEN)
        ticket.status = TicketStatus.IN_PROGRESS
        if not ticket.started_at:
            ticket.started_at = timezone.now()
        ticket.save()
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        ticket = self.get_object()
        if not ticket.assigned_engineer or ticket.assigned_engineer.user != request.user:
            return Response({'detail': 'Not your ticket.'}, status=status.HTTP_403_FORBIDDEN)
        required_fields = [
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
        ]
        for field in required_fields:
            if field not in request.data or request.data.get(field) in (None, ''):
                return Response({'detail': f'Missing {field}.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            number_of_fans = int(request.data['number_of_fans'])
            kms_driven = int(request.data['kms_driven'])
            charges_collected = Decimal(str(request.data['charges_collected']))
        except (ValueError, TypeError, InvalidOperation):
            return Response({'detail': 'Invalid numeric values.'}, status=status.HTTP_400_BAD_REQUEST)
        report = Report.objects.create(
            ticket=ticket,
            engineer=request.user.engineer_profile,
            service_provider_code=request.user.username,
            number_of_fans=number_of_fans,
            serial_number=request.data['serial_number'],
            problem_identified=request.data['problem_identified'],
            action_taken=request.data['action_taken'],
            pcb_board_number=request.data['pcb_board_number'],
            comments=request.data['comments'],
            charges_collected=charges_collected,
            kms_driven=kms_driven,
            is_customer_polite=request.data['is_customer_polite'],
            difficult_to_attend=request.data['difficult_to_attend'],
        )
        ticket.status = TicketStatus.COMPLETED
        ticket.completed_at = ticket.completed_at or timezone.now()
        ticket.save()
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('ticket', 'engineer', 'engineer__user').all()
    serializer_class = ReportSerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAdminOrEngineer()]
        if self.request.method in ('POST',):
            return [IsEngineer()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if IsAdmin().has_permission(self.request, self):
            return qs
        if hasattr(self.request.user, 'engineer_profile'):
            return qs.filter(engineer=self.request.user.engineer_profile)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(engineer=self.request.user.engineer_profile)

    @action(detail=True, methods=['get'], permission_classes=[IsAdmin])
    def pdf(self, request, pk=None):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        report = self.get_object()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{report.ticket.ticket_id}.pdf"'
        p = canvas.Canvas(response, pagesize=letter)
        y = 760
        p.setFont('Helvetica-Bold', 14)
        p.drawString(40, y, f"Service Report - {report.ticket.ticket_id}")
        y -= 24
        p.setFont('Helvetica', 11)
        lines = [
            f"Engineer: {report.engineer.display_name}",
            f"Customer: {report.ticket.customer.name}",
            f"Location: {report.ticket.location}",
            f"Status: {report.ticket.status}",
            f"Ticket Created: {report.ticket.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Ticket Started: {report.ticket.started_at.strftime('%Y-%m-%d %H:%M') if report.ticket.started_at else '-'}",
            f"Ticket Completed: {report.ticket.completed_at.strftime('%Y-%m-%d %H:%M') if report.ticket.completed_at else '-'}",
            f"Log Date: {report.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    profile = getattr(request.user, 'engineer_profile', None)
    return Response(
        {
            'user_id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'is_staff': request.user.is_staff,
            'engineer_profile_id': getattr(profile, 'id', None),
            'engineer_profile_user_id': getattr(profile, 'user_id', None),
            'engineer_active': getattr(profile, 'active', None),
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not old_password or not new_password:
        return Response({'detail': 'Missing old_password or new_password.'}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    if not user.check_password(old_password):
        return Response({'detail': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 4:
        return Response({'detail': 'Password too short.'}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(new_password)
    user.save()
    return Response(status=status.HTTP_204_NO_CONTENT)
