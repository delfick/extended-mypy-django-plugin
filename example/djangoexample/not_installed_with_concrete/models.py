from django.db import models


class AnAbstract(models.Model):
    class Meta:
        abstract = True


class Concrete(AnAbstract):
    pass
