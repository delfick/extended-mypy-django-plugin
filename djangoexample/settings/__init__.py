from collections.abc import Sequence

from .base import Base


class Dev(Base):
    def INSTALLED_APPS(self) -> Sequence[str]:
        return [
            *super().INSTALLED_APPS(),
            "djangoexample.exampleapp",
            "djangoexample.exampleapp2",
        ]
