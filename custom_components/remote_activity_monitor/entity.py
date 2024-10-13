"""Base entity for the remote/main activity monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    MAIN_DOMAIN_NAME,
    REMOTE_DOMAIN_NAME,
    SW_VERSION,
    TRANSLATION_KEY_MAIN_DEVICE,
    TRANSLATION_KEY_REMOTE_DEVICE,
)


class ComponentEntityRemote(CoordinatorEntity[DataUpdateCoordinator], Entity):
    """Defines the remote activity monitor entity."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the remote activity monitor entity."""
        super().__init__(coordinator=coordinator)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, REMOTE_DOMAIN_NAME)},
            manufacturer="KGN",
            suggested_area="",
            sw_version=SW_VERSION,
            name=REMOTE_DOMAIN_NAME,
            translation_key=TRANSLATION_KEY_REMOTE_DEVICE,
        )


class ComponentEntityMain(CoordinatorEntity[DataUpdateCoordinator], Entity):
    """Defines the main activity monitor entity."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the main activity monitor entity."""
        super().__init__(coordinator=coordinator)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, MAIN_DOMAIN_NAME)},
            manufacturer="KGN",
            suggested_area="",
            sw_version=SW_VERSION,
            name=MAIN_DOMAIN_NAME,
            translation_key=TRANSLATION_KEY_MAIN_DEVICE,
        )
