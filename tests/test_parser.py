from livigy_ups_bridge.parser import parse_f, parse_i, parse_q1


def test_parse_q1():
    status = parse_q1("(219.7 219.7 219.7 000 50.0 27.3 30.0 01010101")
    assert status.input_voltage == 219.7
    assert status.load_percent == 0
    assert status.utility_fail is False
    assert status.battery_low is True
    assert status.avr_active is False
    assert status.ups_failed is True
    assert status.standby_type is False
    assert status.test_in_progress is True
    assert status.shutdown_active is False
    assert status.beeper_on is True


def test_parse_i():
    data = parse_i("#LIVIGY PSH-1500 FW1.03")
    assert data["company"] == "LIVIGY"
    assert data["model"] == "PSH-1500"
    assert data["firmware"] == "FW1.03"


def test_parse_f():
    data = parse_f("(220.0 5.0 24.0 50.0")
    assert data["rated_voltage"] == 220.0
    assert data["rated_current"] == 5.0
    assert data["rated_battery_voltage"] == 24.0
    assert data["rated_frequency_hz"] == 50.0
