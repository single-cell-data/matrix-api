from typing import Generic, Optional, TypeVar

from typing_extensions import Final, Self

from . import _mixin
from . import base
from . import collection
from . import data
from . import measurement
from . import query

_DF = TypeVar("_DF", bound=data.DataFrame)
"""An implementation of a DataFrame."""
_MeasColl = TypeVar("_MeasColl", bound=collection.Collection[measurement.Measurement])
"""An implementation of a collection of Measurements."""
_RootSO = TypeVar("_RootSO", bound=base.SOMAObject)
"""The root SOMA object type of the implementation."""


class Experiment(collection.BaseCollection[_RootSO], Generic[_DF, _MeasColl, _RootSO]):
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
        print("Running axis query Experiment top class")
        return query.ExperimentAxisQuery(  # type: ignore[type-var]
            self,
            measurement_name,
            obs_query=obs_query or query.AxisQuery(),
            var_query=var_query or query.AxisQuery(),
        )
