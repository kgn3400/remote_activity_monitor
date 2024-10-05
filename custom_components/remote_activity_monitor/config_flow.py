"""Config flow for carousel integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import callback
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)
from homeassistant.helpers.selector import (
    DurationSelector,
    DurationSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_COMPONENT_TYPE,
    CONF_DURATION_WAIT_UPDATE,
    CONF_ENTITY_IDS,
    CONF_MONITOR_ENTITY,
    CONF_MONITOR_STATE_CHANGED_TYPE,
    CONF_SECURE,
    DOMAIN,
    STATE_BOTH,
    TRANSLATION_KEY_STATE_MONTOR_TYPE,
    ComponentType,
    StepType,
)
from .rest_api import ApiProblem, EndpointMissing, RestApi


# ------------------------------------------------------------------
async def _async_create_monitor_list(
    handler: SchemaCommonFlowHandler,
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create a list of remotes to monitors."""

    monitors: list[dict[str, Any]] = await RestApi().async_get_remote_activity_monitors(
        handler.parent_handler.hass,
        options[CONF_HOST],
        options[CONF_PORT],
        options[CONF_ACCESS_TOKEN],
        options[CONF_SECURE],
        options[CONF_VERIFY_SSL],
    )

    tmp_list: list[dict[str, str]] = [
        {"label": monitor["name"], "value": monitor["entity_id"]}
        for monitor in monitors
    ]
    return tmp_list


# ------------------------------------------------------------------
async def _create_form(
    handler: SchemaCommonFlowHandler,
    step: StepType | None = None,
) -> vol.Schema:
    """Create a form for step/option."""

    CONFIG_NAME = {
        vol.Required(
            CONF_NAME,
        ): TextSelector(),
    }

    CONFIG_URL_TOKEN = {
        vol.Required(CONF_HOST, default=handler.options.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=handler.options.get(CONF_PORT, 8123)): int,
        vol.Required(
            CONF_ACCESS_TOKEN, default=handler.options.get(CONF_ACCESS_TOKEN, "")
        ): str,
        vol.Optional(CONF_SECURE, default=handler.options.get(CONF_SECURE, True)): bool,
        vol.Optional(
            CONF_VERIFY_SSL, default=handler.options.get(CONF_VERIFY_SSL, True)
        ): bool,
    }

    CONFIG_REMOTE_OPTIONS_ENTITIES = {
        vol.Required(
            CONF_ENTITY_IDS,
            default=handler.options.get(CONF_ENTITY_IDS, []),
        ): EntitySelector(
            EntitySelectorConfig(domain=Platform.BINARY_SENSOR, multiple=True),
        ),
    }

    match step:
        case StepType.OPTIONS:
            match handler.options.get(CONF_COMPONENT_TYPE, ComponentType.MAIN):
                case ComponentType.MAIN:
                    try:
                        tmp_monitors = await _async_create_monitor_list(
                            handler, handler.options
                        )
                    except Exception:  # noqa: BLE001
                        tmp_monitors = []

                    return vol.Schema(
                        {
                            vol.Required(
                                CONF_MONITOR_ENTITY, default=""
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=tmp_monitors,
                                    sort=True,
                                    mode=SelectSelectorMode.DROPDOWN,
                                )
                            ),
                            vol.Optional(CONF_DURATION_WAIT_UPDATE): DurationSelector(
                                DurationSelectorConfig(
                                    enable_day=True, allow_negative=False
                                )
                            ),
                            vol.Optional(
                                CONF_MONITOR_STATE_CHANGED_TYPE, default=STATE_BOTH
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=[
                                        STATE_BOTH,
                                        STATE_ON,
                                        STATE_OFF,
                                    ],
                                    sort=True,
                                    mode=SelectSelectorMode.DROPDOWN,
                                    translation_key=TRANSLATION_KEY_STATE_MONTOR_TYPE,
                                )
                            ),
                        }
                    )
                case ComponentType.REMOTE:
                    return vol.Schema(
                        {
                            **CONFIG_REMOTE_OPTIONS_ENTITIES,
                        }
                    )

        case StepType.CONFIG | _:
            match handler.options.get(CONF_COMPONENT_TYPE, ComponentType.MAIN):
                case ComponentType.MAIN:
                    return vol.Schema(
                        {
                            **CONFIG_NAME,
                            **CONFIG_URL_TOKEN,
                        }
                    )
                case ComponentType.REMOTE:
                    return vol.Schema(
                        {
                            **CONFIG_NAME,
                            **CONFIG_REMOTE_OPTIONS_ENTITIES,
                        }
                    )


MENU_OPTIONS = [
    ComponentType.REMOTE,
    ComponentType.MAIN,
]


# ------------------------------------------------------------------
async def _validate_input_main(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input for main integration."""

    return user_input


# ------------------------------------------------------------------
async def _validate_input_main_url(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input for main integration."""

    try:
        monitors: list[dict[str, Any]] = await _async_create_monitor_list(
            handler, user_input
        )

    except EndpointMissing:
        raise SchemaFlowError("missing_endpoint") from None
    except InvalidAuth:
        raise SchemaFlowError("invalid_auth") from None
    except ApiProblem:
        raise SchemaFlowError("cannot_connect") from None

    if len(monitors) == 0:
        raise SchemaFlowError("no_monitors")
    return user_input


# ------------------------------------------------------------------
async def _validate_input_remote(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input for remote integration."""
    if CONF_ENTITY_IDS not in user_input:
        raise SchemaFlowError("missing_selection")

    if len(user_input[CONF_ENTITY_IDS]) == 0:
        raise SchemaFlowError("missing_selection")

    return user_input


# ------------------------------------------------------------------
async def choose_options_step(options: dict[str, Any]) -> str:
    """Return next step_id for options flow according to component type."""
    return cast(str, options[CONF_COMPONENT_TYPE])


# ------------------------------------------------------------------
async def config_remote_component_schema(
    handler: SchemaCommonFlowHandler,
) -> vol.Schema:
    """Return schema for the sensor config step."""
    handler.options[CONF_COMPONENT_TYPE] = ComponentType.REMOTE
    return await _create_form(
        handler,
        step=StepType.CONFIG,
    )


# ------------------------------------------------------------------
async def config_main_component_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for the sensor config step."""
    handler.options[CONF_COMPONENT_TYPE] = ComponentType.MAIN
    return await _create_form(
        handler,
        step=StepType.CONFIG,
    )


# ------------------------------------------------------------------
async def config_main_options_component_schema(
    handler: SchemaCommonFlowHandler,
) -> vol.Schema:
    """Return schema for the sensor config step."""
    return await _create_form(
        handler,
        step=StepType.OPTIONS,
    )


# ------------------------------------------------------------------
async def options_remote_component_schema(
    handler: SchemaCommonFlowHandler,
) -> vol.Schema:
    """Return schema for the sensor config step."""
    handler.options[CONF_COMPONENT_TYPE] = ComponentType.REMOTE
    return await _create_form(
        handler,
        step=StepType.OPTIONS,
    )


# ------------------------------------------------------------------
async def options_main_component_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for the sensor config step."""
    handler.options[CONF_COMPONENT_TYPE] = ComponentType.MAIN
    return await _create_form(
        handler,
        step=StepType.OPTIONS,
    )


CONFIG_FLOW = {
    "user": SchemaFlowMenuStep(MENU_OPTIONS),
    ComponentType.MAIN: SchemaFlowFormStep(
        config_main_component_schema,
        validate_user_input=_validate_input_main_url,
        next_step="config_main_options",
    ),
    "config_main_options": SchemaFlowFormStep(
        config_main_options_component_schema,
        validate_user_input=_validate_input_main,
    ),
    ComponentType.REMOTE: SchemaFlowFormStep(
        config_remote_component_schema,
        validate_user_input=_validate_input_remote,
    ),
}


OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(next_step=choose_options_step),
    ComponentType.MAIN: SchemaFlowFormStep(
        options_main_component_schema,
        validate_user_input=_validate_input_main,
    ),
    ComponentType.REMOTE: SchemaFlowFormStep(
        options_remote_component_schema,
        validate_user_input=_validate_input_remote,
    ),
}


# ------------------------------------------------------------------
# ------------------------------------------------------------------
class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""

        return cast(str, options[CONF_NAME])

    # ------------------------------------------------------------------
    @callback
    def async_config_flow_finished(self, options: Mapping[str, Any]) -> None:
        """Take necessary actions after the config flow is finished, if needed.

        The options parameter contains config entry options, which is the union of user
        input from the config flow steps.
        """
