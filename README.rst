Example of extending extended mypy django plugin
================================================

This is an example of extending the extended-mypy-django-plugin to support using
``django-configurations`` for settings.

To run::

    > uv sync
    > uv run mypy .

And it should output

.. code-block::

    djangoexample/views.py:6: note: Revealed type is "typing.Mapping[builtins.str, builtins.int]"
    Success: no issues found in 23 source files

It is configured by enabling the ``example_mypy.main`` plugin in ``mypy.ini``
and setting the ``mypy.mypy_path`` option and the ``mypy.plugins.django-stubs``
section. All the custom code is then under ``./tools/example-mypy/example_mypy``.

There are four files in this module that do the work:

* ``main.py``
* ``plugin.py``
* ``logic.py``
* ``virtual_dependencies.py``

main.py
-------

This is the entry point to the plugin. It defines a ``plugin`` variable that is
an instance of the ``PluginProvider`` from ``extended-mypy-django-plugin`` and
it joins together the logic in ``plugin.py`` and ``virtual_dependencies.py``

plugin.py
---------

This is the plugin from ``extended-mypy-django-plugin`` with some extra logic
for the ``get_attribute_hook`` hook that uses logic from ``logic.py`` to
find the types for custom django settings that are introduced on the base
``django-configurations`` settings class.

logic.py
--------

Contains logic for resolving a django setting.

virtual_dependencies.py
-----------------------

This defines at the bottom of the file a custom ``VirtualDependencyHandler``
class which knows how to load a ``django-configurations`` project and do
settings discovery on a ``django-configurations`` class.

It also defines a custom ``ReportMaker``, that has some extra logic used by
``extended-mypy-django-plugin`` when determining the result for the
``get_additional_deps`` plugin. This extra logic ensures that any file that
depends on ``django.conf.settings`` also depends on our base ``django-configurations``
class defined in ``djangoexample.settings.base``.

Using the VirtualDependencyHandler class
----------------------------------------

Note that the code in ``virtual_dependencies.py`` can be repurposed in code
that wants to discover settings/models in the django project.

For example, if the Django project isn't already loaded:

.. code-block:: python

    from example_mypy.virtual_dependencies import VirtualDependencyHandler

    project = VirtualDependencyHandler.make_project(
        project_root=PROJECT_ROOT, django_settings_module="djangoexample.settings"
    )

    discovered = project.load_project().perform_discovery()

    # discovered is now an instance of ``extended_mypy_django_plugin.django_analysis.Discovered
    # and has a number of things on it

Or if inside tests for the django project and Django is already loaded:

.. code-block:: python

    from example_mypy.virtual_dependencies import VirtualDependencyHandler
    from extended_mypy_django_plugin.django_analysis import Loaded
    from django.apps import apps
    from django.conf import settings

    project = VirtualDependencyHandler.make_project(
        project_root=PROJECT_ROOT, django_settings_module="djangoexample.settings"
    )

    loaded_project = Loaded(
        project=project,
        root_dir=project.root_dir,
        env_vars=project.env_vars,
        settings=settings,
        apps=apps,
        discovery=project.discovery,
    )

    discovered = loaded_project.perform_discovery()

What happens during discovery can also be changed. For example, see
``scripts/ensure_unique_querysets.py``.
