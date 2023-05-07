import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, Type, List, ClassVar

from dacite.frozen_dict import FrozenDict

if sys.version_info.minor >= 8:
    from functools import cached_property  # type: ignore  # pylint: disable=no-name-in-module
else:
    # Remove when we drop support for Python<3.8
    cached_property = property  # type: ignore  # pylint: disable=invalid-name


@dataclass
class Config:
    type_hooks: Dict[Type, Callable[[Any], Any]] = field(default_factory=dict)
    cast: List[Type] = field(default_factory=list)
    forward_references: Optional[Dict[str, Any]] = None
    check_types: bool = True
    strict: bool = False
    strict_unions_match: bool = False
    allow_superclasses: bool = False  # allow a JSON field to map to a superclass of the field type
    follow_type_hints: bool = False  # if we have a type hint for a built-in field, try to cast to it
    paths: dict[ClassVar, dict[str, str]] = field(default_factory=dict)

    @cached_property
    def hashable_forward_references(self) -> Optional[FrozenDict]:
        return FrozenDict(self.forward_references) if self.forward_references else None
