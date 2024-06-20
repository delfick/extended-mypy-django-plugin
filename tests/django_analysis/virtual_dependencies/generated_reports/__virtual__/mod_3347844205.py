def interface____differentiated__5() -> None:
    return None

mod = "djangoexample.exampleapp.models"
summary = "__virtual__.mod_3347844205::djangoexample.exampleapp.models::installed_apps=__installed_apps_hash__::significant=2358377148"

import django.db.models
import djangoexample.exampleapp.models
import djangoexample.exampleapp2.models
ConcreteQuerySet__Child1 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child1]
ConcreteQuerySet__Child2 = djangoexample.exampleapp.models.Child2QuerySet
ConcreteQuerySet__Child3 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child3]
ConcreteQuerySet__Child4 = djangoexample.exampleapp.models.Child4QuerySet
ConcreteQuerySet__Parent = django.db.models.QuerySet[djangoexample.exampleapp.models.Child1] | djangoexample.exampleapp.models.Child2QuerySet | django.db.models.QuerySet[djangoexample.exampleapp.models.Child3] | djangoexample.exampleapp.models.Child4QuerySet | django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther] | django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther2]
ConcreteQuerySet__Parent2 = django.db.models.QuerySet[djangoexample.exampleapp.models.Child3] | djangoexample.exampleapp.models.Child4QuerySet
Concrete__Child1 = djangoexample.exampleapp.models.Child1
Concrete__Child2 = djangoexample.exampleapp.models.Child2
Concrete__Child3 = djangoexample.exampleapp.models.Child3
Concrete__Child4 = djangoexample.exampleapp.models.Child4
Concrete__Parent = djangoexample.exampleapp.models.Child1 | djangoexample.exampleapp.models.Child2 | djangoexample.exampleapp.models.Child3 | djangoexample.exampleapp.models.Child4 | djangoexample.exampleapp2.models.ChildOther | djangoexample.exampleapp2.models.ChildOther2
Concrete__Parent2 = djangoexample.exampleapp.models.Child3 | djangoexample.exampleapp.models.Child4
