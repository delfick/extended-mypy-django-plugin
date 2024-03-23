from django.http import HttpRequest, HttpResponse, HttpResponseBase

from .exampleapp.models import Child1, Child2, Parent
from .mypy_plugin import Concrete, ConcreteQuerySet, DefaultQuerySet

T_Child = Concrete.type_var("T_Child", Parent)
T_ChildStr = Concrete.type_var("T_ChildStr", "Parent")


def make_child(child: type[T_Child]) -> T_Child:
    return child.objects.create()


def make_child_str(child: type[T_ChildStr]) -> T_ChildStr:
    return child.objects.create()


def make_any_queryset(child: type[Concrete[Parent]]) -> ConcreteQuerySet[Parent]:
    return child.objects.all()


def make_child1_queryset() -> DefaultQuerySet[Child1]:
    return Child1.objects.all()


def make_child2_queryset() -> DefaultQuerySet[Child2]:
    return Child2.objects.all()


def make_child_typevar_queryset(child: type[T_Child]) -> DefaultQuerySet[T_Child]:
    return child.objects.all()


def ones(model: type[Concrete[Parent]]) -> list[str]:
    # Union[django.db.models.manager.Manager[djangomypytest.exampleapp.models.Child1], djangomypytest.exampleapp.models.ManagerFromChild2QuerySet[djangomypytest.exampleapp.models.Child2], django.db.models.manager.Manager[djangomypytest.exampleapp.models.Child3]]
    reveal_type(model.objects)
    return list(model.objects.values_list("one", flat=True))


def index(request: HttpRequest) -> HttpResponseBase:
    made = make_child(Child1)
    # djangomypytest.exampleapp.models.Child1
    reveal_type(made)

    made_str = make_child(Child1)
    # djangomypytest.exampleapp.models.Child1
    reveal_type(made_str)

    any_qs = make_any_queryset(Child1)
    # Union[django.db.models.query._QuerySet[djangomypytest.exampleapp.models.Child1], djangomypytest.exampleapp.models.Child2QuerySet, django.db.models.query._QuerySet[djangomypytest.exampleapp.models.Child3]]
    reveal_type(any_qs)

    qs1 = make_child1_queryset()
    # django.db.models.query._QuerySet[djangomypytest.exampleapp.models.Child1]
    reveal_type(qs1)

    qs2 = make_child2_queryset()
    # djangomypytest.exampleapp.models.Child2QuerySet
    reveal_type(qs2)
    # djangomypytest.exampleapp.models.Child2QuerySet
    reveal_type(qs2.all())
    # djangomypytest.exampleapp.models.ManagerFromChild2QuerySet[djangomypytest.exampleapp.models.Child2]
    reveal_type(Child2.objects)
    # djangomypytest.exampleapp.models.Child2QuerySet[djangomypytest.exampleapp.models.Child2]
    reveal_type(Child2.objects.all())

    tvqs1 = make_child_typevar_queryset(Child1)
    # django.db.models.query._QuerySet[djangomypytest.exampleapp.models.Child1]
    reveal_type(tvqs1)

    tvqs2 = make_child_typevar_queryset(Child2)
    # djangomypytest.exampleapp.models.Child2QuerySet
    reveal_type(tvqs2)

    return HttpResponse("Hello there")
