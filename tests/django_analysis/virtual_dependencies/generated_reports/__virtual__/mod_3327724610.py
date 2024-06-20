def interface____differentiated__7() -> None:
    return None

mod = "djangoexample.relations1.models"
summary = "__virtual__.mod_3327724610::djangoexample.relations1.models::installed_apps=__installed_apps_hash__::significant=448140218"

import django.db.models
import djangoexample.relations1.models
ConcreteQuerySet__Abstract = djangoexample.relations1.models.Child1QuerySet | django.db.models.QuerySet[djangoexample.relations1.models.Child2]
ConcreteQuerySet__Child1 = djangoexample.relations1.models.Child1QuerySet
ConcreteQuerySet__Child2 = django.db.models.QuerySet[djangoexample.relations1.models.Child2]
ConcreteQuerySet__Concrete1 = djangoexample.relations1.models.Concrete1QuerySet
ConcreteQuerySet__Concrete2 = django.db.models.QuerySet[djangoexample.relations1.models.Concrete2]
Concrete__Abstract = djangoexample.relations1.models.Child1 | djangoexample.relations1.models.Child2
Concrete__Child1 = djangoexample.relations1.models.Child1
Concrete__Child2 = djangoexample.relations1.models.Child2
Concrete__Concrete1 = djangoexample.relations1.models.Concrete1
Concrete__Concrete2 = djangoexample.relations1.models.Concrete2
