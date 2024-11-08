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

from . import base, options

_RO_AUTO = options.ResultOrder.AUTO


class DataFrame(base.SOMAObject, metaclass=abc.ABCMeta):
    """A multi-column table with a user-defined schema.

    Lifecycle: maturing
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
        domain: Optional[Sequence[Optional[Tuple[Any, Any]]]] = None,
        platform_config: Optional[options.PlatformConfig] = None,
        context: Optional[Any] = None,
    ) -> Self:
        """Creates a new ``DataFrame`` at the given URI.

        The schema of the created dataframe will include a column named
        ``soma_joinid`` of type ``pyarrow.int64``, with negative values
        disallowed.  If a ``soma_joinid`` column is present in the provided
        schema, it must be of the correct type.  If no ``soma_joinid`` column
        is provided, one will be added.  It may be used as an indexed column.

        Args:
            uri: The URI where the dataframe will be created.

            schema: Arrow schema defining the per-column schema. This schema
                must define all columns, including columns to be named as index
                columns.  If the schema includes types unsupported by the SOMA
                implementation, an error will be raised.

            index_column_names: A list of column names to use as user-defined
                index columns (e.g., ``['cell_type', 'tissue_type']``).
                All named columns must exist in the schema, and at least one
                index column name is required.

            domain: An optional sequence of tuples specifying the domain of each
                index column. Each tuple should be a pair consisting of
                the minimum and maximum values storable in the index column.
                For example, if there is a single int64-valued index column,
                then ``domain`` might be ``[(100, 200)]`` to indicate that
                values between 100 and 200, inclusive, can be stored in that
                column.  If provided, this sequence must have the same length as
                ``index_column_names``, and the index-column domain will be as
                specified.  If omitted entirely, or if ``None`` in a given
                dimension, the corresponding index-column domain will use
                the minimum and maximum possible values for the column's
                datatype.  This makes a dataframe growable.

            platform_config: platform-specific configuration; keys are SOMA
                implementation names.

            context: Other implementation-specific configuration.

        Returns:
            The newly created dataframe, opened for writing.

        Lifecycle: maturing
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

        Args:
            coords: for each index dimension, which rows to read.
                Defaults to ``()``, meaning no constraint -- all IDs.
            column_names: the named columns to read and return.
                Defaults to ``None``, meaning no constraint -- all column names.
            partitions: If present, specifies that this is part of
                a partitioned read, and which part of the data to include.
            result_order: the order to return results, specified as a
                :class:`~options.ResultOrder` or its string value.
            value_filter: an optional value filter to apply to the results.
                The default of ``None`` represents no filter. Value filter
                syntax is implementation-defined; see the documentation
                for the particular SOMA implementation for details.
        Returns:
            A :class:`ReadIter` of :class:`pa.Table`s.


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

        Lifecycle: maturing
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

        As duplicate index values are not allowed, index values already present
        in the object are overwritten and new index values are added.

        Args:
            values: An Arrow table containing all columns, including
                the index columns. The schema for the values must match
                the schema for the ``DataFrame``.

        Returns: ``self``, to enable method chaining.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    # Metadata operations

    @property
    @abc.abstractmethod
    def schema(self) -> pa.Schema:
        """The schema of the data in this dataframe.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def index_column_names(self) -> Tuple[str, ...]:
        """The names of the index (dimension) columns.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def domain(self) -> Tuple[Tuple[Any, Any], ...]:
        """The allowable range of values in each index column.

        Returns: a tuple of minimum and maximum values, inclusive,
            storable on each index column of the dataframe.

        Lifecycle: maturing
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
        shape: Sequence[Optional[int]],
        platform_config: Optional[options.PlatformConfig] = None,
        context: Optional[Any] = None,
    ) -> Self:
        """Creates a new ND array of the current type at the given URI.

        Args:
            uri: The URI where the array will be created.
            type: The Arrow type to store in the array.
                If the type is unsupported, an error will be raised.
            shape: The maximum capacity of each dimension, including room
                for any intended future appends, specified as one element
                per dimension, e.g. ``(100, 10)``.  All lengths must be in
                the positive int64 range, or ``None``.  It's necessary to say
                ``shape=(None, None)`` or ``shape=(None, None, None)``,
                as the sequence length determines the number of dimensions
                (N) in the N-dimensional array.

                For sparse arrays only, if a slot is None, then the maximum
                possible int64 will be used, making a sparse array growable.

        Returns: The newly created array, opened for writing.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    # Metadata operations

    @property
    @abc.abstractmethod
    def shape(self) -> Tuple[int, ...]:
        """The maximum capacity (domain) of each dimension of this array.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    @property
    def ndim(self) -> int:
        """The number of dimensions in this array.

        Lifecycle: maturing
        """
        return len(self.shape)

    @property
    @abc.abstractmethod
    def schema(self) -> pa.Schema:
        """The schema of the data in this array.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    is_sparse: ClassVar[Literal[True, False]]
    """True if the array is sparse, False if it is dense.

    Lifecycle: maturing
    """


class DenseNDArray(NDArray, metaclass=abc.ABCMeta):
    """
    An N-dimensional array stored densely.

    Lifecycle: maturing
    """

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
        """Reads the specified subarray as a Tensor.

        Coordinates must specify a contiguous subarray, and the number of
        coordinates must be less than or equal to the number of dimensions.
        For example, if the array is 10×20, acceptable values of ``coords``
        include ``()``, ``(3, 4)``, ``[slice(5, 10)]``, and
        ``[slice(5, 10), slice(6, 12)]``.

        Args:
            coords: A per-dimension sequence of coordinates defining
                the range to read.
            partitions: If present, specifies that this is part of
                a partitioned read, and which part of the data to include.
            result_order: the order to return results, specified as a
                :class:`~options.ResultOrder` or its string value.
            platform_config: platform-specific configuration; keys are SOMA
                implementation names.

        Returns: The data over the requested range as a tensor.

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

        Lifecycle: maturing
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

        The subarray written is defined by ``coords`` and ``values``. This will
        overwrite existing values in the array.

        Args:
            coords: A per-dimension tuple of scalars or slices
                defining the bounds of the subarray to be written.
                See :meth:`read` for details about indexing.
            values: The values to be written to the subarray.  Must have
                the same shape as ``coords``, and matching type to the array.
        Returns: ``self``, to enable method chaining.
        Lifecycle: maturing
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
    """A N-dimensional array stored sparsely.

    Lifecycle: maturing
    """

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
        """Reads the specified subarray in batches.

        Values returned are a :class:`SparseRead` object which can be converted
        to any number of formats::

            some_dense_array.read(...).tables()
            # -> an iterator of Arrow Tables

        Args:
            coords: A per-dimension sequence of coordinates defining
                the range to be read.
            batch_size: The size of batches that should be returned from a read.
            See :class:`options.BatchSize` for details.
            partitions: Specifies that this is part of a partitioned read,
                and which partition to include, if present.
            result_order: the order to return results, specified as a
                :class:`~options.ResultOrder` or its string value.
            platform_config: platform-specific configuration; keys are SOMA
                implementation names.

        Returns: The data that was requested in a :class:`SparseRead`,
            allowing access in any supported format.

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

        Lifecycle: maturing
        """

    @abc.abstractmethod
    def write(
        self,
        values: SparseArrowData,
        *,
        platform_config: Optional[options.PlatformConfig] = None,
    ) -> Self:
        """Writes a Tensor to a subarray of the persistent object.

        Args:
            values: The values to write to the array. Supported types are:

                Arrow sparse tensor: the coordinates in the tensor are
                interpreted as the coordinates to write to.  Supports the
                *experimental* types SparseCOOTensor, SparseCSRMatrix, and
                SparseCSCMatrix. There is currently no support for
                SparseCSFTensor or dense Tensor.

                Arrow table: a COO table, with columns named ``soma_dim_0``,
                    ..., ``soma_dim_N`` and ``soma_data``.
            platform_config: platform-specific configuration; keys are SOMA
                implementation names.

        Returns: ``self``, to enable method chaining.

        Lifecycle: maturing
        """
        raise NotImplementedError()

    @property
    def nnz(self) -> int:
        """The number of values stored in the array, including explicit zeros.

        Lifecycle: maturing
        """
        raise NotImplementedError()


#
# Read types
#

_T = TypeVar("_T")


# Sparse reads are returned as an iterable structure:


class ReadIter(Iterator[_T], metaclass=abc.ABCMeta):
    """SparseRead result iterator allowing users to flatten the iteration.

    Lifecycle: maturing
    """

    __slots__ = ()

    # __iter__ is already implemented as `return self` in Iterator.
    # SOMA implementations must implement __next__.

    @abc.abstractmethod
    def concat(self) -> _T:
        """Returns all the requested data in a single operation.

        If some data has already been retrieved using ``next``, this will return
        the remaining data, excluding that which as already been returned.

        Lifecycle: maturing
        """
        raise NotImplementedError()


class SparseRead:
    """Intermediate type to choose result format when reading a sparse array.

    A query may not be able to return all of these formats. The concrete result
    may raise a ``NotImplementedError`` or may choose to raise a different
    exception (likely a ``TypeError``) containing more specific information
    about why the given format is not supported.

    Lifecycle: maturing
    """

    __slots__ = ()

    def coos(self) -> ReadIter[pa.SparseCOOTensor]:
        raise NotImplementedError()

    def dense_tensors(self) -> ReadIter[pa.Tensor]:
        raise NotImplementedError()

    def record_batches(self) -> ReadIter[pa.RecordBatch]:
        raise NotImplementedError()

    def tables(self) -> ReadIter[pa.Table]:
        raise NotImplementedError()
