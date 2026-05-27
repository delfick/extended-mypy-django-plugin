from django.db import models


class Parent(models.Model):
    one = models.CharField(max_length=50)

    class Meta:
        abstract = True


class Child1(Parent):
    concrete_from_myapp = models.CharField(max_length=50)
    two = models.CharField(max_length=60)


class Child2QuerySet[T_Child2: Child2 = Child2](models.QuerySet[T_Child2]):
    pass


Child2Manager = models.Manager.from_queryset(Child2QuerySet)


class Child2(Parent):
    concrete_from_myapp = models.CharField(max_length=50)
    two = models.CharField(max_length=60)
    four = models.CharField(max_length=1)

    three = models.CharField(max_length=70)

    objects = Child2Manager()


class Parent2(Parent):
    three = models.CharField(max_length=51)

    class Meta:
        abstract = True


class Child3(Parent2):
    concrete_from_myapp = models.CharField(max_length=50)
    two = models.CharField(max_length=60)

    three = models.CharField(max_length=70)
