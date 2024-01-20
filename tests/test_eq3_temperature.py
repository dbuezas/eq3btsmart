from eq3btsmart.eq3_temperature import Eq3Temperature


def test_value():
    value_original = 21.5
    value = Eq3Temperature(value_original)

    assert value == 43
