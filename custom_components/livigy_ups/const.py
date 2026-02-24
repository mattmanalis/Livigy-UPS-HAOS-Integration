"""Constants for Livigy UPS integration."""

DOMAIN = "livigy_ups"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TIMEOUT = "timeout"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 2001
DEFAULT_TIMEOUT = 5.0
DEFAULT_SCAN_INTERVAL = 15

SERVICE_SEND_COMMAND = "send_command"
SERVICE_TOGGLE_BEEPER = "toggle_beeper"
SERVICE_START_BATTERY_TEST = "start_battery_test"
SERVICE_CANCEL_BATTERY_TEST = "cancel_battery_test"
SERVICE_SHUTDOWN = "shutdown"
SERVICE_CANCEL_SHUTDOWN = "cancel_shutdown"

SENSOR_DESCRIPTIONS = {
    "input_voltage": {"name": "Input Voltage", "native_unit": "V", "device_class": "voltage"},
    "fault_voltage": {"name": "Fault Voltage", "native_unit": "V", "device_class": "voltage"},
    "output_voltage": {"name": "Output Voltage", "native_unit": "V", "device_class": "voltage"},
    "load_percent": {"name": "UPS Load", "native_unit": "%"},
    "estimated_load_watts": {"name": "Estimated Load Watts", "native_unit": "W", "device_class": "power"},
    "input_frequency_hz": {"name": "Input Frequency", "native_unit": "Hz", "device_class": "frequency"},
    "battery_voltage": {"name": "Battery Voltage", "native_unit": "V", "device_class": "voltage"},
    "temperature_c": {"name": "UPS Temperature", "native_unit": "°C", "device_class": "temperature"},
    "company": {"name": "UPS Company"},
    "model": {"name": "UPS Model"},
    "firmware": {"name": "UPS Firmware"},
    "rated_voltage": {"name": "Rated Voltage", "native_unit": "V", "device_class": "voltage"},
    "rated_current": {"name": "Rated Current", "native_unit": "A", "device_class": "current"},
    "rated_battery_voltage": {"name": "Rated Battery Voltage", "native_unit": "V", "device_class": "voltage"},
    "rated_frequency_hz": {"name": "Rated Frequency", "native_unit": "Hz", "device_class": "frequency"},
}

BINARY_SENSOR_DESCRIPTIONS = {
    "utility_fail": "Utility Fail",
    "battery_low": "Battery Low",
    "avr_active": "AVR Active",
    "ups_failed": "UPS Failed",
    "standby_type": "Standby Type",
    "test_in_progress": "Test In Progress",
    "shutdown_active": "Shutdown Active",
    "beeper_on": "Beeper On",
}
