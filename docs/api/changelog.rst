.. _changelog:

Changelog
---------

.. _release-0.7.0:

0.7.0 - 8 July 2024

    * The ``Concrete.cast_as_concrete`` helper is now handled by a different mypy plugin
      hook. This lets the helper understand type vars and it lets it handle more
      complicated inputs.

      However it means that in methods when using it to override ``self`` and ``cls``
      that we can no longer override those variables. In these cases use a different
      variable name as the result.
    * Removed Concrete.type_var. Can use
      ``TypeVar("T_Model", bound=Concrete[Model])`` instead
    * Previous versions would create an implicit ``# type: ignore[return-value]`` on the
      return statement of methods/functions that returned a concrete annotation of a
      type var. This is no longer the case.
    * Removed the ability to annotate type vars

.. _release-0.6.4:

0.6.4 - 4 July 2024
    * Improved error messages when using ``Concrete.cast_as_concrete`` and ``Concrete.type_var``
    * Ensure that ``Concrete.type_var`` is only used in the module scope
    * Fixed a bug where it's possible for virtual dependency cleanup to try remove a file
      that doesn't exist
    * Various small cleanups

.. _release-0.6.3:

0.6.3 - 1 June 2024
    * Fixed a bug with resolving Concrete annotations at the module scope

.. _release-0.6.2:

0.6.2 - 27 June 2024
    * Make sure that mypy/dmypy clear caches when a new version of the plugin is installed.
    * Using ``Concrete.cast_as_concrete`` with something that isn't a NameExpr will give an explicit error
    * Some of the mypy specific code was cleaned up, but should remain functionally the same

.. _release-0.6.1:

0.6.1 - 26 June 2024
    * Fix bug where ``Concrete.type_var("T_Name", model.Name)`` wouldn't work because the plugin
      couldn't resolve ``model.Name``
    * Fix bug where untyped arguments in a function that returns a concrete type var would crash
      the plugin
    * Improved mypy performance by realising we can give drastically less additional deps for files

.. _release-0.6.0:

0.6.0 - 20 June 2024
    * The extra configuration now relies on the config using a ``$MYPY_CONFIG_FILE_DIR``
      marker rather than assuming the paths are relative to the configuration.
    * Removed the need to specify a script for determining django state
    * The plugin provider now takes in an object that will be used to determine django state
      and this is used for both the plugin itself and for what the determine state script was
      doing.
    * Fixed a bug where using a concrete annotation on a model where that model is defined would
      mean that additional concrete models are not seen when they are added

.. _release-0.5.5:

0.5.5 - 6 June 2024
    * Make it possible to restart dmypy if settings names/types change

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
