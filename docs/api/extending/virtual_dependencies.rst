.. _virtual_dependencies:

Virtual Dependencies
====================

As mentioned in :ref:`tracking_changes` this plugin creates "virtual" dependencies
so that ``mypy`` we re-analyse particular parts of the Django project that
otherwise wouldn't be looked at again when other parts of the project change.

For example, let's say the project has a Django App that defines the abstract
model ``MyAbstractModel`` and a separate app that defines ``ConcreteOne`` that
inherits this abstract model. If there are any ``Concrete[MyAbstractModel]``
annotations where that abstract model is defined, it is desirable for that
annotation is changed when another concrete model is added, either through adding
to the existing django app, or adding a new app. Or even, if ``ConcreteOne`` or
the Django app it is in is deleted.

Without changes to the interface that ``mypy`` plugins have access to there is
no way of forcing mypy to do that re-analysis without having a file the plugin
can write to that ``mypy`` knows about when the file containing the abstract
model is first seen.

This ``mypy`` plugin adds a mandatory ``scratch_path`` setting that defines a
specific folder that the mypy plugin may write to. Then every python module
that contains a Django model will get an equivalent file in this folder.

These files will either look something like this if it's part of an installed app:

.. code-block:: python

    def interface__1727419768_657105() -> None:
        return None

    mod = "django.contrib.auth.base_user"
    summary = "__virtual__.mod_2833058650::django.contrib.auth.base_user::installed_apps=__installed_apps_hash__::significant=3626250221"

    import django.contrib.auth.base_user
    import django.contrib.auth.models
    import django.db.models
    ConcreteQuerySet__AbstractBaseUser = django.db.models.QuerySet[django.contrib.auth.models.User]
    Concrete__AbstractBaseUser = django.contrib.auth.models.User

or something like this if it's not an installed app but still part of the static
analysis:

.. code-block::

    mod = "my_company.some.module"
    summary = "||not_installed||"

These files will contain the unions that the
:class:`Concrete <extended_mypy_django_plugin.Concrete>` will end up resolving to
and this ``mypy`` plugin will register these files using the ``get_additional_deps``
hook.

Then when the mypy plugin starts up and does Django introspection to discover the
available models, any changes to these files will change the public interface
making ``mypy`` believe that the files that depend on these need to be
re-analysed.

Given discovery depends on how Django starts up, that is functionality that
can be customised by projects using the mypy plugin.

Changing discovery
------------------

To change discovery logic, instead of directly adding this plugin to mypy options
by adding the following:

.. code-block:: ini

    [mypy]
    plugins =
        extended_mypy_django_plugin.main

The project author should instead create their own mypy plugin based off
this one.

For example, to make this plugin work for a project that uses ``django-configurations``
see the code here: https://github.com/delfick/extended-mypy-django-plugin/tree/django-configurations-example

Essentially a new module is added to the environment that extends the plugin in
a number of ways.

It shows:

* Discovery of the project/settings
* Assigning types to settings in an extended ``get_attribute_hook``
* Changing the logic used by the plugin with the information from the discovery
* Creating a plugin provider that joins the custom mypy plugin and virtual
  dependency logic
* Programmatically using the virtual dependency code for other uses

The Report
----------

This plugin operates on an object that represents what models are in the project
and this object is called the "report". There are two sides to this object:

* :protocol:`extended_mypy_django_plugin.django_analysis.protocols.Report`
* :protocol:`extended_mypy_django_plugin.plugin.protocols.Report <extended_mypy_django_plugin._plugin.protocols.Report>`

The first is from the code that is doing django analysis. This happens outside
of the ``mypy`` plugin and knows about ``django`` specific concepts. The other
side is from the ``mypy`` plugin itself and isn't in terms of ``django``
specific concepts.

The idea is that if ``django-stubs`` itself didn't also depend on django introspection
then the second interface can be serialised and sent between different processes
allowing us to have our own daemon for Django introspection. If this were possible
then changes to the Django process would not require restarting the dmypy daemon.

Currently these two interfaces are satisfied by the same object but statically
only the django analysis code sees the methods in the first interface, and only
the mypy plugin sees the methods in the second interface.

To change the behaviour of this report requires overriding the ``get_report_maker``
hook on the ``VirtualDependencyHandler`` that is passed to the plugin provider.

The plugin provider
-------------------

The :class:`plugin provider <extended_mypy_django_plugin._plugin.entry.PluginProvider>` 
is an object that connects the mypy plugin with the ``VirtualDependencyHandler``.

It has these responsibilities:

* Creating a :protocol:`report <extended_mypy_django_plugin._plugin.protocols.Report>`
  to give to an instance of the mypy plugin
* Provide an instance of the mypy plugin to mypy
* Determine if the dmypy plugin should be restarted

This object takes advantage of the fact that dmypy will restart if the ``version``
property next to ``plugin`` changes (in this case ``plugin`` is the instance of
the plugin provider). So on subsequent runs of dmypy the plugin provider will
start a subprocess that creates the report and determines if it is different than
the previous run of dmypy. If the version is different, the ``locals()`` instance
passed into the plugin provider is modified such that the ``version`` in that
module is different. In an ideal world we instead had mypy being able to natively
supported this ability.

That external process will find the instance of the plugin provider (by looking
at the mypy configuration to discover all the activated plugins) and is able
to access the ``VirtualDependencyHandler`` off that instance to do the django
analysis required to generate a report.
