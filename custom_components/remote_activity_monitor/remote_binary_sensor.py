"""Support for Remote Activity Monitor."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, STATE_OFF, STATE_ON
from homeassistant.core import (
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    State,
    SupportsResponse,
    callback,
)
from homeassistant.helpers import entity_registry as er, issue_registry as ir, start
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_MONITOR_ACTIVITY_ENTITY_ID,
    ATTR_MONITOR_ACTIVITY_FRIENDLY_NAME,
    ATTR_MONITOR_ACTIVITY_LAST_UPDATED,
    CONF_ALL_ENTITIES_ON,
    CONF_ENTITY_IDS,
    DOMAIN,
    DOMAIN_NAME,
    LOGGER,
    SERVICE_GET_REMOTE_ENTITIES,
    TRANSLATION_KEY,
    TRANSLATION_KEY_REMOTE_MISSING_ENTITY,
)
from .entity import ComponentEntityRemote


# ------------------------------------------------------
# ------------------------------------------------------
class RemoteAcitvityMonitorBinarySensor(ComponentEntityRemote, BinarySensorEntity):
    """Binary sensor class for Remote activity monitor."""

    class_entity_list: list[RemoteAcitvityMonitorBinarySensor] = []

    _unrecorded_attributes = frozenset({MATCH_ALL})

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Binary sensor."""

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

        self.remote_state: bool = False
        self.remote_friendly_name: str = ""
        self.remote_entity_id: str = ""
        self.remote_last_updated: datetime = dt_util.now()

        registry = er.async_get(hass)
        self.monitor_activity_entities: list[str] = er.async_validate_entity_ids(
            registry, entry.options[CONF_ENTITY_IDS]
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_GET_REMOTE_ENTITIES,
            self.async_get_remote_entities,
            supports_response=SupportsResponse.ONLY,
        )

    # ------------------------------------------------------------------
    async def async_get_remote_entities(self, call: ServiceCall) -> ServiceResponse:
        """Get active remote entities."""

        remotes: list[dict[str, str]] = []

        for item in RemoteAcitvityMonitorBinarySensor.class_entity_list:
            state: State | None = self.hass.states.get(item.entity_id)

            if state:
                remotes.append(
                    {
                        "name": item.name,
                        "entity_id": item.entity_id,
                        "state": state.state,
                        "last_updated": state.last_updated.isoformat(),
                        "hass_uuid": await async_get_instance_id(self.hass),
                    }
                )

        return {"remotes": remotes}

    # ------------------------------------------------------
    async def async_will_remove_from_hass(self) -> None:
        """When removed from hass."""

        RemoteAcitvityMonitorBinarySensor.class_entity_list.remove(self)

    # ------------------------------------------------------
    @callback
    async def sensor_state_listener(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state changes on the observed device."""

        if event.data["new_state"] is None:
            return

        await self.check_entities_state()

        await self.coordinator.async_refresh()

    # ------------------------------------------------------
    async def check_entities_state(self) -> None:
        """Check entities state."""

        last_updated_timestamp: float = 0.0
        last_updated: datetime = dt_util.now()
        entity_name: str = ""
        entity_id: str = ""

        self.remote_state = self.entry.options.get(CONF_ALL_ENTITIES_ON, False) is True

        for entity in self.monitor_activity_entities:
            state: State | None = self.hass.states.get(entity)

            if state is not None:
                if state.last_updated_timestamp > last_updated_timestamp:
                    last_updated_timestamp = state.last_updated_timestamp
                    last_updated = state.last_updated
                    entity_name = state.name
                    entity_id = state.entity_id

                if (
                    self.entry.options.get(CONF_ALL_ENTITIES_ON, False) is True
                    and state.state == STATE_OFF
                ):
                    self.remote_state = False
                elif (
                    self.entry.options.get(CONF_ALL_ENTITIES_ON, False) is False
                    and state.state == STATE_ON
                ):
                    self.remote_state = True

        if last_updated_timestamp > 0.0:
            self.remote_last_updated = last_updated
            self.remote_friendly_name = entity_name
            self.remote_entity_id = entity_id

    # ------------------------------------------------------
    async def hass_started(self, _event: Event) -> None:
        """Hass started."""

        await self.check_entities_state()

        if await self.async_verify_entity_exist():
            pass

    # ------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Complete device setup after being added to hass."""

        await self.coordinator.async_config_entry_first_refresh()

        RemoteAcitvityMonitorBinarySensor.class_entity_list.append(self)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self.monitor_activity_entities,
                self.sensor_state_listener,
            )
        )

        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

        self.async_on_remove(start.async_at_started(self.hass, self.hass_started))

    # ------------------------------------------------------
    async def async_verify_entity_exist(
        self,
    ) -> bool:
        """Verify entity exist."""

        for entity in self.monitor_activity_entities:
            state: State | None = self.hass.states.get(entity)

            if state is None:
                await self.async_create_issue_entity(
                    entity,
                    TRANSLATION_KEY_REMOTE_MISSING_ENTITY,
                )
                self.coordinator.update_interval = None
                return False

        return True

    # ------------------------------------------------------
    async def async_refresh(self) -> None:
        """Refresh dummy."""

    # ------------------------------------------------------------------
    async def async_create_issue_entity(
        self, entity_id: str, translation_key: str
    ) -> None:
        """Create issue on entity."""

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            DOMAIN_NAME + datetime.now().isoformat(),
            issue_domain=DOMAIN,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={
                "entity": entity_id,
                "integration": self.entity_id,
            },
        )

    # ------------------------------------------------------
    @property
    def name(self) -> str:
        """Name.

        Returns:
            str: Name of sensor

        """
        return self.entry.title

    # ------------------------------------------------------
    @property
    def unique_id(self) -> str:
        """Unique id.

        Returns:
            str: Unique id

        """

        return (
            self.entry.unique_id
            if self.entry.unique_id is not None
            else self.entry.entry_id
        )

    # ------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Get the state."""

        return self.remote_state

    # ------------------------------------------------------
    @property
    def extra_state_attributes(self) -> dict:
        """Extra state attributes.

        Returns:
            dict: _description_

        """

        return {
            ATTR_MONITOR_ACTIVITY_FRIENDLY_NAME: self.remote_friendly_name,
            ATTR_MONITOR_ACTIVITY_ENTITY_ID: self.remote_entity_id,
            ATTR_MONITOR_ACTIVITY_LAST_UPDATED: self.remote_last_updated.isoformat(),
        }

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

    # ------------------------------------------------------
    async def async_update(self) -> None:
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()
