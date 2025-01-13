# `soma_joinid`: identifier or index? (May 2023)

The SOMA specification introduces `soma_joinid` like so:

> Every `SOMADataFrame` must contain a column called `soma_joinid`, of type `int64` and domain `[0, 2^63-1]`. The `soma_joinid` column contains a unique value for each row in the `SOMADataFrame`, and intended to act as a join key for other objects, such as `SOMASparseNDArray`.

Notice this defines `soma_joinid` merely as an *identifier*; not necessarily starting at zero or one, nor forming a contiguous range, nor even ascending with the data frame's row order. Those are properties associated with an *index*. Though the field is often populated like an index in practice, this need not be so. For example, we might create a `SOMAExperiment` by subsetting the variables of a larger existing one, preserving the original `soma_joinid` in the `var` data frame. Or, observables might be withdrawn from version to version of a `SOMAExperiment`, keeping the `soma_joinid` of the remaining entries in the `obs` data frame.

**However**, beyond this primary definition, `soma_joinid` is also used as the row & column numbers of any `X` matrix in a `SOMAExperiment`. It clearly *is* an index in this secondary role, with the constraint that the row & column numbers correspond to the `soma_joinid` values in the `obs` and `var` dataframes. 

This dual nature of `soma_joinid` is easy to miss, and has caused our team at least two significant design dilemmas:

## 1. Implementations with one-based vector/matrix indexing

Languages like R conventionally use one-based indexing for vectors and matrices. If a given `obs`/`var` item has `soma_joinid = 0`, it cannot be directly represented on a one-based `X` matrix dimension. If we get around that by populating the R implementation of an `X` matrix with `soma_joinid+1`, then the row & column numbers no longer correspond to the `soma_joinid` in the `obs`/`var` data frames -- making the "join" very error-prone.

We addressed this by [introducing a zero-based wrapper](https://github.com/single-cell-data/TileDB-SOMA/pull/1313) for the R matrix implementation, so that `W[i,j]` would access `M[i+1,j+1]` and these index values correspond to the data frame entries as expected. This requires clear signalling and documentation, for example naming the method `SOMASparseNDArray$read_sparse_matrix_zero_based()` and providing an `as.one.based(W)` accessor to the underlying R matrix.

[Alternatives discussed](https://github.com/single-cell-data/TileDB-SOMA/issues/1232) included excluding zero from the domain of `soma_joinid`, or even fully redefining `soma_joinid` as an index; but these would have been significant breaking changes to the SOMA specification after releasing version 1.0.

## 2. Dense array indexing

The definition of `soma_joinid` as an arbitrary integer identifier is problematic for constructing dense matrices indexed by this value, since the values needn't start at zero/one and may be much larger than the actual number of entries. [The role of dense matrices remains unresolved](https://github.com/single-cell-data/TileDB-SOMA/issues/1245) as of this writing, and sparse matrices have been suitable for our initial applications. To fully support dense representations in the future, we may need to introduce another column in the `obs`/`var` data frames that is explicitly the index (row number), and use that for dense indexing instead of `soma_joinid`.


