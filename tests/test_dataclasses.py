from dataclasses import dataclass, fields, field
from typing import Optional

import pytest

from dacite.dataclasses_helpers import get_default_value_for_field, DefaultValueNotFoundError, is_frozen, has, get, _has


def test_get_default_value_for_field_with_default_value():
    @dataclass
    class X:
        i: int = 1

    dataclass_field = fields(X)[0]

    value = get_default_value_for_field(field=dataclass_field, type_=dataclass_field.type)

    assert value == 1


def test_get_default_value_for_field_with_default_factory():
    @dataclass
    class X:
        i: int = field(default_factory=lambda: 1)

    dataclass_field = fields(X)[0]

    value = get_default_value_for_field(field=dataclass_field, type_=dataclass_field.type)

    assert value == 1


def test_get_default_value_for_optional_field():
    @dataclass
    class X:
        i: Optional[int]

    dataclass_field = fields(X)[0]

    value = get_default_value_for_field(field=dataclass_field, type_=dataclass_field.type)

    assert value is None


def test_get_default_value_for_field_without_default_value():
    @dataclass
    class X:
        i: int

    dataclass_field = fields(X)[0]

    with pytest.raises(DefaultValueNotFoundError):
        get_default_value_for_field(field=dataclass_field, type_=dataclass_field.type)


def test_is_frozen_with_frozen_dataclass():
    @dataclass(frozen=True)
    class X:
        pass

    assert is_frozen(X)


def test_is_frozen_with_non_frozen_dataclass():
    @dataclass(frozen=False)
    class X:
        pass

    assert not is_frozen(X)


def test_has():
    assert True == has("a", {"a": "foo"})
    assert True == has("a", {"a": {"b": 2}})
    assert True == has("a.b", {"a": {"b": 2}})

    assert True == has("x_renamed.deep.deeper",
                   {'i_renamed': 0,
                    'x_renamed': {'deep':
                                      {'deeper': 'mystring'}}})

    assert False == has("b", {"a": 1})
    assert False == has("b", {"a": {"b": 2}})
    assert False == has("a.b.c", {"a": {"b": 2}})
    assert False == has("a.c", {"a": {"b": 2}})

    assert False == has("b.c.d", {"a": 1})
    assert False == has("b.c.d", {"a": {"b": 2}})


def test_get():
    assert "foo" == get("a", {"a": "foo"})
    assert {"b": 2} == get("a", {"a": {"b": 2}})
    assert 2 == get("a.b", {"a": {"b": 2}})

    assert "mystring" == get("x_renamed.deep.deeper",
                             {'i_renamed': 0,
                              'x_renamed': {'deep':
                                                {'deeper': 'mystring'}}})
    with pytest.raises(KeyError):
        get("b", {"a": 1})
    with pytest.raises(KeyError):
        get("b", {"a": {"b": 2}})
    with pytest.raises(KeyError):
        get("a.b.c", {"a": {"b": 2}})
    with pytest.raises(KeyError):
        get("a.c", {"a": {"b": 2}})

    with pytest.raises(KeyError):
        get("b.c.d", {"a": 1})
    with pytest.raises(KeyError):
        get("b.c.d", {"a": {"b": 2}})

    with pytest.raises(ValueError):
        get("b.c.d", {"a": {"b": 2}}, ValueError("foo"))

    assert "foo" == get("b.c.d", {"a": {"b": 2}}, "foo")
