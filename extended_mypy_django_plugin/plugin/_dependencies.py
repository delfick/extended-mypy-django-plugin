from ._reports import ModelModules, ReportNamesGetter

Dep = tuple[int, str, int]
DepList = list[tuple[int, str, int]]


class Dependencies:
    """
    This object is used to determine if a model is known, and also what
    dependencies to return for a file for the get_additional_deps hook
    """

    def __init__(
        self, model_modules: ModelModules, report_names_getter: ReportNamesGetter
    ) -> None:
        self._model_modules = model_modules
        self._report_names_getter = report_names_getter

    def is_model_known(self, fullname: str) -> bool:
        for mod, known in self._model_modules.items():
            for cls in known.values():
                if fullname == f"{cls.__module__}.{cls.__qualname__}":
                    return True

        return False
