"""Module base for the Python reference specification of SOMA.

Types will be defined in their own modules and then imported here for a single
unified namespace.
"""

# __init__ files, used strictly for re-exporting, are the exception to the
# "import modules only" style used in somacore.

from typing import Tuple, Union

# TODO: pyarrow >= 14.0.1 doesn't play well with some other PyPI packages
# on Mac OS: https://github.com/apache/arrow/issues/42154
# Remove this once we can pin to recent pyarrow.
import pyarrow_hotfix  # noqa: F401

from .base import SOMAObject
from .collection import Collection
from .coordinates import Axis
from .coordinates import CoordinateSystem
from .coordinates import CoordinateTransform
from .data import DataFrame
from .data import DenseNDArray
from .data import GeometryDataFrame
from .data import NDArray
from .data import PointCloud
from .data import ReadIter
from .data import SparseNDArray
from .data import SparseRead
from .data import SpatialDataFrame
from .experiment import Experiment
from .images import Image2DCollection
from .images import ImageCollection
from .measurement import Measurement
from .options import BatchSize
from .options import IOfN
from .options import ResultOrder
from .query import AxisColumnNames
from .query import AxisQuery
from .query import ExperimentAxisQuery
from .scene import Scene
from .types import ContextBase

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
    "Scene",
    "ImageCollection",
    "Image2DCollection",
    "SpatialDataFrame",
    "PointCloud",
    "GeometryDataFrame",
    "BatchSize",
    "IOfN",
    "ResultOrder",
    "AxisColumnNames",
    "AxisQuery",
    "ExperimentAxisQuery",
    "ContextBase",
    "Axis",
    "CoordinateSystem",
    "CoordinateTransform",
)
