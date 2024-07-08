from django.db import models
from typing_extensions import Self

from extended_mypy_django_plugin import Concrete, DefaultQuerySet


@Concrete.change_default_queryset_returns
class Parent(models.Model):
    one = models.CharField(max_length=50)

    @classmethod
    def new(cls, one: str) -> Self:
        concrete = Concrete.cast_as_concrete(cls)
        created = concrete.objects.create(one=one)
        assert isinstance(created, cls)
        return created

    @classmethod
    def qs(cls) -> DefaultQuerySet["Parent"]:
        concrete = Concrete.cast_as_concrete(cls)
        return concrete.objects.all()

    class Meta:
        abstract = True


@Concrete.change_default_queryset_returns
class Child1(Parent):
    two = models.CharField(max_length=60)


class Child2QuerySet(models.QuerySet["Child2"]):
    pass


Child2Manager = models.Manager.from_queryset(Child2QuerySet)


@Concrete.change_default_queryset_returns
class Child2(Parent):
    two = models.CharField(max_length=60)
    four = models.CharField(max_length=1)

    three = models.CharField(max_length=70)

    objects = Child2Manager()


@Concrete.change_default_queryset_returns
class Parent2(Parent):
    three = models.CharField(max_length=50)

    class Meta:
        abstract = True


@Concrete.change_default_queryset_returns
class Child3(Parent2):
    two = models.CharField(max_length=60)

    three = models.CharField(max_length=70)


class Child4QuerySet(models.QuerySet["Child2"]):
    pass


Child4Manager = models.Manager.from_queryset(Child4QuerySet)


@Concrete.change_default_queryset_returns
class Child4(Parent2):
    two = models.CharField(max_length=60)

    three = models.CharField(max_length=70)

    objects = Child4Manager()
