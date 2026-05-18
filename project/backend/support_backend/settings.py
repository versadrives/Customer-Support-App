from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'dev-only-change-me'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SessionExpiryMiddleware',
]

ROOT_URLCONF = 'support_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'support_backend.template_flags.panel_flags',
            ],
        },
    }
]

WSGI_APPLICATION = 'support_backend.wsgi.application'
ASGI_APPLICATION = 'support_backend.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DOWNLOADS_URL = '/downloads/'
DOWNLOADS_ROOT = Path('/var/www/html/downloads')

REPLACEMENT_INVOICE_LOGO_DIR = BASE_DIR / 'invoice_assets' / 'logos'
REPLACEMENT_INVOICE_HEADER_IMAGE = REPLACEMENT_INVOICE_LOGO_DIR / 'invoice_header.png'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Feature flags for the admin panel UI.
PANEL_SHOW_FILTERS = True
PANEL_SHOW_ENGINEER_ADD = True
PANEL_SHOW_ADMIN_LINK = False
PANEL_SHOW_LISTS = False

# Panel login protection.
PANEL_LOGIN_MAX_FAILURES = 5
PANEL_LOGIN_LOCKOUT_SECONDS = 900
PANEL_LOGIN_FAILURE_WINDOW_SECONDS = 900

# Security settings.
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 hours in seconds
X_FRAME_OPTIONS = 'DENY'

# Mobile app update metadata.
APP_UPDATE_VERSION = '1.0.2'
APP_UPDATE_BUILD_NUMBER = 5
APP_UPDATE_APK_URL = 'http://13.201.34.16/downloads/superfan-release-v1.0.2-5.apk'
APP_UPDATE_NOTES = 'Updated with Application name and bug fixes.'
APP_UPDATE_FORCE = False
# Last Update date 12-05-2026
