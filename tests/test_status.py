from eq3btsmart.models import Status


def test_status():
    received = bytes([0x02, 0x01, 0x09, 0x11, 0x04, 0x2A])
    Status.from_bytes(received)
