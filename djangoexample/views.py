from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.conf import settings


def index(request: HttpRequest) -> HttpResponseBase:
    reveal_type(settings.CUSTOM_SETTING)
    return HttpResponse("Hello there")
