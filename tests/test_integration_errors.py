"""Integration tests: pin Alma's real error response formats.

Six exception classes scrape attributes out of Alma's prose error messages.
Those formats are undocumented and can change without notice, and every parser
degrades silently — a wording change yields an empty attribute rather than an
error, so nothing else in the suite would notice.

The unit tests use fixtures written from assumption. That is how
BarcodeNotFoundError came to be parsed with the wrong shape: the fixture said
``Input barcode [ABC]`` while Alma actually sends the bare barcode followed by a
full stop, so the shipped parser silently truncated the barcode's first
character for every real 401689.

These tests use deliberately invalid identifiers, so they need no fixture data
and mutate nothing. They are the only tests in the suite that check almapy's
assumptions about Alma rather than almapy's behaviour given those assumptions.

Skipped unless ALMA_INTEGRATION=1 and an API_KEY is available (see .env.example).
"""

import pytest

from almapy import AlmaClient, exceptions

# Identifiers chosen to be structurally valid but certain not to exist.
_MISSING_BARCODE = "almapy-integration-no-such-barcode"
_MISSING_MMS_ID = "99999999999999999"
_MISSING_USER_ID = "almapy-integration-no-such-user"


@pytest.mark.integration
class TestErrorMessageFormats:
    async def test_missing_barcode_populates_the_barcode_attribute(
        self, integration_client: AlmaClient
    ) -> None:
        """Guards the parser against a wording change in Alma's 401689."""
        with pytest.raises(exceptions.BarcodeNotFoundError) as exc_info:
            await integration_client.bibs.get_item(_MISSING_BARCODE)

        exc = exc_info.value
        assert exc.code == "401689"
        assert exc.barcode == _MISSING_BARCODE, (
            f"BarcodeNotFoundError failed to parse the barcode out of Alma's message. "
            f"Raw message: {exc.error!r}. The parser in exceptions.py needs updating "
            f"to match the current wording."
        )

    async def test_missing_mms_id_populates_the_mms_attribute(
        self, integration_client: AlmaClient
    ) -> None:
        with pytest.raises(exceptions.MMSIdNotFoundError) as exc_info:
            await integration_client.bibs.get_bib(_MISSING_MMS_ID)

        exc = exc_info.value
        assert exc.mms == _MISSING_MMS_ID, (
            f"MMSIdNotFoundError failed to parse the MMS ID. Raw message: {exc.error!r}"
        )

    async def test_missing_user_populates_the_user_id_attribute(
        self, integration_client: AlmaClient
    ) -> None:
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            await integration_client.users.get_user(_MISSING_USER_ID)

        exc = exc_info.value
        assert exc.code == "401861"
        assert exc.user_id == _MISSING_USER_ID, (
            f"UserNotFoundError failed to parse the identifier. Raw message: {exc.error!r}"
        )

    async def test_error_bodies_map_to_specific_exceptions(
        self, integration_client: AlmaClient
    ) -> None:
        """A degradation to bare APIClientError means the glom chain in
        _raise_for_error_body no longer matches Alma's error body shape."""
        with pytest.raises(exceptions.APIClientError) as exc_info:
            await integration_client.users.get_user(_MISSING_USER_ID)

        exc = exc_info.value
        assert type(exc) is not exceptions.APIClientError, (
            f"Error body no longer parsed into a specific exception; "
            f"code={exc.code!r} message={exc.error!r}"
        )
        assert exc.code.isdigit(), f"expected a numeric Alma code, got {exc.code!r}"

    async def test_exceptions_survive_a_process_boundary(
        self, integration_client: AlmaClient
    ) -> None:
        """Real exceptions, not just synthesised ones, must pickle — callers run
        almapy behind process pools and task queues."""
        import pickle  # noqa: S403 — local to keep the module import clean

        with pytest.raises(exceptions.BarcodeNotFoundError) as exc_info:
            await integration_client.bibs.get_item(_MISSING_BARCODE)

        restored = pickle.loads(pickle.dumps(exc_info.value))  # noqa: S301
        assert type(restored) is exceptions.BarcodeNotFoundError
        assert str(restored) == str(exc_info.value)
