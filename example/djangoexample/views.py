from typing import TypeVar

from django.http import HttpRequest, HttpResponse, HttpResponseBase

from extended_mypy_django_plugin import Concrete, DefaultQuerySet

from .exampleapp.models import Child1, Child2, Parent

T_Child = TypeVar("T_Child", bound=Concrete[Parent])


def make_child(child: type[T_Child]) -> T_Child:
    created = child.objects.create()
    assert isinstance(created, child)
    return created


def make_any_queryset(child: type[Concrete[Parent]]) -> DefaultQuerySet[Parent]:
    return child.objects.all()


def make_child1_queryset() -> DefaultQuerySet[Child1]:
    return Child1.objects.all()


def make_child2_queryset() -> DefaultQuerySet[Child2]:
    return Child2.objects.all()


def ones(model: type[Concrete[Parent]]) -> list[str]:
    # Union[django.db.models.manager.Manager[djangoexample.exampleapp.models.Child1], djangoexample.exampleapp.models.ManagerFromChild2QuerySet[djangoexample.exampleapp.models.Child2], django.db.models.manager.Manager[djangoexample.exampleapp.models.Child3]]
    reveal_type(model.objects)
    return list(model.objects.values_list("one", flat=True))


def index(request: HttpRequest) -> HttpResponseBase:
    made = make_child(Child1)
    # djangoexample.exampleapp.models.Child1
    reveal_type(made)

    any_qs = make_any_queryset(Child1)
    # Union[django.db.models.query._QuerySet[djangoexample.exampleapp.models.Child1], djangoexample.exampleapp.models.Child2QuerySet, django.db.models.query._QuerySet[djangoexample.exampleapp.models.Child3]]
    reveal_type(any_qs)

    qs1 = make_child1_queryset()
    # django.db.models.query._QuerySet[djangoexample.exampleapp.models.Child1]
    reveal_type(qs1)

    qs2 = make_child2_queryset()
    # djangoexample.exampleapp.models.Child2QuerySet
    reveal_type(qs2)
    # djangoexample.exampleapp.models.Child2QuerySet
    reveal_type(qs2.all())
    # djangoexample.exampleapp.models.ManagerFromChild2QuerySet[djangoexample.exampleapp.models.Child2]
    reveal_type(Child2.objects)
    # djangoexample.exampleapp.models.Child2QuerySet[djangoexample.exampleapp.models.Child2]
    reveal_type(Child2.objects.all())

    return HttpResponse("Hello there")
