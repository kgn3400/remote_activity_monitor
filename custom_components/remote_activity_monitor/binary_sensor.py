"""Support for Remote Activity Monitor."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CommonConfigEntry
from .const import CONF_COMPONENT_TYPE, ComponentType
from .main_binary_sensor import MainAcitvityMonitorBinarySensor
from .main_on_binary_sensor import RemoteAcitvityMonitorMainOnBinarySensor
from .remote_binary_sensor import RemoteAcitvityMonitorBinarySensor


# ------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: CommonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Entry for Remote activity monitor setup."""

    match entry.options[CONF_COMPONENT_TYPE]:
        case ComponentType.MAIN:
            async_add_entities([MainAcitvityMonitorBinarySensor(hass, entry)])
        case ComponentType.REMOTE:
            async_add_entities(
                [
                    RemoteAcitvityMonitorBinarySensor(hass, entry),
                    RemoteAcitvityMonitorMainOnBinarySensor(hass, entry),
                ]
            )
