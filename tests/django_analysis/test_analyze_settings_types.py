from extended_mypy_django_plugin.django_analysis import discovery, protocols


class TestSettingsTypesAnalyzer:
    def test_it_looks_at_values_to_determine_types(
        self, loaded_django_example: protocols.LoadedProject
    ) -> None:
        settings_types = discovery.NaiveSettingsTypesDiscovery()(loaded_django_example)
        assert settings_types == {
            "ABSOLUTE_URL_OVERRIDES": "<class 'dict'>",
            "ADMINS": "<class 'list'>",
            "ALLOWED_HOSTS": "<class 'list'>",
            "APPEND_SLASH": "<class 'bool'>",
            "AUTHENTICATION_BACKENDS": "<class 'list'>",
            "AUTH_PASSWORD_VALIDATORS": "<class 'list'>",
            "AUTH_USER_MODEL": "<class 'str'>",
            "BASE_DIR": "<class 'pathlib.PosixPath'>",
            "CACHES": "<class 'dict'>",
            "CACHE_MIDDLEWARE_ALIAS": "<class 'str'>",
            "CACHE_MIDDLEWARE_KEY_PREFIX": "<class 'str'>",
            "CACHE_MIDDLEWARE_SECONDS": "<class 'int'>",
            "CSRF_COOKIE_AGE": "<class 'int'>",
            "CSRF_COOKIE_DOMAIN": "<class 'NoneType'>",
            "CSRF_COOKIE_HTTPONLY": "<class 'bool'>",
            "CSRF_COOKIE_MASKED": "<class 'bool'>",
            "CSRF_COOKIE_NAME": "<class 'str'>",
            "CSRF_COOKIE_PATH": "<class 'str'>",
            "CSRF_COOKIE_SAMESITE": "<class 'str'>",
            "CSRF_COOKIE_SECURE": "<class 'bool'>",
            "CSRF_FAILURE_VIEW": "<class 'str'>",
            "CSRF_HEADER_NAME": "<class 'str'>",
            "CSRF_TRUSTED_ORIGINS": "<class 'list'>",
            "CSRF_USE_SESSIONS": "<class 'bool'>",
            "DATABASES": "<class 'dict'>",
            "DATABASE_ROUTERS": "<class 'list'>",
            "DATA_UPLOAD_MAX_MEMORY_SIZE": "<class 'int'>",
            "DATA_UPLOAD_MAX_NUMBER_FIELDS": "<class 'int'>",
            "DATA_UPLOAD_MAX_NUMBER_FILES": "<class 'int'>",
            "DATETIME_FORMAT": "<class 'str'>",
            "DATETIME_INPUT_FORMATS": "<class 'list'>",
            "DATE_FORMAT": "<class 'str'>",
            "DATE_INPUT_FORMATS": "<class 'list'>",
            "DEBUG": "<class 'bool'>",
            "DEBUG_PROPAGATE_EXCEPTIONS": "<class 'bool'>",
            "DECIMAL_SEPARATOR": "<class 'str'>",
            "DEFAULT_AUTO_FIELD": "<class 'str'>",
            "DEFAULT_CHARSET": "<class 'str'>",
            "DEFAULT_EXCEPTION_REPORTER": "<class 'str'>",
            "DEFAULT_EXCEPTION_REPORTER_FILTER": "<class 'str'>",
            "DEFAULT_FILE_STORAGE": "<class 'str'>",
            "DEFAULT_FROM_EMAIL": "<class 'str'>",
            "DEFAULT_INDEX_TABLESPACE": "<class 'str'>",
            "DEFAULT_TABLESPACE": "<class 'str'>",
            "DISALLOWED_USER_AGENTS": "<class 'list'>",
            "EMAIL_BACKEND": "<class 'str'>",
            "EMAIL_HOST": "<class 'str'>",
            "EMAIL_HOST_PASSWORD": "<class 'str'>",
            "EMAIL_HOST_USER": "<class 'str'>",
            "EMAIL_PORT": "<class 'int'>",
            "EMAIL_SSL_CERTFILE": "<class 'NoneType'>",
            "EMAIL_SSL_KEYFILE": "<class 'NoneType'>",
            "EMAIL_SUBJECT_PREFIX": "<class 'str'>",
            "EMAIL_TIMEOUT": "<class 'NoneType'>",
            "EMAIL_USE_LOCALTIME": "<class 'bool'>",
            "EMAIL_USE_SSL": "<class 'bool'>",
            "EMAIL_USE_TLS": "<class 'bool'>",
            "FILE_UPLOAD_DIRECTORY_PERMISSIONS": "<class 'NoneType'>",
            "FILE_UPLOAD_HANDLERS": "<class 'list'>",
            "FILE_UPLOAD_MAX_MEMORY_SIZE": "<class 'int'>",
            "FILE_UPLOAD_PERMISSIONS": "<class 'int'>",
            "FILE_UPLOAD_TEMP_DIR": "<class 'NoneType'>",
            "FIRST_DAY_OF_WEEK": "<class 'int'>",
            "FIXTURE_DIRS": "<class 'list'>",
            "FORCE_SCRIPT_NAME": "<class 'NoneType'>",
            "FORMAT_MODULE_PATH": "<class 'NoneType'>",
            "FORM_RENDERER": "<class 'str'>",
            "IGNORABLE_404_URLS": "<class 'list'>",
            "INSTALLED_APPS": "<class 'list'>",
            "INTERNAL_IPS": "<class 'list'>",
            "LANGUAGES": "<class 'list'>",
            "LANGUAGES_BIDI": "<class 'list'>",
            "LANGUAGE_CODE": "<class 'str'>",
            "LANGUAGE_COOKIE_AGE": "<class 'NoneType'>",
            "LANGUAGE_COOKIE_DOMAIN": "<class 'NoneType'>",
            "LANGUAGE_COOKIE_HTTPONLY": "<class 'bool'>",
            "LANGUAGE_COOKIE_NAME": "<class 'str'>",
            "LANGUAGE_COOKIE_PATH": "<class 'str'>",
            "LANGUAGE_COOKIE_SAMESITE": "<class 'NoneType'>",
            "LANGUAGE_COOKIE_SECURE": "<class 'bool'>",
            "LOCALE_PATHS": "<class 'list'>",
            "LOGGING": "<class 'dict'>",
            "LOGGING_CONFIG": "<class 'str'>",
            "LOGIN_REDIRECT_URL": "<class 'str'>",
            "LOGIN_URL": "<class 'str'>",
            "LOGOUT_REDIRECT_URL": "<class 'NoneType'>",
            "MANAGERS": "<class 'list'>",
            "MEDIA_ROOT": "<class 'str'>",
            "MEDIA_URL": "<class 'str'>",
            "MESSAGE_STORAGE": "<class 'str'>",
            "MIDDLEWARE": "<class 'list'>",
            "MIGRATION_MODULES": "<class 'dict'>",
            "MONTH_DAY_FORMAT": "<class 'str'>",
            "NUMBER_GROUPING": "<class 'int'>",
            "PASSWORD_HASHERS": "<class 'list'>",
            "PASSWORD_RESET_TIMEOUT": "<class 'int'>",
            "PREPEND_WWW": "<class 'bool'>",
            "ROOT_URLCONF": "<class 'str'>",
            "SECRET_KEY": "<class 'str'>",
            "SECRET_KEY_FALLBACKS": "<class 'list'>",
            "SECURE_CONTENT_TYPE_NOSNIFF": "<class 'bool'>",
            "SECURE_CROSS_ORIGIN_OPENER_POLICY": "<class 'str'>",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": "<class 'bool'>",
            "SECURE_HSTS_PRELOAD": "<class 'bool'>",
            "SECURE_HSTS_SECONDS": "<class 'int'>",
            "SECURE_PROXY_SSL_HEADER": "<class 'NoneType'>",
            "SECURE_REDIRECT_EXEMPT": "<class 'list'>",
            "SECURE_REFERRER_POLICY": "<class 'str'>",
            "SECURE_SSL_HOST": "<class 'NoneType'>",
            "SECURE_SSL_REDIRECT": "<class 'bool'>",
            "SERVER_EMAIL": "<class 'str'>",
            "SESSION_CACHE_ALIAS": "<class 'str'>",
            "SESSION_COOKIE_AGE": "<class 'int'>",
            "SESSION_COOKIE_DOMAIN": "<class 'NoneType'>",
            "SESSION_COOKIE_HTTPONLY": "<class 'bool'>",
            "SESSION_COOKIE_NAME": "<class 'str'>",
            "SESSION_COOKIE_PATH": "<class 'str'>",
            "SESSION_COOKIE_SAMESITE": "<class 'str'>",
            "SESSION_COOKIE_SECURE": "<class 'bool'>",
            "SESSION_ENGINE": "<class 'str'>",
            "SESSION_EXPIRE_AT_BROWSER_CLOSE": "<class 'bool'>",
            "SESSION_FILE_PATH": "<class 'NoneType'>",
            "SESSION_SAVE_EVERY_REQUEST": "<class 'bool'>",
            "SESSION_SERIALIZER": "<class 'str'>",
            "SETTINGS_MODULE": "<class 'str'>",
            "SHORT_DATETIME_FORMAT": "<class 'str'>",
            "SHORT_DATE_FORMAT": "<class 'str'>",
            "SIGNING_BACKEND": "<class 'str'>",
            "SILENCED_SYSTEM_CHECKS": "<class 'list'>",
            "STATICFILES_DIRS": "<class 'list'>",
            "STATICFILES_FINDERS": "<class 'list'>",
            "STATICFILES_STORAGE": "<class 'str'>",
            "STATIC_ROOT": "<class 'NoneType'>",
            "STATIC_URL": "<class 'str'>",
            "STORAGES": "<class 'dict'>",
            "TEMPLATES": "<class 'list'>",
            "TEST_NON_SERIALIZED_APPS": "<class 'list'>",
            "TEST_RUNNER": "<class 'str'>",
            "THOUSAND_SEPARATOR": "<class 'str'>",
            "TIME_FORMAT": "<class 'str'>",
            "TIME_INPUT_FORMATS": "<class 'list'>",
            "TIME_ZONE": "<class 'str'>",
            "UNIQUE_SETTING_TO_EXTENDED_MYPY_PLUGIN_DJANGOEXAMPLE": "<class 'str'>",
            "USE_DEPRECATED_PYTZ": "<class 'bool'>",
            "USE_I18N": "<class 'bool'>",
            "USE_L10N": "<class 'bool'>",
            "USE_THOUSAND_SEPARATOR": "<class 'bool'>",
            "USE_TZ": "<class 'bool'>",
            "USE_X_FORWARDED_HOST": "<class 'bool'>",
            "USE_X_FORWARDED_PORT": "<class 'bool'>",
            "WSGI_APPLICATION": "<class 'str'>",
            "X_FRAME_OPTIONS": "<class 'str'>",
            "YEAR_MONTH_FORMAT": "<class 'str'>",
        }
