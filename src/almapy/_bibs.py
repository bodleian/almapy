"""Bibliographic, holding and item namespaces.

Reached as ``client.bibs``, which carries the record-level methods themselves plus
two sub-namespaces:

| Attribute | Covers |
|---|---|
| ``client.bibs.loans`` | Loans reached from a record or item, rather than a user |
| ``client.bibs.requests`` | Requests on a record or item, and processing them |

Most methods here want the full MMS ID / holding ID / item PID path;
[`get_item`][almapy._bibs.AlmaClientBibNS.get_item] resolves all three from a
barcode.

**Not everything returns a Box.** The holding and bib-record methods exchange raw
MARC XML as ``str`` because Alma has no JSON representation of a MARC record. Those
methods do not accept a ``model=`` argument; the rest of the module does. See
[Responses](../guide/responses.md).
"""

import re
from typing import TYPE_CHECKING, Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, Request, _ModelT
from almapy.exceptions import APIClientError, CannotRenewError, InvalidCodeError, RequestFailedError

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


def _bib_write_params(
    *, validate: bool, override_warning: bool, check_match: bool
) -> dict[str, str | bool]:
    """Query parameters shared by bib create and update.

    ``override_warning`` is deliberately left out of the plain default call.
    Alma's own default is ``true``, and it rejects an explicit ``false`` unless
    ``validate`` or ``check_match`` is also set (error 401873) – so sending it
    unconditionally, as this once did, broke every default create and update.
    Once either check is on the ``false`` must be explicit, or Alma quietly
    saves over the warnings the caller asked it to raise.
    """
    params: dict[str, str | bool] = {"validate": validate, "check_match": check_match}
    if override_warning or validate or check_match:
        params["override_warning"] = override_warning
    return params


class AlmaClientBibLoansNS(BaseNamespace):
    """Namespace for bib loans, exposed at ``client.bibs.loans``.

    Loans reached from the bibliographic side – by record or by item – which is the
    route to take when you know what was borrowed but not who has it. To act on a
    loan (renewing it, changing its due date) use ``client.users.loans``, which is
    where the write operations live.
    """

    @overload
    async def get_loans(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_loans(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_loans(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        limit: int = 100,
        offset: int = 0,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = "due_date",
        direction: Literal["asc", "desc"] = "asc",
        loan_status: Literal["Active", "Complete"] = "Active",
        *,
        model: Any = None,
    ) -> Any:
        """Retrieves loans for a specific item."""
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        return await self._get(
            AlmaEndpoint.ITEM_LOANS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            model=model,
            params=params,
        )

    @overload
    async def create_loan(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        circ_desk: str,
        library: str,
        request_id: str | None = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_loan(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        circ_desk: str,
        library: str,
        request_id: str | None = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_loan(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        circ_desk: str,
        library: str,
        request_id: str | None = None,
        *,
        model: Any = None,
    ) -> Any:
        """Creates a loan for a specific copy of an item."""
        loan: dict[str, Any] = {"circ_desk": {"value": circ_desk}, "library": {"value": library}}
        if request_id:
            loan["request_id"] = {"value": request_id}
        return await self._post(
            AlmaEndpoint.ITEM_LOANS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            model=model,
            json=loan,
            params={"user_id": user_id},
        )

    @overload
    async def get_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: Any = None
    ) -> Any:
        """Get the details of a specific loan on a specific copy of an item."""
        return await self._get(
            AlmaEndpoint.ITEM_LOAN,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id, "LOAN_ID": loan_id},
            model=model,
        )

    @overload
    async def renew_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def renew_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def renew_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, *, model: Any = None
    ) -> Any:
        """Renew a loan on a specific copy of an item."""
        try:
            resp: Any = await self._post(
                AlmaEndpoint.ITEM_LOAN,
                {
                    "MMS_ID": mms_id,
                    "HOLDING_ID": holding_id,
                    "ITEM_PID": item_id,
                    "LOAN_ID": loan_id,
                },
                model=model,
                params={"op": "renew"},
            )
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            raise
        return resp

    @overload
    async def change_loan_due_date(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        loan_id: str,
        due_date: str,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def change_loan_due_date(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        loan_id: str,
        due_date: str,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def change_loan_due_date(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        loan_id: str,
        due_date: str,
        *,
        model: Any = None,
    ) -> Any:
        """Changes the due date of a loan on a specific copy of an item."""
        loan = {"due_date": due_date}
        return await self._put(
            AlmaEndpoint.ITEM_LOAN,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id, "LOAN_ID": loan_id},
            model=model,
            json=loan,
        )

    @overload
    async def get_bib_loans(
        self,
        mms_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_bib_loans(
        self,
        mms_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_bib_loans(
        self,
        mms_id: str,
        limit: int = 100,
        offset: int = 0,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = "due_date",
        direction: Literal["asc", "desc"] = "asc",
        loan_status: Literal["Active", "Complete"] = "Active",
        *,
        model: Any = None,
    ) -> Any:
        """List every loan across all items on a bibliographic record.

        The record-level counterpart to
        [`get_loans`][almapy._bibs.AlmaClientBibLoansNS.get_loans], which narrows to
        a single item.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            limit: Maximum number of loans to return in this page.
            offset: Index of the first loan to return, for paging.
            order_by: Field to sort by.
            direction: Sort direction.
            loan_status: ``"Active"`` for loans still out, ``"Complete"`` for
                returned ones.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of loans across the record's items, with ``total_record_count``
            giving the full result size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            loans = await client.bibs.loans.get_bib_loans(
                "99123456789012345", loan_status="Active"
            )
            for loan in loans.item_loan:
                print(loan.item_barcode, loan.user_id, loan.due_date)
            ```
        """
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        return await self._get(
            AlmaEndpoint.BIB_LOANS, {"MMS_ID": mms_id}, model=model, params=params
        )

    @overload
    async def get_bib_loan(self, mms_id: str, loan_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_bib_loan(self, mms_id: str, loan_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_bib_loan(self, mms_id: str, loan_id: str, *, model: Any = None) -> Any:
        """Retrieve a single loan on a bibliographic record.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            loan_id: The loan identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The loan record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            LoanNotFoundError: If the record has no loan with that ID.

        Examples:
            ```python
            loan = await client.bibs.loans.get_bib_loan("99123456789012345", "987654321")
            ```
        """
        return await self._get(
            AlmaEndpoint.BIB_LOAN, {"MMS_ID": mms_id, "LOAN_ID": loan_id}, model=model
        )


class AlmaClientBibRequestsNS(BaseNamespace):
    """Namespace for bib requests, exposed at ``client.bibs.requests``.

    Requests reached from the bibliographic side. Alma splits these across two levels
    and this namespace mirrors that split, which is the main thing to get right here:

    - **Item level** – ``get_requests``, ``get_request``, ``create_request``,
      ``update_request``, ``cancel_request`` all take an MMS ID, holding ID and item
      PID, and act on requests against one physical copy.
    - **Record level** – the ``*_for_bib`` methods take only an MMS ID and act on
      title level requests, where Alma has not yet picked a copy.

    ``client.users.requests`` covers the same requests from the borrower's side, and
    is where to start when you know the user rather than the record.
    """

    @overload
    async def get_requests(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = ...,
        status: Literal["active", "history"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_requests(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = ...,
        status: Literal["active", "history"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_requests(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = "all_types",
        status: Literal["active", "history"] = "active",
        *,
        model: Any = None,
    ) -> Any:
        """List the requests on a single item.

        Also callable as ``client.bibs.requests.get_requests_for_item(...)``. For
        title level requests on the record as a whole, use
        [`get_requests_for_bib`][almapy._bibs.AlmaClientBibRequestsNS.get_requests_for_bib].

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_id: The item PID.
            request_type: Restrict to one kind of request, or ``"all_types"`` for
                every kind.
            status: ``"active"`` for outstanding requests, ``"history"`` for
                completed and cancelled ones.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The item's requests, with ``total_record_count`` giving the result size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding or item does not exist.

        Examples:
            ```python
            reqs = await client.bibs.requests.get_requests(
                "99123456789012345", "22123456780001234", "23123456770001234"
            )
            ```
        """
        params = {"request_type": request_type, "status": status}
        return await self._get(
            AlmaEndpoint.ITEM_REQUESTS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            model=model,
            params=params,
        )

    get_requests_for_item = get_requests
    """Alias for [`get_requests`][almapy._bibs.AlmaClientBibRequestsNS.get_requests]."""

    @overload
    async def get_requests_for_bib(
        self,
        mms_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = ...,
        status: Literal["active", "history"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_requests_for_bib(
        self,
        mms_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = ...,
        status: Literal["active", "history"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_requests_for_bib(
        self,
        mms_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = "all_types",
        status: Literal["active", "history"] = "active",
        *,
        model: Any = None,
    ) -> Any:
        """List the title level requests on a bibliographic record.

        Returns requests placed against the record as a whole, where Alma has not yet
        assigned a specific copy. For requests on one item, use
        [`get_requests`][almapy._bibs.AlmaClientBibRequestsNS.get_requests].

        Args:
            mms_id: The MMS ID of the bibliographic record.
            request_type: Restrict to one kind of request, or ``"all_types"`` for
                every kind.
            status: ``"active"`` for outstanding requests, ``"history"`` for
                completed and cancelled ones.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The record's title level requests.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            reqs = await client.bibs.requests.get_requests_for_bib(
                "99123456789012345", request_type="HOLD"
            )
            ```
        """
        params = {"request_type": request_type, "status": status}
        return await self._get(
            AlmaEndpoint.BIB_REQUESTS,
            {"MMS_ID": mms_id},
            model=model,
            params=params,
        )

    @overload
    async def get_request_for_bib(
        self, mms_id: str, request_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_request_for_bib(
        self, mms_id: str, request_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_request_for_bib(self, mms_id: str, request_id: str, *, model: Any = None) -> Any:
        """Retrieve a single title level request on a bibliographic record.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            request_id: The request identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The request record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the record has no request with that ID.

        Examples:
            ```python
            req = await client.bibs.requests.get_request_for_bib(
                "99123456789012345", "987654321"
            )
            ```
        """
        return await self._get(
            AlmaEndpoint.BIB_REQUEST,
            {"MMS_ID": mms_id, "REQUEST_ID": request_id},
            model=model,
        )

    @overload
    async def update_request_for_bib(
        self, mms_id: str, request_id: str, request: Request, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_request_for_bib(
        self, mms_id: str, request_id: str, request: Request, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_request_for_bib(
        self, mms_id: str, request_id: str, request: Request, *, model: Any = None
    ) -> Any:
        """Update a title level request on a bibliographic record.

        Alma replaces the whole request, so fetch it with
        [`get_request_for_bib`][almapy._bibs.AlmaClientBibRequestsNS.get_request_for_bib]
        and modify that rather than sending a partial body.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            request_id: The request identifier.
            request: The full, modified request record.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated request record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the request does not exist, or a field that cannot be
                changed was modified.

        Examples:
            ```python
            req = await client.bibs.requests.get_request_for_bib(
                "99123456789012345", "987654321"
            )
            req.pickup_location_library = "SCIENCE"
            await client.bibs.requests.update_request_for_bib(
                "99123456789012345", "987654321", req
            )
            ```
        """
        return await self._put(
            AlmaEndpoint.BIB_REQUEST,
            {"MMS_ID": mms_id, "REQUEST_ID": request_id},
            model=model,
            json=request,
        )

    @overload
    async def process_request_for_bib(
        self,
        mms_id: str,
        request_id: str,
        op: str = ...,
        *,
        release_item: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def process_request_for_bib(
        self,
        mms_id: str,
        request_id: str,
        op: str = ...,
        *,
        release_item: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def process_request_for_bib(
        self,
        mms_id: str,
        request_id: str,
        op: str = "next_step",
        *,
        release_item: bool = False,
        model: Any = None,
    ) -> Any:
        """Advance a title level request through its workflow.

        Moves the request to the next step in Alma's fulfilment workflow – the API
        equivalent of processing it at a desk.

        Being a POST, this call is **not replayed** if the response is lost in
        transit. See [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            request_id: The request identifier.
            op: The operation to perform. ``"next_step"`` advances the request.
            release_item: Whether to release the item assigned to the request back
                into circulation as part of the operation.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The request record in its new state.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the request does not exist, or is not in a state that
                can be advanced.

        Examples:
            ```python
            req = await client.bibs.requests.process_request_for_bib(
                "99123456789012345", "987654321", op="next_step"
            )
            ```
        """
        params = {"op": op, "release_item": release_item}
        return await self._post(
            AlmaEndpoint.BIB_REQUEST,
            {"MMS_ID": mms_id, "REQUEST_ID": request_id},
            model=model,
            params=params,
        )

    @overload
    async def get_request(
        self, mms_id: str, holding_id: str, item_id: str, request_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_request(
        self, mms_id: str, holding_id: str, item_id: str, request_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_request(
        self, mms_id: str, holding_id: str, item_id: str, request_id: str, *, model: Any = None
    ) -> Any:
        """Retrieve a single request on an item.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_id: The item PID.
            request_id: The request identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The request record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding, item or request does not exist.

        Examples:
            ```python
            req = await client.bibs.requests.get_request(
                "99123456789012345",
                "22123456780001234",
                "23123456770001234",
                "987654321",
            )
            ```
        """
        return await self._get(
            AlmaEndpoint.ITEM_REQUEST,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
                "ITEM_PID": item_id,
                "REQUEST_ID": request_id,
            },
            model=model,
        )

    async def cancel_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_id: str,
        reason: str,
        *,
        notify_user: bool,
        note: str | None = None,
    ) -> None:
        """Cancel a request on an item.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_id: The item PID.
            request_id: The request identifier.
            reason: Cancellation reason. Must be a code from the
                ``RequestCancellationReasons`` code table – fetch the valid values
                with ``client.config.code_tables.get_code_table()``.
            notify_user: Whether Alma should notify the requester.
            note: Free-text note included in the notification.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the request does not exist, is already fulfilled, or
                the reason code is not valid.

        Examples:
            ```python
            await client.bibs.requests.cancel_request(
                "99123456789012345",
                "22123456780001234",
                "23123456770001234",
                "987654321",
                reason="CannotBeFulfilled",
                notify_user=True,
            )
            ```
        """
        params: dict[str, Any] = {"reason": reason, "notify_user": notify_user}
        if note:
            params["note"] = note
        await self._delete(
            AlmaEndpoint.ITEM_REQUEST,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
                "ITEM_PID": item_id,
                "REQUEST_ID": request_id,
            },
            parser="none",
            params=params,
        )

    @overload
    async def create_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        request: Request,
        user_id_type: str = ...,
        *,
        allow_same_request: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        request: Request,
        user_id_type: str = ...,
        *,
        allow_same_request: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        request: Request,
        user_id_type: str = "all_unique",
        *,
        allow_same_request: bool = False,
        model: Any = None,
    ) -> Any:
        """Place a request on a specific item.

        Pins the request to one physical copy. To let Alma choose a copy, place a
        title level request with ``client.users.requests.create_request()`` instead.

        Being a POST, this call is **not replayed** if the response is lost in
        transit – a retry could place a duplicate request. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_id: The item PID.
            user_id: The identifier of the user the request is for.
            request: The request to create. Requires at least ``request_type`` and,
                for holds, a ``pickup_location_type`` and ``pickup_location_library``.
            user_id_type: Which kind of identifier ``user_id`` is.
            allow_same_request: Whether to permit a second request when the user
                already has one on this title.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created request record, including its ``request_id``.

        Raises:
            RequestFailedError: If Alma rejected the request (code ``401873``).
            NoItemsCanFulfillRequestError: If the item cannot satisfy it.
            ParallelRequestError: If the user already has a request on another copy
                and ``allow_same_request`` is False.
            MMSIdNotFoundError: If no record has that MMS ID.
            UserNotFoundError: If no user matches the identifier.

        Examples:
            ```python
            req = await client.bibs.requests.create_request(
                "99123456789012345",
                "22123456780001234",
                "23123456770001234",
                "12345678",
                {
                    "request_type": "HOLD",
                    "pickup_location_type": "LIBRARY",
                    "pickup_location_library": "MAIN",
                },
            )
            ```
        """
        params = {
            "user_id": user_id,
            "user_id_type": user_id_type,
            "allow_same_request": allow_same_request,
        }
        return await self._post(
            AlmaEndpoint.ITEM_REQUESTS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            model=model,
            params=params,
            json=request,
        )

    @overload
    async def update_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_id: str,
        request: Request,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def update_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_id: str,
        request: Request,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def update_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_id: str,
        request: Request,
        *,
        model: Any = None,
    ) -> Any:
        """Update a request on an item.

        Alma replaces the whole request, so fetch it with
        [`get_request`][almapy._bibs.AlmaClientBibRequestsNS.get_request] and modify
        that rather than sending a partial body.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_id: The item PID.
            request_id: The request identifier.
            request: The full, modified request record.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated request record.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the request does not exist, or a field that cannot be
                changed was modified.

        Examples:
            ```python
            req = await client.bibs.requests.get_request(
                "99123456789012345", "22123456780001234", "23123456770001234", "987654321"
            )
            req.pickup_location_library = "SCIENCE"
            await client.bibs.requests.update_request(
                "99123456789012345",
                "22123456780001234",
                "23123456770001234",
                "987654321",
                req,
            )
            ```
        """
        return await self._put(
            AlmaEndpoint.ITEM_REQUEST,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
                "ITEM_PID": item_id,
                "REQUEST_ID": request_id,
            },
            model=model,
            json=request,
        )


class AlmaClientBibNS(BaseNamespace):
    """Namespace for bibliographic functionality, exposed at ``client.bibs``.

    Carries the record, holding and item methods themselves, plus two sub-namespaces:

    | Attribute | Class |
    |---|---|
    | ``client.bibs.loans`` | [`AlmaClientBibLoansNS`][almapy._bibs.AlmaClientBibLoansNS] |
    | ``client.bibs.requests`` | [`AlmaClientBibRequestsNS`][almapy._bibs.AlmaClientBibRequestsNS] |

    Start with [`get_item`][almapy._bibs.AlmaClientBibNS.get_item] when all you have
    is a barcode: it resolves the MMS ID, holding ID and item PID that the other
    methods need.

    The holding and bib-record methods (``get_holding``, ``update_holding``,
    ``create_holding``, ``get_bib``, ``create_bib``, ``update_bib``) exchange raw
    MARC XML as ``str`` and take no ``model=`` argument. Everything else returns a
    ``Box``.
    """

    def __init__(self, client: "_AlmaExecutable") -> None:
        super().__init__(client)
        self.loans = AlmaClientBibLoansNS(client)
        self.requests = AlmaClientBibRequestsNS(client)

    @overload
    async def get_item(self, item_barcode: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_item(self, item_barcode: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_item(self, item_barcode: str, *, model: Any = None) -> Any:
        """Retrieve an item by its barcode.

        The usual entry point into this namespace: given only a barcode, the response
        carries the MMS ID, holding ID and item PID that the other methods need, along
        with the bib data and the item's current loan and request state.

        Args:
            item_barcode: The item's barcode.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The item record, with ``bib_data``, ``holding_data`` and ``item_data``.

        Raises:
            BarcodeNotFoundError: If no item has that barcode.
            IllegalBarcodeError: If the barcode is malformed.

        Examples:
            ```python
            item = await client.bibs.get_item("39001234567890")
            print(item.bib_data.title)
            mms_id = item.bib_data.mms_id
            holding_id = item.holding_data.holding_id
            item_pid = item.item_data.pid
            ```
        """
        return await self._get(
            AlmaEndpoint.BARCODE, model=model, params={"item_barcode": item_barcode}
        )

    @overload
    async def get_item_by_pid(
        self, mms_id: str, holding_id: str, item_pid: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_item_by_pid(
        self, mms_id: str, holding_id: str, item_pid: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_item_by_pid(
        self, mms_id: str, holding_id: str, item_pid: str, *, model: Any = None
    ) -> Any:
        """Retrieve an item by its full inventory path.

        Use [`get_item`][almapy._bibs.AlmaClientBibNS.get_item] when you have a
        barcode instead.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_pid: The item PID.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The item record, with ``bib_data``, ``holding_data`` and ``item_data``.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding or item does not exist.

        Examples:
            ```python
            item = await client.bibs.get_item_by_pid(
                "99123456789012345", "22123456780001234", "23123456770001234"
            )
            ```
        """
        return await self._get(
            AlmaEndpoint.ITEM,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
            model=model,
        )

    @overload
    async def create_item(
        self,
        mms_id: str,
        holding_id: str,
        item: Body,
        *,
        generate_description: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_item(
        self,
        mms_id: str,
        holding_id: str,
        item: Body,
        *,
        generate_description: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_item(
        self,
        mms_id: str,
        holding_id: str,
        item: Body,
        *,
        generate_description: bool = False,
        model: Any = None,
    ) -> Any:
        """Create an item under a holding.

        Being a POST, this call is **not replayed** if the response is lost in
        transit – a retry could create a duplicate item. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID to create the item under.
            item: The item record to create. ``item_data.barcode`` is normally
                required. Accepts a mapping or any object implementing
                ``dump``/``model_dump``.
            generate_description: Whether Alma should build the item's description
                from its enumeration and chronology fields.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created item record, including its assigned PID.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            InvalidCodeError: If a code in the item – its policy or material type,
                for instance – is not valid for this institution.
            APIClientError: If the holding does not exist or the barcode is in use.

        Examples:
            ```python
            item = await client.bibs.create_item(
                "99123456789012345",
                "22123456780001234",
                {"item_data": {"barcode": "39001234567890", "policy": {"value": "STANDARD"}}},
            )
            ```
        """
        return await self._post(
            AlmaEndpoint.ITEMS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            model=model,
            params={"generate_description": generate_description},
            json=item,
        )

    @overload
    async def update_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        item: Body,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def update_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        item: Body,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def update_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        item: Body,
        *,
        model: Any = None,
    ) -> Any:
        """Update an item.

        Alma replaces the whole item, so fetch it with
        [`get_item`][almapy._bibs.AlmaClientBibNS.get_item] or
        [`get_item_by_pid`][almapy._bibs.AlmaClientBibNS.get_item_by_pid] and modify
        that rather than sending a partial body.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_pid: The item PID.
            item: The full, modified item record.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated item record.

        Raises:
            InvalidCodeError: If a code in the item is not valid for this institution.
                Raised in place of the generic ``RequestFailedError`` so the offending
                field and value are named in the message.
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding or item does not exist.

        Examples:
            ```python
            item = await client.bibs.get_item("39001234567890")
            item.item_data.public_note = "Reference only"
            await client.bibs.update_item(
                item.bib_data.mms_id,
                item.holding_data.holding_id,
                item.item_data.pid,
                item,
            )
            ```
        """
        try:
            resp: Any = await self._put(
                AlmaEndpoint.ITEM,
                {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
                model=model,
                json=item,
            )
        except RequestFailedError as e:
            # e.error is Alma's raw message; e.message has " [401873]" appended,
            # which the greedy (?P<code>.+) would capture into the item code.
            m = re.match(r"Request failed: Invalid (?P<type>\w+) code: (?P<code>.+)", e.error)
            if m:
                msg = f"Invalid {m.group('type')} '{m.group('code')}'"
                raise InvalidCodeError(msg) from e
            raise
        return resp

    async def withdraw_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        override: bool = False,
        handle_holding: Literal["retain", "delete", "suppress"] = "retain",
        handle_bib: Literal["retain", "delete", "suppress"] = "retain",
    ) -> None:
        """Withdraw (delete) an item.

        ``handle_holding`` and ``handle_bib`` decide what happens to the now-empty
        parents. Both default to ``"retain"``, which leaves them in place – the
        conservative choice, and deliberately so: a bib record deleted here is gone
        along with everything attached to it.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_pid: The item PID.
            override: Whether to override Alma's warnings, for example when the item
                is on loan or has outstanding requests.
            handle_holding: What to do with the holding if this was its last item –
                ``"retain"``, ``"delete"`` or ``"suppress"``.
            handle_bib: What to do with the bib record if this was its last holding.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding or item does not exist, or Alma refuses
                the withdrawal and ``override`` is False.

        Examples:
            ```python
            await client.bibs.withdraw_item(
                "99123456789012345",
                "22123456780001234",
                "23123456770001234",
                handle_holding="delete",
            )
            ```
        """
        await self._delete(
            AlmaEndpoint.ITEM,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
            parser="none",
            params={"bib": handle_bib, "holdings": handle_holding, "override": override},
        )

    @overload
    async def get_items(
        self,
        mms_id: str,
        holding_id: str,
        expand: str | None = ...,
        user_id: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        current_library: str | None = ...,
        current_location: str | None = ...,
        q: str | None = ...,
        order_by: str | None = ...,
        direction: Literal["asc", "desc"] = ...,
        create_date_from: str | None = ...,
        create_date_to: str | None = ...,
        modify_date_from: str | None = ...,
        receive_date_from: str | None = ...,
        receive_date_to: str | None = ...,
        expected_receive_date_from: str | None = ...,
        expected_receive_date_to: str | None = ...,
        view: Literal["brief", "label"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_items(
        self,
        mms_id: str,
        holding_id: str,
        expand: str | None = ...,
        user_id: str | None = ...,
        limit: int = ...,
        offset: int = ...,
        current_library: str | None = ...,
        current_location: str | None = ...,
        q: str | None = ...,
        order_by: str | None = ...,
        direction: Literal["asc", "desc"] = ...,
        create_date_from: str | None = ...,
        create_date_to: str | None = ...,
        modify_date_from: str | None = ...,
        receive_date_from: str | None = ...,
        receive_date_to: str | None = ...,
        expected_receive_date_from: str | None = ...,
        expected_receive_date_to: str | None = ...,
        view: Literal["brief", "label"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_items(
        self,
        mms_id: str,
        holding_id: str,
        expand: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
        current_library: str | None = None,
        current_location: str | None = None,
        q: str | None = None,
        order_by: str | None = None,
        direction: Literal["asc", "desc"] = "desc",
        create_date_from: str | None = None,
        create_date_to: str | None = None,
        modify_date_from: str | None = None,
        receive_date_from: str | None = None,
        receive_date_to: str | None = None,
        expected_receive_date_from: str | None = None,
        expected_receive_date_to: str | None = None,
        view: Literal["brief", "label"] = "brief",
        *,
        model: Any = None,
    ) -> Any:
        """List the items under a holding.

        Pass ``holding_id="ALL"`` to list every item on the record regardless of
        holding. Arguments left as ``None`` are omitted from the query entirely
        rather than sent empty.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID, or ``"ALL"`` for every holding on the record.
            expand: Pass ``"due_date"`` or ``"due_date_policy"`` to have Alma
                calculate and include loan information per item.
            user_id: A user identifier to calculate the due-date policy against, used
                together with ``expand``.
            limit: Maximum number of items to return in this page. Note the default
                here is 10, not 100.
            offset: Index of the first item to return, for paging.
            current_library: Restrict to items currently at this library code.
            current_location: Restrict to items currently in this location code.
            q: Search query, in Alma's ``field~value`` form.
            order_by: Field to sort by.
            direction: Sort direction.
            create_date_from: Earliest creation date, as ``YYYY-MM-DD``.
            create_date_to: Latest creation date, as ``YYYY-MM-DD``.
            modify_date_from: Earliest modification date, as ``YYYY-MM-DD``.
            receive_date_from: Earliest receiving date, as ``YYYY-MM-DD``.
            receive_date_to: Latest receiving date, as ``YYYY-MM-DD``.
            expected_receive_date_from: Earliest expected receiving date.
            expected_receive_date_to: Latest expected receiving date.
            view: ``"brief"`` for the standard item data, ``"label"`` for the reduced
                set used when printing spine labels.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of items, with ``total_record_count`` giving the full result size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding does not exist or a date is malformed.

        Examples:
            Every item on a record, with due dates:

            ```python
            items = await client.bibs.get_items(
                "99123456789012345", "ALL", expand="due_date", limit=100
            )
            for item in items.item:
                print(item.item_data.barcode, item.item_data.base_status.desc)
            ```
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "expand": expand,
            "user_id": user_id,
            "current_library": current_library,
            "current_location": current_location,
            "q": q,
            "order_by": order_by,
            "direction": direction,
            "create_date_from": create_date_from,
            "create_date_to": create_date_to,
            "modify_date_from": modify_date_from,
            "receive_date_from": receive_date_from,
            "receive_date_to": receive_date_to,
            "expected_receive_date_from": expected_receive_date_from,
            "expected_receive_date_to": expected_receive_date_to,
            "view": view,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._get(
            AlmaEndpoint.ITEMS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            model=model,
            params=params,
        )

    @overload
    async def get_portfolios(
        self, mms_id: str, limit: int = ..., offset: int = ..., *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_portfolios(
        self, mms_id: str, limit: int = ..., offset: int = ..., *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_portfolios(
        self, mms_id: str, limit: int = 10, offset: int = 0, *, model: Any = None
    ) -> Any:
        """List the electronic portfolios on a bibliographic record.

        Portfolios are the electronic counterpart to physical items – the individual
        holdings of an e-resource within a collection.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            limit: Maximum number of portfolios to return in this page. Note the
                default here is 10, not 100.
            offset: Index of the first portfolio to return, for paging.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of portfolios, with ``total_record_count`` giving the full result
            size.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            portfolios = await client.bibs.get_portfolios("99123456789012345", limit=100)
            for p in portfolios.portfolio:
                print(p.id, p.electronic_collection.value)
            ```
        """
        params = {"limit": limit, "offset": offset}
        return await self._get(
            AlmaEndpoint.PORTFOLIOS, {"MMS_ID": mms_id}, model=model, params=params
        )

    async def get_holding(self, mms_id: str, holding_id: str) -> str:
        """Retrieve a holding record as raw MARC XML.

        Returns a ``str``, not a ``Box`` – Alma has no JSON representation of a MARC
        record – and so takes no ``model=`` argument. Parse the result with your own
        MARC or XML library.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID.

        Returns:
            The holding as a MARC XML string.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding does not exist.

        Examples:
            ```python
            xml = await client.bibs.get_holding("99123456789012345", "22123456780001234")
            ```
        """
        return await self._get_text(
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml"},
        )

    async def update_holding(self, mms_id: str, holding_id: str, record: str) -> str:
        """Replace a holding record with MARC XML.

        Takes and returns ``str``, not ``Box``. Alma replaces the whole record, so
        fetch it with [`get_holding`][almapy._bibs.AlmaClientBibNS.get_holding] and
        edit that XML rather than composing a partial document.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID.
            record: The complete holding record as a MARC XML string.

        Returns:
            The updated holding as a MARC XML string.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding does not exist, or the XML is malformed or
                fails Alma's validation.

        Examples:
            ```python
            xml = await client.bibs.get_holding("99123456789012345", "22123456780001234")
            updated = xml.replace("<subfield code='h'>QA76</subfield>", "<subfield code='h'>QA77</subfield>")
            await client.bibs.update_holding("99123456789012345", "22123456780001234", updated)
            ```
        """
        return await self._put_text(
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
            data=record,
        )

    async def create_holding(self, mms_id: str, record: str) -> str:
        """Create a holding on a bibliographic record from MARC XML.

        Takes and returns ``str``, not ``Box``.

        Being a POST, this call is **not replayed** if the response is lost in
        transit – a retry could create a duplicate holding. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            record: The holding record as a MARC XML string.

        Returns:
            The newly created holding as a MARC XML string, including its assigned
            holding ID.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the XML is malformed or fails Alma's validation.

        Examples:
            ```python
            xml = "<holding><record>...</record></holding>"
            created = await client.bibs.create_holding("99123456789012345", xml)
            ```
        """
        return await self._post_text(
            AlmaEndpoint.HOLDINGS,
            {"MMS_ID": mms_id},
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
            data=record,
        )

    async def delete_holding(
        self,
        mms_id: str,
        holding_id: str,
        *,
        handle_bib: Literal["retain", "delete", "suppress"] = "retain",
    ) -> None:
        """Delete a holding record.

        The holding must have no items left under it. ``handle_bib`` defaults to
        ``"retain"``, the conservative choice – deleting the bib record removes
        everything attached to it.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID.
            handle_bib: What to do with the bib record if this was its last holding –
                ``"retain"``, ``"delete"`` or ``"suppress"``.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding does not exist or still has items.

        Examples:
            ```python
            await client.bibs.delete_holding("99123456789012345", "22123456780001234")
            ```
        """
        await self._delete(
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            parser="none",
            params={"bib": handle_bib},
        )

    @overload
    async def get_holdings(self, mms_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_holdings(self, mms_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_holdings(self, mms_id: str, *, model: Any = None) -> Any:
        """List the holdings on a bibliographic record.

        Unlike the single-holding methods, this one returns a ``Box`` and accepts
        ``model=`` – it is a summary list rather than MARC records. Use
        [`get_holding`][almapy._bibs.AlmaClientBibNS.get_holding] for the MARC XML of
        one holding.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The record's holdings, each with its ID, library and location.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            holdings = await client.bibs.get_holdings("99123456789012345")
            for h in holdings.holding:
                print(h.holding_id, h.library.value, h.location.value)
            ```
        """
        return await self._get(AlmaEndpoint.HOLDINGS, {"MMS_ID": mms_id}, model=model)

    async def create_bib(
        self,
        record: str,
        *,
        from_nz_mms_id: str | None = None,
        from_cz_mms_id: str | None = None,
        normalization: str | None = None,
        validate: bool = False,
        override_warning: bool = False,
        check_match: bool = False,
        import_profile: str | None = None,
    ) -> str:
        """Create a bib record from the supplied MARC XML.

        Args:
            record: Full MARC XML record to create.
            from_nz_mms_id: Link the new bib to this Network Zone record.
            from_cz_mms_id: Link the new bib to this Community Zone record.
            normalization: Normalisation process ID to run on the record.
            validate: Run MARC validation before saving.
            override_warning: Save despite Alma's validation warnings – which
                include the duplicate-match warning raised by ``check_match``.
                Defaults to ``False``, but is only sent on the wire when it
                is ``True`` or when ``validate`` or ``check_match`` is on:
                Alma rejects an explicit ``false`` outside those cases (error
                401873), and with neither check running there is no warning
                to override anyway.
            check_match: Run match detection against existing records. Only has
                an effect while ``override_warning`` is ``False``.
            import_profile: Import profile ID governing the create.
        """
        params = _bib_write_params(
            validate=validate, override_warning=override_warning, check_match=check_match
        )
        if from_nz_mms_id:
            params["from_nz_mms_id"] = from_nz_mms_id
        if from_cz_mms_id:
            params["from_cz_mms_id"] = from_cz_mms_id
        if normalization:
            params["normalization"] = normalization
        if import_profile:
            params["import_profile"] = import_profile
        return await self._post_text(
            AlmaEndpoint.BIBS,
            data=record,
            params=params,
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
        )

    async def get_bib(
        self,
        mms_id: str,
        *,
        view: Literal["full", "brief", "local_fields"] = "full",
        expand_physical: bool = False,
        expand_electronic: bool = False,
        expand_digital: bool = False,
        expand_requests: bool = False,
    ) -> str:
        """Retrieve a bibliographic record as raw MARC XML.

        Returns a ``str``, not a ``Box`` – Alma has no JSON representation of a MARC
        record – and so takes no ``model=`` argument.

        The ``expand_*`` flags append availability information to the record. Each
        one makes Alma do extra work, so leave off the ones you do not need.

        Args:
            mms_id: The MMS ID of the bibliographic record.
            view: ``"full"`` for the complete record, ``"brief"`` for a reduced set of
                fields, ``"local_fields"`` for the institution's local fields only.
            expand_physical: Append physical holdings availability (``p_avail``).
            expand_electronic: Append electronic availability (``e_avail``).
            expand_digital: Append digital availability (``d_avail``).
            expand_requests: Append the record's request count.

        Returns:
            The bibliographic record as a MARC XML string.

        Raises:
            MMSIdNotFoundError: If no record has that MMS ID.

        Examples:
            ```python
            xml = await client.bibs.get_bib(
                "99123456789012345", expand_physical=True, expand_requests=True
            )
            ```
        """
        expand_params = []
        if expand_physical:
            expand_params.append("p_avail")
        if expand_electronic:
            expand_params.append("e_avail")
        if expand_digital:
            expand_params.append("d_avail")
        if expand_requests:
            expand_params.append("requests")

        expand_param_string = ",".join(expand_params)
        params: dict[str, str] = {"view": view}
        if expand_param_string:
            params["expand"] = expand_param_string

        return await self._get_text(
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            params=params,
            headers={"Accept": "application/xml"},
        )

    async def update_bib(
        self,
        mms_id: str,
        record: str,
        *,
        normalization: str | None = None,
        validate: bool = False,
        override_warning: bool = False,
        override_lock: bool = False,
        stale_version_check: bool = False,
        cataloguer_level: str | None = None,
        check_match: bool = False,
    ) -> str:
        """Update a bib record with the supplied MARC XML.

        Args:
            mms_id: MMS ID of the bib to update.
            record: Full MARC XML record to write.
            normalization: Normalisation process ID to run on the record.
            validate: Run MARC validation before saving.
            override_warning: Save despite Alma's validation warnings. Defaults
                to ``False``, but is only sent on the wire when it is ``True``
                or when ``validate`` or ``check_match`` is on – see
                [`create_bib`][almapy._bibs.AlmaClientBibNS.create_bib].
            override_lock: Save despite another cataloguer holding the record
                lock, discarding their in-progress edit. Defaults to ``False``.
            stale_version_check: Reject the update if the record changed since
                it was read.
            cataloguer_level: Cataloguer level to apply to the operation.
            check_match: Run match detection against existing records.
        """
        params = _bib_write_params(
            validate=validate, override_warning=override_warning, check_match=check_match
        )
        if normalization:
            params["normalization"] = normalization
        if override_lock:
            params["override_lock"] = override_lock
        if stale_version_check:
            params["stale_version_check"] = stale_version_check
        if cataloguer_level:
            params["cataloguer_level"] = cataloguer_level
        return await self._put_text(
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            data=record,
            params=params,
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
        )

    async def delete_bib(
        self,
        mms_id: str,
        *,
        override: bool = False,
        cataloguer_level: str | None = None,
    ) -> None:
        """Delete a bib record.

        Args:
            mms_id: MMS ID of the bib to delete.
            override: Delete even when Alma objects – e.g. the bib still has
                holdings, items or orders attached. Defaults to ``False`` so the
                shortest call cannot silently discard inventory.
            cataloguer_level: Cataloguer level to apply to the operation.
        """
        params: dict[str, str | bool] = {"override": override}
        if cataloguer_level:
            params["cataloguer_level"] = cataloguer_level
        await self._delete(
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            parser="none",
            params=params,
        )

    @overload
    async def scan_in(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        library: str | None = ...,
        department: str | None = ...,
        circ_desk: str | None = ...,
        work_order_type: str | None = ...,
        status: str | None = ...,
        external_id: bool = ...,
        request_id: str | None = ...,
        auto_print_slip: bool = ...,
        place_on_hold_shelf: bool = ...,
        confirm: bool = ...,
        register_in_house_use: bool = ...,
        done: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def scan_in(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        library: str | None = ...,
        department: str | None = ...,
        circ_desk: str | None = ...,
        work_order_type: str | None = ...,
        status: str | None = ...,
        external_id: bool = ...,
        request_id: str | None = ...,
        auto_print_slip: bool = ...,
        place_on_hold_shelf: bool = ...,
        confirm: bool = ...,
        register_in_house_use: bool = ...,
        done: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def scan_in(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        library: str | None = None,
        department: str | None = None,
        circ_desk: str | None = None,
        work_order_type: str | None = None,
        status: str | None = None,
        external_id: bool = False,
        request_id: str | None = None,
        auto_print_slip: bool = False,
        place_on_hold_shelf: bool = False,
        confirm: bool = False,
        register_in_house_use: bool = False,
        done: bool = False,
        model: Any = None,
    ) -> Any:
        """Scan an item in at a circulation desk or work department.

        The API equivalent of passing an item over the desk: returns it if it is on
        loan, and moves it to its next workflow step – onto the hold shelf, into
        transit, or back to the shelf.

        Supply **either** ``circ_desk`` with ``library`` (a circulation desk scan) or
        ``department`` with ``work_order_type`` (a work department scan), not both.

        Being a POST, this call is **not replayed** if the response is lost in
        transit. See [Rate limiting](../guide/rate-limiting.md).

        Args:
            mms_id: The MMS ID of the bibliographic record.
            holding_id: The holding ID the item belongs to.
            item_pid: The item PID.
            library: Code of the library owning the circulation desk.
            department: Code of the work department scanning the item in.
            circ_desk: Code of the circulation desk scanning the item in.
            work_order_type: The work order type, when scanning into a department.
            status: The work order status to move the item to.
            external_id: Whether ``request_id`` is an external identifier rather than
                an Alma one.
            request_id: Identifier of the request this scan fulfils.
            auto_print_slip: Whether Alma should generate the transit or hold slip.
            place_on_hold_shelf: Whether to place the item on the hold shelf for a
                waiting request.
            confirm: Whether to confirm Alma's scan-in messages, such as a transit
                prompt.
            register_in_house_use: Whether to record the scan as in-house use rather
                than a return.
            done: Whether the work order step is complete, releasing the item from
                the department.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The item record in its post-scan state, including any transit or hold
            instructions Alma generated.

        Raises:
            ScanItemRetrievalError: If the scan succeeded but Alma did not return the
                item information (code ``402504``).
            MMSIdNotFoundError: If no record has that MMS ID.
            APIClientError: If the holding or item does not exist, or the desk,
                library or department codes are not valid.

        Examples:
            ```python
            item = await client.bibs.get_item("39001234567890")
            scanned = await client.bibs.scan_in(
                item.bib_data.mms_id,
                item.holding_data.holding_id,
                item.item_data.pid,
                library="MAIN",
                circ_desk="DEFAULT",
                auto_print_slip=True,
            )
            ```
        """
        params: dict[str, Any] = {
            "op": "scan",
            "library": library,
            "department": department,
            "work_order_type": work_order_type,
            "circ_desk": circ_desk,
            "status": status,
            "done": done,
            "external_id": external_id,
            "request_id": request_id,
            "auto_print_slip": auto_print_slip,
            "place_on_hold_shelf": place_on_hold_shelf,
            "confirm": confirm,
            "register_in_house_use": register_in_house_use,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._post(
            AlmaEndpoint.ITEM,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
            model=model,
            params=params,
        )
