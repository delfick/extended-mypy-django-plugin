from django.db import models

from djangoexample.exampleapp.models import Parent
from extended_mypy_django_plugin import Concrete


@Concrete.change_default_queryset_returns
class ChildOther(Parent):
    two = models.CharField(max_length=60)


@Concrete.change_default_queryset_returns
class ChildOther2(Parent):
    two = models.CharField(max_length=60)
