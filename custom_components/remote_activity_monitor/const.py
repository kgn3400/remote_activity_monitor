"""Constants for the Remote Activity Monitor integration."""

from enum import StrEnum
from logging import Logger, getLogger

DOMAIN = "remote_activity_monitor"
DOMAIN_NAME = "Remote activity monitor"
REMOTE_DOMAIN_NAME = DOMAIN_NAME
MAIN_DOMAIN_NAME = "Main activity monitor"
LOGGER: Logger = getLogger(__name__)

TRANSLATION_KEY = DOMAIN
TRANSLATION_KEY_MISSING_ENTITY = "missing_entity"
TRANSLATION_KEY_MISSING__TIMER_ENTITY = "missing_timer_entity"
TRANSLATION_KEY_TEMPLATE_ERROR = "template_error"
TRANSLATION_KEY_STATE_MONTOR_TYPE = "state_changed_type"

CONF_COMPONENT_TYPE = "component_type"
CONF_SECURE = "secure"
CONF_MONITOR_ENTITY = "monitor_entity"
CONF_DURATION_WAIT_UPDATE = "duration_wait_update"
CONF_MONITOR_STATE_CHANGED_TYPE = "monitor_state_changed_type"

CONF_ENTITY_IDS = "entity_ids"

SERVICE_GET_REMOTE_ENTITIES = "get_remote_entities"
STATE_INIT = "initializing"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_AUTH_INVALID = "auth_invalid"
STATE_AUTH_REQUIRED = "auth_required"
STATE_RECONNECTING = "reconnecting"
STATE_DISCONNECTED = "disconnected"

STATE_BOTH = "both"

DEFAULT_MAX_MSG_SIZE = 16 * 1024 * 1024
HEARTBEAT_INTERVAL = 20
HEARTBEAT_TIMEOUT = 5


class ComponentType(StrEnum):
    """Available entity component types."""

    MAIN = "main"
    REMOTE = "remote"


class StepType(StrEnum):
    """Available entity component types."""

    CONFIG = "config"
    OPTIONS = "options"
