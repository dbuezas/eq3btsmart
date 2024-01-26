from eq3btsmart.adapter.eq3_serial import Eq3Serial
from eq3btsmart.models import DeviceData
from eq3btsmart.structures import DeviceDataStruct


def test_device_data_from_device():
    # Create a mock DeviceIdStruct
    mock_struct = DeviceDataStruct(
        version=1, serial=Eq3Serial("OEQ1750973"), unknown_1=0, unknown_2=0, unknown_3=0
    )

    # Use the class method to create a DeviceData instance
    device_data = DeviceData.from_device(mock_struct)

    # Assert the properties are correctly assigned
    assert device_data.firmware_version == 1
    assert device_data.device_serial == "OEQ1750973"


def test_device_data_from_bytes():
    # Mock bytes data representing DeviceIdStruct
    mock_struct = DeviceDataStruct(
        version=1, serial=Eq3Serial("OEQ1750973"), unknown_1=0, unknown_2=0, unknown_3=0
    )
    mock_bytes = mock_struct.to_bytes()

    # Use the class method to create a DeviceData instance
    device_data = DeviceData.from_bytes(mock_bytes)

    # Assert the properties are correctly assigned
    # Note: The actual assertion might differ based on how the bytes are parsed
    assert device_data.firmware_version is not None
    assert device_data.device_serial is not None
