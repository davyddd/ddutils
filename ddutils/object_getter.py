import importlib
from typing import Any


def get_object_by_path(path: str | None) -> Any:
    try:
        if not isinstance(path, str):
            raise ValueError
        module_path, object_name = path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        _object = getattr(module, object_name)
    except (ModuleNotFoundError, AttributeError, ValueError):
        _object = None

    return _object
