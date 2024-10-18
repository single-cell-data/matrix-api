# Introduction

<!-- Note to editors: this version string is independent of GitHub release tags on this repo. In particular, it needs to match `get_SOMA_version()` in impls. -->

**Specification version**: `0.3.0-dev`

ℹ️ **Note**: Feedback on this spec is encouraged. Please [file an issue](https://github.com/single-cell-data/SOMA/issues)
with any and all feedback, comments, or concerns.

The goal of SOMA (“stack of matrices, annotated”) is a flexible, extensible, and open-source API providing access to annotated, 2D matrix data stored in multiple underlying formats and systems. The vision for this API family includes:

- support access to persistent, cloud-resident datasets.
- enable use within popular data-science environments (e.g., R, Python), using the tools of that environment (e.g., Python Pandas integration).
- enable "out-of-core" access to data aggregations much larger than single-host main memory.
- enable distributed computation over datasets.
- provide a building block for higher-level API that may embody domain-specific conventions or schema around annotated 2D matrices (e.g., a cell "atlas").

The core SOMA data model is centered on annotated 2-D matrices, conceptually similar to commonly used single-cell 'omics data structures including Seurat Assay, Bioconductor SingleCellExperiment, and Scanpy AnnData. The core data model is supplemented with spatial indexed data for single-cell spatial 'omics support.

Where possible, the SOMA API attempts to be general-purpose and agnostic to the specifics of any given environment, or to the specific conventions of the Single Cell scientific ecosystem.

SOMA is an abstract _API specification_, with the goal of enabling multiple concrete API implementations within different computing environments and data-storage systems. SOMA does not specify an at-rest serialization format or underlying storage system.

This document attempts to codify the abstract, language-neutral SOMA data model and functional operations. Other specifications will document specific language bindings and particular storage-system implementations. Where the term _language-specific SOMA specification_ is used below, it implies a specification of the SOMA API as it is presented in a given language or computing environment (e.g., the SOMA Python API), common across all storage-engine implementations in that language.

# API Maturity Lifecycle Stages

The SOMA API uses [RStudio's lifecycle stage model](https://lifecycle.r-lib.org) to indicate the maturity of its classes, methods, and parameters. The lifecycle stages are:

- `experimental`: Under active development and may undergo significant and breaking changes.
- `maturing`: Under active development but the interface and behavior have stabilized and are unlikely to change significantly but breaking changes are still possible.
- `stable`: The interface is considered stable and breaking changes will be avoided where possible. Breaking changes that cannot be avoided will be accompanied by a major version bump.
- `deprecated`: The API is no longer recommended for use and may be removed in a future release.

Lifecycle stages are indicated in the documentation for each class, method and parameter using a `[lifecycle: <stage>]` tag. For example:

```python
class DataFrame():
    """
    A multi-column table with indexing on user-specified columns [lifecycle: maturing].
    """
...
    def create(
        self,
        schema: pa.Schema,
    ) -> "DataFrame":
        """
        Create a SOMADataFrame from a `pyarrow.Schema` [lifecycle: maturing].

        Parameters
        ----------
        schema : pyarrow.Schema
            The schema of the DataFrame to create [lifecycle: stable].
        """
```

If a class, method, or parameter is not explicitly marked with a lifecycle stage, it is assumed to be `experimental`.

# Data Model

The data model comprises two layers:

- a set of _foundational_ types which are general in nature.
- a set of _composed_ types, which are composed from the foundational types and are intended to improve ease of dataset use and interoperability.

The foundational types are:

- `SOMACollection`: a string-keyed container (key-value map) of other SOMA data types, e.g., `SOMADataFrame`, `SOMASparseNDArray`, and `SOMACollection`.
- `SOMADataFrame`: a multi-column table -- essentially a dataframe with indexing on user-specified columns.
- `SOMAGeometryDataFrame` and `SOMAPointCloudDataFrame`: multi-column tables for storing spatial indexed dataframes, available for point or full geometry instantiations.
- `SOMADenseNDArray` and `SOMASparseNDArray`: an offset-addressed (zero-based), single-type N-D array, available in either sparse or dense instantiations.
- `SOMAMultiscaleImage`: a multiscale image pyramid that stores multiple levels of `SOMADenseNDArray`s.

The composed types are:

- `SOMAExperiment`: a specialization and extension of `SOMACollection`, codifying a set of naming and indexing conventions to represent an annotated, 2-D matrix of observations across _multiple_ sets of variables.
- `SOMAMeasurement`: a specialization and extension of `SOMACollection`, that contains a set of annotated observables that are common to one or more sets of measurements and/or derived calculations.
- `SOMAScene`: a specialization and extension of `SOMACollection` that stores spatially resolved data that can be registered to a single coordinate space.

In this document, the term `dataframe` implies something akin to an Arrow `Table` (or `RecordBatch`), R `data.frame` or Python `pandas.DataFrame`, where:

- multiple columns may exist, each with a string column name.
- all columns are individually typed and contain simple data types (e.g., `int64`).
- all columns are of equal length.
- rows are addressed by one or more dataframe columns.

All SOMA data objects are named with URIs.

## Base Type System

The SOMA API borrows its base type system from the Arrow language-agnostic in-memory system for data typing and serialization ([format](https://arrow.apache.org/docs/format/Columnar.html)). The SOMA API is intended to be used with an Arrow implementation such as [PyArrow](https://arrow.apache.org/docs/python/) or the [Arrow R package](https://arrow.apache.org/docs/r/), or other libraries which interoperate with Arrow (e.g., Pandas).

Where SOMA requires an explicit typing system, it utilizes the Arrow types and schema. SOMA has no specific requirements on the type or serialization system used by the underlying storage engine, other than it be capable of understanding and representing the Arrow types. It is expected that any given implementation of SOMA will have limits on the underlying capabilities of its data-type system (e.g., just because you can express a type in the Arrow type system does not mean all SOMA implementations will understand it).

### Type definitions used in this document

In the following:

- `primitive` types in this specification refer to Arrow primitive types, e.g., `int32`, `float`, etc.
- `string` refers to Arrow UTF-8 variable-length `string`, i.e., `List<Char>`.
- `simple` types include all primitive types, plus `string`.

Other Arrow types are explicitly noted as such, e.g., `Arrow RecordBatch`.

Numeric index types (e.g., offset indexing into dense arrays) are specified with `int64` type and a domain of `[0, 2^63-1]`. In other words, non-negative `int64` values are used for offset indexing.

### Type conformance and promotion

SOMA is intended to be strongly typed. With one exception noted below, all requests for a given Arrow type must be fulfilled or generate an error based upon the capabilities of the underlying storage system. Silently casting to a less capable type (e.g., `float64` to `float32`) is _not_ permitted. All operations specifying or introspecting the type system must be self-consistent, e.g., if object `create` accepts a given Arrow type or schema, the `get schema` operation must return the same types.

SOMA _does_ permit one form of type promotion: variable-length types (`string`, `binary`) may be promoted to their 64-bit-length variants (`large_string`, `large_binary`) at the time of object creation. However, this promotion must be explicit and visible to the API user via the `get schema` operation.

SOMA places no constraints on the underlying types used by the storage system, as long as the API-level representation is consistent across operations, and the supported types fully match the Arrow definition of their type semantics.

## Metadata

All SOMA objects may be annotated with a small amounts of simple metadata. Metadata for any SOMA object is a `string`-keyed map of values. Metadata values are Arrow primitive types and Arrow strings. The metadata lifecycle is the same as its containing object, e.g., it will be deleted when the containing object is deleted.

> ℹ️ **Note**: larger or more complex types should be stored using `SOMADataFrame`, `SOMADenseNDArray` or `SOMASparseNDArray` and added to a `SOMACollection`.

## Foundational Types

The foundational types represent the core data structures used to store and index data. They are intended to be moderately general-purpose, and to serve as building blocks for the [composed types](#composed-types) which codify domain-specific use cases (e.g., single-cell experimental datasets).

### SOMACollection

`SOMACollection` is an unordered, `string`-keyed map of values. Values may be any SOMA foundational or composed type, including other (nested) `SOMACollection` objects. Keys in the map are unique and singular (no duplicates, i.e., the `SOMACollection` is _not_ a multi-map). The `SOMACollection` is expected to be used for a variety of use cases:

- as a container of independent objects (e.g., a collection of single-cell datasets, each manifest as a [`SOMAExperiment`](#soma-experiment) object).
- as the basis for building other composed types (e.g., using `SOMACollection` to organize pre-defined fields in [`SOMAExperiment`](#soma-experiment) such as multiple layers of `X`).

#### Collection entry URIs

Collections refer to their elements by URI.
A collection may store its reference to an element by **absolute** URI or **relative** URI.

A reference to an **absolute** URI is, as the name implies, absolute.
This means that the collection stores the full URI of the element.
When the backing storage of the collection itself is moved, absolute URI references do not change.

A collection can also refer to sub-paths of itself by **relative** URI.
This means that the collection's elements are stored as suffixes of the collection's path; for instance for a collection at `backend://host/dataset`, the name `child` would refer to `backend://host/dataset/child`.
This applies both to truly hierarchical systems (like POSIX filesystems) and systems that are technically non-hierarchical but can emulate a hierarchical namespace, like Amazon S3 or Google Cloud Storage.
If the entire directory storing a collection and a child referred to by relative URI is moved, the relative URI references now refer to the changed base URI.
While the term "relative" is used, only **child** URIs are supported as relative URIs; relative paths like `../sibling-path/sub-entry` are not supported.

Consider a directory tree of a SOMA implementation that uses a file named `.collection-info.toml` to store the URIs of the collection's contents:

- `file:///soma-dataset`
  - `collection`
    - `.collection-info.toml`:
      ```toml
      [contents]
      absolute = "file:///soma-dataset/collection/abspath"
      external-absolute = "file:///soma-dataset/more-data/other-data"
      relative = "relpath"
      ```
    - `abspath`
      - _SOMA object data_
    - `relpath`
      - _SOMA object data_
  - `more-data`
    - _SOMA object data_

When `file:///soma-dataset/collection` is opened, the URIs will be resolved as follows:

- `absolute`: `file:///soma-dataset/collection/abspath`.
- `external-absolute`: `file:///soma-dataset/more-data/other-data`.
- `relative`: `file:///soma-dataset/collection/relpath`.

If the entire `collection` directory is moved to a new path:

- `file:///soma-dataset`
  - `old-data`
    - `the-collection`
      - `.collection-info.toml`
        ```toml
        [contents]
        absolute = "file:///soma-dataset/collection/abspath"
        external-absolute = "file:///soma-dataset/more-data/other-data"
        relative = "relpath"
        ```
      - `abspath`
        - _SOMA object data_
      - `relpath`
        - _SOMA object data_
  - `more-data`
    - _SOMA object data_

When `file:///soma-dataset/old-data/the-collection` is opened, the URIs will be resolved as follows:

- `absolute`: `file:///soma-dataset/collection/abspath`
  (This resolved URI is the same as before. However, the data is no longer at this location; attempting to access this element will fail.)
- `external-absolute`: `file:///soma-dataset/more-data/other-data`
  (This URI is identical and still points to the same data.)
- `relative`: `file:///soma-dataset/old-data/the-collection/relpath`
  (This URI resolves differently and still points to the same data even after it has been moved.)

In general, absolute and relative URIs can both be used interchangeably within the same collection (as in the example above).
However, in certain situations, an implementation may support only absolute or relative URIs.
For instance, a purely filesystem-based implementation may support only relative URIs, or a non-hierarchichal storage backend may support only absolute URIs.

### SOMADataFrame

`SOMADataFrame` is a multi-column table with a user-defined schema, defining the number of columns and their respective column name and value type. The schema is expressed as an Arrow `Schema`.

Every `SOMADataFrame` must contain a column called `soma_joinid`, of type `int64` and domain `[0, 2^63-1]`. The `soma_joinid` column contains a unique value for each row in the `SOMADataFrame`, and intended to act as a joint key for other objects, such as `SOMASparseNDArray`.

The default "fill" value for `SOMADataFrame` is the zero or null value of the respective column data type (e.g., `Arrow.float32` defaults to 0.0, `Arrow.string` to `""`, etc).

Most language-specific bindings will provide convertors between `SOMADataFrame` and other convenient data structures, such as Python `pandas.DataFrame`, R `data.frame`.

### SOMAPointCloudDataFrame

`SOMAPointCloudDataFrame` is a multi-column table with a user-defined schema, defining the number of columns and their respective column name and value type. The schema is expressed as an Arrow `Schema`.

Like the `SOMADataFrame`, every `SOMAPointCloudDataFrame` must contain a column called `soma_joinid` of type `int64` and domain `[0, 2^63-1]`. The `soma_joinid` is intended to act as a joint key for other objects, such as `SOMASparseNDArray`. There may be multiple items with the same `soma_joinid` stored in the `SOMAPointCloudDataFrame`.

In addition to the `soma_joinid`, the user must define spatial columns, referred to as "spatial axes", that define the "points" in the array. Each spatial axis must be either an integer or floating type, and they must all have the same type. The user may specify a restriced domain for spatial axes or allow the axes to support the entire valid type range. The spatial axes must be index columns for the `SOMAPointCloudDataFrame`, but the user may also specify other columns as index columns.

The default "fill" value for `SOMAPointCloudDataFrame` is the zero or null value of the respective column data type (e.g., `Arrow.float32` defaults to 0.0, `Arrow.string` to `""`, etc).

### SOMAGeometryDataFrame

`SOMAGeometryDataFrame` is a multi-column table with a user-defined schema, defining the number of columns and their respective column name and value type. The schema is expressed as an Arrow `Schema`.

Like the `SOMADataFrame`, every `SOMAGeometryDataFrame` must contain a column called `soma_joinid` of type `int64` and domain `[0, 2^63-1]`. TThe `soma_joinid` is intended to act as a joint key for other objects, such as `SOMASparseNDArray`. There may be multiple items with the same `soma_joinid` stored in the `SOMAGeometryDataFrame`.

In addition to the `soma_joinid`, every `SOMAGeometryDataFrame` must contain a column called `soma_geometry` with type `binary` that stores a well-known binary blob. The user must provide names for the axes of the geometry stored in the well-known binary that is distinct from the
names of other columns in the table. The `soma_geometry` must be an index column, but the user may also specify other additional columns as
index columns. Multiple items with the same geometry may be stored in the `SOMAGeometryDataFrame`.

SOMADataFrame`is the zero or null value of the respective column data type (e.g.,`Arrow.float32`defaults to 0.0,`Arrow.string`to`""`, etc).

### SOMADenseNDArray

`SOMADenseNDArray` is a dense, N-dimensional array of `primitive` type, with offset (zero-based) integer indexing on each dimension. The `SOMADenseNDArray` has a user-defined schema, which includes:

- type: a `primitive` type, expressed as an Arrow type (e.g., `int64`, `float32`, etc), indicating the type of data contained within the array.
- shape: the shape of the array, i.e., number and length of each dimension.

All dimensions must have a positive, non-zero length, and there must be 1 or more dimensions. Where explicitly referenced in the API, the dimensions are named `soma_dim_N`, where `N` is the dimension number (e.g., `soma_dim_0`), and elements are named `soma_data`.

The default "fill" value for `SOMADenseNDArray` is the zero or null value of the array type (e.g., `Arrow.float32` defaults to 0.0).

> ℹ️ **Note**: on TileDB this is an dense array with `N` `int64` dimensions of domain [0, maxInt64), and a single attribute.

### SOMASparseNDArray

`SOMASparseNDArray` is a sparse, N-dimensional array of `primitive` type, with offset (zero-based) integer indexing on each dimension. The `SOMASparseNDArray` has a user-defined schema, which includes:

- type: a `primitive` type, expressed as an Arrow type (e.g., `int64`, `float32`, etc), indicating the type of data contained within the array.
- shape: the shape of the array, i.e., number and length of each dimension.

All dimensions must have a positive (in particular, non-zero) length, and there must be 1 or more dimensions. Implicitly stored elements (i.e., those not explicitly stored in the array) are assumed to have a value of zero. Where explicitly referenced in the API, the dimensions are named `soma_dim_N`, where `N` is the dimension number (e.g., `soma_dim_0`), and elements are named `soma_data`.

The default "fill" value for `SOMASparseNDArray` is the zero or null value of the array type (e.g., Arrow.float32 defaults to 0.0).

> ℹ️ **Note**: on TileDB this is an sparse array with `N` `int64` dimensions of domain `[0, maxInt64)`, and a single attribute.

### SOMAMultiscaleImage

`SOMAMultiscaleImage` is `string`-keyed map of "images" that are stored as `SOMADenseNDArray`s. The `SOMAMultiscaleImage` is additionally indexed by the maximum shape (largest to smallest). The maximum shape of each `SOMADenseNDArray` must be the size of the entire image, but it may contain regions without data (in which case the `fill` value of the `SOMADenseNDArray` will be used). Keys in the map are unique and singular (no duplicates, i.e., the `SOMAMultiscaleImage` is _not_ a multi-map).

The `SOMAMultiscaleImage` must have a fixed image axis order (e.g. channel-height-width) and a fixed number of channels (if there is a channel column). Each image within the `SOMAMultiscaleImage` must match these conventions. The user may provide names for the columns that correspond to spatial information (e.g. "x" for width and "y" for height).

#### SOMAMultiscaleImage entry URIs

A `SOMAMultiscaleImage` refers to its elements by URI. Like the `SOMACollection`, its reference to an element by **absolute** URI or **relative** URI. See above for a more complete description of **absolute** and **relative** URI behavior.

## Composed Types

Composed types are defined as a composition of foundational types, adding name, type and indexing constraints. These types are intended to facilitate data interoperability, ease of use, and _potentially_ enable implementation optimizations by virtue of their typing and structural guarantees. The initial composed types are motivated by single-cell biology, but additional types may be added in the future for more diverse use cases.

### SOMAExperiment, SOMAMeasurement, and SOMAScene

`SOMAExperiment` is a specialized `SOMACollection`, representing an annotated 2-D matrix of measurements. In the single-cell-biology use case, a `SOMAExperiment` can represent multiple modes of measurement across a single collection of cells (also known as a "multimodal dataset"). Within a `SOMAExperiment`, a set of measurements on a single set of variables (features) is represented as a `SOMAMeasurement`. A `SOMAExperiment` may also contain spatially resolved data that is stored in a `SOMAScene`.

The `SOMAExperiment`, `SOMAMeasurement`, and `SOMAScene` types comprise [foundational types](#foundational-types):

- `SOMAExperiment`: a well-defined set of annotated observations defined by a `SOMADataFrame`, one or more "measurement" on those observations, and one of more "scenes" of the observables and measurements.
- `SOMAMeasurement`: for all observables, a common set of annotated variables (defined by a `SOMADataFrame`) for which values (e.g., measurements, calculations) are stored in `SOMADenseNDArray` and `SOMASparseNDArray`.
- `SOMAScene`: images and spatially indexed data stored on a fixed coordinate system that relate back to the observables and measurements.

In other words, every `SOMAMeasurement` has a distinct set of variables (features), and inherits common observables from its parent `SOMAExperiment`. The `obs` and `var` dataframes define the axis annotations, and their respective `soma_joinid` values are the indices for all matrixes stored in the `SOMAMeasurement`. Each `SOMAScene` stores images and spatial dataframes that join on the `obs` and var` dataframes.

[comment]: <> (TODO: Replace this image with an updated one.)

<figure>
    <img src="images/SOMAExperiment.png" alt="SOMAExperiment">
</figure>

These types have pre-defined fields, each of which have well-defined naming, typing, dimensionality and indexing constraints. Other user-defined data may be added to a `SOMAExperiment`, `SOMAMeasurement`, or `SOMAScene`, as each is a specialization of the `SOMACollection`. Implementations _should_ enforce the constraints on these pre-defined fields. Pre-defined fields are distinguished from other user-defined collection elements, where no schema or indexing semantics are presumed or enforced.

The shape of each axis (`obs` and `var`) are defined by their respective dataframes, and the indexing of matrices is defined by the `soma_joinid` of the respective axis dataframe.

- `obs`: the observation annotations are shared across the entire `SOMAExperiment`. Matrices indexed on this dimension use the domain defined by the `soma_joinid` values of the `obs` SOMADataFrame (also known as `obsid`).
- `var`: the variable annotations are shared within any given `SOMAMeasurement`. Matrices indexed on this dimension use the domain defined by the `soma_joinid` values of the `var` SOMADataFrame (also known as `varid`).

The pre-defined fields of a `SOMAExperiment` object are:

| Field name             | Field type                                | Field description                                                                                                                                                                                                                           |
| ---------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `obs`                  | `SOMADataFrame`                           | Primary annotations on the _observation_ axis. The contents of the `soma_joinid` pseudo-column define the _observation_ index domain, also known as `obsid`. All observations for the `SOMAExperiment` _must_ be defined in this dataframe. |
| `ms`                   | `SOMACollection[string, SOMAMeasurement]` | A collection of named measurements.                                                                                                                                                                                                         |
| `spatial`              | `SOMACollection[string, SOMAScene]`       | A collection of named scenes.                                                                                                                                                                                                               |
| `obs_spatial_presence` | `SOMADataFrame`                           | Join table that stores if a particular _observation_ is stored in a given `SOMAScene`. This dataframe is optional and may be omitted even in a `SOMAExperiment` with multiple `SOMAScene` items.                                            |

The `SOMAMeasurement` is a sub-element of a `SOMAExperiment`, and is otherwise a specialized `SOMACollection` with pre-defined fields:

| Field name             | Field type                                                    | Field description                                                                                                                                                                                                                                                                                  |
| ---------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `var`                  | `SOMADataFrame`                                               | Primary annotations on the _variable_ axis, for variables in this measurement (i.e., annotates columns of `X`). The contents of the `soma_joinid` pseudo-column define the _variable_ index domain, also known as `varid`. All variables for this measurement _must_ be defined in this dataframe. |
| `X`                    | `SOMACollection[string, SOMASparseNDArray\|SOMADenseNDArray]` | A collection of matrices, each containing measured feature values. Each matrix is indexed by `[obsid, varid]`. Both sparse and dense 2D arrays are supported in `X`.                                                                                                                               |
| `obsm`                 | `SOMACollection[string, SOMASparse\|SOMADenseNDArray]`        | A collection of dense matrices containing annotations of each _obs_ row. Has the same shape as `obs`, and is indexed with `obsid`.                                                                                                                                                                 |
| `obsp`                 | `SOMACollection[string, SOMASparseNDArray]`                   | A collection of sparse matrices containing pairwise annotations of each _obs_ row. Indexed with `[obsid_1, obsid_2].`                                                                                                                                                                              |
| `varm`                 | `SOMACollection[string, SOMASparseNDArray\|SOMADenseNDArray]` | A collection of dense matrices containing annotations of each _var_ row. Has the same shape as `var`, and is indexed with `varid`.                                                                                                                                                                 |
| `varp`                 | `SOMACollection[string, SOMASparseNDArray]`                   | A collection of sparse matrices containing pairwise annotations of each _var_ row. Indexed with `[varid_1, varid_2]`                                                                                                                                                                               |
| `var_spatial_presence` | `SOMADataFrame`                                               | Join table that stores if a particular _variable_ is stored in a given `SOMAScene`. This dataframe is optional and may be omitted even if the `SOMAExperiment` the `SOMAMeasurement` is in contains multiple `SOMAScene` items.                                                                    |

The `SOMAScene` is a sub-element of a `SOMAExperiment`, and is otherwise a specialized `SOMACollection` with pre-defined fields:

| Field name | Field type                                                                                    | Field description                                                                                                                                                                                                                     |
| ---------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `obsl`     | `SOMACollection[string, SOMAPointCloudDataFrame\|SOMAGeometryDataFrame]`                      | Location-based annotations on the _observable_ domain. The `soma_joinid` in any item in this collection should be interpreted as the `obsid`                                                                                          |
| `varl`     | `SOMACollection[string, SOMACollection[str, SOMAPointCloudDataFrame\|SOMAGeometryDataFrame]]` | Location-based annotations on the _variable_ domain. The outer collection is keyed on the measurement names. The `soma_joinid` for items in the inner collection should be interpreted as the `varid` for the respective measurement. |
| `img`      | `SOMACollection[string, MultiscaleImage]`                                                     | A collection of multiscale images related to the experiment.                                                                                                                                                                          |

For the entire `SOMAExperiment`, the index domain for the elements within `obsp`, `obsm` and `X` (first dimension) are the values defined by the `obs` dataframe `soma_joinid` column. For each `SOMAMeasurement`, the index domain for `varp`, `varm` and `X` (second dimension) are the values defined by the `var` dataframe `soma_joinid` column in the same measurement. In other words, all predefined fields in the `SOMAMeasurement` share a common `obsid` and `varid` domain, which is defined by the contents of the respective columns in `obs` and `var` dataframes.

As with other `SOMACollections`, the `SOMAExperiment`, `SOMAMeasurement`, and `SOMAScene` also have a `metadata` field, and may contain other user-defined elements. Keys in a `SOMAExperiment`, `SOMAMeasurement`, and `SOMAScene` beginning with the characters `_`, `.`, or `$` are reserved for ad-hoc use, and will not be utilized by this specification. All other keys are reserved for future specifications.

The following naming and indexing constraints are defined for the `SOMAExperiment` and `SOMAMeasurement`:

| Field name                                     | Field constraints                                                                                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `obs`, `var`                                   | Field type is a `SOMADataFrame`.                                                                                                                                         |
| `ms`                                           | Field type is a `SOMACollection`, and each element in the collection has a value of type `SOMAMeasurement`.                                                              |
| `spatial`                                      | Field type is a `SOMACollection`, and each element in the collection has a value of type `SOMAScene`.                                                                    |
| `X`                                            | Field type is a `SOMACollection`, and each element in the collection has a value of type `SOMADenseNDArray` or `SOMASparseNDArray`.                                      |
| `obsp`, `varp`                                 | Field type is a `SOMACollection`, and each element in the collection has a value of type `SOMASparseNDArray`.                                                            |
| `obsm`, `varm`                                 | Field type is a `SOMACollection`, and each element in the collection has a value of type `SOMADenseNDArray`.                                                             |
| `obsm`, `obsp`, `varm`, `varp`                 | Fields may be empty collections.                                                                                                                                         |
| `X` collection values                          | All matrixes must have the shape `(O, V)`, where `O` is the domain of `obs.soma_joinid`, and `V` is the domain of `var.soma_joinid` in the containing `SOMAMeasurement`. |
| `obsm` collection values                       | All matrixes must have the shape `(O, M)`, where `M` is user-defined. The domain of the first dimension is the values of `obs.soma_joinid`.                              |
| `obsp` collection values                       | All matrixes must have the shape `(O, O)`. The domain of both dimensions is the values of `obs.soma_joinid`.                                                             |
| `varm` collection values                       | All matrixes must have the shape `(V, M)`, where `M` is user-defined. The domain of the first dimension is the values of `var.soma_joinid`.                              |
| `varp` collection values                       | All matrixes must have the shape `(V, V)`. The domain of both dimensions is the values of `var.soma_joinid`.                                                             |
| `obs_spatial_presence`, `var_spatial_presence` | Field type is a `SOMADataFrame`. Index columns are `soma_joinid` and a string column named `scene_id` with exactly one other boolean column named `data`.                |

# Functional Operations

The SOMA API includes functional capabilities built around the [SOMA data model](#datamodel.md). The specifics of how these operations manifest in any given language and computing environment is defined elsewhere (**to be created**). Each implementation will minimally support the functional operations defined here. For example, it is likely that a Python implementation will prefer `__getattr__` over an explicit `get()` method, and will augment these functional operations with other Pythonic functionality for ease of use.

In several cases an explicit Application Binary Interface (ABI) has been specified for a function, in the form of an Arrow type or construct. The choice of Arrow as both a type system and data ABI is intended to facilitate integration with third-party software in a variety of computing environments.

Any given storage engine upon which SOMA is implemented may have additional features and capabilities, and support advanced use cases: it is expected that SOMA implementations will expose storage-engine-specific features. Where possible, these should be implemented to avoid conflict with future changes to the common SOMA API. Where possible, types and variables beginning with 'soma' or 'SOMA' should be preserved for future versions of this spec.

> ℹ️ **Note**: this section is just a sketch, and is primarily focused on defining abstract primitive operations that must exist on each type.

## Object lifecycle

SOMA object instances have a lifecycle analogous to the lifecycle of OS-level file objects.
A SOMA object is instantiated by **opening** a provided URI, in one of [_read_ or _write_ mode](#openmode).
The opened object can be manipulated (pursuant to its open state) until it is **closed**, at which point any further calls which attempt to access or modifying backing data will fail (again, akin to a file object).

SOMA objects are open for **exclusively** reading or writing.
When a SOMA object is open for writing, the `read()` method cannot be called. However, its metadata, its schema, and information directly derived from the schema may be inspected.
Additionally, for collection objects, the members of the collection are also accessible when the collection is open in write mode.
For example:

```
writable_collection = soma_impl.open('file:///some/collection', 'w')
dataframe = writable_collection['dataframe']  # OK
dataframe.schema  # OK
dataframe.read(...)  # This is forbidden and will cause an error.
dataframe.metadata['soma_type']  # OK
writable_collection.add_new_collection('new_sub_collection')  # OK

readable_collection = soma_impl.open('file:///other/collection')
nd_array = readable_collection['nd_array']  # OK
nd_array.type  # OK
nd_array.read(...)  # OK
nd_array.write(...)  # This is forbidden.
readable_collection['new_member'] = other_soma_object  # This is forbidden.
```

When a SOMA object is opened for writing, write operations are not guaranteed to be complete until the object is **closed**.

The common SOMA lifecycle operations are as follows:

| Operation                      | Description                                                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| static open(string uri, ...)   | Opens the SOMA object (of the type it is attached to).                                                       |
| static create(string uri, ...) | Creates a new SOMA object (of the given type) at the given URI, and returns that object, opened for writing. |
| close()                        | Closes the SOMA object, flushing all unsaved data.                                                           |

The exact mechanism by which these "static" methods are exposed may vary by language.
For instance, in Python, `@classmethod`s are used, while in a language without class methods, the methods can be implemented as global-level functions:

```python
class Collection:
    @classmethod
    def open(cls, uri, ...): ...
```

```
bool soma_dataframe_exists(char *uri, ...) { ... }
```

Where possible, the lifecycle should be integrated into language-specific resource-management frameworks (e.g., context management with `with` in Python, try-with-resources in Java).

### Operation: create

The `create` static method **creates** a new stored SOMA object, then returns that object opened in write mode.

The create operation should be atomic, in that it is only possible for one caller to successfully create a SOMA object at a given URI (like `open(..., mode='x')` in Python, or the `O_EXCL` flag to the C `open` function).
If an object already exists at the given location, `create` throws an error.

```
SomeSOMAType.create(string uri, [additional per-type parameters], PlatformConfig platform_config, Context context) -> SomeSOMAType
```

Parameters:

- `uri`: The URI where the object should be created.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

Each SOMA type will have its own distinct set of parameters for `create`, described in its own section.

### Operation: open

The `open` static method **opens** a SOMA object of its type and returns it.

If the object does not exist at the given location, `open` throws an error.

```
SomeSOMAType.open(string uri, OpenMode mode = READ, PlatformConfig platform_config, Context context) -> SomeSOMAType
```

Parameters:

- `uri`: URI of the object to open.
- `mode`: The mode to open this object in. Defaults to **read** mode.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

### Operation: close

The `close` method **closes** a SOMA object.
This completes all writes (if applicable) and releases other resources associated with this SOMA object.
Implementations of `close` must be idempotent.

If the implementation permits it, a write operation should function atomically; i.e., any other reader should not see partially-completed reads _until_ the close operation is called.

```
writer = soma_impl.open('file:///write/here', 'w')
writer.write(...)

reader = soma_impl.open('file:///write/here')
reader.read(...)  # May not (ideally, will not) see the data written above.
writer.close()

post_close = soma_impl.open('file:///write/here')
post_close.read(...)  # Will see the data written by write_data.
```

Additionally, opened SOMA object instances are not guaranteed to see changes made by other writers after they were opened.
As with atomic writes above, an implementation may provide an even stronger contract guaranteeing that an opened SOMA object will only see a "snapshot" of the object as of the time of opening.
This applies to all aspects of a SOMA object: data, metadata, collection contents, etc.

```
reader = soma_impl.open('file:///important/data')

writer = soma_impl.open('file:///important/data', 'w')
writer.metadata['key'] = 12
writer.write(...)
writer.close()

# It is not guaranteed that this read will include any of the data written above.
# Some implementations may guarantee that writer's writes will not be visible.
reader.read(...)
reader.metadata['key']  # May not be 12.
```

Collections have additional closing-related semantics, described in [`SOMACollection`'s close operation](#operation-close-collection-types).

## Other common operations

All SOMA objects share the following common operations, in addition to the type-specific operations specified in each type's section:

| Operation                      | Description                                                                                          |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| get metadata                   | Accesses the metadata as a mutable [`SOMAMetadataMapping`](#somametadatamapping).                    |
| get context                    | Gets an implementation-specific [context value](#long-lived-context-data) for the given SOMA object. |
| get soma_type                  | Returns a constant string describing the type of the object.                                         |
| static exists(string uri, ...) | Tells if there is a SOMA object of the given type at the URI.                                        |

### Operation: exists

The `exists` static method checks to see whether a SOMA object of its type is stored at the given URI.

```
SomeSOMAType.exists(string uri, Context context) -> bool
```

The context parameter is optional.

If the object stored at the URI is of a _different_ type, the function should still return false:

```
soma_impl.Experiment.exists("backend://host/path/to/some/experiment")
# -> True
soma_impl.DataFrame.exists("backend://host/path/to/some/experiment")
# -> False; the data stored there is not a DataFrame.
soma_impl.Collection.exists("backend://host/nonexistent/path")
# -> False
```

## SOMACollection

Summary of operations on a `SOMACollection`, where `ValueType` is any SOMA-defined foundational or composed type, including `SOMACollection`, `SOMADataFrame`, `SOMAPointCloudDataFrame`, `SOMAGeometryDataFrame`, `SOMADenseNDArray`, `SOMASparseNDArray`, `SOMAMultiscaleImage`, `SOMAExperiment`, `SOMAMeasurement`, or `SOMAScene`:

| Operation     | Description                                                                |
| ------------- | -------------------------------------------------------------------------- |
| close()       | Closes this `SOMACollection` and other objects whose lifecycle it manages. |
| get soma_type | Returns the constant "SOMACollection".                                     |

In addition, `SOMACollection` supports operations to manage the contents of the collection:

| Operation                                           | Description                                                                               |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| get(string key)                                     | Gets the object associated with the key.                                                  |
| has(string key)                                     | Tests for the existence of key in collection.                                             |
| iterator                                            | Iterates over the collection.                                                             |
| get length                                          | Gets the number of elements in the collection.                                            |
| set(string key, SOMAObject value, use_relative_uri) | Sets the key/value in the collection.                                                     |
| del(string key)                                     | Removes the key/value from the collection. Does not delete the underlying object (value). |
| add_new_collection(string key, ...)                 | Creates a new sub-Collection and adds it to this `SOMACollection`.                        |
| add_new_dataframe(string key, ...)                  | Creates a new `DataFrame` and adds it to this `SOMACollection`.                           |
| add_new_dense_ndarray(string key, ...)              | Creates a new `DenseNDArray` and adds it to this `SOMACollection`.                        |
| add_new_sparse_ndarray(string key, ...)             | Creates a new `SparseNDArray` and adds it to this `SOMACollection`.                       |

A `SOMACollection` also manages the lifecycle of objects directly instantiated by it.
Objects accessed via getting a collection element, or objects created with one of the <code>add_new\_<var>object_type</var></code> methods are considered "owned" by the collection.
All such objects will be automatically closed together by [the collection's close operation](#operation-close-collection-types).

### Operation: create() (Collection types)

Create a new collection of the given type with the user-specified URI.
The collection type created should match the collection type it is called upon; for example `SOMAExperiment.create` should create a `SOMAExperiment`.
This `create` function has no parameters beyond [those shared by all `create` methods](#operation-create).

```
SOMACollectionType.create(string uri, platform_config, context) -> SOMACollectionType
```

### Operation: close (Collection types)

In addition to the details of the [common close operation](#operation-close), closing has additional semantics specific to collection types.

When a `SOMACollection` is directly used to instantiate child SOMA objects, those SOMA objects are considered "owned" by the collection, and the collection manages their lifecycle.
When the collection is closed, it must close any of these child objects before closing itself.
For example:

```
root = soma_impl.open('path://netloc/root/collection', 'w')

child_a = root['child_a']
# child_a was reified by root and is thus is owned by root.
grandchild = child_a['grandchild']
# grandchild is owned by child_a and in turn by root.

new_child = root.add_new_dataframe('new_child', ...)
# new_child was created by root and thus is also owned by root.

external_object = soma_impl.open('path://other/data')
# external_object was created independently and thus has no owner.
root['other_key'] = external_object
# Even though external_object has been set as an element of root,
# the instance `external_object` was not itself created by root
# and is thus still not owned by root.

root.close()
# Root will close its members, which will in turn recursively close theirs.
# The exact order may vary but will still reflect the ownership tree:
#  1. root is asked to close.
#      2. root asks child_a to close.
#          3. child_a asks grandchild to close.
#              4. grandchild closes itself.
#          5. child_a closes itself.
#      6. root asks new_child to close.
#          7. new_child closes itself.
#      8. root closes itself.
#
# external_object remains open because it is not owned by root.
```

A user may close a child object before closing the parent object.
Because `close` is idempotent, this is explicitly allowed.
Closing the child will _not_ otherwise affect the parent object; it will remain open as usual.

### Operation: set

Adds an entry to the collection, overwriting an existing key if one exists already.

```
set(string key, SOMAObject value, URIType uri_type)
```

Parameters:

- `key`: The key to set.
- `value`: The value to set the key to. If a user sets a collection entry to a type inconsistent with the type of that key (e.g., a defined key in a `SOMAExperiment`) or with the general type of the collection (e.g., a collection of `SOMAMeasurement`s), behavior is unspecified. Implementations are encouraged to raise an error if possible, to prevent latent errors when later attempting to use the data.
- `uri_type`: How the collection should refer to the URI of the newly-added element, whether by absolute or relative URI. The default is `auto`, which will use a relative URI if possible but otherwise use an absolute URI. If `absolute`, the entry will always use an absolute URI. If `relative`, the entry will always use a relative URI, and an error will be raised if a relative URI cannot be used.

### Operation: add_new\_<var>object_type</var>

Each <code>add_new\_<var>object_type</var></code> method creates a new SOMA dataset in storage, adds it to the collection (with the same semantics as the `create` operation), and returns it to the user. The newly created entry has the same `context` value as the existing collection and is [owned by the current collection](#operation-close-collection-types).

```
add_new_dataframe(string key, string uri = "", ...) -> SOMADataFrame
add_new_dense_ndarray(string key, string uri = "", ...) -> SOMADenseNDArray
add_new_sparse_ndarray(string key, string uri = "", ...) -> SOMASparseNDArray
```

Parameters:

- `key`: The key to add the new element at. This cannot already be a key of the collection.
- `uri`: An optional parameter to specify a URI to create the new collection, which may be [relative or absolute](#collection-entry-uris). If the URI is relative, the new entry will be added with that relative URI. If the URI is absolute, the new entry will be added with that absolute URI. If a collection already exists at the user-provided URI, the operation should fail. If the user does not specify a URI, the collection will generate a new URI for the entry. When possible, this should be a relative URI based on a sanitized version of the key.

The remaining parameters are passed directly to the respective type's `create` static method, except for `context`, which is always set to the current collection's context.

`add_new_collection` has an extra parameter allowing control over the kind of collection to be added:

```
add_new_collection(string key, CollectionType kind, string uri = "", PlatformConfig platform_config) -> SOMACollection
```

- `kind`: The kind of collection to add. For instance, if `SOMAExperiment` is provided, the newly-added collection, and the returned instance, will be a `SOMAExperiment`.

## SOMAScene

<!-- TODO: Add the operations. -->

## SOMADataFrame

Summary of operations:

| Operation                                | Description                                           |
| ---------------------------------------- | ----------------------------------------------------- |
| static create(uri, ...) -> SOMADataFrame | Create a `SOMADataFrame`.                             |
| get soma_type                            | Returns the constant "SOMADataFrame".                 |
| get schema -> Arrow.Schema               | Return data schema, in the form of an Arrow `Schema`. |
| get index_column_names -> [string, ...]  | Return index (dimension) column names.                |
| get count -> int                         | Return the number of rows in the `SOMADataFrame`.     |
| read                                     | Read a subset of data from the `SOMADataFrame`.       |
| write                                    | Write a subset of data to the `SOMADataFrame`.        |

A `SOMADataFrame` is indexed by one or more dataframe columns (also known as "dimensions"). The name and order of dimensions is specified at the time of creation. [Slices](#indexing-and-slicing) are addressable by the user-specified dimensions. The `soma_joinid` column may be specified as an index column.

`SOMADataFrame` rows require unique coordinates. In other words, the read and write operations will assume that any given coordinate tuple for indexed columns uniquely identifies a single dataframe row.

### Operation: create()

Create a new `SOMADataFrame` with user-specified URI and schema.

The schema parameter must define all user-specified columns. The schema may optionally include `soma_joinid`, but an error will be raised if it is not of type Arrow.int64. If `soma_joinid` is not specified, it will be added to the schema. All other column names beginning with `soma_` are reserved, and if present in the schema, will generate an error. If the schema includes types unsupported by the SOMA implementation, an error will be raised.

```
create(string uri, Arrow.Schema schema, string[] index_column_names, platform_config, context) -> SOMADataFrame
```

Parameters:

- `uri`: location at which to create the object.
- `schema`: an Arrow Schema defining the per-column schema.
- `index_column_names`: a list of column names to use as index columns, also known as "dimensions" (e.g., `['cell_type', 'tissue_type']`). All named columns must exist in the schema, and at least one index column name is required. Index column order is significant and may affect other operations (e.g., read result order). The `soma_joinid` column may be indexed.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

Returns: The newly created `SOMADataFrame`, opened in write mode.

### get schema

Return the `SOMADataFrame` schema as an Arrow schema object. The schema will include all user- and system-defined columns, including `soma_joinid`.

### get index column names

Return a list of all column names which index the dataframe.

### Operation: read()

Read a user-defined slice of data, optionally filtered, and return results as one or more Arrow.Table.

Summary:

```
read(
    coords=[[coord,...]|all, ...],
    column_names=[`string`, ...]|all,
    batch_size,
    partitions,
    result_order,
    value_filter,
    platform_config,
) -> delayed iterator over Arrow.Table
```

Parameters:

- `coords`: the rows to read. Defaults to all. Coordinates for each dimension may be specified by value, a value range (slice -- see the [indexing and slicing](#indexing-and-slicing) section below), an Arrow array of values, or a list of both.
- `column_names`: the named columns to read and return. Defaults to all, including system-defined columns (`soma_joinid`).
- `batch_size`: a [`SOMABatchSize`](#SOMABatchSize), indicating the size of each "batch" returned by the read iterator. Defaults to `auto`.
- `partitions`: an optional [`SOMAReadPartitions`](#SOMAReadPartitions) to partition read operations.
- `result_order`: a [`ResultOrder`](#resultorder) specifying the order of read results.
- `value_filter`: an optional [value filter](#value-filters) to apply to the results. Defaults to no filter.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

The `read` operation will return a language-specific iterator over one or more Arrow `Table` objects, allowing the incremental processing of results larger than available memory. The actual iterator used is delegated to language-specific SOMA specs.

### Operation: write()

Write an `Arrow.RecordBatch` or `Arrow.Table` to the persistent object. As duplicate index values are not allowed, index values already present in the object are overwritten and new index values are added.

```
write(Arrow.RecordBatch values, platform_config)
write(Arrow.Table values, platform_config)
```

Parameters:

- `values`: a parameter containing all columns, including the index columns. The schema for the values must match the schema for the `SOMADataFrame`.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

All columns, including index columns and `soma_joinid` must be specified in the `values` parameter.

## SOMAPointCloudDataFrame

<!-- TODO: Add the operations. -->

## SOMAGeometryDataFrame

<!-- TODO: Add the operations. -->

## SOMADenseNDArray

Summary of operations:

| Operation                                   | Description                                                      |
| ------------------------------------------- | ---------------------------------------------------------------- |
| static create(uri, ...) -> SOMADenseNDArray | Create a `SOMADenseNDArray` named with the URI.                  |
| get soma_type                               | Returns the constant "SOMADenseNDArray".                         |
| get shape -> (int, ...)                     | Return length of each dimension, always a list of length `ndim`. |
| get ndim -> int                             | Return number of dimensions.                                     |
| get schema -> Arrow.Schema                  | Return data schema, in the form of an Arrow Schema.              |
| get is_sparse -> False                      | Return the constant False.                                       |
| read                                        | Read a subarray from the `SOMADenseNDArray`.                     |
| write                                       | Write a subarray to the `SOMADenseNDArray`.                      |

### Operation: create()

Create a new SOMADenseNDArray with user-specified URI and schema.

```
create(string uri, type, shape, platform_config, context) -> SOMADenseNDArray
```

Parameters:

- `uri`: location at which to create the object.
- `type`: an Arrow `primitive` type defining the type of each element in the array. If the type is unsupported, an error will be raised.
- `shape`: the length of each domain as a list, e.g., [100, 10]. All lengths must be positive values the `int64` range `[0, 2^63-1]`.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

Returns: The newly created `SOMADenseNDArray`, opened for writing.

### Operation: get schema

Return the array schema as an `Arrow.Schema` object. This operation will return the schema of the `Arrow.RecordBatch` objects returned
by the `read`, `record_batches` chained operations. Field names in the schema will be:

- `soma_dim_N`: the type of the Nth dimension. This will always be an `int64` in the range `[0, 2^63-1]`.
- `soma_data`: the user-specified type of the array elements, as specified in the `create` operation.

### Operation: read()

Read a user-specified dense subarray from the object and return as an `Arrow.Tensor`.

Summary:

```
read(
    coords,
    partitions,
    result_order,
    platform_config,
) -> Arrow.Tensor
```

- `coords`: per-dimension slice (see the [indexing and slicing](#indexing-and-slicing) section below), expressed as a per-dimension list of scalar or range.
- `partitions`: an optional [`SOMAReadPartitions`](#SOMAReadPartitions) to partition read operations.
- `result_order`: a [`ResultOrder`](#resultorder) specifying the order of read results.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

The `read` operation will return an Arrow Tensor containing the requested subarray.

### Operation: write()

Write an Arrow `Tensor` to a dense subarray of the persistent object.

```
write(
    coords,
    values,
    platform_config
)
```

Values are specified as an Arrow Tensor.

Parameters:

- `coords`: per-dimension slice, expressed as a per-dimension list of scalar or range.
- `values`: values to be written, provided as an Arrow Tensor. The type of elements in `values` must match the type of the SOMADenseNDArray.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

## SOMASparseNDArray

Summary of operations:

| Operation                                    | Description                                                             |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| static create(uri, ...) -> SOMASparseNDArray | Create a `SOMASparseNDArray` named with the URI.                        |
| get soma_type                                | Returns the constant "SOMASparseNDArray".                               |
| get shape -> (int, ...)                      | Return length of each dimension, always a list of length `ndim`.        |
| get ndim -> int                              | Return number of dimensions.                                            |
| get schema -> Arrow.Schema                   | Return data schema, in the form of an Arrow `Schema`.                   |
| get is_sparse -> True                        | Return the constant True.                                               |
| get nnz -> uint                              | Return the number stored values in the array, including explicit zeros. |
| read                                         | Read a slice of data from the `SOMASparseNDArray`.                      |
| write                                        | Write a slice of data to the `SOMASparseNDArray`.                       |

### Operation: create()

Create a new `SOMASparseNDArray` with user-specified URI and schema.

```
create(string uri, type, shape, platform_config, context) -> SOMASparseNDArray
```

Parameters:

- `uri`: location at which to create the object.
- `type`: an Arrow `primitive` type defining the type of each element in the array. If the type is unsupported, an error will be raised.
- `shape`: the length of each domain as a list, e.g., [100, 10]. All lengths must be in the `int64` range `[0, 2^63-1]`.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

Returns: The newly created `SOMASparseNDArray`, opened for writing.

### Operation: get schema

Return the array schema as an `Arrow.Schema` object. This operation will return the schema of the `Arrow.RecordBatch` objects returned
by the `read`, `record_batches` chained operations. Field names in the schema will be:

- `soma_dim_N`: the type of the Nth dimension. This will always be a `int64` in the range `[0, 2^63-1]`.
- `soma_data`: the user-specified type of the array elements, as specified in the `create` operation.

### Operation: read()

Read a user-specified subset of the object, and return as one or more read batches.

Summary:

```
read(
    coords,
    batch_size,
    partitions,
    result_order,
    platform_config,
) -> SOMASparseNDArrayRead
```

- `coords`: per-dimension slice (see the [indexing and slicing](#indexing-and-slicing) section below), expressed as a scalar, a range, an Arrow array or chunked array of scalar, or a list of both.
- `batch_size`: a [`SOMABatchSize`](#SOMABatchSize), indicating the size of each "batch" returned by the read iterator. Defaults to `auto`.
- `partitions`: an optional [`SOMAReadPartitions`](#SOMAReadPartitions) to partition read operations.
- `result_order`: a [`ResultOrder`](#resultorder) specifying the order of read results.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

The `read` operation will return a `SOMASparseNDArrayRead` type, allowing the result encoding type to be selected. The encoding type, in turn, will provide a language-specific iterator over the result data, allowing for the incremental processing of results larger than available memory. The actual iterator used is delegated to language-specific SOMA specs.

### Operation: write()

Write values to the persistent object. As duplicate coordinates are not allowed, coordinates already present in the object are overwritten and new coordinates are added.

```
write(values, platform_config)
```

Values to write may be provided in a variety of formats:

- `Tensor`: caller provides values as an `Arrow.Tensor`, and the coordinates at which the dense tensor is written.
- `SparseTensor`: caller provides a Arrow COO, CSC or CSR `SparseTensor`.
- `RecordBatch`: caller provides COO-encoded coordinates and data as an `Arrow.RecordBatch`.
- `Table`: caller provides COO-encoded coordinates and data as an `Arrow.Table`.

Parameters:

- `values`: values to be written. The type of elements in `values` must match the type of the `SOMASparseNDArray`.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.

## SOMAMultiscaleImage

<!-- TODO: Add the operations. -->

## Enumeration types

Some functions accept enumerated values as parameters. Language-specific implementations may use language-provided `enum` types to implement these, or use bare constants or another mechanism, depending upon the context.

### OpenMode

The mode used to open a SOMA object from storage, defining the operations that can be performed.

| Entry   | Description                                                                   |
| ------- | ----------------------------------------------------------------------------- |
| `read`  | The default opening mode. The caller can read from the object, but not write. |
| `write` | The caller can write to the object, but not read.                             |

In the Python implementation, this uses the string constants `'r'` and `'w'`.

For more details about the semantics of read and write mode, see the [object lifecycle](#object-lifecycle) section.

### ResultOrder

The order that values will be returned from a read operation.

| Entry          | Description                                                                        |
| -------------- | ---------------------------------------------------------------------------------- |
| `auto`         | The caller does not care about result order. Results can be returned in any order. |
| `row-major`    | The results are returned in row-major order.                                       |
| `column-major` | The results are returned in column-major order.                                    |

### URIType

How the URI of a new element should be stored by a collection.

| Entry      | Description                                                          |
| ---------- | -------------------------------------------------------------------- |
| `auto`     | The collection will determine what type of URI to use automatically. |
| `absolute` | The collection will always use an absolute URI to store the entry.   |
| `relative` | The collection will always use a relative URI to store the entry.    |

In the Python implementation, this is represented with a `use_relative_uri` parameter to the given method, where `None` (the default) represents `auto`, `False` represents `absolute`, and `True` represents `relative`.

See [collection entry URIs](#collection-entry-uris) for details about the semantics of absolute and relative URIs as they pertain to collections.

## Common Interfaces

The following are interfaces defined only to make the subsequent specification simpler. They are not elements in the data model, but rather are named sets of operations used to facilitate the definition of supported operations.

### SOMAMetadataMapping

The `SOMAMetadataMapping` is an interface to a string-keyed mutable map, representing the available operations on the metadata field in all foundational objects. In most implementations, it will be presented with a language-appropriate interface, e.g., Python `MutableMapping`.

The following operations will exist to manipulate the mapping, providing a getter/setter interface plus the ability to iterate on the collection:

| Operation                      | Description                                            |
| ------------------------------ | ------------------------------------------------------ |
| get(string key) -> value       | Get the value associated with the key.                 |
| has(string key) -> bool        | Test for key existence.                                |
| set(string key, value) -> void | Set the value associated with the key.                 |
| del(string key) -> void        | Remove the key/value from the collection.              |
| iterator                       | Iterate over the collection.                           |
| get length                     | Get the length of the map, the number of keys present. |

> ℹ️ **Note**: it is possible that the data model will grow to include more complex value types. If possible, retain that future option in any API defined.

### SOMABatchSize

Read operations on foundational types return an iterator over "batches" of data, enabling the processing of larger-than-core datasets. The `SOMABatchSize` allows user control over read batch size, and accepts the following methods of determining batch size:

| BatchSize type | Description                                                                                                                                           |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `count`        | Batch size defined by result count. For a SOMADataFrame this indicates row count returned per `Arrow.Table`, or for an ND array the number of values. |
| `size`         | Partition defined by size, in bytes, e.g., max `Arrow.Table` size returned by `SOMADataFRame` read operation.                                         |
| `auto`         | An automatically determined, "reasonable" default partition size. This is the default batch size.                                                     |

### SOMAReadPartitions

To facilitate distributed computation, read operations on foundational types accept a user-specified parameter indicating the desired partitioning of reads and which partition any given read should return. The following options are supported:

| Partition Type | Description                                                                                                                                                                        |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `IofN`         | Given I and N, read operations will return the Ith partition of N approximately equal size partitions. Partition boundaries will be stable for any given N and array or dataframe. |

### SOMASparseNDArrayRead

`SparseNDArray` `read` operations can return results in a variety of formats. The `SOMASparseNDArrayRead` type is an intermediate result type that allows the client to choose the encoding format that will be used to return the result data.

| Format         | Description                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------- |
| `dense`        | Return an iterator of `Arrow Tensor`s containing slice values.                                |
| `coos`         | Return an iterator of `Arrow.SparseCOOTensor`s containing COO-encoded coordinates and values. |
| `record-batch` | Return an iterator `Arrow.RecordBatch` containing COO-encoded coordinates and values.         |
| `table`        | Return an iterator of `Arrow.Table`s containing COO-encoded coordinates and values.           |

## General Utilities

Summary:

```
open(string uri, ...) -> SOMA object      # identify a SOMA object and open it
get_SOMA_version() -> string              # return semver-compatible version of the supported SOMA API
get_implementation() -> string            # return the implementation name, e.g., "R-tiledb"
get_implementation_version() -> string    # return the package implementation version as a semver-compatible string
get_storage_engine() -> string            # return underlying storage engine name, e.g., "tiledb"
```

Semver compatible strings comply with the specification at [semver.org](https://semver.org).

### Method: open

The `open` global method finds the SOMA data at the given URI, identifies its type using metadata, and opens it as that type.

If there is no SOMA object at the given URI, `open` raises an error.

```
open(string uri, OpenMode mode, PlatformConfig platform_config, Context context) -> SOMAObject
```

Parameters:

- `uri`: The URI to open.
- `mode`: The mode to open in. Defaults to **read** mode.
- [`platform_config`](#platform-specific-configuration): optional storage-engine-specific configuration.
- [`context`](#long-lived-context-data): optional context to use for this new object.

For example, a Java-based implementation might look like this:

```java
SOMAObject theDataFrame = SOMAImpl.open("file:///path/to/some/dataframe");
theDataFrame.class;  // -> example.somaimpl.DataFrame
theDataFrame.mode();  // READ
SOMAObject writeExperiment = SOMAImpl.open("file:///path/to/some/exp", "w");
writeExperiment.class;  // -> example.somaimpl.Experiment
writeExperiment.mode();  // WRITE
```

### Method: get_SOMA_version

## Indexing and slicing

- In the above `read()` methods, indexing by an empty list of coordinates must result in zero-length query results.
- Negative indices must not be interpreted as aliases for positive indices (as is common in Python) or as exclusionary (as is common in R).
- Slices define a closed interval, i.e., are doubly inclusive of specified values. For example, slicing with bounds 2 and 4 includes array indices 2, 3, and 4.
- Slices may include the lower bound, upper bound, both, or neither:
  - Slicing with neither (e.g., Python's `[:]`) means select all.
  - Slicing with lower bound 2 and no upper bound selects indices 2 through the highest index present in the given data.
  - Slicing with no lower bound and upper bound 4 selects from the lower index present in the given data up to and including 4.
- Slice steps, or stride, if supported in the implementation language, may only be 1.

## Value Filters

Value filters are expressions used to filter the results of a `read` operation, and specify which results should be returned. Value filters operate on materialized columns, including `soma_joinid`, and will not filter pseudo-columns such as `soma_rowid`.

The specific means to create and manipulate a value filter is delegated to per-language specifications. This specification uses a pseudo-language for _examples only_.

Value filter expressions will have the following capabilities:

- per-column filter expressions which define:
  1. a column name,
  1. a comparison operator, supporting `==`, `!=`, `<`, `>`, `<=`, `>=`,
  1. and a constant.
- compound expressions combining other expressions with AND and OR boolean operations.

Examples, using a pseudo-syntax:

- `col_A > 0`
- `(col_A > 0) AND (col_B != "deleted")`

## Platform-Specific Configuration

SOMA includes provisions for two separate ways to provide platform-specific configuration data to objects and operations.
All SOMA operations include a `platform_config` parameter that allow a caller to provide implementation-specific configuration settings that affect the behavior of an operation on per-call basis.
All SOMA objects expose a `context` field that contain implementation-specific configuration settings and shared local state that apply to all operations called on a SOMA object, any of its children, and any other SOMA objects that share the same `context` instance. These settings and state are used for the entire lifetime of that object and any other objects sharing the same `context`.

### Per-call configuration

Many operations include a `platform_config` parameter.
This parameter provides a generic way to pass storage-platform–specific hints to the backend implementation that cannot effectively be exposed in SOMA’s generic, platform-agnostic API.
End users and libraries can use these to tune or otherwise adjust the behavior of individual operations without needing to know exactly which backend is being used, or directly depending upon the storage platform implementation in question.

The `platform_config` parameter is defined as a key–value mapping from strings to configuration data.
Each **key** in the mapping corresponds to the name of a particular SOMA implementation (i.e., the same string returned by the `get_storage_engine` call).
The value stored in each is implementation defined.
For example, a Python library that handles SOMA dataframes would make a call that looks roughly like this:

```python
def process(df: somacore.DataFrame) -> ...:
    # ...
    results = df.read(
        ...,
        platform_config={
            "tiledb": {
                # TileDB-specific read config settings go here.
            },
            "otherimpl": {
                # OtherImpl-specific read config settings go here.
            },
        },
    )
```

When a `SOMADataFrame` is passed into this code, the function does not need to care whether the dataframe in question is TileDB-based, OtherImpl-based, or otherwise; each platform will read the configuration necessary to tune its own reading process (and in other cases, the storage backend will simply use the default settings).

Implementations may also accept an implementation-specific type as a `platform_config` parameter.
Other implementations should ignore `platform_config` objects not specific to their implementation:

```python
df.read(
    ...,
    platform_config=someimpl.SomeImplConfig(...),
)
# A someimpl-based dataframe can use the passed-in SomeImplConfig.
# Any other implementation, e.g. tiledbsoma, should ignore the SomeImplConfig
# and act as if no platform_config were passed at all.
```

#### Configuration data structure

The exact contents of each platform’s entry in the configuration mapping are fully specified by that platform’s implementation itself, but it should conform to certain conventions.
While the specification or its generic implementation cannot _enforce_ these guidelines, following them will ensure that API users have a consistent and predictable interface.

- At the top level, each individual platform’s configuration should be a string-keyed mapping.
  - In Python, these keys should be `snake_case`.
- The contents of these configuration entries should be represented declaratively, using built-in data structures from the host language to the extent possible (for example, strings, dicts, lists and tuples, etc. in Python).
  This allows libraries that use SOMA objects to provide configuration data to multiple platforms without having to depend upon implementation it _may_ want to use.
  - An implementation may also use objects and types from libraries that the generic SOMA interface specification uses, like Arrow types.
  - For highly-specialized cases, a storage platform implementation may also accept values of a platform-defined type.
    However, to the extent possible, using platform-specific objects should be an option _in addition to_ a fully delcarative structure, and should _not_ be the _only_ way to provide configuration data.
- In situations where a configuration setting of the same name, but with different type, semantics, or values will be used across operations, a separate string key should be provided for that setting for each operation.
  This allows for the same `platform_config` data to be reused across multiple operations by the user.
  - For example, a storage backend may provide a way to read and write data in a given block size.
    However, the performance characteristics of these operations may be very different.
    The implementation should provide `read_block_size` and `write_block_size` parameters (or use some similar disambiguation strategy) rather than only allowing a single `shard_size` parameter.

#### Implementation and usage guidelines

The configuration passed in the `platform_config` object is intended for operation-specific tuning (though it may make sense for user code to use the same `platform_config` across multiple operations).
A `platform_config` should only be used for the operation it was provided to (and to directly dependent operations); it should not be stored for later calls.
Environmental configuration (like login credentials or backend storage region) should be provided via the (to-be-defined) Context object.

Operations should not _require_ a `platform_config` entry to complete; the platform should use a sensible default if a given configuration value is not provided.
Required environmental data generally belongs in the Context object.

A platform should only ever examine its own entry in the `platform_config` mapping.
Since the structure and contents of each entry is wholly implementation-defined, one platform cannot make any assumptions at all about another’s configuration, and for predictability should avoid even trying to extract any information from any other configuration entries.
If the platform does not recognize the type of the `platform_config` object (e.g., it is a type provided by another implementation), the platform should ignore the value entirely.

### Long-lived context data

In addition to the `platform_config` parameters described above, implementations can also store a value on the `context` field of a SOMA object.
This read-only field should be used to store long-lived implementation-specific settings that are used to access SOMA datasets.
Examples of settings that might belong in a context includes:

- Storage credentials or API keys.
- Endpoint URLs.
- Database connections.

In other words, the `context` contains what is effectively shared configuration information across multiple individual SOMA objects.
A context can be specified when instantiating a SOMA object, whether in the process of creating new SOMA data in storage, or in the process of opening existing stored SOMA data.
Implementations should provide a new empty "default" context if one is not specified when opening an object.
This context is automatically propagated by implementations when a parent object is used to access a child.
For example, in a hypothetical Python SOMA implementation named `somalib`:

```python
# The details of context creation are implementation-defined; this is just a
# hypothetical builder that returns a `context` used by somaimpl.
context = somaimpl.create_context(...)

exp = somaimpl.open("file:///uri/of/some/experiment", "w", context=context)
# The data in the `context` value is used when opening the Experiment,
# and is available at `exp.context`.

obs_df = exp.obs
# The `obs` field of `exp` is opened. When opening it, the Experiment passes
# its context value into the dataframe's opener.

exp.ms.add_new_collection("bases", somaimpl.Measurement)
# The context value in `exp` is first used to open `exp.ms`, and then `exp.ms`
# uses that same context value in the creation of the new "bases" collection.

# A user can open other data in a different context:
unrelated_collection = somaimpl.open("file:///unrelated/collection", "r")
# In this case, the context of `unrelated_collection` is completely separate
# from that of `exp`.

# and they can manually pass the context of an existing SOMA object when
# opening (or creating) a different SOMA object.
another_collection = somaimpl.Collection.create(
    "file:///another/collection", context=unrelated_collection.context)
```

While this example code is Python-based, the core concepts and data flow apply to the use of Contexts in any language.

The format and contents of a Context object is completely implementation-defined.
An implementation may provide a way to construct its specific context type, which can be used by user setup code to connect to the SOMA data store (represented above as the `somaimpl.create_context` call).
However, client code should treat the `context` object on any instantiated SOMA objects as an opaque value, and only pass it directly as the context parameter when creating or opening other SOMA data.

# Changelog

1. Acceptance of Arrow as base type system.
2. Adding explicit separation of foundational and composed types, and clarified the intent of composed types.
3. Rename `uns` to `metadata`.
4. Added initial prose for value filter expressions.
5. Added further clarification to read incremental return.
6. SOMAMatrix removed.
7. Operations clarified (add description). Remove assumption of handle/object state.
8. SOMADataFrame generalized to row-indexed or (multi-) user-indexed. Adding \_\_rowid pseudo-column to use in indexing dense matrices.
9. Introduced SOMADenseNdArray/SOMAsparseNdArray and SOMAExperiment/SOMAMeasurement.
10. Removed composed type `SOMA`.
11. Added initial general utility operations.
12. Clarified the data types that may be stored in `metadata`.
13. Clarified namespacing of reserved slots in SOMAExperiment/SOMAMeasurement.
14. Renamed SOMAMapping to SOMAMetadataMapping to clarify use.
15. Add read partitions and ordering to foundational types.
16. Clarify ABI for read/write chunks to NDArrays.
17. Removed open issues around `raw` - there is already sufficient expressiveness in this spec.
18. Removed var_ms/obs_ms.
19. Editorial cleanup and clarifications.
20. Simplified dataframe indexing to indexed/non-indexed. Removed from data model; isolated to only those operations affected.
21. Add parameter for storage-engine-specific config, to read/write/create ops.
22. Support both sparse and dense ndarray in SOMAExperiment X slot.
23. Split read batch_size and partitioning, and clarify intent.
24. Allow multiple format support for NDArray read/write ops.
25. Clarified SOMACollection delete semantics.
26. \_\_rowid changed to soma_rowid. Use `soma` and `SOMA` as "reserved" prefixes.
27. Various editorial clarifications.
28. Clarify distinction between soma_rowid pseudo-column and soma_joinid column.
29. Split indexed/non-indexed dataframe into two types to clarify differing indexing/slicing semantics, and the existence of the soma_rowid pseudo-column only in non-indexed dataframes.
30. Most use of Arrow RecordBatch updated to be a Table, as this allows for chunked arrays (larger objects).
31. Clarify that read operations can accept a "list of scalar" in the form of an Arrow Array or ChunkedArray.
32. Clarify the return value of `get schema` operation for NdArray types.
33. Clarified the function name returning the SOMA API version (`get_SOMA_version`), and bumped API version to `0.2.0-dev`.
34. All offset types (soma_rowid, soma_joinid) changed from uint64 to positive int64.
35. Remove `reshape` operation from the NdArray types.
36. Clarify type conformance and promotion.
37. NdArray COO column names - add `soma` prefix to move all names into the reserved namespace.
38. Clarify explicit nature of soma_rowid/soma_joinid handling throughout.
39. Renamed `type` fields to `soma_type`.
40. Remove SOMADataFrame; rename `SOMAIndexedDataFrame` to `SOMADataFrame`.
41. Add description of `platform_config` objects.
42. Change `NdArray` to `NDArray`.
43. Add `context` field.
44. Pull description of common operations into its own section.
45. Specify object lifecycle and related operations (`create`, `open`, `add_new_*`, etc.).
46. Uniformize backticks, punctuation, etc.
47. Fixed erroneous backticks, spelling, and capitalization.
48. Renamed `SOMADataFrame.read()` `ids` param and `SOMASparseNDArray.read()` `slice` param to `coords`, for consistency between `SOMADataFrame`, `SOMASparseNDArray` and `SOMADenseNDArray` types.
49. Updated `SOMABatchFormat` section, renaming to `SOMASparseNDArrayRead` and removing the `csr`, `csc`, and `record-batch` format options.
50. Removed `SOMASparseNDArray.read()` `batch_format` param and changed return type to `SOMASparseNDArrayRead`.
51. Renamed `Collection.add_new_collection()` `type` param to `kind`.
52. Removed ⚠️-marked commentary.
53. Added `SOMAMeasurement` to "Data Model" section, under "composed types".
54. Allowed all N-d arrays to be sparse.
55. Added new datatypes `SOMAScene`, `SOMAPointCloudDataFrame`, `SOMAGeometryDataframe`, and `SOMAMultiscaleImage`, and bumped the API version to `0.3.0-dev`.
