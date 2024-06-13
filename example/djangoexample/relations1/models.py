from django.db import models


class Abstract(models.Model):
    class Meta:
        abstract = True


class Child1(Abstract):
    pass


class Child2(Abstract):
    pass


class Concrete1(models.Model):
    pass


class Concrete2(models.Model):
    concrete1 = models.ForeignKey(
        "relations1.Concrete1", related_name="c2s", on_delete=models.CASCADE
    )
    children = models.ManyToManyField(Child1, related_name="children")
