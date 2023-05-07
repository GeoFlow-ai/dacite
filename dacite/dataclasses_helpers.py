from dataclasses import Field, MISSING, _FIELDS, _FIELD, _FIELD_INITVAR  # type: ignore
from typing import Type, Any, TypeVar, List

from dacite.cache import cache
from dacite.types import is_optional

T = TypeVar("T", bound=Any)


class DefaultValueNotFoundError(Exception):
    pass


def get_default_value_for_field(field: Field, type_: Type) -> Any:
    if field.default != MISSING:
        return field.default
    elif field.default_factory != MISSING:  # type: ignore
        return field.default_factory()  # type: ignore
    elif is_optional(type_):
        return None
    raise DefaultValueNotFoundError()


@cache
def get_fields(data_class: Type[T]) -> List[Field]:
    fields = getattr(data_class, _FIELDS)
    return [f for f in fields.values() if f._field_type is _FIELD or f._field_type is _FIELD_INITVAR]


@cache
def is_frozen(data_class: Type[T]) -> bool:
    return data_class.__dataclass_params__.frozen

def has(path: str, dicts: dict[str, Any]) -> bool:
    return _has(path.split('.'), dicts)


def _has(path: list[str], dicts: dict[str, Any]) -> bool:
    p = path.copy()
    d = dicts.copy()

    while len(p) > 1:
        if p[0] not in d:
            return False
        d = d[p[0]]

        if not isinstance(d, dict):
            return False

        p = p[1:]

    return p[0] in d


def get(path: str, dicts: dict[str, Any], default: Any=KeyError()) -> Any:
    """
    get the given path from nested dicts. If the field is missing, look
    at the value for default. If it's set to an Exception, raise that, else
    return the default.
    """
    return _get(path.split('.'), dicts, default)


def _get(path: list[str], dicts: dict[str, Any], default: Any=KeyError()) -> Any:
    p = path.copy()
    d = dicts.copy()

    while len(p) > 1:
        if p[0] not in d:
            if isinstance(default, Exception):
                raise default

            return default

        d = d[p[0]]

        if not isinstance(d, dict):
            raise KeyError(f"element is not a dict: {p[0]}")

        p = p[1:]

    if p[0] in d:
        return d[p[0]]

    if isinstance(default, Exception):
        raise default

    return default
