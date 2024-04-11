import operator
from dataclasses import is_dataclass
from functools import reduce
from itertools import zip_longest
from types import GenericAlias
from typing import TypeVar, Type, Optional, get_type_hints, Mapping, Any, Collection, MutableMapping, _GenericAlias

from dacite.cache import cache
from dacite.config import Config
from dacite.data import Data
from dacite.dataclasses_helpers import (
    get_default_value_for_field,
    DefaultValueNotFoundError,
    get_fields,
    is_frozen,
    has,
    get,
)
from dacite.exceptions import (
    ForwardReferenceError,
    WrongTypeError,
    DaciteError,
    UnionMatchError,
    MissingValueError,
    DaciteFieldError,
    UnexpectedDataError,
    StrictUnionMatchError, )
from dacite.types import (
    is_instance,
    is_generic_collection,
    is_union,
    extract_generic,
    is_optional,
    extract_origin_collection,
    is_init_var,
    extract_init_var,
    is_subclass,
)

T = TypeVar("T")



def from_dict(data_class: Type[T], data: Data, config: Optional[Config] = None) -> T:
    """Create a data class instance from a dictionary.

    :param data_class: a data class type
    :param data: a dictionary of a input data
    :param config: a configuration of the creation process
    :return: an instance of a data class
    """
    init_values: MutableMapping[str, Any] = {}
    post_init_values: MutableMapping[str, Any] = {}
    config = config or Config()
    try:
        data_class_hints = cache(get_type_hints)(data_class, localns=config.hashable_forward_references)
    except NameError as error:
        raise ForwardReferenceError(str(error))
    data_class_fields = cache(get_fields)(data_class)
    if config.strict:
        extra_fields = set(data.keys()) - {f.name for f in data_class_fields}
        if extra_fields:
            raise UnexpectedDataError(keys=extra_fields)
    for field in data_class_fields:
        field_type = data_class_hints[field.name]

        if data_class in config.paths and field.name in config.paths[data_class]:
            path_or_paths = config.paths[data_class][field.name]

            if "SKIPME" == path_or_paths: continue

            try:
                default = get_default_value_for_field(field, field_type)
            except DefaultValueNotFoundError:
                default = DefaultValueNotFoundError(f"failed to find path and no default set for: {path_or_paths} in: {data}")

            # TODO: use DaciteFieldError as directly below:
            deep_field_data = _get_deep_value(data=data,
                                              path_or_paths=path_or_paths,
                                              default=default)

            value = _build_value(type_=field_type, data=deep_field_data, config=config)
        elif field.name in data:
            try:
                field_data = data[field.name]
                value = _build_value(type_=field_type, data=field_data, config=config)
            except DaciteFieldError as error:
                error.update_path(field.name)
                raise
            if config.check_types:
                if config.allow_superclasses and is_union(field_type):
                    types = extract_generic(field_type)
                    is_sub = reduce(operator.or_, [issubclass(inner_type, type(value)) for inner_type in types])

                    if not is_sub:
                        raise WrongTypeError(field_path=field.name, field_type=field_type, value=value)
                elif isinstance(field_type, GenericAlias) or isinstance(field_type, _GenericAlias):
                    generic_type = field_type.__origin__

                    # TODO: handle other container types, like dict!
                    if generic_type == list:
                        contained_type = field_type.__args__[0]
                        if type(value) is not list:
                            raise WrongTypeError(field_path=field.name, field_type=field_type, value=value)
                        if len(value) > 0 and not issubclass(field_type.__args__[0], type(value[0])):
                            raise WrongTypeError(field_path=field.name, field_type=field_type, value=value)
                elif config.allow_superclasses and issubclass(field_type, type(value)):
                    pass
                elif not is_instance(value, field_type):
                    raise WrongTypeError(field_path=field.name, field_type=field_type, value=value)
        else:
            try:
                value = get_default_value_for_field(field, field_type)
            except DefaultValueNotFoundError:
                if not field.init:
                    continue
                raise MissingValueError(field.name)
        if field.init:
            init_values[field.name] = value
        elif not is_frozen(data_class):
            post_init_values[field.name] = value
    instance = data_class(**init_values)
    for key, value in post_init_values.items():
        setattr(instance, key, value)
    return instance


def _build_value(type_: Type, data: Any, config: Config) -> Any:
    if is_init_var(type_):
        type_ = extract_init_var(type_)
    if type_ in config.type_hooks:
        data = config.type_hooks[type_](data)
    if is_optional(type_) and data is None:
        return data
    if is_union(type_):
        data = _build_value_for_union(union=type_, data=data, config=config)
    elif is_generic_collection(type_):
        data = _build_value_for_collection(collection=type_, data=data, config=config)
    elif cache(is_dataclass)(type_) and isinstance(data, Mapping):
        data = from_dict(data_class=type_, data=data, config=config)

    casted = False
    for cast_type in config.cast:
        if is_subclass(type_, cast_type):
            if is_generic_collection(type_):
                data = extract_origin_collection(type_)(data)
                casted = True
            else:
                data = type_(data)
                casted = True
            break
    # TODO: do other types, e.g. a float -> an int field?
    # TODO: make certain that we don't change the behavior if check_types is either True or False,
    # particularly when a nullable type like str is None by default or it's not in the json or if it's
    # explicitly set to null.
    if not casted and config.follow_type_hints and type(data) == str and type_ != str and data is not None:
        if type_ == int:
            data = int(data)
        elif type_ == float:
            data = float(data)

    return data


def _get_deep_value(data: Any, path_or_paths: str, default: Optional[Any]=None):
    """
    Given a path or list of paths inside of data, return the value.
    NOTE: paths are checked in order, so if you specify multiple potentially-matching paths
    and one path is the subset of another, you must list the more-specific one first!
    """

    source_field = default
    if isinstance(path_or_paths, str):
        return get(path_or_paths, data, default)  # raises if field not found and default is an Exception
    elif isinstance(path_or_paths, list):
        for path in path_or_paths:
            try:
                return get(path, data, KeyError())
            except:
                pass
    else:
        raise ValueError(f'Expected either a path string or a list of path strings for: {data}.')

    if isinstance(default, Exception):
        raise default

    return default

def _build_value_for_union(union: Type, data: Any, config: Config) -> Any:
    # TODO: allow_superclass; add test!
    types = extract_generic(union)
    if is_optional(union) and len(types) == 2:
        return _build_value(type_=types[0], data=data, config=config)
    union_matches = {}
    for inner_type in types:
        try:
            # noinspection PyBroadException
            try:
                value = _build_value(type_=inner_type, data=data, config=config)
            except Exception:  # pylint: disable=broad-except
                continue
            if is_instance(value, inner_type) or \
                config.allow_superclasses and issubclass(inner_type, type(value)):
                if config.strict_unions_match:
                    union_matches[inner_type] = value
                else:
                    return value
        except DaciteError:
            pass
    if config.strict_unions_match:
        if len(union_matches) > 1:
            raise StrictUnionMatchError(union_matches)
        return union_matches.popitem()[1]
    if not config.check_types:
        return data
    raise UnionMatchError(field_type=union, value=data)


def _build_value_for_collection(collection: Type, data: Any, config: Config) -> Any:
    data_type = data.__class__
    if isinstance(data, Mapping) and is_subclass(collection, Mapping):
        item_type = extract_generic(collection, defaults=(Any, Any))[1]
        return data_type((key, _build_value(type_=item_type, data=value, config=config)) for key, value in data.items())
    elif isinstance(data, tuple) and is_subclass(collection, tuple):
        if not data:
            return data_type()
        types = extract_generic(collection)
        if len(types) == 2 and types[1] == Ellipsis:
            return data_type(_build_value(type_=types[0], data=item, config=config) for item in data)
        return data_type(
            _build_value(type_=type_, data=item, config=config) for item, type_ in zip_longest(data, types)
        )
    elif isinstance(data, Collection) and is_subclass(collection, Collection):
        item_type = extract_generic(collection, defaults=(Any,))[0]
        return data_type(_build_value(type_=item_type, data=item, config=config) for item in data)
    return data
