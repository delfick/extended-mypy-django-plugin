from typing import TYPE_CHECKING

def interface____differentiated__5() -> None:
    return None

mod = "djangoexample.exampleapp.models"
summary = "__virtual__.mod_3347844205::djangoexample.exampleapp.models::installed_apps=__installed_apps_hash__::significant=2358377148"

if TYPE_CHECKING:
    import django.db.models.QuerySet
    import djangoexample.exampleapp.models.Child1
    import djangoexample.exampleapp.models.Child2
    import djangoexample.exampleapp.models.Child2QuerySet
    import djangoexample.exampleapp.models.Child3
    import djangoexample.exampleapp.models.Child4
    import djangoexample.exampleapp.models.Child4QuerySet
    import djangoexample.exampleapp.models.Parent
    import djangoexample.exampleapp.models.Parent2
    import djangoexample.exampleapp2.models.ChildOther
    import djangoexample.exampleapp2.models.ChildOther2
    ConcreteQuerySet__Child1 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child1]
    ConcreteQuerySet__Child2 = djangoexample.exampleapp.models.Child2QuerySet
    ConcreteQuerySet__Child3 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child3]
    ConcreteQuerySet__Child4 = djangoexample.exampleapp.models.Child4QuerySet
    ConcreteQuerySet__Parent = django.db.models.QuerySet[djangoexample.exampleapp.models.Child1] | django.db.models.QuerySet[djangoexample.exampleapp.models.Child3] | django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther2] | django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther] | djangoexample.exampleapp.models.Child2QuerySet | djangoexample.exampleapp.models.Child4QuerySet
    ConcreteQuerySet__Parent2 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child3] | djangoexample.exampleapp.models.Child4QuerySet
    Concrete__Child1 = djangoexample.exampleapp.models.Child1
    Concrete__Child2 = djangoexample.exampleapp.models.Child2
    Concrete__Child3 = djangoexample.exampleapp.models.Child3
    Concrete__Child4 = djangoexample.exampleapp.models.Child4
    Concrete__Parent = djangoexample.exampleapp.models.Child1 | djangoexample.exampleapp.models.Child2 | djangoexample.exampleapp.models.Child3 | djangoexample.exampleapp.models.Child4 | djangoexample.exampleapp2.models.ChildOther | djangoexample.exampleapp2.models.ChildOther2
    Concrete__Parent2 = djangoexample.exampleapp.models.Child3 | djangoexample.exampleapp.models.Child4