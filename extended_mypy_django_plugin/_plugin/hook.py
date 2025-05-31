"""
The helpers under ``extended_mypy_django_plugin.plugin.hooks`` exist as a helper
for defining hooks on a mypy plugin.

The way a mypy plugin works is there is a class that inherits from
``mypy.plugin.Plugin`` with specific hooks that take in a string and returns
a function.

So for example, the ``get_customize_class_mro_hook`` hook will take in the
``fullname`` representing classes that can be altered, and a function must be
returned if the plugin wants to do something with that object (such that the
function takes in a single ``ClassDefContext`` object and returns ``None``).

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
    from extended_mypy_django_plugin.plugin import hook


    class MyPlugin(Plugin):
        @hook.hook
        class get_attribute_hook(hook.Hook["MyPlugin", AttributeContext, MypyType]):
            def choose(
                self, *, fullname: str, super_hook: hook.MypyHook[AttributeContext, MypyType]
            ) -> bool:
                # return True if we want to use the run method for ``self.fullname``.
                # With super_hook being the result of `super().get_attribute_hook(fullname)` on the plugin
                return self.fullname.endswith(".blah")

            def run(self, ctx: AttributeContext) -> MypyType:
                # Do stuff
                return ...

The :class:`extended_mypy_django_plugin.plugin.hook.hook` decorator turns that
attribute into a descriptor that will cache an instance
of the ``Hook`` with the instance of the plugin and that hook on the parent class
(useful when the mypy plugin is subclassing an existing mypy plugin)

The descriptor will then return the ``hook`` method on the Hook, which matches the required
signature for the hook.

There are two default implementations of this Hook class:

.. autoclass:: PlainHook
    :no-index:

.. autoclass:: HookWithExtra
    :no-index:

And they must be used with the :class:`hook <hook>` decorator:

.. autoclass:: hook(hook_kls: type[Hook[T_Plugin, T_Ctx, T_Ret]])
    :no-index:
"""

from __future__ import annotations

import abc
import dataclasses
import functools
from collections.abc import Callable
from typing import Generic, Literal, TypeVar, overload

from mypy.plugin import Plugin

T_Ctx = TypeVar("T_Ctx")
T_Ret = TypeVar("T_Ret")
T_Extra = TypeVar("T_Extra")
T_Plugin = TypeVar("T_Plugin", bound=Plugin)


Choice = Literal[False] | tuple[Literal[True], T_Extra]
MypyHook = Callable[[T_Ctx], T_Ret] | None
MypyHookMaker = Callable[[str], MypyHook[T_Ctx, T_Ret]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class Hook(Generic[T_Plugin, T_Ctx, T_Ret], abc.ABC):
    """
    Class used to represent both the choosing and running logic for a hook
    on a mypy Plugin.

    This is to be used with the ``hook`` descriptor defined below. See the
    docstring on the module for more information.

    Concrete subclasses of this must implement ``hook``.
    """

    plugin: T_Plugin
    super_hook_maker: MypyHookMaker[T_Ctx, T_Ret]

    @abc.abstractmethod
    def hook(self, fullname: str) -> MypyHook[T_Ctx, T_Ret]:
        """
        This is the function that mypy ends up calling when asking the plugin
        if it should handle something.
        """


@dataclasses.dataclass(frozen=True, kw_only=True)
class HookWithExtra(
    Generic[T_Plugin, T_Ctx, T_Extra, T_Ret], Hook[T_Plugin, T_Ctx, T_Ret], abc.ABC
):
    """
    This is an implementation of Hook that allows passing information from the choose
    method into the run method.

    Mypy plugins work by implementing methods that take in a string and either return a callable
    that takes action, or returns None. Whichever plugin returns a function first wins.

    This hook class splits the two parts into two methods: deciding if we should choose this hook
    and the running of the logic.

    This implementation in particular also allows passing information from the choosing part into the running
    part:

    .. code-block:: python

        from typing import Generic
        from mypy.plugin import Plugin, AttributeContext
        from mypy.types import Type as MypyType
        from extended_mypy_django_plugin.plugin import hook


        class MyPlugin(Plugin):
            @hook.hook
            class get_attribute_hook(hook.HookWithExtra["MyPlugin", AttributeContext, str, MypyType]):
                def choose(
                    self, *, fullname: str, super_hook: hook.MypyHook[AttributeContext, MypyType]
                ) -> hook.Choice[str]:
                    if fullname.startswith("things"):
                        return True, "one"
                    elif fullname.startswith("other"):
                        return True, "two"
                    else:
                        return False

                def run(
                    self,
                    ctx: AttributeContext,
                    *,
                    fullname: str,
                    super_hook: hook.MypyHook[AttributeContext, MypyType],
                    extra: str,
                ) -> MypyType:
                    # at this point, extra will either be "one" or "two"

                    # Do stuff
                    return ...

    The type of the data passed between ``choose`` and ``run`` is specified when filling out the Generic.

    When the plugin runs the ``hook`` method on this implementation, it will determine what
    the parent class would return from this hook, get a result from ``choose`` from the ``fullname``
    and that ``super_hook`` and either return ``super_hook`` if the ``choose`` returned ``False``
    or return ``functools.partial(self.run, fullname=fullname, super_hook=super_hook, extra=extra)``
    where extra is the second item in a ``(True, extra)`` tuple returned from ``choose``.
    """

    @abc.abstractmethod
    def run(
        self,
        ctx: T_Ctx,
        *,
        fullname: str,
        super_hook: MypyHook[T_Ctx, T_Ret],
        extra: T_Extra,
    ) -> T_Ret: ...

    @abc.abstractmethod
    def choose(self, *, fullname: str, super_hook: MypyHook[T_Ctx, T_Ret]) -> Choice[T_Extra]: ...

    def hook(self, fullname: str) -> MypyHook[T_Ctx, T_Ret]:
        """
        This is the function that mypy ends up calling when asking the plugin
        if it should handle something.
        """
        super_hook = self.super_hook_maker(fullname)
        result = self.choose(fullname=fullname, super_hook=super_hook)
        if result is False:
            return super_hook
        else:
            return functools.partial(
                self.run, fullname=fullname, super_hook=super_hook, extra=result[1]
            )


@dataclasses.dataclass(frozen=True, kw_only=True)
class PlainHook(Hook[T_Plugin, T_Ctx, T_Ret], abc.ABC):
    """
    This is an implementation of ``Hook`` that does the bare minimum.

    It's ``hook`` method will determine what would have been returned for this hook from
    the parent class and pass the ``fullname`` and that ``super_hook`` to ``choose``.

    If ``choose`` returns ``False``, then ``hook`` returns the ``super_hook``, otherwise
    it returns ``self.run``.
    """

    @abc.abstractmethod
    def run(self, ctx: T_Ctx) -> T_Ret: ...

    @abc.abstractmethod
    def choose(self, *, fullname: str, super_hook: MypyHook[T_Ctx, T_Ret]) -> bool: ...

    def hook(self, fullname: str) -> MypyHook[T_Ctx, T_Ret]:
        """
        This is the function that mypy ends up calling when asking the plugin
        if it should handle something.
        """
        super_hook = self.super_hook_maker(fullname)
        result = self.choose(fullname=fullname, super_hook=super_hook)
        if result is False:
            return super_hook
        else:
            return self.run


@dataclasses.dataclass
class hook(Generic[T_Plugin, T_Ctx, T_Ret]):
    """
    This is a class decorator used to return a callable object that takes in
    a string and either returns a function that mypy can use to perform an action,
    or return None if this hook does not need to do anything in that instance.

    It is used as a decorator for a subclass of ``Hook`` and will cache an instance
    of that hook between multiple access of the descriptor
    """

    hook_kls: type[Hook[T_Plugin, T_Ctx, T_Ret]]

    name: str = dataclasses.field(init=False)
    owner: type = dataclasses.field(init=False)

    _hook_instance: Hook[T_Plugin, T_Ctx, T_Ret] | None = dataclasses.field(
        default=None, init=False
    )

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.owner = owner
        self.__doc__ = self.hook_kls.__doc__

    @overload
    def __get__(self, instance: None, owner: None) -> hook[T_Plugin, T_Ctx, T_Ret]: ...

    @overload
    def __get__(
        self, instance: T_Plugin, owner: type[T_Plugin]
    ) -> MypyHookMaker[T_Ctx, T_Ret]: ...

    def __get__(
        self, instance: T_Plugin | None, owner: type[T_Plugin] | None = None
    ) -> hook[T_Plugin, T_Ctx, T_Ret] | MypyHookMaker[T_Ctx, T_Ret]:
        if instance is None:
            return self

        if self._hook_instance is None:
            self._hook_instance = self.hook_kls(
                # We use self.owner cause we want the class where the descriptor was used
                # Rather than the class of the instance the attribute was accessed on
                plugin=instance,
                super_hook_maker=getattr(super(self.owner, instance), self.name),
            )

        return self._hook_instance.hook


__all__ = ["Choice", "Hook", "HookWithExtra", "MypyHook", "MypyHookMaker", "PlainHook", "hook"]
