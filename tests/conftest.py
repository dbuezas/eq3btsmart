import asyncio
from asyncio import AbstractEventLoop, AbstractEventLoopPolicy, DefaultEventLoopPolicy
from typing import Generator

import pytest
from bleak.backends.device import BLEDevice

from eq3btsmart.const import Adapter
from eq3btsmart.thermostat import Thermostat
from eq3btsmart.thermostat_config import ThermostatConfig
from tests.mock_client import MockClient


@pytest.fixture(scope="session", autouse=True)
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy() -> AbstractEventLoopPolicy:
    return DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
def mock_device() -> BLEDevice:
    device = BLEDevice("00:11:22:33:44:55", name=None, details={}, rssi=0)

    return device


@pytest.fixture(scope="function")
@pytest.mark.asyncio
def mock_thermostat(
    monkeypatch: pytest.MonkeyPatch, mock_device: BLEDevice
) -> Thermostat:
    monkeypatch.setattr("bleak.BleakClient", MockClient)
    monkeypatch.setattr("eq3btsmart.thermostat.BleakClient", MockClient)
    from bleak import BleakClient

    client = BleakClient(mock_device)

    assert isinstance(client, MockClient)
    assert not client.is_connected

    thermostat = Thermostat(
        ThermostatConfig(
            mac_address=mock_device.address,
            name="",
            adapter=Adapter.LOCAL,
            stay_connected=True,
        ),
        mock_device,
    )

    return thermostat
