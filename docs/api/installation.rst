Installation
============

Install from pypi::

    python -m pip install extended-mypy-django-plugin

Enabling this plugin in a project is adding either to ``mypy.ini``:

.. code-block:: ini

    [mypy]
    plugins =
        extended_mypy_django_plugin.main
    mypy_path = $MYPY_CONFIG_FILE_DIR/path/for/virtual_dependencies

    [mypy.plugins.django-stubs]
    # scratch path is mandatory and will be used to write virtual dependencies into
    # it must also be added to the MYPY_PATH
    scratch_path = $MYPY_CONFIG_FILE_DIR/path/for/virtual_dependencies

    # Optional path to a script used to determine if the state of django has changed
    # This is used when running in daemon mode to know if the daemon needs to be restarted
    django_settings_module = $MYPY_CONFIG_FILE_DIR/path/to/script.py

Or to ``pyproject.toml``:

.. code-block:: toml

    [tool.mypy]
    plugins = ["extended_mypy_django_plugin.main"]
    mypy_path = "$MYPY_CONFIG_FILE_DIR/path/for/virtual_dependencies"

    [tool.django-stubs]
    # See comments in mypy.ini example above
    scratch_path = "$MYPY_CONFIG_FILE_DIR/path/for/virtual_dependencies"
    django_settings_module = "$MYPY_CONFIG_FILE_DIR/path/to/script.py"

.. note:: This project adds a mandatory setting ``scratch_path`` that
   will be where the mypy plugin will write files to for the purpose of
   understanding when the mypy daemon needs to be restarted
