"""Definitions of data storage interfaces for SOMA implementations.

SOMA users should ordinarily not need to import this module directly; relevant
members will be exported to the ``somacore`` namespace.

Default values are provided here as a reference for implementors.
"""

import abc
from typing import (
    Any,
    ClassVar,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import pyarrow as pa
from typing_extensions import Final, Literal, Self

from . import base
from . import options

_RO_AUTO = options.ResultOrder.AUTO


class DataFrame(base.SOMAObject, metaclass=abc.ABCMeta):
    """A multi-column table with a user-defined schema.
    [lifecycle: experimental]
    """

    __slots__ = ()
    soma_type: Final = "SOMADataFrame"  # type: ignore[misc]

    # Lifecycle

    @classmethod
    @abc.abstractmethod
    def create(
        cls,
        uri: str,
        *,
        schema: pa.Schema,
        index_column_names: Sequence[str] = (options.SOMA_JOINID,),
        platform_config: Optional[options.PlatformConfig] = None,
        context: Optional[Any] = None,
    ) -> Self:
        """Creates a new ``DataFrame`` at the given URI.
        [lifecycle: experimental]

        The schema of the created dataframe will include a column named
        ``soma_joinid`` of type ``pyarrow.int64``, with negative values
        disallowed.  If a ``soma_joinid`` column is present in the provided
        schema, it must be of the correct type.  If no ``soma_joinid`` column
        is provided, one will be added.  It may be used as an indexed column.

        :param uri: The URI where the ``DataFrame`` will be created.
        :param schema: Arrow schema defining the per-column schema. This schema
            must define all columns, including columns to be named as index
            columns.  If the schema includes types unsupported by the SOMA
            implementation, an error will be raised.
        :param index_column_names: A list of column names to use as user-defined
            index columns (e.g., ``['cell_type', 'tissue_type']``).
            All named columns must exist in the schema, and at least one
            index column name is required.
        """
        raise NotImplementedError()

    # Data operations

    @abc.abstractmethod
    def read(
        self,
        coords: options.SparseDFCoords = (),
        column_names: Optional[Sequence[str]] = None,
        *,
        batch_size: options.BatchSize = options.BatchSize(),
        partitions: Optional[options.ReadPartitions] = None,
        result_order: options.ResultOrderStr = _RO_AUTO,
        value_filter: Optional[str] = None,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> "ReadIter[pa.Table]":
        """Reads a user-defined slice of data into Arrow tables.
        [lifecycle: experimental]

        :param coords: for each index dimension, which rows to read.
            Defaults to ``()``, meaning no constraint -- all IDs.
        :param column_names: the named columns to read and return.
            Defaults to ``None``, meaning no constraint -- all column names.
        :param partitions: If present, specifies that this is part of
            a partitioned read, and which part of the data to include.
        :param result_order: the order to return results, specified as a
            :class:`~options.ResultOrder` or its string value.
        :param value_filter: an optional value filter to apply to the results.
            The default of ``None`` represents no filter. Value filter syntax
            is implementation-defined; see the documentation for a particular
            SOMA implementation for details.

        **Indexing:**

        Indexing is performed on a per-column basis for each indexed column.
        To specify dimensions:

        - A sequence of coordinates is accepted, one per indexed dimension.
        - The sequence length must be less than or equal to the number of
          indexed dimensions.
        - If the sequence is shorter than the number of indexed coordinates,
          then no constraint (i.e. ``None``) is used for the remaining
          indexed dimensions.
        - Specifying an empty sequence (e.g. ``()``, the default) represents
          no constraints over any dimension, returning the entire dataset.

        Each dimension may be indexed as follows:

        - ``None`` or ``slice(None)`` places no constraint on the dimension.
        - Coordinates can be specified as a scalar value, a Python sequence
          (``list``, ``tuple``, etc.), a NumPy ndarray, an Arrow array, or
          similar objects (as defined by ``SparseDFCoords``).
        - Slices specify a closed range: ``slice(2, 4)`` includes both 2 and 4.
          Slice *steps* may not be used: ``slice(10, 20, 2)`` is invalid.
          ``slice(None)`` places no constraint on the dimension. Half-specified
          slices like ``slice(None, 99)`` and ``slice(5, None)`` specify
          all indices up to and including the value, and all indices
          starting from and including the value.
        - Negative values in indices and slices are treated as raw domain values
          and not as indices relative to the end, unlike traditional Python
          sequence indexing. For instance, ``slice(-10, 3)`` indicates the range
          from −10 to 3 on the given dimension.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def write(
        self,
        values: Union[pa.RecordBatch, pa.Table],
        *,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> Self:
        """Writes the data from an Arrow table to the persistent object.
        [lifecycle: experimental]

        As duplicate index values are not allowed, index values already present
        in the object are overwritten and new index values are added.

        :param values: An Arrow table containing all columns, including
            the index columns. The schema for the values must match
            the schema for the ``DataFrame``.
        :return: ``self``, to enable method chaining.
        """
        raise NotImplementedError()

    # Metadata operations

    @property
    @abc.abstractmethod
    def schema(self) -> pa.Schema:
        """The schema of the data in this dataframe.
        [lifecycle: experimental]
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def index_column_names(self) -> Tuple[str, ...]:
        """The names of the index (dimension) columns.
        [lifecycle: experimental]
        """
        raise NotImplementedError()


class NDArray(base.SOMAObject, metaclass=abc.ABCMeta):
    """Common behaviors of N-dimensional arrays of a single primitive type."""

    __slots__ = ()

    # Lifecycle

    @classmethod
    @abc.abstractmethod
    def create(
        cls,
        uri: str,
        *,
        type: pa.DataType,
        shape: Sequence[Union[int, None]],
        platform_config: Optional[options.PlatformConfig] = None,
        context: Optional[Any] = None,
    ) -> Self:
        """Creates a new ND array of the current type at the given URI.
        [lifecycle: experimental]

        :param uri: The URI where the array will be created.
        :param type: The Arrow type to store in the array.
            If the type is unsupported, an error will be raised.
        :param shape: The length of each dimension as a sequence,
            e.g. ``(100, 10)``. All lengths must be in the postive int64 range,
            or `None`.  If a slot is `None` -- only supported for
            `SparseNDArray`, not `DenseNDArray` -- then 2**63-1 will be used.
            This makes a `SparseNDArray` growable.
        """
        raise NotImplementedError()

    # Metadata operations

    @property
    @abc.abstractmethod
    def shape(self) -> Tuple[int, ...]:
        """The length of each dimension of this array.
        [lifecycle: experimental]
        """
        raise NotImplementedError()

    @property
    def ndim(self) -> int:
        """The number of dimensions in this array. [lifecycle: experimental]"""
        return len(self.shape)

    @property
    @abc.abstractmethod
    def schema(self) -> pa.Schema:
        """The schema of the data in this array. [lifecycle: experimental]"""
        raise NotImplementedError()

    is_sparse: ClassVar[Literal[True, False]]
    """True if the array is sparse. False if it is dense.
    [lifecycle: experimental]
    """


class DenseNDArray(NDArray, metaclass=abc.ABCMeta):
    """A N-dimensional array stored densely. [lifecycle: experimental]"""

    __slots__ = ()
    soma_type: Final = "SOMADenseNDArray"  # type: ignore[misc]
    is_sparse: Final = False  # type: ignore[misc]

    @abc.abstractmethod
    def read(
        self,
        coords: options.DenseNDCoords = (),
        *,
        partitions: Optional[options.ReadPartitions] = None,
        result_order: options.ResultOrderStr = _RO_AUTO,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> pa.Tensor:
        """Reads the specified subarray as a Tensor. [lifecycle: experimental]

        Coordinates must specify a contiguous subarray, and the number of
        coordinates must be less than or equal to the number of dimensions.
        For example, if the array is 10×20, acceptable values of ``coords``
        include ``()``, ``(3, 4)``, ``[slice(5, 10)]``, and
        ``[slice(5, 10), slice(6, 12)]``.

        :param coords: A per-dimension sequence of coordinates defining
            the range to read.
        :param partitions: If present, specifies that this is part of
            a partitioned read, and which part of the data to include.
        :param result_order: the order to return results, specified as a
            :class:`~options.ResultOrder` or its string value.

        **Indexing:**

        Indexing is performed on a per-dimension basis.

        - A sequence of coordinates is accepted, one per dimension.
        - The sequence length must be less than or equal to
          the number of dimensions.
        - If the sequence is shorter than the number of dimensions, the
          remaining dimensions are unconstrained.
        - Specifying an empty sequence (e.g. ``()``, the default) represents
          no constraints over any dimension, returning the entire dataset.

        Each dimension may be indexed by value or slice:

        - Slices specify a closed range: ``slice(2, 4)`` includes 2, 3, and 4.
          Slice *steps* may not be used: ``slice(10, 20, 2)`` is invalid.
          ``slice(None)`` places no constraint on the dimension. Half-specified
          slices like ``slice(None, 99)`` and ``slice(5, None)`` specify
          all indices up to and including the value, and all indices
          starting from and including the value.
        - Negative indexing is not supported.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def write(
        self,
        coords: options.DenseNDCoords,
        values: pa.Tensor,
        *,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> Self:
        """Writes an Arrow tensor to a subarray of the persistent object.
        [lifecycle: experimental]

        The subarray written is defined by ``coords`` and ``values``. This will
        overwrite existing values in the array.

        :param coords: A per-dimension tuple of scalars or slices
            defining the bounds of the subarray to be written.
            See :meth:`read` for details about indexing.
        :param values: The values to be written to the subarray.  Must have
            the same shape as ``coords``, and matching type to the array.
        :return: ``self``, to enable method chaining.
        """
        raise NotImplementedError()


SparseArrowData = Union[
    pa.SparseCSCMatrix,
    pa.SparseCSRMatrix,
    pa.SparseCOOTensor,
    pa.Table,
]
"""Any of the sparse data storages provided by Arrow."""


class SparseNDArray(NDArray, metaclass=abc.ABCMeta):
    """A N-dimensional array stored sparsely. [lifecycle: experimental]"""

    __slots__ = ()
    soma_type: Final = "SOMASparseNDArray"  # type: ignore[misc]
    is_sparse: Final = True  # type: ignore[misc]

    @abc.abstractmethod
    def read(
        self,
        coords: options.SparseNDCoords = (),
        *,
        batch_size: options.BatchSize = options.BatchSize(),
        partitions: Optional[options.ReadPartitions] = None,
        result_order: options.ResultOrderStr = _RO_AUTO,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> "SparseRead":
        """Reads the specified subarray in batches. [lifecycle: experimental]

        Values returned are a :class:`SparseRead` object which can be converted
        to any number of formats::

            some_dense_array.read(...).tables()
            # -> an iterator of Arrow Tables

        :param coords: A per-dimension sequence of coordinates defining
            the range to be read.
        :param batch_size: The size of batches that should be returned
            from a read. See :class:`options.BatchSize` for details.
        :param partitions: Specifies that this is part of a partitioned read,
            and which partition to include, if present.
        :param result_order: the order to return results, specified as a
            :class:`~options.ResultOrder` or its string value.

        **Indexing:**

        Indexing is performed on a per-dimension basis.

        - A sequence of coordinates is accepted, one per dimension.
        - The sequence length must be less than or equal to
          the number of dimensions.
        - If the sequence is shorter than the number of dimensions, the
          remaining dimensions are unconstrained.
        - Specifying an empty sequence (e.g. ``()``, the default) represents
          no constraints over any dimension, returning the entire dataset.

        Each dimension may be indexed as follows:

        - ``None`` or ``slice(None)`` places no constraint on the dimension.
        - Coordinates can be specified as a scalar value, a Python sequence
          (``list``, ``tuple``, etc.), a ``ndarray``, an Arrow array, and
          similar objects (as defined by ``SparseNDCoords``).
        - Slices specify a closed range: ``slice(2, 4)`` includes 2, 3, and 4.
          Slice *steps* may not be used: ``slice(10, 20, 2)`` is invalid.
          ``slice(None)`` places no constraint on the dimension. Half-specified
          slices like ``slice(None, 99)`` and ``slice(5, None)`` specify
          all indices up to and including the value, and all indices
          starting from and including the value.
        - Negative indexing is not supported.
        """

    @abc.abstractmethod
    def write(
        self,
        values: SparseArrowData,
        *,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> Self:
        """Writes a Tensor to a subarray of the persistent object.
        [lifecycle: experimental]

        :param values: The values to write to the array.
        :return: ``self``, to enable method chaining.

        **Value types:**

        Arrow sparse tensor: the coordinates in the tensor are interpreted as
        the coordinates to write to.  Supports the *experimental* types
        SparseCOOTensor, SparseCSRMatrix and SparseCSCMatrix. There is currently
        no support for Arrow SparseCSFTensor or dense Tensor.

        Arrow table: a COO table, with columns named ``soma_dim_0``, ...,
        ``soma_dim_N`` and ``soma_data``, to be written to the array.
        """
        raise NotImplementedError()

    @property
    def nnz(self) -> int:
        """The number of values stored in the array, including explicit zeros.
        [lifecycle: experimental]
        """
        raise NotImplementedError()


#
# Read types
#

_T = TypeVar("_T")


# Sparse reads are returned as an iterable structure:


class ReadIter(Iterator[_T], metaclass=abc.ABCMeta):
    """SparseRead result iterator allowing users to flatten the iteration.
    [lifecycle: experimental]
    """

    __slots__ = ()

    # __iter__ is already implemented as `return self` in Iterator.
    # SOMA implementations must implement __next__.

    @abc.abstractmethod
    def concat(self) -> _T:
        """Returns all the requested data in a single operation.
        [lifecycle: experimental]

        If some data has already been retrieved using ``next``, this will return
        the rest of the data after that which has already been returned.
        """
        raise NotImplementedError()


class SparseRead:
    """Intermediate type to choose result format when reading a sparse array.
    [lifecycle: experimental]

    A query may not be able to return all of these formats. The concrete result
    may raise a ``NotImplementedError`` or may choose to raise a different
    exception (likely a ``TypeError``) containing more specific information
    about why the given format is not supported.
    """

    __slots__ = ()

    def dense_tensors(self) -> ReadIter[pa.Tensor]:
        raise NotImplementedError()

    def record_batches(self) -> ReadIter[pa.RecordBatch]:
        raise NotImplementedError()

    def tables(self) -> ReadIter[pa.Table]:
        raise NotImplementedError()
