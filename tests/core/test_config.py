from dataclasses import dataclass
from enum import Enum
from types import NoneType
from typing import Optional, List, Union, ClassVar

import pytest

from dacite import (
    from_dict,
    Config,
    ForwardReferenceError,
    UnexpectedDataError,
    StrictUnionMatchError,
    MissingValueError,
    WrongTypeError,
)


def test_from_dict_with_paths():
    @dataclass
    class X1:
        s1: str = None
        s2: str = "default"

    # simple field renaming
    result = from_dict(
        X1, {"s1": "same_name", "foo": "diff_name"}, Config(paths={X1: {"s2": "foo"}})
    )

    assert result == X1(s1="same_name", s2="diff_name")

    # extracting (and renaming) a field
    result = from_dict(
        X1,
        {"s1": "same_name", "foo": {"bar": "diff_name"}},
        Config(paths={X1: {"s2": "foo.bar"}}),
    )

    assert result == X1(s1="same_name", s2="diff_name")

    # missing field, with a default
    result = from_dict(
        X1, {"s1": "same_name", "foo": {}}, Config(paths={X1: {"s2": "foo.bar"}})
    )

    assert result == X1(s1="same_name", s2="default")

    # missing fields, None is a default
    result = from_dict(
        X1, {"s1_hideme": "same_name", "foo": {}}, Config(paths={X1: {"s2": "foo.bar"}})
    )

    assert result == X1(s1=None, s2="default")  # both are the default values

    # check for DefaultValueNotFoundError

    @dataclass
    class X2:
        s1: str  # note: no default
        s2: str = "default"

    with pytest.raises(MissingValueError):
        result = from_dict(
            X2, {"s1_hideme": "same_name", "foo": {}}, Config(paths={"s2": "foo.bar"})
        )


def test_from_dict_with_multiple_paths():
    @dataclass
    class X:
        a: str
        b: int

    result = from_dict(
        X,
        {"str": "val", "int": -1},
        Config(paths={
            X: {
                "a": ["str", "foo.bar"],
                "b": ["baz.blat", "int"],
            }
        })
    )
    assert result.a == "val"
    assert result.b == -1


def test_from_dict_with_paths_with_nested_data_class():
    @dataclass
    class X:
        i: int

    @dataclass
    class Y:
        s: str
        x: X

    result = from_dict(
        Y,
        {"s_renamed": "test", "x_renamed": {"i": 1}},
        Config(paths={Y: {"s": "s_renamed", "x": "x_renamed"}}),
    )

    assert result == Y(s="test", x=X(i=1))


def test_from_dict_with_paths_with_nested_data_class_with_defaults():
    @dataclass
    class X:
        i: int = 1
        j: int = 2  # skip

    @dataclass
    class Y:
        x: X
        s: str = "test"

    paths: dict[ClassVar, dict[str, str]] = {Y: {"s": "s_renamed", "x": "x_renamed", "j": None}}
    result = from_dict(Y, {"x_renamed": {}}, Config(paths=paths))

    assert result == Y(s="test", x=X(i=1, j=2))


def test_from_dict_with_paths_with_nested_data():
    @dataclass
    class X:
        i: int = -1
        s: str = "default"

    paths = {X:
                 {"s": "x_renamed.deep.deeper",
                  "i": "i_renamed"}
             }

    # test explicitly-set values
    result = from_dict(
        X,
        {"x_renamed": {"deep": {"deeper": "mystring"}},
         "i_renamed": 0},
        Config(paths=paths),
    )

    assert result == X(i=0, s="mystring")

    # test default values
    result = from_dict(X, {}, Config(paths=paths))

    assert result == X(i=-1, s="default")


def test_from_dict_with_paths_nested():
    @dataclass
    class X1:
        s1: str = None
        s2: str = "default2"

    # simple field renaming
    result = from_dict(
        X1, {"s1": "same_name", "foo": "diff_name"}, Config(paths={X1: {"s2": "foo"}})
    )

    assert result == X1(s1="same_name", s2="diff_name")


def test_from_dict_with_type_hooks():
    @dataclass
    class X:
        s: str

    result = from_dict(X, {"s": "TEST"}, Config(type_hooks={str: str.lower}))

    assert result == X(s="test")


def test_from_dict_with_type_hooks_and_optional():
    @dataclass
    class X:
        s: Optional[str]

    result = from_dict(X, {"s": "TEST"}, Config(type_hooks={str: str.lower}))

    assert result == X(s="test")


def test_from_dict_with_type_hooks_and_optional_null_value():
    @dataclass
    class X:
        s: Optional[str]

    result = from_dict(X, {"s": None}, Config(type_hooks={str: str.lower}))

    assert result == X(s=None)


def test_from_dict_with_type_hooks_and_union():
    @dataclass
    class X:
        s: Union[str, int]

    result = from_dict(X, {"s": "TEST"}, Config(type_hooks={str: str.lower}))

    assert result == X(s="test")


def test_from_dict_with_cast():
    @dataclass
    class X:
        s: str

    result = from_dict(X, {"s": 1}, Config(cast=[str]))

    assert result == X(s="1")


def test_from_dict_with_base_class_cast():
    class E(Enum):
        A = "a"

    @dataclass
    class X:
        e: E

    result = from_dict(X, {"e": "a"}, Config(cast=[Enum]))

    assert result == X(e=E.A)


def test_from_dict_with_base_class_cast_and_optional():
    class E(Enum):
        A = "a"

    @dataclass
    class X:
        e: Optional[E]

    result = from_dict(X, {"e": "a"}, Config(cast=[Enum]))

    assert result == X(e=E.A)


def test_from_dict_with_cast_and_generic_collection():
    @dataclass
    class X:
        s: List[int]

    result = from_dict(X, {"s": (1,)}, Config(cast=[List]))

    assert result == X(s=[1])


def test_from_dict_with_type_hooks_and_generic_sequence():
    @dataclass
    class X:
        c: List[str]

    result = from_dict(X, {"c": ["TEST"]}, config=Config(type_hooks={str: str.lower}))

    assert result == X(c=["test"])


def test_from_dict_with_type_hook_exception():
    @dataclass
    class X:
        i: int

    def raise_error(_):
        raise KeyError()

    with pytest.raises(KeyError):
        from_dict(X, {"i": 1}, config=Config(type_hooks={int: raise_error}))


def test_from_dict_with_forward_reference():
    @dataclass
    class X:
        y: "Y"

    @dataclass
    class Y:
        s: str

    data = from_dict(X, {"y": {"s": "text"}}, Config(forward_references={"Y": Y}))
    assert data == X(Y("text"))


def test_from_dict_with_missing_forward_reference():
    @dataclass
    class X:
        y: "Y"

    @dataclass
    class Y:
        s: str

    with pytest.raises(ForwardReferenceError) as exception_info:
        from_dict(X, {"y": {"s": "text"}})

    assert (
        str(exception_info.value)
        == "can not resolve forward reference: name 'Y' is not defined"
    )


def test_form_dict_with_disabled_type_checking():
    @dataclass
    class X:
        i: int

    result = from_dict(X, {"i": "test"}, config=Config(check_types=False))

    # noinspection PyTypeChecker
    assert result == X(i="test")


def test_form_dict_with_disabled_type_checking_and_union():
    @dataclass
    class X:
        i: Union[int, float]

    result = from_dict(X, {"i": "test"}, config=Config(check_types=False))

    # noinspection PyTypeChecker
    assert result == X(i="test")


def test_from_dict_with_strict():
    @dataclass
    class X:
        s: str

    with pytest.raises(UnexpectedDataError) as exception_info:
        from_dict(X, {"s": "test", "i": 1}, Config(strict=True))

    assert str(exception_info.value) == 'can not match "i" to any data class field'


def test_from_dict_with_strict_unions_match_and_ambiguous_match():
    @dataclass
    class X:
        i: int

    @dataclass
    class Y:
        i: int

    @dataclass
    class Z:
        u: Union[X, Y]

    data = {
        "u": {"i": 1},
    }

    with pytest.raises(StrictUnionMatchError) as exception_info:
        from_dict(Z, data, Config(strict_unions_match=True))

    assert (
        str(exception_info.value)
        == 'can not choose between possible Union matches for field "u": X, Y'
    )


def test_from_dict_with_strict_unions_match_and_single_match():
    @dataclass
    class X:
        f: str

    @dataclass
    class Y:
        f: int

    @dataclass
    class Z:
        u: Union[X, Y]

    data = {
        "u": {"f": 1},
    }

    result = from_dict(Z, data, Config(strict_unions_match=True))

    assert result == Z(u=Y(f=1))


def test_allow_superclasses():
    @dataclass
    class CarCompany(str):
        pass

    @dataclass
    class Dealership:
        brand: CarCompany

    with pytest.raises(WrongTypeError):
        from_dict(Dealership, {"brand": "bmw"})

    result: Dealership = from_dict(
        Dealership, {"brand": "bmw"}, config=Config(allow_superclasses=True)
    )
    assert result.brand == "bmw"

    @dataclass
    class Dealership2:
        brand: Union[CarCompany, int]

    with pytest.raises(WrongTypeError):
        from_dict(Dealership2, {"brand": "bmw"})

    result: Dealership2 = from_dict(
        Dealership2, {"brand": "bmw"}, config=Config(allow_superclasses=True)
    )
    assert result.brand == "bmw"


def test_allow_superclasses_with_generics_1():
    @dataclass
    class CarCompany(str):
        pass

    # test a list of generics
    @dataclass
    class Dealership3:
        brands: list[CarCompany]

    result: Dealership3 = from_dict(Dealership3, {"brands": ["bmw", "yugo"]})
    yugo: CarCompany = "yugo"
    assert yugo in result.brands

def test_allow_superclasses_with_generics_2():
    # test a generic dict
    # TODO: broken, because field list function doesn't work for dicts
    @dataclass
    class CarCompany(str):
        pass

    @dataclass
    class DealerDirectory(dict[str, list[CarCompany]]):
        pass

    result: DealerDirectory = from_dict(
        DealerDirectory,
        {
            "cheapo dealer": ["yugo", "lada"],
            "sportcar dealer": ["aston martin", "lamborghini"],
        },
    )
    lambo: CarCompany = "lamborghini"
    assert "sportcar dealer" in result.keys()
    assert lambo in result["sportcar dealer"]


def test_follow_type_hints():
    """follow_type_hints=True means that we should cast values to confirm to the field's type hint."""

    @dataclass
    class X:
        i: int = 42
        f: float = 42.0
        s: str = None

    result = from_dict(X, {"i": 1, "f": 1.0})
    assert (
        type(result.i) == int
        and type(result.f) == float
        and result.i == 1
        and result.f == 1.0
    )

    with pytest.raises(WrongTypeError):
        result = from_dict(X, {"i": "1", "f": "1.0"}, Config(check_types=True))

    # result = from_dict(X, { 'i': '1', 'f': '1.0' })
    # assert type(result.i) == str and type(result.f) == str and result.i == '1' and result.f == '1.0'

    # NOTE: if check_types, then nullable values (e.g., str) can't take on the value None:
    with pytest.raises(WrongTypeError):
        result = from_dict(X, {"s": None}, Config(follow_type_hints=True))

    result = from_dict(
        X, {"s": None}, Config(follow_type_hints=True, check_types=False)
    )
    assert type(result.s) == NoneType and result.s == None

    result = from_dict(X, {"i": "1", "f": "1.0"}, Config(follow_type_hints=True))
    assert (
        type(result.i) == int
        and type(result.f) == float
        and result.i == 1
        and result.f == 1.0
    )

    result = from_dict(X, {"s": "foo"}, Config(follow_type_hints=True))
    assert type(result.s) == str and result.s == "foo"

    result = from_dict(X, {}, Config(follow_type_hints=True))
    assert type(result.s) == NoneType and result.s == None
