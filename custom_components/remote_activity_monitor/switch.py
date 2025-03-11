"""Remote activity monitor switch platform."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_COMPONENT_TYPE,
    DOMAIN,
    MAIN_DOMAIN_NAME,
    POSTFIX_PAUSE_SWITCH_ENTITY,
    REMOTE_DOMAIN_NAME,
    SW_VERSION,
    TRANSLATION_KEY_MAIN_DEVICE,
    TRANSLATION_KEY_REMOTE_DEVICE,
    ComponentType,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Remote activity monitor pause switch platform."""

    match entry.options[CONF_COMPONENT_TYPE]:
        case ComponentType.MAIN:
            async_add_entities([MainPauseSwitch(hass, entry)])
        case ComponentType.REMOTE:
            async_add_entities([RemotePauseSwitch(hass, entry)])


# ------------------------------------------------------
# ------------------------------------------------------
class RemotePauseSwitch(SwitchEntity):
    """Implement the Remote activity monitor switch entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Remote activity monitor switch entity."""

        self.hass: HomeAssistant = hass
        self.entry: ConfigEntry = entry

        self.pause: bool = False

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="KGN",
            suggested_area="",
            sw_version=SW_VERSION,
            name=REMOTE_DOMAIN_NAME,
            translation_key=TRANSLATION_KEY_REMOTE_DEVICE,
        )

    @property
    # ------------------------------------------------------
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self.pause

    # ------------------------------------------------------
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.pause = True
        self.async_write_ha_state()

    # ------------------------------------------------------
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.pause = False
        self.async_write_ha_state()

    # ------------------------------------------------------
    @property
    def name(self) -> str:
        """Name.

        Returns:
            str: Name of sensor

        """
        return self.entry.title + " Pause"

    # ------------------------------------------------------
    @property
    def unique_id(self) -> str:
        """Unique id.

        Returns:
            str: Unique id

        """

        return self.entry.entry_id + POSTFIX_PAUSE_SWITCH_ENTITY


# ------------------------------------------------------
# ------------------------------------------------------
class MainPauseSwitch(SwitchEntity):
    """Implement the Main activity monitor switch entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Main activity monitor switch entity."""

        self.hass: HomeAssistant = hass
        self.entry: ConfigEntry = entry

        self.pause: bool = False

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="KGN",
            suggested_area="",
            sw_version=SW_VERSION,
            name=MAIN_DOMAIN_NAME,
            translation_key=TRANSLATION_KEY_MAIN_DEVICE,
        )

    @property
    # ------------------------------------------------------
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self.pause

    # ------------------------------------------------------
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.pause = True
        self.async_write_ha_state()

    # ------------------------------------------------------
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.pause = False
        self.async_write_ha_state()

    # ------------------------------------------------------
    @property
    def name(self) -> str:
        """Name.

        Returns:
            str: Name of sensor

        """
        return self.entry.title + POSTFIX_PAUSE_SWITCH_ENTITY

    # ------------------------------------------------------
    @property
    def unique_id(self) -> str:
        """Unique id.

        Returns:
            str: Unique id

        """

        return self.entry.entry_id + POSTFIX_PAUSE_SWITCH_ENTITY
