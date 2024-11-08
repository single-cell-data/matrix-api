from typing import Generic, Optional, TypeVar

from typing_extensions import Final, Self

from . import _mixin, base, collection, data, measurement, query, scene

_DF = TypeVar("_DF", bound=data.DataFrame)
"""An implementation of a DataFrame."""
_MeasColl = TypeVar("_MeasColl", bound=collection.Collection[measurement.Measurement])
"""An implementation of a collection of Measurements."""
_SceneColl = TypeVar("_SceneColl", bound=collection.Collection[scene.Scene])
"""An implementation of a collection of spatial data."""
_RootSO = TypeVar("_RootSO", bound=base.SOMAObject)
"""The root SOMA object type of the implementation."""


class Experiment(
    collection.BaseCollection[_RootSO], Generic[_DF, _MeasColl, _SceneColl, _RootSO]
):
    """A collection subtype representing an annotated 2D matrix of measurements.

    In single cell biology, this can represent multiple modes of measurement
    across a single collection of cells (i.e., a "multimodal dataset").
    Within an experiment, a set of measurements on a single set of variables
    (i.e., features) is represented as a :class:`~measurement.Measurement`.

    Lifecycle: maturing
    """

    # This class is implemented as a mixin to be used with SOMA classes.
    # For example, a SOMA implementation would look like this:
    #
    #     # This type-ignore comment will always be needed due to limitations
    #     # of type annotations; it is (currently) expected.
    #     class Experiment(  # type: ignore[type-var]
    #         ImplBaseCollection[ImplSOMAObject],
    #         somacore.Experiment[
    #             ImplDataFrame,    # _DF
    #             ImplMeasurement,  # _MeasColl
    #             ImplScene,        # _SceneColl
    #             ImplSOMAObject,   # _RootSO
    #         ],
    #     ):
    #         ...

    __slots__ = ()
    soma_type: Final = "SOMAExperiment"  # type: ignore[misc]

    obs = _mixin.item[_DF]()
    """Primary observations on the observation axis.

    The contents of the ``soma_joinid`` pseudo-column define the observation
    index domain, i.e. ``obsid``. All observations for the experiment must be
    defined here.
    """

    ms = _mixin.item[_MeasColl]()
    """A collection of named measurements."""

    spatial = _mixin.item[_SceneColl]()  # TODO: Discuss the name of this element.
    """A collection of named spatial scenes."""

    obs_spatial_presence = _mixin.item[_DF]()
    """A dataframe that stores the presence of obs in the spatial scenes.

    This provides a join table for the obs ``soma_joinid`` and the scene names used in
    the ``spatial`` collection. This dataframe must contain index columns ``soma_joinid``
    and ``scene_id``. The ``scene_id`` column must have type ``string``. The
    dataframe must contain a ``boolean`` column ``soma_data``. The values of ``soma_data`` are
    ``True`` if the obs ``soma_joinid`` is contained in the scene
    ``scene_id`` and ``False`` otherwise.
    """

    def axis_query(
        self,
        measurement_name: str,
        *,
        obs_query: Optional[query.AxisQuery] = None,
        var_query: Optional[query.AxisQuery] = None,
    ) -> "query.ExperimentAxisQuery[Self]":
        """Creates an axis query over this experiment.

        See :class:`query.ExperimentAxisQuery` for details on usage.

        Lifecycle: maturing
        """
        # mypy doesn't quite understand descriptors so it issues a spurious
        # error here.
        return query.ExperimentAxisQuery(  # type: ignore[type-var]
            self,
            measurement_name,
            obs_query=obs_query or query.AxisQuery(),
            var_query=var_query or query.AxisQuery(),
        )
