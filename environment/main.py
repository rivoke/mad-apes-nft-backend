from environment.variables import EnvironmentVariable
from environment.base import *
from datetime import timedelta

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': EnvironmentVariable.DATABASE_NAME,
        'HOST': EnvironmentVariable.DATABASE_HOST,
        'PORT': EnvironmentVariable.DATABASE_PORT,
        'USER': EnvironmentVariable.DATABASE_USERNAME,
        'PASSWORD': EnvironmentVariable.DATABASE_PASSWORD,
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }


AUTH_USER_MODEL = "user.User"

ALLOWED_HOSTS = ["*", "tg-api.covey.academy"]

if EnvironmentVariable.DEBUG == "True":
    ALLOWED_HOSTS.append("127.0.0.1")

# JWT Configuration
JWT_SECRET_KEY = EnvironmentVariable.JWT_SECRET_KEY
JWT_ALGORITHM = "HS256"


# Simple JWT Configurations
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=2)
}

ASGI_APPLICATION = 'common.asgi.application'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}


