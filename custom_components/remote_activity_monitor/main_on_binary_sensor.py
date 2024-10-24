"""Support for Remote Activity Monitor."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    LOGGER,
    POSTFIX_MAIN_ON_ENTITY,
    SERVICE_MAIN_ON_SWITCH,
    TRANSLATION_KEY,
)
from .entity import ComponentEntityRemote


# ------------------------------------------------------
# ------------------------------------------------------
class RemoteAcitvityMonitorMainOnBinarySensor(
    ComponentEntityRemote, BinarySensorEntity
):
    """Binary sensor class for Remote activity monitor."""

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Binary sensor indicating if the host is on."""
        self.entry: ConfigEntry = entry
        self.hass = hass

        self.coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
            self.hass,
            LOGGER,
            name=DOMAIN,
            update_method=self.async_refresh,
        )

        super().__init__(self.coordinator, entry)

        self.translation_key = TRANSLATION_KEY

        self.main_on: bool = False

        self.platform: EntityPlatform = entity_platform.async_get_current_platform()

        self.platform.async_register_entity_service(
            SERVICE_MAIN_ON_SWITCH,
            {
                vol.Required(SERVICE_MAIN_ON_SWITCH): bool,
            },
            self.async_host_on_entity_dispatcher,
        )

    # ------------------------------------------------------------------
    async def async_host_on_entity_dispatcher(
        self, entity: RemoteAcitvityMonitorMainOnBinarySensor, service_data: ServiceCall
    ) -> None:
        """Host on entity."""

        await entity.async_host_on_entity(service_data)

    # ------------------------------------------------------------------
    async def async_host_on_entity(self, service_data: ServiceCall) -> None:
        """Host on entity."""
        self.main_on = service_data.data.get(SERVICE_MAIN_ON_SWITCH, False)
        self.async_write_ha_state()

    # ------------------------------------------------------
    async def async_refresh(self) -> None:
        """Refresh dummy."""

    # ------------------------------------------------------
    @property
    def name(self) -> str:
        """Name.

        Returns:
            str: Name of sensor

        """
        return self.entry.title + POSTFIX_MAIN_ON_ENTITY

    # ------------------------------------------------------
    @property
    def unique_id(self) -> str:
        """Unique id.

        Returns:
            str: Unique id

        """

        return self.entry.entry_id + POSTFIX_MAIN_ON_ENTITY

    # ------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Get the state."""

        return self.main_on

    # ------------------------------------------------------
    @property
    def extra_state_attributes(self) -> dict:
        """Extra state attributes.

        Returns:
            dict: _description_

        """

        return {}

    # ------------------------------------------------------
    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    # ------------------------------------------------------
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
