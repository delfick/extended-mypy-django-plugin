from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario


def test_works(scenario: Scenario) -> None:
    out = """
     main:33: note: Revealed type is "Union[django.db.models.manager.Manager[myapp.models.Child1], myapp.models.ManagerFromChild2QuerySet[myapp.models.Child2], django.db.models.manager.Manager[myapp.models.Child3], django.db.models.manager.Manager[myapp2.models.ChildOther]]"
     main:38: note: Revealed type is "myapp.models.Child1"
     main:41: note: Revealed type is "Union[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1], myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3], django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]"
     main:44: note: Revealed type is "django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]"
     main:47: note: Revealed type is "myapp.models.Child2QuerySet"
     main:48: note: Revealed type is "myapp.models.Child2QuerySet"
     main:49: note: Revealed type is "myapp.models.ManagerFromChild2QuerySet[myapp.models.Child2]"
     main:50: note: Revealed type is "myapp.models.Child2QuerySet[myapp.models.Child2]"
     main:53: note: Revealed type is "django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]"
     main:56: note: Revealed type is "myapp.models.Child2QuerySet"
     main:59: note: Revealed type is "Union[myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]]"
     """

    @scenario.run_and_check_mypy_after
    def _(expected: OutputBuilder) -> None:
        scenario.file(
            expected,
            "main.py",
            """
            from extended_mypy_django_plugin import Concrete, DefaultQuerySet

            from myapp.models import Parent, Child1, Child2

            T_Child = Concrete.type_var("T_Child", Parent)


            def make_child(child: type[T_Child]) -> T_Child:
                return child.objects.create()


            def make_any_queryset(child: type[Concrete[Parent]]) -> DefaultQuerySet[Parent]:
                return child.objects.all()


            def make_child1_queryset() -> DefaultQuerySet[Child1]:
                return Child1.objects.all()


            def make_child2_queryset() -> DefaultQuerySet[Child2]:
                return Child2.objects.all()


            def make_multiple_queryset(child: type[Child1 | Child2]) -> DefaultQuerySet[Child2 | Child1]:
                return child.objects.all()


            def make_child_typevar_queryset(child: type[T_Child]) -> DefaultQuerySet[T_Child]:
                return child.objects.all()


            def ones(model: type[Concrete[Parent]]) -> list[str]:
                reveal_type(model.objects)
                return list(model.objects.values_list("one", flat=True))


            made = make_child(Child1)
            reveal_type(made)

            any_qs = make_any_queryset(Child1)
            reveal_type(any_qs)

            qs1 = make_child1_queryset()
            reveal_type(qs1)

            qs2 = make_child2_queryset()
            reveal_type(qs2)
            reveal_type(qs2.all())
            reveal_type(Child2.objects)
            reveal_type(Child2.objects.all())

            tvqs1 = make_child_typevar_queryset(Child1)
            reveal_type(tvqs1)

            tvqs2 = make_child_typevar_queryset(Child2)
            reveal_type(tvqs2)

            tvqsmult = make_multiple_queryset(Child1)
            reveal_type(tvqsmult)
            """,
        )

        expected.from_out(out)
