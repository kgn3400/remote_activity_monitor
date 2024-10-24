"""The Remote activity monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_COMPONENT_TYPE, DOMAIN, ComponentType
from .shared import Shared


# ------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Remote activity monitor from a config entry."""

    shared = Shared()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "shared": shared,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    match entry.options[CONF_COMPONENT_TYPE]:
        case ComponentType.MAIN:
            await hass.config_entries.async_forward_entry_setups(
                entry, [Platform.BINARY_SENSOR, Platform.SWITCH]
            )
        case ComponentType.REMOTE:
            await hass.config_entries.async_forward_entry_setups(
                entry, [Platform.BINARY_SENSOR, Platform.SWITCH]
            )

    return True


# ------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    match entry.options[CONF_COMPONENT_TYPE]:
        case ComponentType.MAIN:
            return await hass.config_entries.async_unload_platforms(
                entry, [Platform.BINARY_SENSOR, Platform.SWITCH]
            )
        case ComponentType.REMOTE:
            return await hass.config_entries.async_unload_platforms(
                entry, [Platform.BINARY_SENSOR, Platform.SWITCH]
            )


# ------------------------------------------------------------------
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ------------------------------------------------------------------
async def update_listener(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Reload on config entry update."""

    shared: Shared = hass.data[DOMAIN][config_entry.entry_id]["shared"]

    if shared.supress_update_listener:
        shared.supress_update_listener = False
        return

    await hass.config_entries.async_reload(config_entry.entry_id)
