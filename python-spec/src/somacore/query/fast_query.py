import numpy as np
import numpy.typing as npt
from typing import Union
import pyarrow as pa
from IntIndexer import IntIndexer
from . import ExperimentAxisQuery


_Numpyable = Union[pa.Array, pa.ChunkedArray, npt.NDArray[np.int64]]
def _to_numpy(it: _Numpyable) -> np.ndarray:
    if isinstance(it, np.ndarray):
        return it
    return it.to_numpy()

class OptimizedAxisQuery(ExperimentAxisQuery):

    @property
    def _obs_index(self) -> IntIndexer:
        """Private. Return an index for the ``obs`` axis."""
        if self._cached_obs is None:
            self._cached_obs = IntIndexer.map_location(keys=self.query.obs_joinids().to_numpy(), 4)
        return self._cached_obs

    @property
    def _var_index(self) -> IntIndexer:
        """Private. Return an index for the ``var`` axis."""
        if self._cached_var is None:
            self._cached_var = IntIndexer.Index(data=self.query.var_joinids().to_numpy())
        return self._cached_var

    def by_obs(self, coords: _Numpyable) -> npt.NDArray[np.intp]:
        """Reindex the coords (soma_joinids) over the ``obs`` axis."""
        return self._obs_index.lookup(_to_numpy(coords))

    def by_var(self, coords: _Numpyable) -> npt.NDArray[np.intp]:
        """Reindex for the coords (soma_joinids) over the ``var`` axis."""
        return self._var_index.lookup(_to_numpy(coords))