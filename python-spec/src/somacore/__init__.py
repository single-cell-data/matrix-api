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
from .coordinates import (
    AffineTransform,
    Axis,
    CoordinateSpace,
    CoordinateTransform,
    IdentityTransform,
    ScaleTransform,
    UniformScaleTransform,
)
from .data import DataFrame, DenseNDArray, NDArray, ReadIter, SparseNDArray, SparseRead
from .experiment import Experiment
from .measurement import Measurement
from .options import BatchSize, IOfN, ResultOrder
from .query import AxisColumnNames, AxisQuery, ExperimentAxisQuery
from .scene import Scene
from .spatial import (
    GeometryDataFrame,
    MultiscaleImage,
    PointCloudDataFrame,
    SpatialRead,
)
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
    "SpatialRead",
    "Experiment",
    "Measurement",
    "Scene",
    "ImageProperties",
    "MultiscaleImage",
    "GeometryDataFrame",
    "PointCloudDataFrame",
    "BatchSize",
    "IOfN",
    "ResultOrder",
    "AxisColumnNames",
    "AxisQuery",
    "ExperimentAxisQuery",
    "ContextBase",
    "Axis",
    "CoordinateSpace",
    "CoordinateTransform",
    "AffineTransform",
    "ScaleTransform",
    "UniformScaleTransform",
    "IdentityTransform",
)
