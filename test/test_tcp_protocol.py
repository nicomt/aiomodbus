import pytest
import struct
from unittest.mock import MagicMock
import aiomodbus
import asyncio

import aiomodbus.exceptions
import aiomodbus.serial
import aiomodbus.tcp


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


def respond(protocol, arr):
    def _tmp(data):
        protocol.data_received(arr)

    return _tmp


@pytest.fixture
def create_mock_coro(mocker, monkeypatch):
    def _create_mock_patch_coro(to_patch=None):
        mock = mocker.Mock()

        async def _coro(*args, **kwargs):
            return mock(*args, **kwargs)

        if to_patch:  # <-- may not need/want to patch anything
            monkeypatch.setattr(to_patch, _coro)
        return mock, _coro

    return _create_mock_patch_coro


@pytest.fixture
def mock_sleep(create_mock_coro):
    # won't need the returned coroutine here
    mock, _ = create_mock_coro(to_patch="asyncio.sleep")
    return mock


@pytest.fixture
def client():
    client = aiomodbus.tcp.ModbusTCPClient("127.0.0.1", 502)
    client.transport = MagicMock()
    client.protocol = aiomodbus.tcp.ModbusTcpProtocol(client)
    client.connected.set()
    return client


@pytest.mark.asyncio
async def test_read_coils(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol,
                                                 b"\x00\x01\x00\x00\x00\x08\x11\x01\x05\xCD\x6B\xB2\x0E\x1B")
    fut = asyncio.create_task(client.read_coils(0x13, 0x25, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x01\x00\x13\x00\x25")
    assert fut.result() == [True, False, True, True, False, False, True, True, True, True, False, True, False, True,
                            True,
                            False, False, True, False, False, True, True, False, True, False, True, True, True, False,
                            False,
                            False, False, True, True, False, True, True]


@pytest.mark.asyncio
async def test_read_discrete_inputs(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x00\x01\x00\x00\x00\x06\x11\x02\x03\xAC\xDB\x35")
    fut = asyncio.create_task(client.read_discrete_inputs(0xC4, 0x16, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x02\x00\xC4\x00\x16")
    assert fut.result() == [False, False, True, True, False, True, False, True, True, True, False, True, True, False,
                            True,
                            True, True, False, True, False, True, True]


@pytest.mark.asyncio
async def test_read_holding_registers(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol,
                                                 b"\x00\x01\x00\x00\x00\x09\x11\x03\x06\xAE\x41\x56\x52\x43\x40")
    fut = asyncio.create_task(client.read_holding_registers(0x6b, 0x3, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x03\x00\x6b\x00\x03")
    assert fut.result() == (0xAE41, 0x5652, 0x4340)


@pytest.mark.asyncio
async def test_read_input_registers(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x00\x01\x00\x00\x00\x05\x11\x04\x02\x00\x0A")
    fut = asyncio.create_task(client.read_input_registers(0x08, 0x1, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x04\x00\x08\x00\x01")
    assert fut.result() == (0xA,)


@pytest.mark.asyncio
async def test_write_coil(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x00\x01\x00\x00\x00\x06\x11\x05\x00\xAC\xFF\x00")
    fut = asyncio.create_task(client.write_single_coil(0xAC, True, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x05\x00\xAC\xFF\x00")


@pytest.mark.asyncio
async def test_write_register(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x00\x01\x00\x00\x00\x06\x11\x06\x00\x01\x00\x03")
    fut = asyncio.create_task(client.write_single_register(0x01, 0x3, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x06\x00\x01\x00\x03")


@pytest.mark.asyncio
async def test_write_coils(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x00\x01\x00\x00\x00\x06\x11\x0F\x00\x13\x00\x0A")
    fut = asyncio.create_task(
        client.write_multiple_coils(0x13, True, False, True, True, False, False, True, True, True, False, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x00\x01\x00\x00\x00\x06\x11\x0F\x00\x13\x00\x0A\x02\xCD\x01")


@pytest.mark.asyncio
async def test_write_registers(mock_sleep, client):
    client.transport.write.side_effect = respond(client.protocol, b"\x11\x10\x00\x01\x00\x02\x12\x98")
    fut = asyncio.create_task(client.write_multiple_registers(0x01, 0xA, 0x102, unit=0x11))
    await fut
    client.transport.write.assert_called_once_with(b"\x11\x10\x00\x01\x00\x02\x04\x00\x0A\x01\x02\xC6\xF0")


@pytest.mark.parametrize("exceptioncls,exception_code", [
    (aiomodbus.exceptions.IllegalFunction, 1),
    (aiomodbus.exceptions.IllegalDataAddress, 2),
    (aiomodbus.exceptions.IllegalDataValue, 3),
    (aiomodbus.exceptions.SlaveDeviceFailure, 4),
    (aiomodbus.exceptions.AcknowledgeError, 5),
    (aiomodbus.exceptions.DeviceBusy, 6),
    (aiomodbus.exceptions.NegativeAcknowledgeError, 7),
    (aiomodbus.exceptions.MemoryParityError, 8),
    (aiomodbus.exceptions.GatewayPathUnavailable, 10),
    (aiomodbus.exceptions.GatewayDeviceFailedToRespond, 11),
    (ConnectionError, 12),
])
@pytest.mark.asyncio
async def test_exceptions(exceptioncls, exception_code, mock_sleep, client):
    client = client
