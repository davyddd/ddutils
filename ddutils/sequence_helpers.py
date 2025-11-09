from collections.abc import Sequence
from typing import Any


def get_safe_element(seq: Sequence[Any], index: int) -> Any:
    try:
        return seq[index]
    except IndexError:
        return None
