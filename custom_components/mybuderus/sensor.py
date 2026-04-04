"""Sensor entities for myBuderus."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSORS, MyBuderusSensorDescription
from .coordinator import MyBuderusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up myBuderus sensor entities from config entry."""
    coordinator: MyBuderusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MyBuderusSensor(coordinator, description, entry)
        for description in SENSORS
    )


class MyBuderusSensor(CoordinatorEntity[MyBuderusCoordinator], SensorEntity):
    """A single myBuderus sensor entity backed by the coordinator."""

    entity_description: MyBuderusSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyBuderusCoordinator,
        description: MyBuderusSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.gateway_id)},
            name=entry.title,
            manufacturer="Bosch",
            model="myBuderus",
        )

    @property
    def native_value(self):
        """Return the current sensor value from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.resource_path)
