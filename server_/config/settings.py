import pymysql
from decouple import config
from pathlib import Path
import os

# ====================== PyMySQL SETUP (Critical for Render + Django 6.0) ======================
pymysql.install_as_MySQLdb()

# This tricks Django into thinking we have a newer mysqlclient version
# Django 6.0 now requires mysqlclient >= 2.2.1
pymysql.version_info = (2, 2, 1, 'final', 0)

BASE_DIR = Path(__file__).resolve().parent.parent

# ====================== BASIC SETTINGS ======================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# ====================== INSTALLED APPS ======================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',

    # Your apps
    'apps.authentication.apps.AuthenticationConfig',
    'apps.prescriptions',
    'apps.inventory',
    'apps.orders',
    'apps.bulk_orders',
    'apps.deliveries',
    'apps.reporting',
    'apps.receipts',
    'apps.settings_module',
]

AUTH_USER_MODEL = 'authentication.PharmacyUser'

# ====================== TEMPLATES ======================
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
            ],
        },
    },
]

# ====================== PASSWORD HASHERS ======================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ====================== MIDDLEWARE ======================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ====================== DATABASE (TiDB Cloud) ======================
# ====================== DATABASE (TiDB Cloud Serverless) ======================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int, default=4000),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 300,
    }
}

# ====================== SSL Configuration for TiDB (Production vs Local) ======================
# TiDB Serverless requires SSL, but we make it flexible for different environments

tidb_ca_path = config('TIDB_CA_PATH', default=None)

if tidb_ca_path:
    ca_full_path = BASE_DIR / tidb_ca_path
    if ca_full_path.exists():
        # Use custom CA file if it exists (works locally)
        DATABASES['default']['OPTIONS']['ssl'] = {
            'ca': str(ca_full_path),
            'ssl_mode': 'VERIFY_IDENTITY',
        }
    else:
        # Fallback for Render / environments where CA file is not present
        DATABASES['default']['OPTIONS']['ssl'] = {
            'ssl_mode': 'PREFERRED',      # Most reliable for Render + TiDB
        }
else:
    # No TIDB_CA_PATH provided → use preferred mode
    DATABASES['default']['OPTIONS']['ssl'] = {
        'ssl_mode': 'PREFERRED',
    }

# ====================== REST FRAMEWORK ======================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.StandardPagination',
    'PAGE_SIZE': 20,
}

# ====================== SIMPLE JWT ======================
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'SIGNING_KEY': config('JWT_SIGNING_KEY'),
    'ALGORITHM': 'HS256',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ====================== CORS ======================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# ====================== MEDIA & STATIC ======================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'