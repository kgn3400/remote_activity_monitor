"""Rest api connection to Home Assistant."""
# borrowed from https://github.com/custom-components/remote_homeassistant

import asyncio
from typing import Any

from aiohttp import ClientSession

from homeassistant import exceptions
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class ApiProblem(exceptions.HomeAssistantError):
    """Error to indicate problem reaching API."""

    def __str__(self):
        """Return a human readable error."""
        return "api_problem"


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

    def __str__(self):
        """Return a human readable error."""
        return "cannot_connect"


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""

    def __str__(self):
        """Return a human readable error."""
        return "invalid_auth"


class BadResponse(exceptions.HomeAssistantError):
    """Error to indicate a bad response was received."""

    def __str__(self):
        """Return a human readable error."""
        return "bad_response"


class UnsupportedVersion(exceptions.HomeAssistantError):
    """Error to indicate an unsupported version of Home Assistant."""

    def __str__(self):
        """Return a human readable error."""
        return "unsupported_version"


class EndpointMissing(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""

    def __str__(self):
        """Return a human readable error."""
        return "endpoint_missing"


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
        retry: int = 0,
        retry_delay: int = 0,
    ) -> list[dict[str, Any]] | None:
        """Post to hass rest api."""

        # -------------------------
        async def async_post() -> list[dict[str, Any]] | None:
            async with session.post(url, headers=headers) as resp:
                self._check_resp_status(resp.status)

                json = await resp.json()

                if return_response and (
                    not isinstance(json, dict) or "service_response" not in json
                ):
                    raise BadResponse(f"Bad response data: {json}")
            return json["service_response"] if return_response else None

        # -------------------------

        retry_count: int = retry if retry > 0 else 1

        url = f"{'https' if secure else 'http'}://{host}:{port}/api/services/{domain}/{service}{'?return_response=true' if return_response else ''}"

        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }
        session: ClientSession = async_get_clientsession(hass, verify_ssl)

        for loop_count in range(retry_count):
            try:
                service_resp = await async_post()
                break

            except (
                # BadResponse,
                EndpointMissing,
                InvalidAuth,
                # ApiProblem,
                CannotConnect,
            ) as err:
                last_err = err

            except Exception:  # noqa: BLE001
                last_err = CannotConnect()

            # If this is the last retry, create an issue
            if loop_count == (retry_count - 1):
                raise last_err

            await asyncio.sleep(retry_delay)

        return service_resp

    # ------------------------------------------------------
    def _check_resp_status(self, status: int) -> None:
        if status == 401:
            raise InvalidAuth
        if status == 404:
            raise EndpointMissing
        if 400 <= status < 500:
            raise CannotConnect
        if status not in (200, 201):
            raise ApiProblem
