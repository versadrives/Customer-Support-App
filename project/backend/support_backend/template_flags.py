from django.conf import settings


def panel_flags(request):
    return {
        "PANEL_SHOW_FILTERS": getattr(settings, "PANEL_SHOW_FILTERS", True),
        "PANEL_SHOW_ENGINEER_ADD": getattr(settings, "PANEL_SHOW_ENGINEER_ADD", True),
        "PANEL_SHOW_ADMIN_LINK": getattr(settings, "PANEL_SHOW_ADMIN_LINK", True),
    }
