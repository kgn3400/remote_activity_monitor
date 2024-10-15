"""Rest api connection to Home Assistant."""
# borrowed from https://github.com/custom-components/remote_homeassistant

from typing import Any

from aiohttp import ClientSession

from homeassistant import exceptions
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, SERVICE_GET_REMOTE_ENTITIES


class ApiProblem(exceptions.HomeAssistantError):
    """Error to indicate problem reaching API."""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class BadResponse(exceptions.HomeAssistantError):
    """Error to indicate a bad response was received."""


class UnsupportedVersion(exceptions.HomeAssistantError):
    """Error to indicate an unsupported version of Home Assistant."""


class EndpointMissing(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class RestApi:
    """Home Assistant REST API."""

    async def async_get_remote_activity_monitors(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        access_token: str,
        secure: bool,
        verify_ssl: bool,
    ) -> list[dict[str, Any]] | None:
        """Get remote activity monitors."""

        url = f'{"https" if secure else "http"}://{host}:{port}/api/services/{DOMAIN}/{SERVICE_GET_REMOTE_ENTITIES}?return_response=true'

        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }
        session: ClientSession = async_get_clientsession(hass, verify_ssl)

        # Get remote activity monitors
        async with session.post(url, headers=headers) as resp:
            if resp.status == 404:
                raise EndpointMissing
            if 400 <= resp.status < 500:
                raise InvalidAuth
            if resp.status != 200:
                raise ApiProblem
            json = await resp.json()
            if not isinstance(json, dict) or "service_response" not in json:
                raise BadResponse(f"Bad response data: {json}")
            return json["service_response"]["remotes"]
