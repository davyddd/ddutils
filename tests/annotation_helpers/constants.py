# Both the legacy `typing` spelling and the builtin generics are under test here, so pyupgrade is silenced on purpose.
from typing import Dict, List, NewType, Optional, Union  # noqa: UP035

COMMON_PYTHON_TYPES = (bool, int, float, str, tuple, list, dict)

OPTIONAL_INT_ANNOTATIONS = [(Optional[int],), (Union[int, None],), (int | None,)]  # noqa: UP007, UP045

# List annotations

ListAnnotationNotNative = List[int]  # noqa: UP006
ListAnnotationNative = list[int]
CustomListNotNative = NewType('CustomListNotNative', ListAnnotationNotNative)
CustomListNative = NewType('CustomListNative', ListAnnotationNative)

GENERIC_LIST_ANNOTATIONS = [
    (ListAnnotationNotNative,),
    (ListAnnotationNative,),
    (CustomListNotNative,),
    (CustomListNative,),
]

# Dict annotations

DictAnnotationNotNative = Dict[str, int]  # noqa: UP006
DictAnnotationNative = dict[str, int]
CustomDictNotNative = NewType('CustomDictNotNative', DictAnnotationNotNative)
CustomDictNative = NewType('CustomDictNative', DictAnnotationNative)

GENERIC_DICT_ANNOTATIONS = [
    (DictAnnotationNotNative,),
    (DictAnnotationNative,),
    (CustomDictNotNative,),
    (CustomDictNative,),
]
