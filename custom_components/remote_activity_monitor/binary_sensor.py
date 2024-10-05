"""Support for Pin alert."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
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
    CONF_COMPONENT_TYPE,
    CONF_DURATION_WAIT_UPDATE,
    CONF_ENTITY_IDS,
    CONF_MONITOR_ENTITY,
    CONF_MONITOR_STATE_CHANGED_TYPE,
    CONF_SECURE,
    DOMAIN,
    DOMAIN_NAME,
    LOGGER,
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

    entity_list: list[RemoteAcitvityMonitorBinarySensor] = []

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
            # update_interval=timedelta(minutes=1),
            update_method=self.async_refresh,
        )

        super().__init__(self.coordinator, entry)

        self.translation_key = TRANSLATION_KEY

        self.remote_state = False
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

        tmp_remotes: list[dict[str, str]] = []

        for item in self.entity_list:
            state: State | None = self.hass.states.get(item.entity_id)

            if state:
                tmp_remotes.append(
                    {
                        "name": item.name,
                        "entity_id": item.entity_id,
                        "state": state.state,
                        "last_updated": state.last_updated.isoformat(),
                    }
                )

        return {"remotes": tmp_remotes}

    # ------------------------------------------------------
    async def async_will_remove_from_hass(self) -> None:
        """When removed from hass."""
        RemoteAcitvityMonitorBinarySensor.entity_list.remove(self)

    # ------------------------------------------------------
    @callback
    async def sensor_state_listener(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state changes on the observed device."""

        if (tmp_state := event.data["new_state"]) is None:
            return

        self.remote_state = tmp_state.state == STATE_ON
        self.remote_friendly_name = tmp_state.name
        self.remote_entity_id = tmp_state.entity_id
        self.remote_last_updated = dt_util.now()
        await self.coordinator.async_refresh()

    # ------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Complete device setup after being added to hass."""

        await self.coordinator.async_config_entry_first_refresh()

        RemoteAcitvityMonitorBinarySensor.entity_list.append(self)

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

    # ------------------------------------------------------
    async def hass_started(self, _event: Event) -> None:
        """Hass started."""

        if await self.async_verify_entity_exist():
            pass

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
            "monitor_activity_friendly_name": self.remote_friendly_name,
            "monitor_activity_entity_id": self.remote_entity_id,
            "monitor_activity_last_updated": self.remote_last_updated.isoformat(),
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

        self.remote_state: bool = False
        self.remote_friendly_name: str = ""
        self.remote_entity_id: str = ""
        self.remote_last_updated: datetime = dt_util.now()

        self.main_state: bool = False
        self.main_last_updated: datetime = dt_util.now()

        self.duration_wait_update: timedelta | None = None
        tmp_duration: dict = entry.options.get(CONF_DURATION_WAIT_UPDATE, None)

        if tmp_duration:
            self.duration_wait_update = timedelta(**tmp_duration)

        self.monitor_state_changed_type: str = entry.options.get(
            CONF_MONITOR_STATE_CHANGED_TYPE, STATE_BOTH
        )

        self.coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
            self.hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
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
    async def async_will_remove_from_hass(self) -> None:
        """When removed from hass."""
        await self.websocket_connection.async_stop()

    # ------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Complete device setup after being added to hass."""

        await self.coordinator.async_config_entry_first_refresh()

        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

        self.async_on_remove(start.async_at_started(self.hass, self.hass_started))

    # ------------------------------------------------------
    def _get_remote_state_for_changed_type(self, remote_state: str) -> bool:
        """Get remote state for changed type."""

        if self.monitor_state_changed_type == STATE_ON:
            return remote_state == STATE_ON
        if self.monitor_state_changed_type == STATE_OFF:
            return remote_state == STATE_OFF

        return remote_state

    # ------------------------------------------------------
    def _check_set_state(self, is_state: bool | None) -> None:
        """Check and set state."""

        if self.remote_state is is_state or is_state is None:
            if self.duration_wait_update is None or (
                self.duration_wait_update
                and dt_util.now()
                < (self.remote_last_updated + self.duration_wait_update)
            ):
                self.main_state = self._get_remote_state_for_changed_type(
                    self.remote_state
                )
                self.main_last_updated = dt_util.now()

        else:
            self.main_state = self._get_remote_state_for_changed_type(self.remote_state)
            self.main_last_updated = dt_util.now()

    # ------------------------------------------------------
    async def async_refresh(self) -> None:
        """Refresh."""

        if self.main_state == self._get_remote_state_for_changed_type(
            self.remote_state
        ):
            return

        if self.monitor_state_changed_type == STATE_ON:
            self._check_set_state(True)

        elif self.monitor_state_changed_type == STATE_OFF:
            self._check_set_state(False)

        elif self.monitor_state_changed_type == STATE_BOTH:
            self._check_set_state(None)

    # ------------------------------------------------------
    async def hass_started(self, _event: Event) -> None:
        """Hass started."""

        try:
            tmp_remote_entyties: list = (
                await RestApi().async_get_remote_activity_monitors(
                    self.hass,
                    self.entry.options.get(CONF_HOST),
                    self.entry.options.get(CONF_PORT),
                    self.entry.options.get(CONF_ACCESS_TOKEN),
                    self.entry.options.get(CONF_SECURE),
                    self.entry.options.get(CONF_VERIFY_SSL),
                )
            )

            for remote_entity in tmp_remote_entyties:
                if remote_entity["entity_id"] == self.entry.options.get(
                    CONF_MONITOR_ENTITY
                ):
                    self.remote_state = remote_entity["state"] == "on"
                    self.remote_last_updated = dt_util.as_local(
                        datetime.fromisoformat(remote_entity["last_updated"])
                    )
                    break

        except Exception:  # noqa: BLE001
            # Todo: create issue
            pass

        await self.websocket_connection.async_connect(self.async_connected)

    # ------------------------------------------------------------------
    async def async_connected(self) -> None:
        """Host connection established."""

        await self.websocket_connection.call(
            self.async_handle_event_message,
            "subscribe_trigger",
            trigger={
                "platform": "state",
                "entity_id": self.entry.options.get(CONF_MONITOR_ENTITY),
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
                self.remote_state = to_state["state"] == "on"
                self.remote_entity_id = to_state["attributes"][
                    "monitor_activity_entity_id"
                ]
                self.remote_friendly_name = to_state["attributes"][
                    "monitor_activity_friendly_name"
                ]
                self.remote_last_updated = self.main_last_updated = dt_util.as_local(
                    datetime.fromisoformat(
                        to_state["attributes"]["monitor_activity_last_updated"]
                    )
                )

                self.main_state = self._get_remote_state_for_changed_type(
                    self.remote_state
                )

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

        if self.main_state:
            return "mdi:alert-plus-outline"

        return "mdi:alert-outline"

    # ------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Get the state."""

        return self.main_state

    # ------------------------------------------------------
    @property
    def extra_state_attributes(self) -> dict:
        """Extra state attributes.

        Returns:
            dict: _description_

        """

        return {
            "remote_activity_friendly_name": self.remote_friendly_name,
            "remote_activity_entity_id": self.remote_entity_id,
            "remote_activity_last_updated": self.remote_last_updated,
            "main_activity_last_updated": self.main_last_updated,
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
