"""Implementation of the SOMA scene collection for spatial data"""

import abc
from typing import Generic, MutableMapping, TypeVar

from typing_extensions import Final

from . import _mixin
from . import base
from . import collection
from . import coordinates
from . import data
from . import images

_ImageColl = TypeVar("_ImageColl", bound=images.ImageCollection)
"""A particular implementation of a collection of spatial arrays."""
_SpatialDFColl = TypeVar(
    "_SpatialDFColl", bound=collection.Collection[data.SpatialDataFrame]
)
_RootSO = TypeVar("_RootSO", bound=base.SOMAObject)
"""The root SomaObject type of the implementation."""


class Scene(
    collection.BaseCollection[_RootSO],
    Generic[_SpatialDFColl, _ImageColl, _RootSO],
):
    """TODO: Add documentation for scene

    Lifecycle: experimental
    """

    # This class is implemented as a mixin to be used with SOMA classes.
    # For example, a SOMA implementation would look like this:
    #
    #     # This type-ignore comment will always be needed due to limitations
    #     # of type annotations; it is (currently) expected.
    #     class Scene(  # type: ignore[type-var]
    #         ImplBaseCollection[ImplSOMAObject],
    #         somacore.Scene[
    #             ImplCollection[
    #                 Union[ImplGeometryDataFrame, ImplPointCloud]]
    #             ], # _SpatialDFColl
    #             ImplImageCollection,                          # _ImageColl
    #             ImplSOMAObject,                               # _RootSO
    #         ],
    #     ):
    #         ...

    __slots__ = ()
    soma_type: Final = "SOMAScene"  # type: ignore[misc]

    img = _mixin.item[_ImageColl]()
    """A collection of imagery backing the spatial data

    This collection can contain a combination of sparse and dense arrays that
    contain images or image masks. The specifics of how to best store and manage
    this data internal to the group needs to be explored in more detail. Ideally,
    we would support the following:

    * Single backing image
    * Multi-resolution images
    * Multiple image tiles that create a larger image (may be touching images or with
      gaps)
    * Image masks on top of any of the above
    """

    obsl = _mixin.item[_SpatialDFColl]()
    """A dataframe of the obs locations

    This collection exists to store any spatial data in the scene that joins on the obs
    ``soma_joinid``.

    Each dataframe in ``obsl`` can be either a GeometryDataFrame or a PointCloud. It
    must contain a ``soma_joinid`` and at least 2 spatial dimensions (naming
    convention for spatial dimensions TBD). If it is a ``GeometryDataFrame`` it must
    contain a ``soma_geometry`` column that is either (1) a number type for a
    collection of only circles or (2) a WKB blob for arbitrary 2D geometries. Other
    additional columns may be stored in this dataframe as well.
     """

    varl = _mixin.item[collection.Collection[_SpatialDFColl]]()
    """A collection of collections of dataframes of the var locations.

    This collection exists to store any spatial data in the scene that joins on the
    var ``soma_joinid``. The top-level collection maps from measurement name to a
    collection of dataframes.

    Each dataframe in ``varl`` can be either a GeometryDataFrame or a PointCloud. It
    must contain a ``soma_joinid`` and at least 2 spatial dimensions (naming
    convention for spatial dimensions TBD). If it is a ``GeometryDataFrame`` it must
    contain a ``soma_geometry`` column that is either (1) a number type for a
    collection of only circles or (2) a WKB blob for arbitrary 2D geometries. Other
    additional columns may be stored in this dataframe as well.
    """

    @property
    @abc.abstractmethod
    def local_coordinate_system(self) -> coordinates.CoordinateSystem:
        """Coordinate system for this scene."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def transformations(self) -> MutableMapping[str, coordinates.CoordinateTransform]:
        """Transformations saved for this scene."""
        raise NotImplementedError()
