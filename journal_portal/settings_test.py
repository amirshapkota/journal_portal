from .settings import *

# Ensure postgres-specific model fields pass system checks during tests.
if 'django.contrib.postgres' not in INSTALLED_APPS:
    INSTALLED_APPS = ['django.contrib.postgres'] + INSTALLED_APPS

# Force isolated sqlite database for local test execution.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_test.sqlite3',
    }
}

# Keep tests deterministic and fast.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
