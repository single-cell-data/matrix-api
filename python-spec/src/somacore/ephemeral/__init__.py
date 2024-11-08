"""In-memory-only implementations of SOMA types.

These are meant for testing and exploration, where a user may want to do an
ad-hoc analysis of multiple datasets without having to create a stored
Collection.
"""

from .collections import Collection, Experiment, Measurement, Scene

__all__ = (
    "Collection",
    "Experiment",
    "Measurement",
    "Scene",
)
