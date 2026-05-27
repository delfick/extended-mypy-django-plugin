from typing import Self

from django.db import models
from leader.models import Leader


class Follower1QuerySet[T_Follower1: Follower1 = Follower1](models.QuerySet[T_Follower1]):
    def good_ones(self) -> Self:
        return self.filter(good=True)


Follower1Manager = models.Manager.from_queryset(Follower1QuerySet)


class Follower1(Leader):
    good = models.BooleanField()
    from_follower1 = models.CharField()

    objects = Follower1Manager()
