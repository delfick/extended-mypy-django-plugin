from django.db import models

from djangoexample.relations1 import models as relations1


class Thing(models.Model):
    concrete = models.OneToOneField(
        relations1.Concrete1, related_name="thing", on_delete=models.CASCADE
    )
