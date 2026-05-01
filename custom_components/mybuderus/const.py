"""Constants for myBuderus integration."""
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

DOMAIN = "mybuderus"

# OAuth2 / SingleKey ID
CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
AUTHORIZATION_ENDPOINT = "https://singlekey-id.com/auth/connect/authorize"
TOKEN_ENDPOINT = "https://singlekey-id.com/auth/connect/token"
REDIRECT_URI = "com.buderus.tt.dashtt://app/login"
SCOPES = (
    "openid email profile offline_access "
    "pointt.gateway.list pointt.gateway.resource.dashapp "
    "pointt.castt.flow.token-exchange bacon hcc.tariff.read"
)

# REST API
BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/"

# Config / Options
DEFAULT_SCAN_INTERVAL = 300  # seconds
MIN_SCAN_INTERVAL = 30
OUTAGE_REPAIR_THRESHOLD = 3600  # seconds of consecutive failure before repair issue fires
CONF_SCAN_INTERVAL = "scan_interval"


@dataclass(frozen=True, kw_only=True)
class MyBuderusSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the API resource path."""

    resource_path: str = ""


SENSORS: tuple[MyBuderusSensorDescription, ...] = (
    MyBuderusSensorDescription(
        key="hc_operation_mode",
        name="Heizkreis Betriebsart",
        resource_path="/heatingCircuits/hc1/operationMode",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="hc_room_setpoint",
        name="Heizkreis Solltemperatur",
        resource_path="/heatingCircuits/hc1/currentRoomSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="hc_room_temperature",
        name="Heizkreis Raumtemperatur",
        resource_path="/heatingCircuits/hc1/roomtemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_operation_mode",
        name="WW Betriebsart",
        resource_path="/dhwCircuits/dhw1/operationMode",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="dhw_actual_temp",
        name="WW Speichertemperatur",
        resource_path="/dhwCircuits/dhw1/actualTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_current_setpoint",
        name="WW Aktiver Sollwert",
        resource_path="/dhwCircuits/dhw1/currentSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_setpoint_high",
        name="WW Sollwert high",
        resource_path="/dhwCircuits/dhw1/temperatureLevels/high",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_setpoint_low",
        name="WW Sollwert low",
        resource_path="/dhwCircuits/dhw1/temperatureLevels/low",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="outdoor_temperature",
        name="Außentemperatur",
        resource_path="/system/sensors/temperatures/outdoor_t1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="compressor_status",
        name="Kompressorstatus",
        resource_path="/heatSources/compressor/status",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="supply_temperature",
        name="Vorlauftemperatur",
        resource_path="/heatSources/actualSupplyTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="return_temperature",
        name="Rücklauftemperatur",
        resource_path="/heatSources/returnTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="backup_heater_status",
        name="Zuheizerstatus",
        resource_path="/heatSources/Source/eHeater/status",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="system_mode",
        name="Systemmodus",
        resource_path="/system/seasonOptimizer/mode",
        device_class=SensorDeviceClass.ENUM,
    ),
)
