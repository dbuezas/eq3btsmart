from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Self, Type, TypeVar

from eq3btsmart.structures import Eq3Struct

StructType = TypeVar("StructType", bound=Eq3Struct)


@dataclass
class BaseModel(ABC, Generic[StructType]):
    @classmethod
    @abstractmethod
    def from_struct(cls, struct: StructType) -> Self:
        """Convert the structure to a model."""

    @classmethod
    @abstractmethod
    def struct_type(cls) -> Type[StructType]:
        """Convert the model to a structure."""

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Convert the data to a model."""

        return cls.from_struct(cls.struct_type().from_bytes(data))
