"""Support for Remote Activity Monitor."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_PORT,
    CONF_VERIFY_SSL,
    MATCH_ALL,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import (
    config_validation as cv,
    entity_platform,
    issue_registry as ir,
    start,
)
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import CommonConfigEntry
from .const import (
    ATTR_MAIN_MONITOR_LAST_UPDATED,
    ATTR_MAIN_MONITOR_PAUSE,
    ATTR_MAIN_MONITOR_WAIT_DURATION_LEFT,
    ATTR_MONITOR_ACTIVITY_ENTITY_ID,
    ATTR_MONITOR_ACTIVITY_FRIENDLY_NAME,
    ATTR_MONITOR_ACTIVITY_LAST_UPDATED,
    ATTR_REMOTE_ACTIVITY_ENTITY_ID,
    ATTR_REMOTE_ACTIVITY_FRIENDLY_NAME,
    ATTR_REMOTE_ACTIVITY_LAST_UPDATED,
    ATTR_REMOTE_ACTIVITY_PAUSE,
    CONF_DURATION_WAIT_UPDATE,
    CONF_MONITOR_ENTITY,
    CONF_MONITOR_STATE_CHANGED_TYPE,
    CONF_SAVE_OPTIONS,
    CONF_SECURE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    DOMAIN_NAME,
    LOGGER,
    POSTFIX_MAIN_ON_ENTITY,
    POSTFIX_PAUSE_SWITCH_ENTITY,
    SERVICE_GET_REMOTE_ENTITIES,
    SERVICE_MAIN_ON_SWITCH,
    SERVICE_UPDATE_MAIN_OPTIONS,
    STATE_BOTH,
    TRANSLATION_KEY,
    TRANSLATION_KEY_MAIN_CONNECTION_ERROR,
    TRANSLATION_KEY_MAIN_MISSING_ENTITY,
)
from .entity import ComponentEntityMain
from .rest_api import BadResponse, RestApi
from .shared import Shared
from .websocket_api import ConnectionStateType, RemoteWebsocketConnection


# ------------------------------------------------------
# ------------------------------------------------------
class MainAcitvityMonitorBinarySensor(ComponentEntityMain, BinarySensorEntity):
    """Binary sensor class for the main activity monitor."""

    _unrecorded_attributes = frozenset({MATCH_ALL})

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        entry: CommonConfigEntry,
    ) -> None:
        """Binary sensor."""
        self.entry: CommonConfigEntry = entry
        self.hass = hass

        self.translation_key = TRANSLATION_KEY

        self.remote_state_on: bool = False
        self.remote_friendly_name: str = ""
        self.remote_entity_id: str = ""
        self.remote_last_updated: datetime = dt_util.now()
        self.remote_pause: bool = False

        self.shared: Shared = entry.runtime_data.shared

        self.remote_binary_sensor_name: str = entry.options.get(CONF_MONITOR_ENTITY)
        self.main_on_binary_sensor_name: str = entry.options.get(
            CONF_MONITOR_ENTITY
        ) + POSTFIX_MAIN_ON_ENTITY.lower().replace(" ", "_")
        self.remote_switch_pause_name: str = self.remote_binary_sensor_name.replace(
            "binary_sensor", "switch"
        ) + POSTFIX_PAUSE_SWITCH_ENTITY.lower().replace(" ", "_")

        self.main_state_on: bool = False
        self.main_pause: bool = False

        self.main_last_updated: datetime = dt_util.now()

        self.duration_wait_update: timedelta = timedelta()

        if (duration := entry.options.get(CONF_DURATION_WAIT_UPDATE, None)) is not None:
            self.duration_wait_update = timedelta(**duration)

        self.monitor_state_changed_type: str = entry.options.get(
            CONF_MONITOR_STATE_CHANGED_TYPE, STATE_BOTH
        )

        self.coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
            self.hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
            update_method=self.async_refresh,
        )

        super().__init__(self.coordinator, entry)

        self.websocket_connection: RemoteWebsocketConnection = (
            RemoteWebsocketConnection(
                self.hass,
                self.entry.options.get(CONF_HOST),
                self.entry.options.get(CONF_PORT),
                self.entry.options.get(CONF_ACCESS_TOKEN),
                self.entry.options.get(CONF_SECURE),
                self.entry.options.get(CONF_VERIFY_SSL),
            )
        )

        self.platform: EntityPlatform = entity_platform.async_get_current_platform()

        self.platform.async_register_entity_service(
            SERVICE_UPDATE_MAIN_OPTIONS,
            {
                vol.Optional(CONF_DURATION_WAIT_UPDATE): cv.time_period,
                vol.Optional(CONF_MONITOR_STATE_CHANGED_TYPE): cv.string,
                vol.Required(CONF_SAVE_OPTIONS): cv.boolean,
            },
            self.async_service_update_main_options_dispatcher,
        )

    # ------------------------------------------------------------------
    async def async_service_update_main_options_dispatcher(
        self, entity: MainAcitvityMonitorBinarySensor, service_data: ServiceCall
    ) -> None:
        """Update main options."""

        await entity.async_service_update_main_options(service_data)

    # ------------------------------------------------------------------
    async def async_service_update_main_options(
        self, service_data: ServiceCall
    ) -> None:
        """Update main options."""

        def timedelta_to_dict(td: timedelta) -> dict:
            """Convert timedelta to dict."""
            hours, remainder = divmod(td.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            return {
                "days": td.days,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
            }

        self.monitor_state_changed_type: str = service_data.data.get(
            CONF_MONITOR_STATE_CHANGED_TYPE, self.monitor_state_changed_type
        )

        self.duration_wait_update = service_data.data.get(
            CONF_DURATION_WAIT_UPDATE, timedelta()
        )

        if service_data.data.get(CONF_SAVE_OPTIONS, False):
            tmp_entry_options: dict[str, Any] = self.entry.options.copy()
            tmp_entry_options[CONF_MONITOR_STATE_CHANGED_TYPE] = (
                self.monitor_state_changed_type
            )
            tmp_entry_options[CONF_DURATION_WAIT_UPDATE] = timedelta_to_dict(
                self.duration_wait_update
            )

            self.update_settings(tmp_entry_options)

        await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    def update_settings(self, entry_options: dict[str, Any]) -> None:
        """Update config."""

        self.shared.supress_update_listener = True

        self.hass.config_entries.async_update_entry(
            self.entry, data=entry_options, options=entry_options
        )

    # ------------------------------------------------------
    def map_remote_state_for_changed_type(self, remote_state: bool) -> bool:
        """Map remote state for changed type."""

        if self.monitor_state_changed_type == STATE_ON:
            return remote_state is True
        if self.monitor_state_changed_type == STATE_OFF:
            return remote_state is False

        return remote_state

    # ------------------------------------------------------
    async def check_set_state(self, is_state: bool | None = None) -> None:
        """Check and set state."""

        if self.remote_state_on is is_state or is_state is None:
            if self.duration_wait_update.total_seconds() == 0 or (
                self.duration_wait_update.total_seconds() > 0
                and dt_util.now()
                >= (self.remote_last_updated + self.duration_wait_update)
            ):
                LOGGER.debug("Setting main state")
                self.main_state_on = self.map_remote_state_for_changed_type(
                    self.remote_state_on
                )
                self.main_last_updated = dt_util.now()
                self.coordinator.update_interval = timedelta(
                    seconds=DEFAULT_UPDATE_INTERVAL
                )

                await self.async_websocket_update_main_on()
            else:  # The state is correct, but the wait duration is not yet expired
                LOGGER.debug("The state is correct, set wait duration")

                wait_duration: timedelta = (
                    self.duration_wait_update + timedelta(seconds=1)
                ) - (dt_util.now() - self.remote_last_updated)

                if wait_duration.total_seconds() > 0:
                    self.coordinator.update_interval = wait_duration
                else:  # To low, use default
                    self.coordinator.update_interval = timedelta(
                        seconds=DEFAULT_UPDATE_INTERVAL
                    )

        else:  # The state is not correct
            LOGGER.debug("The state is not correct, reset wait duration to default")
            self.coordinator.update_interval = timedelta(
                seconds=DEFAULT_UPDATE_INTERVAL
            )
            self.main_state_on = self.map_remote_state_for_changed_type(
                self.remote_state_on
            )
            self.main_last_updated = dt_util.now()
            await self.async_websocket_update_main_on()

    # ------------------------------------------------------
    async def async_refresh(self) -> None:
        """Refresh."""

        if self.main_pause or self.remote_pause:
            self.main_state_on = False
            self.async_write_ha_state()
            return

        if self.main_state_on == self.map_remote_state_for_changed_type(
            self.remote_state_on
        ):  # No need to update
            LOGGER.debug("No need to update, set wait duration to default")
            self.coordinator.update_interval = timedelta(
                seconds=DEFAULT_UPDATE_INTERVAL
            )
            return

        if self.monitor_state_changed_type == STATE_BOTH:
            await self.check_set_state()
        else:
            await self.check_set_state(self.monitor_state_changed_type == STATE_ON)

    # ------------------------------------------------------
    async def async_will_remove_from_hass(self) -> None:
        """When removed from hass."""
        await self.websocket_connection.async_stop()

    # ------------------------------------------------------
    @callback
    async def sensor_state_listener(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state changes on the observed device."""

        if event.data["new_state"] is None:
            return

        self.main_pause = event.data["new_state"].state == STATE_ON
        await self.coordinator.async_refresh()

    # ------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Complete device setup after being added to hass."""

        await self.coordinator.async_config_entry_first_refresh()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self.remote_switch_pause_name,
                self.sensor_state_listener,
            )
        )

        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

        self.async_on_remove(start.async_at_started(self.hass, self.hass_started))

    # ------------------------------------------------------
    async def hass_started(self, _event: Event) -> None:
        """Hass started."""

        if await self.async_restapi_service_get_remote_entity():
            await self.websocket_connection.async_connect(
                self.async_websocket_on_connected
            )

    # ------------------------------------------------------------------
    async def async_websocket_service_call_response(self, message: dict) -> None:
        """Handle event from host."""

    # ------------------------------------------------------------------
    async def async_websocket_update_main_on(self) -> None:
        """Update the main on switch."""

        LOGGER.debug("Updating main on switch")

        if (
            self.websocket_connection.connection_state
            != ConnectionStateType.STATE_CONNECTED
        ):
            LOGGER.debug("Not connected, not updating main on switch")
            return

        await self.websocket_connection.async_call(
            self.async_websocket_service_call_response,
            "call_service",
            domain=DOMAIN,
            service=SERVICE_MAIN_ON_SWITCH,
            service_data={
                SERVICE_MAIN_ON_SWITCH: self.main_state_on,
            },
            target={
                "entity_id": self.main_on_binary_sensor_name,
            },
        )

    # ------------------------------------------------------------------
    async def async_restapi_service_get_remote_entity(self) -> None:
        """Restapi service get remote entity."""

        MAX_RETRY_COUNT: int = 5

        # Retry loop
        for loop_count in range(MAX_RETRY_COUNT):
            remote_entyties: list = (
                await self.async_call_restapi_service_get_remote_entity()
            )

            if remote_entyties is not None:
                break

            # If this is the last retry, create an issue
            if loop_count == (MAX_RETRY_COUNT - 1):
                await self.async_create_issue_entity(
                    self.remote_binary_sensor_name,
                    TRANSLATION_KEY_MAIN_CONNECTION_ERROR,
                )

                return False

            await asyncio.sleep(10)

        for remote_entity in remote_entyties:
            if remote_entity["entity_id"] == self.remote_binary_sensor_name:
                self.remote_state_on = remote_entity["state"] == STATE_ON
                self.remote_entity_id = remote_entity["entity_id"]
                self.remote_friendly_name = remote_entity["name"]
                self.remote_last_updated = dt_util.as_local(
                    datetime.fromisoformat(remote_entity["last_updated"])
                )

                await self.coordinator.async_refresh()
                return True

        # No hit on entiy, create an issue
        await self.async_create_issue_entity(
            self.remote_binary_sensor_name,
            TRANSLATION_KEY_MAIN_MISSING_ENTITY,
        )

        return False

    # ------------------------------------------------------------------
    async def async_call_restapi_service_get_remote_entity(self) -> list | None:
        """Call restapi service get remote entity."""

        try:
            remote_entyties: list = (
                await RestApi().async_post_service(
                    self.hass,
                    self.entry.options.get(CONF_HOST),
                    self.entry.options.get(CONF_PORT),
                    self.entry.options.get(CONF_ACCESS_TOKEN),
                    self.entry.options.get(CONF_SECURE),
                    self.entry.options.get(CONF_VERIFY_SSL),
                    DOMAIN,
                    SERVICE_GET_REMOTE_ENTITIES,
                    True,
                )
            )["remotes"]

        except BadResponse:
            return None

        return remote_entyties

    # ------------------------------------------------------------------
    async def async_websocket_on_connected(self) -> None:
        """Host connection established."""

        LOGGER.debug("Host connection established, get remote entities via restapi")

        await self.async_restapi_service_get_remote_entity()

        LOGGER.debug("Host connection established, subscribing to trigger")

        await self.websocket_connection.async_call(
            self.async_websocket_handle_event_message,
            "subscribe_trigger",
            trigger={
                "platform": "state",
                "entity_id": [
                    self.remote_binary_sensor_name,
                    self.remote_switch_pause_name,
                ],
            },
        )

        await self.async_websocket_update_main_on()

    # ------------------------------------------------------------------
    async def async_websocket_handle_event_message(self, message: dict) -> None:
        """Handle event from host."""

        match message["type"]:
            case "result":
                if message["success"] is not True:
                    LOGGER.error("Error on subcribe_trigger")

            case "event":
                to_state: dict = message["event"]["variables"]["trigger"]["to_state"]

                if to_state[ATTR_ENTITY_ID] == self.remote_binary_sensor_name:
                    await self.async_websocket_handle_trigger_binary_sensor(to_state)

                if to_state[ATTR_ENTITY_ID] == self.remote_switch_pause_name:
                    await self.async_websocket_handle_trigger_switch(to_state)

    # ------------------------------------------------------------------
    async def async_websocket_handle_trigger_binary_sensor(
        self,
        to_state: dict,
    ) -> None:
        """Handle trigger binary sensor."""

        to_remote_state_on: bool = to_state["state"] == "on"

        # Wait duration is not yet expired for the last event, should we reset the state
        if (
            to_remote_state_on != self.remote_state_on
            and self.main_state_on
            != self.map_remote_state_for_changed_type(self.remote_state_on)
        ):
            self.main_state_on = self.map_remote_state_for_changed_type(
                self.remote_state_on
            )

        self.remote_state_on = to_remote_state_on
        self.remote_entity_id = to_state["attributes"][ATTR_MONITOR_ACTIVITY_ENTITY_ID]
        self.remote_friendly_name = to_state["attributes"][
            ATTR_MONITOR_ACTIVITY_FRIENDLY_NAME
        ]
        self.remote_last_updated = dt_util.as_local(
            datetime.fromisoformat(
                to_state["attributes"][ATTR_MONITOR_ACTIVITY_LAST_UPDATED]
            )
        )

        await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    async def async_websocket_handle_trigger_switch(self, to_state: dict) -> None:
        """Handle trigger binary sensor."""

        self.remote_pause: bool = to_state["state"] == "on"

        await self.coordinator.async_refresh()

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

        return self.entry.entry_id

    # ------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Get the state."""

        return self.main_state_on

    # ------------------------------------------------------
    @property
    def extra_state_attributes(self) -> dict:
        """Extra state attributes.

        Returns:
            dict: _description_

        """

        tmp_duration: timedelta = dt_util.now() - self.remote_last_updated
        tmp_duration = tmp_duration - timedelta(microseconds=tmp_duration.microseconds)

        attr: dict = {
            ATTR_REMOTE_ACTIVITY_FRIENDLY_NAME: self.remote_friendly_name,
            ATTR_REMOTE_ACTIVITY_ENTITY_ID: self.remote_entity_id,
            ATTR_REMOTE_ACTIVITY_LAST_UPDATED: self.remote_last_updated,
            ATTR_REMOTE_ACTIVITY_PAUSE: self.remote_pause,
            ATTR_MAIN_MONITOR_LAST_UPDATED: self.main_last_updated,
            ATTR_MAIN_MONITOR_PAUSE: self.main_pause,
        }

        tmp_duration = (
            self.duration_wait_update + self.remote_last_updated - dt_util.now()
        )
        tmp_duration = tmp_duration - timedelta(microseconds=tmp_duration.microseconds)

        if (
            tmp_duration.total_seconds() < 0
            or self.duration_wait_update.total_seconds() == 0
        ):
            tmp_duration = timedelta()

        attr[ATTR_MAIN_MONITOR_WAIT_DURATION_LEFT] = str(tmp_duration)

        return attr

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
