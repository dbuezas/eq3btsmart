from construct import Adapter, Construct
from construct_typed import Context

from eq3btsmart.adapter.base_adapter import BaseAdapter


class MockAdapter(BaseAdapter[str, int]):
    @classmethod
    def _encode(cls, value: str) -> int:
        return int(value)

    @classmethod
    def _decode(cls, value: int) -> str:
        return str(value)


def test_value():
    assert MockAdapter("1").value == "1"


def test_encode():
    assert MockAdapter("2").encode() == 2


def test_decode():
    assert MockAdapter.decode(3) == MockAdapter("3")


def test_eq():
    assert MockAdapter("4") == MockAdapter("4")


def test_adapter():
    assert issubclass(MockAdapter.adapter(), Adapter)
    assert MockAdapter.adapter()(Construct())._decode(5, Context(), "") == MockAdapter(
        "5"
    )
    assert (
        MockAdapter.adapter()(Construct())._encode(MockAdapter("6"), Context(), "") == 6
    )


def test_str():
    assert str(MockAdapter("7")) == "7"


def test_repr():
    assert repr(MockAdapter("8")) == "MockAdapter(8)"
