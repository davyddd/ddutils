import ast
import builtins
import inspect
import textwrap
from importlib import import_module
from typing import Any, Callable, Dict, Generator, NamedTuple, Optional, Tuple, Type

from ddutils.module_getter import get_module

UNDEFINED_VALUE = object()


class Annotation(NamedTuple):
    argument: str
    default_value: Any

    def is_empty(self) -> bool:
        return self.default_value is inspect._empty


class ExceptionInfo:
    exception_class: Type[Exception]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]

    def __init__(self, exception_class: Type[Exception], args: Tuple[Any, ...], kwargs: Dict[str, Any]):
        self.exception_class = exception_class
        self.args = tuple(_v.value if isinstance(_v, ast.Constant) else UNDEFINED_VALUE for _v in args)
        self.kwargs = {_k: _v.value if isinstance(_v, ast.Constant) else UNDEFINED_VALUE for _k, _v in kwargs.items()}

    def get_kwargs(self) -> Dict[str, Any]:
        annotations = tuple(
            Annotation(argument, argument_info.default)
            for argument, argument_info in inspect.signature(self.exception_class.__init__).parameters.items()
            if argument not in {'self', 'args', 'kwargs'}
        )
        kwargs = {
            **{annotation.argument: self.args[item] for item, annotation in enumerate(annotations[: len(self.args)])},
            **self.kwargs,
        }
        for annotation in annotations:
            if annotation.argument not in kwargs:
                if not annotation.is_empty():
                    kwargs[annotation.argument] = annotation.default_value
                elif hasattr(self.exception_class, annotation.argument):
                    kwargs[annotation.argument] = getattr(self.exception_class, annotation.argument)
                else:
                    kwargs[annotation.argument] = UNDEFINED_VALUE

        del annotations

        return kwargs

    def get_exception_instance(self, dry_run: bool = True) -> Optional[Exception]:
        kwargs = {k: f'<{k}>' if v is UNDEFINED_VALUE else v for k, v in self.get_kwargs().items()}
        try:
            # There might be issues with strict typing because UNDEFINED_VALUE is always replaced with a string
            return self.exception_class(**kwargs)
        except Exception as err:  # noqa: BLE001
            if dry_run:
                return None
            else:
                raise err


def _get_node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f'{_get_node_name(node.value)}.{node.attr}'
    elif isinstance(node, ast.Call):
        return _get_node_name(node.func)
    else:
        raise TypeError(f'Unsupported node type: {type(node)}')


def extract_function_exceptions(func: Callable) -> Generator[ExceptionInfo, None, None]:
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            if node.exc is None:
                continue

            try:
                exception_name: str = _get_node_name(node.exc)
                exception_args: Tuple[Any, ...] = ()
                exception_kwargs: Dict[str, Any] = {}
            except TypeError:
                continue

            if isinstance(node.exc, ast.Call):
                exception_args = tuple(node.exc.args)
                exception_kwargs = {kw.arg: kw.value for kw in node.exc.keywords if isinstance(kw.arg, str)}

            exception_name_slices = exception_name.split('.')
            class_name = exception_name_slices[-1]
            sub_modules = exception_name_slices[:-1]

            exception_module = get_module(import_module(func.__module__), sub_modules)

            exception_class: Optional[Type[Exception]] = getattr(exception_module, class_name, None)
            if exception_class is None and hasattr(builtins, exception_name):
                exception_class = getattr(builtins, exception_name)

            if exception_class is None:
                continue

            yield ExceptionInfo(exception_class=exception_class, args=exception_args, kwargs=exception_kwargs)
