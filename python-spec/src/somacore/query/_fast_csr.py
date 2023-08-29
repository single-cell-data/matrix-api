import os
from concurrent import futures
from typing import List, NamedTuple, Tuple, Type, cast

import numba
import numba.typed
import numpy as np
import numpy.typing as npt
import pandas as pd
import pyarrow as pa
import time
from scipy import sparse

from .. import data as scd
from . import _eager_iter


def read_scipy_csr(
    matrix: scd.SparseNDArray, obs_joinids: pa.Array, var_joinids: pa.Array
) -> sparse.csr_matrix:
    """
    Given a 2D SparseNDArray and joinids for the two dimensions, read the
    slice and return it as an SciPy sparse.csr_matrix.
    """
    data, indptr, indices, shape = _read_csr(matrix, obs_joinids, var_joinids)
    csr = _create_scipy_csr_matrix(data, indices, indptr, shape=shape)
    return csr


def read_arrow_csr(
    matrix: scd.SparseNDArray, obs_joinids: pa.Array, var_joinids: pa.Array
) -> pa.SparseCSRMatrix:
    """
    Given a 2D SparseNDArray and joinids for the two dimensions, read the
    slice and return it as a pyarrow.SparseCSRMatrix.
    """
    data, indptr, indices, shape = _read_csr(matrix, obs_joinids, var_joinids)
    csr = pa.SparseCSRMatrix.from_numpy(data, indptr, indices, shape=shape)
    return csr


class _CSRAccumulatorFinalResult(NamedTuple):
    """
    Private.

    Return type for the _CSRAccumulator.finalize method.
    Contains a sparse CSR consituent elements
    """

    data: npt.NDArray[np.number]
    indptr: npt.NDArray[np.integer]
    indices: npt.NDArray[np.integer]
    shape: Tuple[int, int]


class _CSRAccumulator:
    """
    Fast accumulator of a CSR, based upon COO input.
    """

    def __init__(
        self,
        obs_joinids: npt.NDArray[np.int64],
        var_joinids: npt.NDArray[np.int64],
        pool: futures.Executor,
    ):
        self.obs_joinids = obs_joinids
        self.var_joinids = var_joinids
        self.pool = pool

        self.shape: Tuple[int, int] = (len(self.obs_joinids), len(self.var_joinids))
        self.obs_indexer: pd.Index = pd.Index(self.obs_joinids)
        self.var_indexer: pd.Index = pd.Index(self.var_joinids)
        self.row_length: npt.NDArray[np.int64] = np.zeros(
            (self.shape[0],), dtype=_select_dtype(self.shape[1])
        )

        # COO accumulated chunks, stored as list of triples (row_ind, col_ind, data)
        self.coo_chunks: List[
            Tuple[
                npt.NDArray[np.integer],  # row_ind
                npt.NDArray[np.integer],  # col_ind
                npt.NDArray[np.number],  # data
            ]
        ] = []

    def append(
        self,
        row_joinids: pa.Array,
        col_joinids: pa.Array,
        data: pa.Array,
    ) -> None:
        """
        At accumulation time, do several things:
        * re-index to positional indices, and if possible, cast to smaller dtype
          to minimize memory footprint (at cost of some amount of time)
        * accumulate column counts by row, i.e., build the basis of the indptr
        * cache the tuple of data, row, col
        """
        rows_future = self.pool.submit(
            _reindex_and_cast,
            self.obs_indexer,
            row_joinids.to_numpy(),
            _select_dtype(self.shape[0]),
        )
        cols_future = self.pool.submit(
            _reindex_and_cast,
            self.var_indexer,
            col_joinids.to_numpy(),
            _select_dtype(self.shape[1]),
        )
        row_ind = rows_future.result()
        col_ind = cols_future.result()
        self.coo_chunks.append((row_ind, col_ind, data.to_numpy()))
        _accum_row_length(self.row_length, row_ind)

    def finalize(self) -> _CSRAccumulatorFinalResult:
        nnz = sum(len(chunk[2]) for chunk in self.coo_chunks)
        index_dtype = _select_dtype(nnz)
        if nnz == 0:
            # There is no way to infer matrix dtype, so use a default and return
            # an empty matrix. Float32 is used as a default type, as it is most
            # compatible with AnnData expectations.
            empty = sparse.csr_matrix((0, 0), dtype=np.float32)
            return _CSRAccumulatorFinalResult(
                data=empty.data,
                indptr=empty.indptr,
                indices=empty.indices,
                shape=self.shape,
            )

        # cumsum row lengths to get indptr
        indptr = np.empty((self.shape[0] + 1,), dtype=index_dtype)
        indptr[0:1] = 0
        np.cumsum(self.row_length, out=indptr[1:])

        # Parallel copy of data and column indices
        indices = np.empty((nnz,), dtype=index_dtype)
        data = np.empty((nnz,), dtype=self.coo_chunks[0][2].dtype)

        # Empirically determined value. Needs to be large enough for reasonable
        # concurrency, without excessive write cache conflict. Controls the
        # number of rows that are processed in a single thread, and therefore
        # is the primary tuning parameter related to concurrency.
        row_rng_mask_bits = 18

        n_jobs = (self.shape[0] >> row_rng_mask_bits) + 1
        chunk_list = numba.typed.List(self.coo_chunks)
        futures.wait(
            [
                self.pool.submit(
                    _copy_chunklist_range,
                    chunk_list,
                    data,
                    indices,
                    indptr,
                    row_rng_mask_bits,
                    job,
                )
                for job in range(n_jobs)
            ]
        )
        _finalize_indptr(indptr)
        return _CSRAccumulatorFinalResult(
            data=data, indptr=indptr, indices=indices, shape=self.shape
        )


@numba.jit(nopython=True, nogil=True)  # type: ignore[attr-defined]
def _accum_row_length(
    row_length: npt.NDArray[np.int64], row_ind: npt.NDArray[np.int64]
) -> None:
    for rind in row_ind:
        row_length[rind] += 1


@numba.jit(nopython=True, nogil=True)  # type: ignore[attr-defined]
def _copy_chunk_range(
    row_ind_chunk: npt.NDArray[np.signedinteger],
    col_ind_chunk: npt.NDArray[np.signedinteger],
    data_chunk: npt.NDArray[np.number],
    data: npt.NDArray[np.number],
    indices: npt.NDArray[np.signedinteger],
    indptr: npt.NDArray[np.signedinteger],
    row_rng_mask: int,
    row_rng_val: int,
):
    for n in range(len(data_chunk)):
        row = row_ind_chunk[n]
        if (row & row_rng_mask) != row_rng_val:
            continue
        ptr = indptr[row]
        indices[ptr] = col_ind_chunk[n]
        data[ptr] = data_chunk[n]
        indptr[row] += 1


@numba.jit(nopython=True, nogil=True)  # type: ignore[attr-defined]
def _copy_chunklist_range(
    chunk_list: numba.typed.List,
    data: npt.NDArray[np.number],
    indices: npt.NDArray[np.signedinteger],
    indptr: npt.NDArray[np.signedinteger],
    row_rng_mask_bits: int,
    job: int,
):
    assert row_rng_mask_bits >= 1 and row_rng_mask_bits < 64
    row_rng_mask = (2**64 - 1) >> row_rng_mask_bits << row_rng_mask_bits
    row_rng_val = job << row_rng_mask_bits
    for row_ind_chunk, col_ind_chunk, data_chunk in chunk_list:
        _copy_chunk_range(
            row_ind_chunk,
            col_ind_chunk,
            data_chunk,
            data,
            indices,
            indptr,
            row_rng_mask,
            row_rng_val,
        )


@numba.jit(nopython=True, nogil=True)  # type: ignore[attr-defined]
def _finalize_indptr(indptr: npt.NDArray[np.signedinteger]):
    prev = 0
    for r in range(len(indptr)):
        t = indptr[r]
        indptr[r] = prev
        prev = t


def _select_dtype(
    maxval: int,
) -> Type[np.signedinteger]:
    """
    Ascertain the "best" dtype for a zero-based index. Given our
    goal of minimizing memory use, "best" is currently defined as
    smallest.
    """
    if maxval > np.iinfo(np.int32).max:
        return np.int64
    else:
        return np.int32


def _reindex_and_cast(
    index: pd.Index, ids: npt.NDArray[np.int64], target_dtype: npt.DTypeLike
) -> npt.NDArray[np.int64]:
    return cast(
        npt.NDArray[np.int64], index.get_indexer(ids).astype(target_dtype, copy=False)
    )


def _read_csr(
    matrix: scd.SparseNDArray, obs_joinids: pa.Array, var_joinids: pa.Array
) -> Tuple[
    npt.NDArray[np.number],  # data
    npt.NDArray[np.integer],  # indptr
    npt.NDArray[np.integer],  # indices
    Tuple[int, int],  # shape
]:
    print(f"data shape {matrix.shape} nnz {matrix.nnz} obs_joinids {len(obs_joinids)} var_joinids {len(var_joinids)}")
    if not isinstance(matrix, scd.SparseNDArray) or matrix.ndim != 2:
        raise TypeError("Can only read from a 2D SparseNDArray")

    max_workers = (os.cpu_count() or 4) + 2
    t1 = time.perf_counter()
    with futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        acc = _CSRAccumulator(
            obs_joinids=obs_joinids, var_joinids=var_joinids, pool=pool
        )
        for tbl in _eager_iter.EagerIterator(
            matrix.read((obs_joinids, var_joinids)).tables(),
            pool=pool,
        ):
            acc.append(tbl["soma_dim_0"], tbl["soma_dim_1"], tbl["soma_data"])
        t2 = time.perf_counter()

        data, indptr, indices, shape = acc.finalize()
        t3 = time.perf_counter()
    print(f"Time for reading and appending {t2 - t1} and Time for finalizing {t3 - t2}")
    return data, indptr, indices, shape


def _create_scipy_csr_matrix(
    data: npt.NDArray[np.number],
    indices: npt.NDArray[np.integer],
    indptr: npt.NDArray[np.integer],
    shape: Tuple[int, int],
) -> sparse.csr_matrix:
    """Create a Scipy sparse.csr_matrix from component elements.

    Conceptually, this is identical to::

        sparse.csr_matrix((data, indices, indptr), shape=shape)

    This ugliness is to bypass the O(N) scan that
    :meth:`scipy.sparse._cs_matrix.__init__`
    does when a new compressed matrix is created.

    See https://github.com/scipy/scipy/issues/11496 for details on the bug.
    """
    matrix = sparse.csr_matrix.__new__(sparse.csr_matrix)
    matrix.data = data
    matrix.indices = indices
    matrix.indptr = indptr
    matrix._shape = shape
    return matrix
