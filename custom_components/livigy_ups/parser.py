"""Megatec and PowerShield parser helpers."""

from __future__ import annotations


def _strip_wrapping(raw: str) -> str:
    payload = raw.strip()
    if payload.startswith("("):
        payload = payload[1:]
    if payload.endswith("\r"):
        payload = payload[:-1]
    return payload.strip()


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _normalize_numeric_token(token: str) -> str:
    token = token.strip()
    while token.startswith("#"):
        token = token[1:]
    return token


def _parse_float(token: str) -> float:
    return float(_normalize_numeric_token(token))


def _parse_int(token: str) -> int:
    return int(float(_normalize_numeric_token(token)))


def parse_q1(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 8:
        raise ValueError(f"Invalid Q1 response: {raw!r}")

    bits = parts[7]
    if len(bits) != 8 or any(bit not in "01" for bit in bits):
        raise ValueError(f"Invalid Q1 bitfield: {bits!r}")

    return {
        "input_voltage": _parse_float(parts[0]),
        "fault_voltage": _parse_float(parts[1]),
        "output_voltage": _parse_float(parts[2]),
        "load_percent": _parse_int(parts[3]),
        "input_frequency_hz": _parse_float(parts[4]),
        "battery_voltage": _parse_float(parts[5]),
        "temperature_c": _parse_float(parts[6]),
        "utility_fail": bits[0] == "1",
        "battery_low": bits[1] == "1",
        "avr_active": bits[2] == "1",
        "ups_failed": bits[3] == "1",
        "standby_type": bits[4] == "1",
        "test_in_progress": bits[5] == "1",
        "shutdown_active": bits[6] == "1",
        "beeper_on": bits[7] == "1",
        "protocol_family": "megatec",
    }


def parse_qgs(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 12:
        raise ValueError(f"Invalid QGS response: {raw!r}")

    bits = parts[11]
    if len(bits) != 12 or any(bit not in "01" for bit in bits):
        raise ValueError(f"Invalid QGS bitfield: {bits!r}")

    b9, b8 = bits[0], bits[1]
    b7, b6, b5, b4, b3, b2, b1, b0 = bits[2:10]
    a0, a1 = bits[10], bits[11]

    return {
        "input_voltage": _parse_float(parts[0]),
        "input_frequency_hz": _parse_float(parts[1]),
        "output_voltage": _parse_float(parts[2]),
        "output_frequency_hz": _parse_float(parts[3]),
        "output_current_a": _parse_float(parts[4]),
        "load_percent": _parse_int(parts[5]),
        "positive_bus_voltage": _parse_float(parts[6]),
        "negative_bus_voltage": _parse_float(parts[7]),
        "battery_voltage": _parse_float(parts[8]),
        "negative_battery_voltage": _parse_float(parts[9]),
        "temperature_c": _parse_float(parts[10]),
        "utility_fail": b7 == "1",
        "battery_low": b6 == "1",
        "avr_active": b5 == "1",
        "ups_failed": b4 == "1",
        "epo_active": b3 == "1",
        "test_in_progress": b2 == "1",
        "shutdown_active": b1 == "1",
        "battery_silence": b0 == "1",
        "beeper_on": b0 == "0",
        "battery_test_fail": a0 == "1",
        "battery_test_ok": a1 == "1",
        "standby_type": b9 == "0" and b8 == "0",
        "ups_topology": {"00": "standby", "01": "line_interactive", "10": "online"}.get(
            f"{b9}{b8}", "unknown"
        ),
        "protocol_family": "centurion",
    }


def parse_qmd(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 8:
        raise ValueError(f"Invalid QMD response: {raw!r}")

    model = parts[0].replace("#", "")
    rated_watt_str = parts[1].replace("#", "")
    rated_watts: int | None
    try:
        rated_watts = int(rated_watt_str) if rated_watt_str else None
    except ValueError:
        rated_watts = None

    power_factor_percent: int | None
    try:
        power_factor_percent = int(parts[2])
    except ValueError:
        power_factor_percent = None

    return {
        "company": "PowerShield",
        "model": model,
        "rated_watts": rated_watts,
        "output_power_factor_percent": power_factor_percent,
    }


def parse_qmod(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    code = payload[:1]
    mode_map = {
        "P": "power_on",
        "S": "standby",
        "Y": "bypass",
        "L": "line",
        "B": "battery",
        "T": "battery_test",
        "F": "fault",
        "E": "eco",
        "C": "converter",
        "D": "shutdown",
    }
    if code not in mode_map:
        raise ValueError(f"Invalid QMOD response: {raw!r}")
    return {"ups_mode": mode_map[code], "ups_mode_code": code}


def parse_qri(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 4:
        raise ValueError(f"Invalid QRI response: {raw!r}")
    return {
        "rated_voltage": _parse_float(parts[0]),
        "rated_current": _parse_float(parts[1]),
        "rated_battery_voltage": _parse_float(parts[2]),
        "rated_frequency_hz": _parse_float(parts[3]),
    }


def parse_qvfw(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    if not payload.startswith("VERFW:"):
        raise ValueError(f"Invalid QVFW response: {raw!r}")
    return {"firmware": payload.split(":", 1)[1].strip()}


def parse_i(raw: str) -> dict[str, object]:
    raw_payload = raw.strip()
    if raw_payload.startswith("("):
        raise ValueError(f"Invalid I response: {raw!r}")

    payload = raw_payload.lstrip("#").strip()
    parts = payload.split()
    if not parts:
        raise ValueError(f"Invalid I response: {raw!r}")
    if _is_number(parts[0]):
        raise ValueError(f"Invalid I response: {raw!r}")
    if len(parts) < 3:
        return {"company": "", "model": payload, "firmware": ""}
    return {
        "company": parts[0],
        "model": parts[1],
        "firmware": " ".join(parts[2:]),
    }


def parse_f(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw).lstrip("#").strip()
    parts = payload.split()
    if len(parts) < 4:
        raise ValueError(f"Invalid F response: {raw!r}")
    return {
        "rated_voltage": _parse_float(parts[0]),
        "rated_current": _parse_float(parts[1]),
        "rated_battery_voltage": _parse_float(parts[2]),
        "rated_frequency_hz": _parse_float(parts[3]),
    }
