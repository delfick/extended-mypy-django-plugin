Actions
-------

The logic that glues together the annotations to be resolved with the resolved
types lives within the ``actions`` subpackage of the plugin.

All the hooks for a mypy plugin will have an ``api`` on the context that is provided
(except ``report_config_data`` and ``get_additional_deps`` and these ``api``
objects are either a ``SemanticAnalyzerPluginInterface``, ``TypeAnalyzerPluginInterface``
or a ``CheckerPluginInterface``.

Curently, in practice though these are going to the specific concrete variants
of these:

* ``SemanticAnalyzerPluginInterface`` is a ``mypy.semanal.SemanticAnalyzer``
* ``TypeAnalyzerPluginInterface`` is a ``mypy.typeanal.TypeAnalyser``
* ``CheckerPluginInterface`` is a ``mypy.checker.TypeChecker``

The plugin will assert that this is the case before passing them into an
instance of the one of the classes in the actions folder to do the work.

There is a class for each of these Interfaces:

.. autoclass:: extended_mypy_django_plugin.plugin.actions._sem_analyze.SemAnalyzing

.. autoclass:: extended_mypy_django_plugin.plugin.actions._sem_analyze.TypeAnalyzer

.. autoclass:: extended_mypy_django_plugin.plugin.actions._type_checker.TypeChecking

The specifics of what they do in this plugin has yet to be documented. More
information of the structure of a mypy plugin is best done by reading the mypy
source code.

Specifically the module level do comment of:

* https://github.com/python/mypy/blob/1.9.0/mypy/plugin.py
* https://github.com/python/mypy/blob/1.9.0/mypy/semanal.py

And plugins that can be found:

* https://github.com/python/mypy/tree/1.9.0/mypy/plugins
* https://github.com/typeddjango/django-stubs
* https://github.com/dry-python/returns/blob/master/returns/contrib/mypy/returns_plugin.py
