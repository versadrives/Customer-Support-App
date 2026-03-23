from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .views import CustomerViewSet, EngineerProfileViewSet, ReportViewSet, TicketViewSet, change_password, me

router = DefaultRouter()
router.register(r'engineers', EngineerProfileViewSet, basename='engineer')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', me),
    path('change-password/', change_password),
]
