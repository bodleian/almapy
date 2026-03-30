"""Async-capable mock for niquests, adapted from the niquests extensions docs."""

from __future__ import annotations

import typing
from typing import cast
from unittest import mock as std_mock

import niquests
import responses


class NiquestsMock(responses.RequestsMock):
    """Extend responses.RequestsMock to patch niquests' async HTTP adapter.

    Niquests uses separate sync (HTTPAdapter) and async (AsyncHTTPAdapter) send
    methods. responses only patches the sync one by default; this subclass patches
    both so that AsyncSession calls are intercepted correctly in tests.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        kwargs.pop("target", None)
        super().__init__(target="niquests.adapters.HTTPAdapter.send", **kwargs)
        self._patcher_async: std_mock._patch[typing.Any] | None = None

    def __enter__(self) -> NiquestsMock:
        self.start()
        return self

    def _unbound_on_async_send(
        self,
    ) -> typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, niquests.Response]]:
        def send(
            adapter: niquests.adapters.AsyncHTTPAdapter,
            request: niquests.PreparedRequest,
            *args: typing.Any,
            **kwargs: typing.Any,
        ) -> niquests.Response:
            if args:
                try:
                    kwargs["stream"] = args[0]
                    kwargs["timeout"] = args[1]
                    kwargs["verify"] = args[2]
                    kwargs["cert"] = args[3]
                    kwargs["proxies"] = args[4]
                except IndexError:
                    pass
            resp = self._on_request(adapter, request, **kwargs)
            if not kwargs.get("stream"):
                resp.__class__ = niquests.Response
            return cast(niquests.Response, resp)

        async def async_send(  # noqa: RUF029
            adapter: niquests.adapters.AsyncHTTPAdapter,
            request: niquests.PreparedRequest,
            *args: typing.Any,
            **kwargs: typing.Any,
        ) -> niquests.Response:
            return send(adapter, request, *args, **kwargs)

        return async_send

    def start(self) -> None:
        if self._patcher:
            return
        self._patcher = std_mock.patch(target=self.target, new=self.unbound_on_send())
        self._patcher_async = std_mock.patch(
            target=self.target.replace("HTTPAdapter", "AsyncHTTPAdapter"),
            new=self._unbound_on_async_send(),
        )
        self._patcher.start()
        self._patcher_async.start()

    def stop(self, allow_assert: bool = True) -> None:
        if self._patcher:
            self._patcher.stop()
            self._patcher = None
        if self._patcher_async:
            self._patcher_async.stop()
            self._patcher_async = None
        if not self.assert_all_requests_are_fired:
            return
        if not allow_assert:
            return
        not_called = [m for m in self.registered() if m.call_count == 0]
        if not_called:
            raise AssertionError(
                "Not all requests have been executed {!r}".format([
                    (match.method, match.url) for match in not_called
                ])
            )
