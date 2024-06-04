.. _changelog:

Changelog
---------

.. _release-0.5.4:

0.5.4 - 4 June 2024
    * Will now check return types for methods and functions more thorouhgly
    * Will throw errors if a type guard is used with a concrete annotation that uses
      a type var (mypy plugin system is limited in a way that makes this impossible to implement)
    * The concrete annotations understand ``type[Annotation[inner]]`` and ``Annotation[type[inner]]``
      better now and will do the right thing
    * When an annotation would transform into a Union of one item, now it becomes that one item
    * Removed ``ConcreteQuerySet`` and made ``DefaultQuerySet`` take on that functionality
    * Concrete annotations now work with the Self type
    * Implemented Concrete.cast_as_concrete
    * Concrete.type_var can now take a forward reference to the model being represented
    * Implemented more scenarios where Concrete.type_var may be used
    * Handle failure of the script for determining the version without crashing dmypy

.. _release-0.5.3:

0.5.3 - 25 May 2024
    * Resolve Invalid cross-device link error when default temporary folder
      is on a different device to the scratch path.
    * Add a fix for a weird corner case in django-stubs where a certain pattern
      of changes after a previous dmypy run would crash dmypy

.. _release-0.5.2:

0.5.2 - 22 May 2024
    * Add more confidence get_function_hook doesn't steal from django-stubs

.. _release-0.5.1:

0.5.1 - 21 May 2024
    * Providing a return code of 2 from the installed_apps script will make dmypy not
      change version to cause a restart.
    * Changed the ``get_installed_apps`` setting to be ``determine_django_state``
    * Changed the name in pyproject.toml to use dashes instead of underscores

.. _release-0.5.0:

0.5.0 - 19 May 2024
    * ``Concrete``, ``ConcreteQuerySet``, ``DefaultQuerySet`` and ``Concrete.type_var``
    * Better support for running the plugin in the ``mypy`` daemon.
