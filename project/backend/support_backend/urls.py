from django.http import HttpResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.admin_site import admin_site

def health(request):
    return HttpResponse('OK')

def favicon(request):
    return HttpResponse(status=204)

urlpatterns = [
    path('', health),
    path('favicon.ico', favicon),
    path('admin/', admin_site.urls),
path('panel/', include('core.panel_urls', namespace='panel')),
    path('api/', include('core.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
