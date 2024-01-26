from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import OperationMode, StatusFlags
from eq3btsmart.models import Status
from eq3btsmart.structures import StatusStruct


def test_status_from_device():
    # Create a mock StatusStruct
    mock_struct = StatusStruct(
        valve=50,
        target_temp=Eq3Temperature(21),  # Example temperature
        mode=StatusFlags.MANUAL,
        # ... other properties
    )

    # Use the class method to create a Status instance
    status = Status.from_device(mock_struct)

    # Assert the properties are correctly assigned
    assert status.valve == 50
    assert status.target_temperature is not None
    assert status.target_temperature.value == 21
    # ... other assertions


def test_status_from_bytes():
    # Mock bytes data representing StatusStruct
    mock_struct = StatusStruct(
        valve=50,
        target_temp=Eq3Temperature(21),  # Example temperature
        mode=StatusFlags.MANUAL,
        # ... other properties
    )
    mock_bytes = mock_struct.to_bytes()

    # Use the class method to create a Status instance
    status = Status.from_bytes(mock_bytes)

    # Assert the properties are correctly assigned
    # Note: The actual assertion might differ based on how the bytes are parsed
    assert status.valve is not None
    assert status.target_temperature is not None
    # ... other assertions


def test_operation_mode_property():
    status = Status(target_temperature=Eq3Temperature(4.5))
    assert status.operation_mode == OperationMode.OFF

    status = Status(target_temperature=Eq3Temperature(30))
    assert status.operation_mode == OperationMode.ON

    status = Status(target_temperature=None, _operation_mode=OperationMode.AUTO)
    assert status.operation_mode == OperationMode.AUTO

    status = Status(
        target_temperature=Eq3Temperature(23), _operation_mode=OperationMode.MANUAL
    )
    assert status.operation_mode == OperationMode.MANUAL

    # ... other cases
