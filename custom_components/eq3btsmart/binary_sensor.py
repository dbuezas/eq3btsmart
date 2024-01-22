"""Platform for eQ-3 binary sensor entities."""


from custom_components.eq3btsmart.eq3_entity import Eq3Entity
from custom_components.eq3btsmart.models import Eq3Config, Eq3ConfigEntry
from eq3btsmart import Thermostat
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_NAME_BATTERY,
    ENTITY_NAME_BUSY,
    ENTITY_NAME_CONNECTED,
    ENTITY_NAME_DST,
    ENTITY_NAME_MONITORING,
    ENTITY_NAME_WINDOW_OPEN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Called when an entry is setup."""

    eq3_config_entry: Eq3ConfigEntry = hass.data[DOMAIN][config_entry.entry_id]
    thermostat = eq3_config_entry.thermostat
    eq3_config = eq3_config_entry.eq3_config

    entities_to_add: list[Entity] = [
        BatterySensor(eq3_config, thermostat),
        WindowOpenSensor(eq3_config, thermostat),
        DSTSensor(eq3_config, thermostat),
    ]

    if eq3_config.debug_mode:
        entities_to_add += [
            BusySensor(eq3_config, thermostat),
            ConnectedSensor(eq3_config, thermostat),
            MonitoringSensor(eq3_config, thermostat),
        ]

    async_add_entities(entities_to_add)


class Base(Eq3Entity, BinarySensorEntity):
    """Base class for all eQ-3 binary sensors."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._attr_has_entity_name = True

    @property
    def unique_id(self) -> str | None:
        if self.name is None or isinstance(self.name, UndefinedType):
            return None

        return format_mac(self._eq3_config.mac_address) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._eq3_config.mac_address)},
        )


class BusySensor(Base):
    """Binary sensor that reports if the thermostat connection is busy."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = ENTITY_NAME_BUSY

    @property
    def is_on(self) -> bool:
        return self._thermostat._lock.locked()


class ConnectedSensor(Base):
    """Binary sensor that reports if the thermostat is connected."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = ENTITY_NAME_CONNECTED
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    # @property
    # def extra_state_attributes(self) -> dict[str, str] | None:
    #     if (device := self._thermostat._conn._device) is None:
    #         return None
    #     if (details := device.details) is None:
    #         return None
    #     if "props" not in details:
    #         return None

    #     return json.loads(json.dumps(details["props"], default=lambda obj: None))

    @property
    def is_on(self) -> bool:
        return self._thermostat._conn.is_connected


class MonitoringSensor(Base):
    """Binary sensor that reports if the thermostat connection monitor is running."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = ENTITY_NAME_MONITORING
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    # @property
    # def extra_state_attributes(self) -> dict[str, str] | None:
    #     if (device := self._thermostat._conn._device) is None:
    #         return None
    #     if (details := device.details) is None:
    #         return None
    #     if "props" not in details:
    #         return None

    #     return json.loads(json.dumps(details["props"], default=lambda obj: None))

    @property
    def is_on(self) -> bool:
        return self._thermostat._monitor._run


class BatterySensor(Base):
    """Binary sensor that reports if the thermostat battery is low."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_BATTERY
        self._attr_device_class = BinarySensorDeviceClass.BATTERY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.status.is_low_battery


class WindowOpenSensor(Base):
    """Binary sensor that reports if the thermostat thinks a window is open."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_WINDOW_OPEN
        self._attr_device_class = BinarySensorDeviceClass.WINDOW

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.status.is_window_open


class DSTSensor(Base):
    """Binary sensor that reports if the thermostat is in daylight savings time mode."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_DST
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.status.is_dst
