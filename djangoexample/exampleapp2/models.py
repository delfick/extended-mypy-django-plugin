from django.db import models

from djangoexample.exampleapp.models import Parent


class ChildOther(Parent):
    two = models.CharField(max_length=60)


class ChildOther2(Parent):
    two = models.CharField(max_length=60)
