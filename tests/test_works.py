from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario


def test_works(scenario: Scenario) -> None:
    @scenario.run_and_check_mypy_after
    def _(expected: OutputBuilder) -> None:
        scenario.file(
            expected,
            "main.py",
            """
            from extended_mypy_django_plugin import Concrete, DefaultQuerySet

            from typing import TypeVar
            from myapp.models import Parent, Child1, Child2

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


            def make_multiple_queryset(child: type[Child1 | Child2]) -> DefaultQuerySet[Child2 | Child1]:
                return child.objects.all()


            def ones(model: type[Concrete[Parent]]) -> list[str]:
                model.objects
                # ^ REVEAL ^ Union[django.db.models.manager.Manager[myapp.models.Child1], myapp.models.ManagerFromChild2QuerySet[myapp.models.Child2], django.db.models.manager.Manager[myapp.models.Child3], django.db.models.manager.Manager[myapp2.models.ChildOther]]
                return list(model.objects.values_list("one", flat=True))


            make_child(Child1)
            # ^ REVEAL ^ myapp.models.Child1

            make_any_queryset(Child1)
            # ^ REVEAL ^ Union[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1], myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3], django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]

            make_child1_queryset()
            # ^ REVEAL ^ django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]

            qs2 = make_child2_queryset()
            # ^ REVEAL ^ myapp.models.Child2QuerySet

            qs2.all()
            # ^ REVEAL ^ myapp.models.Child2QuerySet

            Child2.objects
            # ^ REVEAL ^ myapp.models.ManagerFromChild2QuerySet[myapp.models.Child2]

            Child2.objects.all()
            # ^ REVEAL ^ myapp.models.Child2QuerySet[myapp.models.Child2]

            make_multiple_queryset(Child1)
            # ^ REVEAL ^ Union[myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]]
            """,
        )
