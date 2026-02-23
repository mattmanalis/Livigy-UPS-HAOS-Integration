from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Q1Status:
    input_voltage: float
    fault_voltage: float
    output_voltage: float
    load_percent: int
    input_frequency_hz: float
    battery_voltage: float
    temperature_c: float
    utility_fail: bool
    battery_low: bool
    avr_active: bool
    ups_failed: bool
    standby_type: bool
    test_in_progress: bool
    shutdown_active: bool
    beeper_on: bool


def _strip_wrapping(raw: str) -> str:
    s = raw.strip()
    if s.startswith("("):
        s = s[1:]
    if s.endswith("\r"):
        s = s[:-1]
    return s.strip()


def parse_q1(raw: str) -> Q1Status:
    # Typical format:
    # (219.7 219.7 219.7 000 50.0 27.3 30.0 00000000
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 8:
        raise ValueError(f"Invalid Q1 response (expected >=8 fields): {raw!r}")

    bitfield = parts[7]
    if len(bitfield) != 8 or any(ch not in "01" for ch in bitfield):
        raise ValueError(f"Invalid Q1 bitfield: {bitfield!r}")

    return Q1Status(
        input_voltage=float(parts[0]),
        fault_voltage=float(parts[1]),
        output_voltage=float(parts[2]),
        load_percent=int(float(parts[3])),
        input_frequency_hz=float(parts[4]),
        battery_voltage=float(parts[5]),
        temperature_c=float(parts[6]),
        utility_fail=bitfield[0] == "1",
        battery_low=bitfield[1] == "1",
        avr_active=bitfield[2] == "1",
        ups_failed=bitfield[3] == "1",
        standby_type=bitfield[4] == "1",
        test_in_progress=bitfield[5] == "1",
        shutdown_active=bitfield[6] == "1",
        beeper_on=bitfield[7] == "1",
    )


def parse_i(raw: str) -> dict[str, str]:
    # Common format:
    # #<company> <model> <version>
    payload = raw.strip().lstrip("#").strip()
    parts = payload.split()
    if len(parts) < 3:
        return {"company": "", "model": payload, "firmware": ""}
    return {
        "company": parts[0],
        "model": parts[1],
        "firmware": " ".join(parts[2:]),
    }


def parse_f(raw: str) -> dict[str, float]:
    # Common format values: rated V, rated current, rated battery V, rated Hz
    payload = _strip_wrapping(raw)
    parts = payload.split()
    if len(parts) < 4:
        raise ValueError(f"Invalid F response (expected >=4 fields): {raw!r}")
    return {
        "rated_voltage": float(parts[0]),
        "rated_current": float(parts[1]),
        "rated_battery_voltage": float(parts[2]),
        "rated_frequency_hz": float(parts[3]),
    }
