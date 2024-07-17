"""Definitions of types related to coordinate systems."""

import abc
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import numpy as np
import numpy.typing as npt
import pyarrow as pa


@dataclass
class Axis(metaclass=abc.ABCMeta):
    """A description of an axis of a coordinate system

    Args:
        name: Name of the axis.
        unit:

    Lifecycle: experimental
    """

    name: str
    units: Optional[str] = None
    scale: Optional[np.float64] = None


class CoordinateSpace(metaclass=abc.ABCMeta):
    """A coordinate system for spatial data."""

    @property
    @abc.abstractmethod
    def axes(self) -> Tuple[Axis, ...]:
        """TODO: Add docstring for axes"""
        raise NotImplementedError()


class CoordinateTransform(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def input_space(self) -> CoordinateSpace:
        """TODO: Add docstring for input_space"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def output_space(self) -> CoordinateSpace:
        """TODO: Add docstring for output_space"""
        raise NotImplementedError()

    @abc.abstractmethod
    def apply(self, data: Union[pa.Tensor, pa.Table]) -> Union[pa.Tensor, pa.Table]:
        """TODO: Add docstring for apply"""
        raise NotImplementedError()

    def to_numpy(self) -> npt.NDArray[np.float64]:
        """TODO: Add docstring for to_numpy"""
        raise NotImplementedError()
