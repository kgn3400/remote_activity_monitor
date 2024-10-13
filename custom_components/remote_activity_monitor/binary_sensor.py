"""Support for Remote Activity Monitor."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_PORT,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
)
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    CONF_ALL_ENTITIES_ON,
    CONF_COMPONENT_TYPE,
    CONF_DURATION_WAIT_UPDATE,
    CONF_ENTITY_IDS,
    CONF_MONITOR_ENTITY,
    CONF_MONITOR_STATE_CHANGED_TYPE,
    CONF_SECURE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    DOMAIN_NAME,
    LOGGER,
    PAUSE_SWITCH_ENTITY_POSTFIX,
    SERVICE_GET_REMOTE_ENTITIES,
    STATE_BOTH,
    TRANSLATION_KEY,
    ComponentType,
)
from .entity import ComponentEntityMain, ComponentEntityRemote
from .rest_api import RestApi
from .websocket_api import RemoteWebsocketConnection


# ------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Entry for Remote activity monitor setup."""

    match entry.options[CONF_COMPONENT_TYPE]:
        case ComponentType.MAIN:
            async_add_entities([MainAcitvityMonitorBinarySensor(hass, entry)])
        case ComponentType.REMOTE:
            async_add_entities([RemoteAcitvityMonitorBinarySensor(hass, entry)])


# ------------------------------------------------------
# ------------------------------------------------------
class RemoteAcitvityMonitorBinarySensor(ComponentEntityRemote, BinarySensorEntity):
    """Sensor class for Remote activity monitor."""

    class_entity_list: list[RemoteAcitvityMonitorBinarySensor] = []

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

        self.translation_key: str = TRANSLATION_KEY

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

        # state: State | None = self.hass.states.get(
        #     self.entry.options.get(CONF_ENTITY_ID)
        # )

        # if state is None:
        #     await self.async_create_issue_entity(
        #         self.entry.options.get(CONF_ENTITY_ID),
        #         TRANSLATION_KEY_MISSING_ENTITY,
        #     )
        #     self.coordinator.update_interval = None
        #     return False

        return True

    # ------------------------------------------------------
    async def async_refresh(self) -> None:
        """Refresh."""

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
                "state_updated_helper": self.entity_id,
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
    def icon(self) -> str:
        """Icon.

        Returns:
            str: Icon name

        """

        if self.remote_state:
            return "mdi:alert-plus-outline"

        return "mdi:alert-outline"

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


# ------------------------------------------------------
# ------------------------------------------------------
class MainAcitvityMonitorBinarySensor(ComponentEntityMain, BinarySensorEntity):
    """Sensor class for the main activity monitor."""

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Binary sensor."""
        self.entry: ConfigEntry = entry
        self.hass = hass

        self.translation_key = TRANSLATION_KEY

        self.remote_state_on: bool = False
        self.remote_friendly_name: str = ""
        self.remote_entity_id: str = ""
        self.remote_last_updated: datetime = dt_util.now()
        self.remote_pause: bool = False

        self.remote_binary_sensor_name: str = entry.options.get(CONF_MONITOR_ENTITY)
        self.remote_switch_pause_name: str = (
            self.remote_binary_sensor_name.replace("binary_sensor", "switch")
            + PAUSE_SWITCH_ENTITY_POSTFIX
        )

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
                self.entity_id.replace("binary_sensor", "switch")
                + PAUSE_SWITCH_ENTITY_POSTFIX,
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

        try:
            remote_entyties: list = await RestApi().async_get_remote_activity_monitors(
                self.hass,
                self.entry.options.get(CONF_HOST),
                self.entry.options.get(CONF_PORT),
                self.entry.options.get(CONF_ACCESS_TOKEN),
                self.entry.options.get(CONF_SECURE),
                self.entry.options.get(CONF_VERIFY_SSL),
            )

            for remote_entity in remote_entyties:
                if remote_entity["entity_id"] == self.remote_binary_sensor_name:
                    self.remote_state_on = remote_entity["state"] == STATE_ON
                    self.remote_last_updated = dt_util.as_local(
                        datetime.fromisoformat(remote_entity["last_updated"])
                    )
                    await self.websocket_connection.async_connect(self.async_connected)
                    break

        except Exception:  # noqa: BLE001
            # Todo: create issue for remote host error!
            pass

        # todo: create issue for remote entity not found!

    # ------------------------------------------------------------------
    async def async_connected(self) -> None:
        """Host connection established."""

        await self.websocket_connection.call(
            self.async_handle_event_message,
            "subscribe_trigger",
            trigger={
                "platform": "state",
                "entity_id": [
                    self.remote_binary_sensor_name,
                    self.remote_switch_pause_name,
                ],
            },
        )

    # ------------------------------------------------------------------
    async def async_handle_event_message(self, message: dict) -> None:
        """Handle event from host."""

        match message["type"]:
            case "result":
                pass
            case "event":
                to_state: dict = message["event"]["variables"]["trigger"]["to_state"]

                if to_state[ATTR_ENTITY_ID] == self.remote_binary_sensor_name:
                    await self.async_handle_trigger_binary_sensor(to_state)

                if to_state[ATTR_ENTITY_ID] == self.remote_switch_pause_name:
                    await self.async_handle_trigger_switch(to_state)

    # ------------------------------------------------------------------
    async def async_handle_trigger_binary_sensor(self, to_state: dict) -> None:
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
    async def async_handle_trigger_switch(self, to_state: dict) -> None:
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
                "state_updated_helper": self.entity_id,
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
    def icon(self) -> str:
        """Icon.

        Returns:
            str: Icon name

        """

        if self.main_state_on:
            return "mdi:alert-plus-outline"

        return "mdi:alert-outline"

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
