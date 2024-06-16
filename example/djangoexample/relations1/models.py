from django.db import models


class Abstract(models.Model):
    class Meta:
        abstract = True


class Child1QuerySet(models.QuerySet["Child1"]):
    pass


Child1Manager = models.Manager.from_queryset(Child1QuerySet)


class Child1(Abstract):
    objects = Child1Manager()


class Child2(Abstract):
    pass


class Concrete1QuerySet(models.QuerySet["Concrete1"]):
    pass


Concrete1Manager = models.Manager.from_queryset(Concrete1QuerySet)


class Concrete1(models.Model):
    objects = Concrete1Manager()


class Concrete2(models.Model):
    concrete1 = models.ForeignKey(
        "relations1.Concrete1", related_name="c2s", on_delete=models.CASCADE
    )
    children = models.ManyToManyField(Child1, related_name="children")
