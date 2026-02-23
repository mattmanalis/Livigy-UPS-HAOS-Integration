"""Megatec parser helpers."""

from __future__ import annotations


def _strip_wrapping(raw: str) -> str:
    payload = raw.strip()
    if payload.startswith("("):
        payload = payload[1:]
    if payload.endswith("\r"):
        payload = payload[:-1]
    return payload.strip()


def parse_q1(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 8:
        raise ValueError(f"Invalid Q1 response: {raw!r}")

    bits = parts[7]
    if len(bits) != 8 or any(bit not in "01" for bit in bits):
        raise ValueError(f"Invalid Q1 bitfield: {bits!r}")

    return {
        "input_voltage": float(parts[0]),
        "fault_voltage": float(parts[1]),
        "output_voltage": float(parts[2]),
        "load_percent": int(float(parts[3])),
        "input_frequency_hz": float(parts[4]),
        "battery_voltage": float(parts[5]),
        "temperature_c": float(parts[6]),
        "utility_fail": bits[0] == "1",
        "battery_low": bits[1] == "1",
        "avr_active": bits[2] == "1",
        "ups_failed": bits[3] == "1",
        "standby_type": bits[4] == "1",
        "test_in_progress": bits[5] == "1",
        "shutdown_active": bits[6] == "1",
        "beeper_on": bits[7] == "1",
    }


def parse_i(raw: str) -> dict[str, object]:
    payload = raw.strip().lstrip("#").strip()
    parts = payload.split()
    if len(parts) < 3:
        return {"company": "", "model": payload, "firmware": ""}
    return {
        "company": parts[0],
        "model": parts[1],
        "firmware": " ".join(parts[2:]),
    }


def parse_f(raw: str) -> dict[str, object]:
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 4:
        raise ValueError(f"Invalid F response: {raw!r}")
    return {
        "rated_voltage": float(parts[0]),
        "rated_current": float(parts[1]),
        "rated_battery_voltage": float(parts[2]),
        "rated_frequency_hz": float(parts[3]),
    }
