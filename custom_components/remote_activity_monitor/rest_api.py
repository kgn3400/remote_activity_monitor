"""Rest api connection to Home Assistant."""
# borrowed from https://github.com/custom-components/remote_homeassistant

from typing import Any

from aiohttp import ClientSession

from homeassistant import exceptions
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


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


# ------------------------------------------------------
# ------------------------------------------------------
class RestApi:
    """Home Assistant REST API."""

    # ------------------------------------------------------
    async def async_post_service(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        access_token: str,
        secure: bool,
        verify_ssl: bool,
        domain: str,
        service: str,
        return_response: bool = False,
    ) -> list[dict[str, Any]] | None:
        """Get remote activity monitors."""

        url = f'{"https" if secure else "http"}://{host}:{port}/api/services/{domain}/{service}{"?return_response=true" if return_response else ""}'

        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }
        session: ClientSession = async_get_clientsession(hass, verify_ssl)

        async with session.post(url, headers=headers) as resp:
            self._check_resp_status(resp.status)

            json = await resp.json()

            if (
                return_response
                and not isinstance(json, dict)
                or "service_response" not in json
            ):
                raise BadResponse(f"Bad response data: {json}")

            return json["service_response"] if return_response else None

    # ------------------------------------------------------
    def _check_resp_status(self, status: int) -> None:
        if status == 404:
            raise EndpointMissing
        if 400 <= status < 500:
            raise InvalidAuth
        if status != 200:
            raise ApiProblem
