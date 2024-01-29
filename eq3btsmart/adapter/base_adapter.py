from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from construct import Adapter

EncodedType = TypeVar("EncodedType")
DecodedType = TypeVar("DecodedType")


class BaseAdapter(ABC, Generic[DecodedType, EncodedType]):
    """Base class for adapters."""

    def __init__(self, value: DecodedType):
        """Initialize the parser."""

        self._value: DecodedType = value

    @property
    def value(self) -> DecodedType:
        """Return the original value."""

        return self._value

    @classmethod
    def adapter(cls) -> Type[Adapter]:
        """Return the adapter."""

        class Eq3Adapter(Adapter):
            def _decode(
                self, obj: EncodedType, ctx, path
            ) -> BaseAdapter[DecodedType, EncodedType]:
                return cls(cls._decode(obj))

            def _encode(self, obj: BaseAdapter, ctx, path) -> EncodedType:
                return obj.encode()

        return Eq3Adapter

    def encode(self) -> EncodedType:
        """Return the bytes from the parser."""

        return self._encode(self.value)

    @classmethod
    def decode(cls, value: EncodedType) -> "BaseAdapter":
        """Return the parser from bytes."""

        return cls(cls._decode(value))

    @classmethod
    @abstractmethod
    def _encode(cls, value: DecodedType) -> EncodedType:
        """Return the encoded value."""

    @classmethod
    @abstractmethod
    def _decode(cls, value: EncodedType) -> DecodedType:
        """Return the decoded value."""

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, self.__class__) and self.value == __value.value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"
