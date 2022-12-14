## Vision

Datasets generated by profiling single cells are rapidly increasing in size and complexity. This has resulted in a need for scalable solutions to accommodate data sizes that no longer fit in memory and flexibility to accommodate the diversity of data being produced. To address these emerging needs in the single cell ecosystem, CZI, in partnership with the Feature and Observation Matrix (FOM) Schema Working Group and TileDB, is launching three projects.

**1. SOMA.**

SOMA, “stack of matrices, annotated,” is a flexible, extensible, and open-source API enabling access to data in a variety of formats. The vision for this API is that it will enable single cell datasets, including those with multiple modalities, to be stored in a cloud-friendly format and will be easily queryable, sliceable, and streamable without downloading or copying the full data. SOMA is designed to be general purpose and is grounded in the core assumption that the data can be modeled as a set of 2D annotated matrices that describe measurements of features across observations.

The first implementation of the SOMA API is currently being built in partnership with [TileDB](https://tiledb.com) on top of their open-source (under the MIT License) [TileDB Embedded](https://tiledb.com/products/tiledb-embedded) storage engine. Both the Python and R APIs will be delivered incrementally in the upcoming months.

**2. Pilot project to offer CZ cellxgene’s Data Resource (30M+ cells and growing) via the SOMA API.**

CZI is working on a pilot project to offer the entirety of cellxgene’s standardized single cell data resource, containing over 30 million cells, as a set of SOMA-backed objects. This resource, paired with the Python and R SOMA APIs bindings, will enable scientists to query, slice, and stream a subset of the data for analysis in downstream single cell toolkits.

Over the next few months, as the SOMA data model and API definition work mature, this resource will be offered to the public with accompanying notebooks demonstrating how to make use of the resource.

**3. Supplementary domain specific libraries and schemas.**

While SOMA is intended to be general purpose, two efforts are underway to build on top of the core SOMA format to make its use more single cell domain adaptable.

The first effort is a set of schemas defining how to capture both multimodal and unimodal single cell data, which will be used as the basis for cellxgene data available via the SOMA API. From the outset, SOMA’s APIs will be designed to interface with multimodal data; the API will enable querying and slicing multimodal datasets along any schema-defined axis.

The second effort is a supplemental library called SOMA.io that will enable users to convert SOMA-backed objects to and from the two most popular domain-specific formats: anndata and Seurat.

Both these efforts will be released in the upcoming months in parallel to the two projects above.

CZI is actively soliciting input from the community to help us refine and extend our roadmap. Please reach out to us at [soma@chanzuckerberg.com](mailto:soma@chanzuckerberg.com) with your ideas! If you would like to learn more about SOMA or would like to keep up to date with the latest developments, please join our mailing list [here](https://bit.ly/soma-signup).
