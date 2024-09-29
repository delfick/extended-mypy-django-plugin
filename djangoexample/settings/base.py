from collections.abc import Mapping, Sequence
from pathlib import Path

from configurations import Configuration  # type: ignore[import-untyped]


class Base(Configuration):
    CUSTOM_SETTING: Mapping[str, int] = {}

    UNIQUE_SETTING_TO_EXTENDED_MYPY_PLUGIN_DJANGOEXAMPLE = "unique"

    # Build paths inside the project like this: BASE_DIR / 'subdir'.
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Quick-start development settings - unsuitable for production
    # See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY: str = "django-insecure-_%)ag2w27a34bnnvn%fyc5@8kjj2+pu0!sla(j(lr=8s2ku-cr"

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG: bool = True

    ALLOWED_HOSTS: Sequence[str] = []

    # Application definition

    def INSTALLED_APPS(self) -> Sequence[str]:
        return [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ]

    MIDDLEWARE: Sequence[str] = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    ROOT_URLCONF: str = "djangoexample.urls"

    TEMPLATES: Sequence[Mapping[str, object]] = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    ]

    WSGI_APPLICATION: str = "djangoexample.wsgi.application"

    # Database
    # https://docs.djangoproject.com/en/4.2/ref/settings/#databases

    DATABASES: Mapping[str, object] = {
        "default": {"ENGINE": "django.db.backends.postgresql", "NAME": "djangoexample"}
    }

    # Password validation
    # https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

    AUTH_PASSWORD_VALIDATORS: Sequence[Mapping[str, str]] = [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]

    # Internationalization
    # https://docs.djangoproject.com/en/4.2/topics/i18n/

    LANGUAGE_CODE: str = "en-us"

    TIME_ZONE: str = "UTC"

    USE_I18N: bool = True

    USE_TZ: bool = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/4.2/howto/static-files/

    STATIC_URL: str = "static/"

    # Default primary key field type
    # https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

    DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"
