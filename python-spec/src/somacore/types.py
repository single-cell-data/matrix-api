"""Type and interface declarations that are not specific to options.

These declarations and functions are not directly part of the user-facing API,
but are intended to be used by SOMA implementations for annotations and
their own internal type-checking purposes.
"""

import sys
from concurrent import futures
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Protocol, TypeGuard


def is_nonstringy_sequence(it: object) -> TypeGuard[Sequence]:
    """Returns true if a sequence is a "normal" sequence and not str or bytes.

    str and bytes are "weird" sequences because iterating them gives you
    another str or bytes instance for each character, and when used as a
    sequence is not what users want.
    """
    return not isinstance(it, (str, bytes)) and isinstance(it, Sequence)


def to_string_tuple(obj: Union[str, Sequence[str]]) -> Tuple[str, ...]:
    """Returns a tuple of string values.

    If the input is a string, it is returned as a tuple with the string as its
    only item. If it is otherwise a sequence of strings, the sequence is converted
    to a tuple.
    """
    return (obj,) if isinstance(obj, str) else tuple(obj)


def str_or_seq_length(obj: Union[str, Sequence[str]]) -> int:
    """Returns the number of str values

    If input is a string, returns 1. Otherwise, returns the number of strings in the
    sequence.
    """
    return 1 if isinstance(obj, str) else len(obj)


_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


class Slice(Protocol[_T_co]):
    """A slice which stores a certain type of object.

    This protocol describes the built in ``slice`` type, with a hint to callers
    about what type they should put *inside* the slice.  It is for type
    annotations only and is not runtime-checkable (i.e., you can't do
    ``isinstance(thing, Slice)``), because ``range`` objects also have
    ``start``/``stop``/``step`` and would match, but are *not* slices.
    """

    # We use @property here to indicate that these fields are read-only;
    # just saying::
    #
    #     start: Optional[_T_co]
    #
    # would imply that doing::
    #
    #     some_slice.start = a_new_value
    #
    # was valid, thus making mypy whine (correctly!) that _T_co should be
    # invariant rather than covariant.

    @property
    def start(self) -> Optional[_T_co]: ...

    @property
    def stop(self) -> Optional[_T_co]: ...

    @property
    def step(self) -> Optional[_T_co]: ...

    if sys.version_info >= (3, 12):

        @property
        def __orig_bases__(self) -> Any:
            # Only exists in Python 3.12 and above
            from types import get_original_bases

            return get_original_bases(int)

    if sys.version_info < (3, 10) and not TYPE_CHECKING:
        # Python 3.9 and below have a bug where any Protocol with an @property
        # was always regarded as runtime-checkable.
        @classmethod
        def __subclasscheck__(cls, __subclass: type) -> NoReturn:
            raise TypeError("Slice is not a runtime-checkable protocol")


def is_slice_of(__obj: object, __typ: Type[_T]) -> TypeGuard[Slice[_T]]:
    return (
        # We only respect `slice`s proper.
        isinstance(__obj, slice)
        and (__obj.start is None or isinstance(__obj.start, __typ))
        and (__obj.stop is None or isinstance(__obj.stop, __typ))
        and (__obj.step is None or isinstance(__obj.step, __typ))
    )


class ContextBase(Protocol):
    """A protocol for a context manager that can be used as a base class.
    If a threadpool is specified as part of the context, it will be used by
    experiment queries. Otherwise, the implementer will use its own threadpool.
    """

    threadpool: Optional[futures.ThreadPoolExecutor]
