"""Tests for const.py."""
from custom_components.mybuderus.const import DOMAIN, SENSORS, MyBuderusSensorDescription


def test_domain():
    assert DOMAIN == "mybuderus"


def test_sensors_count():
    assert len(SENSORS) == 14


def test_all_sensors_have_resource_path():
    for s in SENSORS:
        assert s.resource_path.startswith("/"), f"{s.key} hat keinen absoluten Pfad"


def test_sensor_keys_unique():
    keys = [s.key for s in SENSORS]
    assert len(keys) == len(set(keys))
