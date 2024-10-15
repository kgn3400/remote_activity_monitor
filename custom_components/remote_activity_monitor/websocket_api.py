"""Websocket API for connecting toHome Assistant."""
# Inspiration and parts borrowed from https://github.com/custom-components/remote_homeassistant

import asyncio
from collections.abc import Callable
import contextlib
import inspect
from typing import Any

import aiohttp
from aiohttp import ClientWebSocketResponse

import homeassistant.components.websocket_api.auth as api
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_MAX_MSG_SIZE,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    LOGGER,
    STATE_AUTH_INVALID,
    STATE_AUTH_REQUIRED,
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_RECONNECTING,
)


# ------------------------------------------------------
# ------------------------------------------------------
class RemoteWebsocketConnection:
    """A Websocket connection to a remote home-assistant instance."""

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        access_token: str,
        secure: bool = False,
        verify_ssl: bool = False,
        on_connected: Callable[[Any], Any] | None = None,
        on_disconnected: Callable[[Any], Any] | None = None,
    ) -> None:
        """Initialize the connection."""
        self._hass: HomeAssistant = hass
        self._host: str = host
        self._port: int = port
        self._access_token: str = access_token
        self._secure: bool = secure
        self._verify_ssl: bool = verify_ssl
        self._on_connected: Callable[[Any], Any] | None = on_connected
        self._on_disconnected: Callable[[Any], Any] | None = on_disconnected

        self._connection: ClientWebSocketResponse | None = None
        self._heartbeat_task = None
        self._is_stopping: bool = False
        self._handlers: dict = {}
        self.set_connection_state(STATE_CONNECTING)

        self.__id: int = 1

        self._background_tasks = set()

    # ------------------------------------------------------
    def set_connection_state(self, state):
        """Change current connection state."""
        # todo: Do we need this?
        # signal = f"remote_homeassistant_{self._entry.unique_id}"
        # async_dispatcher_send(self._hass, signal, state)

    # ------------------------------------------------------
    @callback
    def _get_url(self) -> str:
        """Get url to connect to."""

        return f"{'wss' if self._secure else 'ws'}://{self._host}:{self._port}/api/websocket"

    # ------------------------------------------------------
    async def async_connect(
        self,
        on_connected: Callable[[Any], Any] | None = None,
        on_disconnected: Callable[[Any], Any] | None = None,
    ) -> None:
        """Connect to remote home-assistant websocket..."""

        self._on_connected: Callable[[Any], Any] | None = on_connected
        self._on_disconnected: Callable[[Any], Any] | None = on_disconnected

        # ------------------------------------------------------
        async def _async_stop_handler(event):
            """Stop when Home Assistant is shutting down."""
            await self.async_stop()

        url = self._get_url()

        session = async_get_clientsession(self._hass, self._verify_ssl)
        self.set_connection_state(STATE_CONNECTING)
        self._handlers: dict = {}
        self.__id = 1

        while True:
            try:
                LOGGER.info("Connecting to %s", url)
                self._connection = await session.ws_connect(
                    url, max_msg_size=DEFAULT_MAX_MSG_SIZE
                )
            except aiohttp.client_exceptions.ClientError:
                LOGGER.error("Could not connect to %s, retry in 10 seconds...", url)
                self.set_connection_state(STATE_RECONNECTING)
                await asyncio.sleep(10)
            else:
                LOGGER.info("Connected to home-assistant websocket at %s", url)
                break

        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop_handler)

        tmp_task = asyncio.ensure_future(self._recv())
        self._background_tasks.add(tmp_task)

        self._heartbeat_task = self._hass.loop.create_task(self._heartbeat_loop())

    # ------------------------------------------------------
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to remote instance."""
        while self._connection is not None and not self._connection.closed:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            LOGGER.debug("Sending ping")
            self._event: asyncio.Event = asyncio.Event()

            def resp(message):
                LOGGER.debug("Got pong: %s", message)
                self._event.set()

            await self.call(resp, "ping")

            try:
                await asyncio.wait_for(self._event.wait(), HEARTBEAT_TIMEOUT)
            except TimeoutError:
                LOGGER.warning("heartbeat failed")

                # Schedule closing on event loop to avoid deadlock
                tmp_task = asyncio.ensure_future(self._connection.close())
                self._background_tasks.add(tmp_task)
                break

    # ------------------------------------------------------
    async def async_stop(self):
        """Close connection."""
        self._is_stopping = True
        if self._connection is not None:
            await self._connection.close()

        if self._on_disconnected is not None:
            if inspect.iscoroutinefunction(self._on_disconnected):
                await self._on_disconnected()
            else:
                self._on_disconnected()

    # ------------------------------------------------------
    def _next_id(self):
        _id = self.__id
        self.__id += 1
        return _id

    # ------------------------------------------------------
    async def call(self, handler, message_type, **extra_args) -> None:
        """Call a websocket on the remote instance."""
        if self._connection is None:
            LOGGER.error("No remote websocket connection")
            return

        _id = self._next_id()
        self._handlers[_id] = handler

        try:
            tmp_message = {"id": _id, "type": message_type, **extra_args}
            LOGGER.debug("Sending: %s", tmp_message)

            await self._connection.send_json(
                {"id": _id, "type": message_type, **extra_args}
            )
        except aiohttp.client_exceptions.ClientError as err:
            LOGGER.error("remote websocket connection closed: %s", err)
            await self._disconnected()

    # ------------------------------------------------------
    async def _disconnected(self):
        """Cleanup on disconnect."""

        if self._on_disconnected is not None:
            if inspect.iscoroutinefunction(self._on_disconnected):
                await self._on_disconnected()
            else:
                self._on_disconnected()

        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        self.set_connection_state(STATE_DISCONNECTED)
        self._heartbeat_task = None

        if not self._is_stopping:
            tmp_task = asyncio.ensure_future(
                self.async_connect(self._on_connected, self._on_disconnected)
            )
            # todo: Skal background task nulstilles?
            self._background_tasks.add(tmp_task)

    # ------------------------------------------------------
    async def _recv(self):
        while self._connection is not None and not self._connection.closed:
            try:
                data = await self._connection.receive()
            except aiohttp.client_exceptions.ClientError as err:
                LOGGER.error("remote websocket connection closed: %s", err)
                break

            if not data:
                break

            if data.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
            ):
                LOGGER.debug("websocket connection is closing")
                break

            if data.type == aiohttp.WSMsgType.ERROR:
                LOGGER.error("websocket connection had an error")
                if data.data.code == aiohttp.WSCloseCode.MESSAGE_TOO_BIG:
                    LOGGER.error(
                        f"please consider increasing message size with `{DEFAULT_MAX_MSG_SIZE} ???`"
                    )
                break

            try:
                message = data.json()
            except TypeError as err:
                LOGGER.error("could not decode data (%s) as json: %s", data, err)
                break

            if message is None:
                break

            LOGGER.debug("received: %s", message)

            if message["type"] == api.TYPE_AUTH_OK:
                self.set_connection_state(STATE_CONNECTED)

                if self._on_connected is not None:
                    if inspect.iscoroutinefunction(self._on_connected):
                        await self._on_connected()
                    else:
                        self._on_connected()

            elif message["type"] == api.TYPE_AUTH_REQUIRED:
                if self._access_token:
                    json_data = {
                        "type": api.TYPE_AUTH,
                        "access_token": self._access_token,
                    }
                else:
                    LOGGER.error("Access token required, but not provided")
                    self.set_connection_state(STATE_AUTH_REQUIRED)
                    return
                try:
                    await self._connection.send_json(json_data)
                except Exception as err:  # noqa: BLE001
                    LOGGER.error("could not send data to remote connection: %s", err)
                    break

            elif message["type"] == api.TYPE_AUTH_INVALID:
                LOGGER.error("Auth invalid, check your access token")
                self.set_connection_state(STATE_AUTH_INVALID)
                await self._connection.close()
                return

            else:
                handler = self._handlers.get(message["id"])
                if handler is not None:
                    if inspect.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)

        await self._disconnected()
