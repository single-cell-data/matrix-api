"""Module base for the Python reference specification of SOMA.

Types will be defined in their own modules and then imported here for a single
unified namespace.
"""

# __init__ files, used strictly for re-exporting, are the exception to the
# "import modules only" style used in somacore.

from typing import Tuple, Union

from .base import SOMAObject
from .collection import Collection
from .data import DataFrame
from .data import DenseNDArray
from .data import NDArray
from .data import ReadIter
from .data import SparseNDArray
from .data import SparseRead
from .experiment import Experiment
from .measurement import Measurement
from .options import BatchSize
from .options import IOfN
from .options import ResultOrder
from .query import AxisColumnNames
from .query import AxisQuery
from .query import AxisQueryResult
from .query import ExperimentAxisQuery
from .query import CSRAccumulator
from .query import EagerIterator

try:
    # This trips up mypy since it's a generated file:
    from . import _version  # type: ignore[attr-defined]

    __version__: str = _version.version
    __version_tuple__: Tuple[Union[int, str], ...] = _version.version_tuple
except ImportError:
    __version__ = "0.0.0.dev+invalid"
    __version_tuple__ = (0, 0, 0, "dev", "invalid")


__all__ = (
    "SOMAObject",
    "Collection",
    "DataFrame",
    "DenseNDArray",
    "NDArray",
    "ReadIter",
    "SparseNDArray",
    "SparseRead",
    "Experiment",
    "Measurement",
    "BatchSize",
    "IOfN",
    "ResultOrder",
    "AxisColumnNames",
    "AxisQuery",
    "ExperimentAxisQuery",
    "CSRAccumulato"
    "EagerIterator",
    "AxisQueryResult",
)
