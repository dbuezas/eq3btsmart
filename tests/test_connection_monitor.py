import asyncio

import pytest

from eq3btsmart.thermostat import Thermostat
from tests.mock_client import MockClient


@pytest.mark.asyncio
async def test_connection_monitor_do_not_reconnect(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    assert mock_thermostat._conn.is_connected

    await mock_thermostat._conn.disconnect()

    assert not mock_thermostat._conn.is_connected

    await mock_thermostat._monitor._check_connection()

    assert not mock_thermostat._conn.is_connected


@pytest.mark.asyncio
async def test_connection_monitor_reconnect(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await asyncio.sleep(0.5)

    assert mock_thermostat._monitor._run
    assert mock_thermostat._conn.is_connected

    mock_client: MockClient = mock_thermostat._conn  # type: ignore

    mock_client._is_connected = False

    assert mock_thermostat._monitor._run

    await mock_thermostat._monitor._check_connection()

    assert mock_thermostat._conn.is_connected


@pytest.mark.asyncio
async def test_connection_monitor_ignore_exception(mock_thermostat: Thermostat):
    mock_thermostat._monitor._run = True

    await mock_thermostat._monitor._check_connection()

    assert mock_thermostat._conn.is_connected

    mock_client: MockClient = mock_thermostat._conn  # type: ignore

    mock_client._fail_on_connect = True
    mock_client._is_connected = False

    await mock_thermostat._monitor._check_connection()

    assert not mock_thermostat._conn.is_connected
