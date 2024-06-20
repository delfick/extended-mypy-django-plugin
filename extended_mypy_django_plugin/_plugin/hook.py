"""
This exists as a helper for defining the mypy plugin.

The way a mypy plugin works is there is a class that inherits from
``mypy.plugin.Plugin`` with specific hooks that take in a string and returns
a function.

So for example, the ``get_customize_class_mro_hook`` hook will take in the
``fullname`` representing classes that can be altered, and a function that takes
in a ``ClassDefContext`` object and returns ``None`` must be returned if
the plugin wants to do something with that object.

The first plugin that mypy encounters which returns a function will win and no
other plugins will get to look at that fullname.

This is fine but it can get awkward when the function returned takes in more
options than only the context. To improve this situation, this module implements
a ``Hook`` class and associated decorator to turn those hooks into python
descriptors that do the correct thing.

.. code-block:: python

    from typing import Generic
    from mypy.plugin import Plugin, AttributeContext
    from mypy.types import Type as MypyType
    from extended_mypy_django_plugin.plugin import _hook



    class Hook(
        Generic[_hook.T_Ctx, _hook.T_Ret], _hook.Hook["MyPlugin", _hook.T_Ctx, _hook.T_Ret]
    ): ...


    class MyPlugin(Plugin):
        @_hook.hook
        class get_attribute_hook(Hook[AttributeContext, MypyType]):
            def choose(self) -> bool:
                # return True if we want to use the run method for ``self.fullname``.
                return self.fullname.endswith(".blah")

            def run(self, ctx: AttributeContext) -> MypyType:
                # Do stuff
                return ...

The hook has ``choose`` which is essentially what would be on the plugin itself
in normal situations. It can find the string that would be passed in as
``self.fullname``. It returns ``True`` if we want to handle this string, otherwise
``False``.

If the hook is chosen, then ``run`` is ran with the specified context class and
needs to return what is needed from it.

The hook has access to it:

plugin
    The plugin instance itself.

fullname
    The string that was passed into the plugin's hook

super_hook
    What would have been returned by the class the plugin is inheriting from.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from typing import Generic, TypeAlias, TypeVar, overload

from mypy.plugin import Plugin

T_Ctx = TypeVar("T_Ctx")
T_Ret = TypeVar("T_Ret")
T_Plugin = TypeVar("T_Plugin", bound=Plugin)


_HookChooser: TypeAlias = Callable[[str], Callable[[T_Ctx], T_Ret] | None]


class Hook(Generic[T_Plugin, T_Ctx, T_Ret], abc.ABC):
    """
    Class used to represent both the choosing and running logic for a hook
    on a mypy Plugin.

    This is to be used with the ``hook`` descriptor defined below. See the
    docstring on the module for more information.

    Concrete subclasses of this must implement ``choose`` and ``run``.

    The ``choose`` method will be used to determine if this hook should be used
    by mypy to do something.

    The ``run`` method will take in the context provided by mypy if this hook
    was chosen. The type of that context and what needs to be returned is defined
    by the specific mypy hook being implemented, and should be specified as
    type vars when defining the implementation of the hook.
    """

    def __init__(
        self,
        plugin: T_Plugin,
        fullname: str,
        super_hook: Callable[[T_Ctx], T_Ret] | None,
    ) -> None:
        self.plugin = plugin
        self.fullname = fullname
        self.super_hook = super_hook
        self.extra_init()

    def extra_init(self) -> None: ...

    @abc.abstractmethod
    def run(self, ctx: T_Ctx) -> T_Ret: ...

    @abc.abstractmethod
    def choose(self) -> bool: ...

    def hook(self) -> Callable[[T_Ctx], T_Ret] | None:
        """
        This is the function that mypy ends up calling when asking the plugin
        if it should handle something.
        """
        if self.choose():
            return self.run
        else:
            return self.super_hook


class hook(Generic[T_Plugin, T_Ctx, T_Ret]):
    """
    This is a descriptor classes used to return a callable object that takes in
    a string and either returns a function that mypy can use to perform an action,
    or return None if this hook does not need to do anything in that instance.
    """

    def __init__(self, hook: type[Hook[T_Plugin, T_Ctx, T_Ret]]) -> None:
        self.hook = hook
        self.__doc__ = hook.__doc__

    name: str

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.owner = owner

    @overload
    def __get__(self, instance: None, owner: None) -> hook[T_Plugin, T_Ctx, T_Ret]: ...

    @overload
    def __get__(self, instance: T_Plugin, owner: type[T_Plugin]) -> _HookChooser[T_Ctx, T_Ret]: ...

    def __get__(
        self, instance: T_Plugin | None, owner: type[T_Plugin] | None = None
    ) -> hook[T_Plugin, T_Ctx, T_Ret] | _HookChooser[T_Ctx, T_Ret]:
        if instance is None:
            return self

        super_hook = getattr(super(self.owner, instance), self.name)

        def result(fullname: str) -> Callable[[T_Ctx], T_Ret] | None:
            return self.hook(
                plugin=instance,
                fullname=fullname,
                super_hook=super_hook(fullname),
            ).hook()

        return result
