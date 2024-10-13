"""Constants for the Remote Activity Monitor integration."""

from enum import StrEnum
from logging import Logger, getLogger

DOMAIN = "remote_activity_monitor"
DOMAIN_NAME = "Remote activity monitor"
REMOTE_DOMAIN_NAME = DOMAIN_NAME
MAIN_DOMAIN_NAME = "Activity monitor"
LOGGER: Logger = getLogger(__name__)

TRANSLATION_KEY = DOMAIN
TRANSLATION_KEY_MISSING_ENTITY = "missing_entity"
TRANSLATION_KEY_MISSING__TIMER_ENTITY = "missing_timer_entity"
TRANSLATION_KEY_TEMPLATE_ERROR = "template_error"
TRANSLATION_KEY_STATE_MONTOR_TYPE = "state_changed_type"

TRANSLATION_KEY_MAIN_DEVICE = "main_device"
TRANSLATION_KEY_REMOTE_DEVICE = "remote_device"

CONF_COMPONENT_TYPE = "component_type"
CONF_SECURE = "secure"
CONF_MONITOR_ENTITY = "monitor_entity"
CONF_DURATION_WAIT_UPDATE = "duration_wait_update"
CONF_MONITOR_STATE_CHANGED_TYPE = "monitor_state_changed_type"

CONF_ENTITY_IDS = "entity_ids"
CONF_ALL_ENTITIES_ON = "all_entities_on"
SERVICE_GET_REMOTE_ENTITIES = "get_remote_entities"
STATE_INIT = "initializing"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_AUTH_INVALID = "auth_invalid"
STATE_AUTH_REQUIRED = "auth_required"
STATE_RECONNECTING = "reconnecting"
STATE_DISCONNECTED = "disconnected"

STATE_BOTH = "both"

PAUSE_SWITCH_ENTITY_POSTFIX = "_pause"

DEFAULT_MAX_MSG_SIZE = 16 * 1024 * 1024
DEFAULT_UPDATE_INTERVAL = 60
HEARTBEAT_INTERVAL = 20
HEARTBEAT_TIMEOUT = 5

SW_VERSION = "1.0"

ATTR_MONITOR_ACTIVITY_ENTITY_ID = "monitor_activity_entity_id"
ATTR_MONITOR_ACTIVITY_FRIENDLY_NAME = "monitor_activity_friendly_name"
ATTR_MONITOR_ACTIVITY_LAST_UPDATED = "monitor_activity_last_updated"
ATTR_REMOTE_ACTIVITY_FRIENDLY_NAME = "remote_activity_friendly_name"
ATTR_REMOTE_ACTIVITY_ENTITY_ID = "remote_activity_entity_id"
ATTR_REMOTE_ACTIVITY_LAST_UPDATED = "remote_activity_last_updated"
ATTR_REMOTE_ACTIVITY_LAST_UPDATED_DURATION = "remote_activity_last_updated_duration"
ATTR_REMOTE_ACTIVITY_PAUSE = "remote_activity_pause"
ATTR_MAIN_MONITOR_LAST_UPDATED = "main_monitor_last_updated"
ATTR_MAIN_MONITOR_WAIT_DURATION_LEFT = "main_monitor_wait_duration_left"
ATTR_MAIN_MONITOR_PAUSE = "main_monitor_pause"


class ComponentType(StrEnum):
    """Available entity component types."""

    MAIN = "main"
    REMOTE = "remote"


class StepType(StrEnum):
    """Available entity component types."""

    CONFIG = "config"
    OPTIONS = "options"
