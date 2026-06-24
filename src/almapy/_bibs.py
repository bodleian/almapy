import re
from typing import TYPE_CHECKING, Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, Request, _ModelT
from almapy.exceptions import APIClientError, CannotRenewError, InvalidCodeError, RequestFailedError

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


class AlmaClientBibLoansNS(BaseNamespace):
    """Namespace for bib requests, exposed at AlmaClient.bibs.requests."""

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
        return await self._get(
            AlmaEndpoint.BIB_LOAN, {"MMS_ID": mms_id, "LOAN_ID": loan_id}, model=model
        )


class AlmaClientBibRequestsNS(BaseNamespace):
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
        params = {"request_type": request_type, "status": status}
        return await self._get(
            AlmaEndpoint.ITEM_REQUESTS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            model=model,
            params=params,
        )

    get_requests_for_item = get_requests

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
    """Namespace for user functionality, exposing a number of sub-namespace via attrs.

    - loans
    - requests
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
        """Get item information by barcode."""
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
        """Get item information by PID."""
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
        """Update item data."""
        try:
            resp: Any = await self._put(
                AlmaEndpoint.ITEM,
                {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
                model=model,
                json=item,
            )
        except RequestFailedError as e:
            m = re.match(r"Request failed: Invalid (?P<type>\w+) code: (?P<code>.+)", e.message)
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
        params = {"limit": limit, "offset": offset}
        return await self._get(
            AlmaEndpoint.PORTFOLIOS, {"MMS_ID": mms_id}, model=model, params=params
        )

    async def get_holding(self, mms_id: str, holding_id: str) -> str:
        return await self._get_text(
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml"},
        )

    async def update_holding(self, mms_id: str, holding_id: str, record: str) -> str:
        return await self._put_text(
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
            data=record,
        )

    async def create_holding(self, mms_id: str, record: str) -> str:
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
        return await self._get(AlmaEndpoint.HOLDINGS, {"MMS_ID": mms_id}, model=model)

    async def create_bib(
        self,
        record: str,
        *,
        from_nz_mms_id: str | None = None,
        from_cz_mms_id: str | None = None,
        normalization: str | None = None,
        validate: bool = False,
        override_warning: bool = True,
        check_match: bool = False,
        import_profile: str | None = None,
    ) -> str:
        params: dict[str, str | bool] = {
            "validate": validate,
            "override_warning": override_warning,
            "check_match": check_match,
        }
        if from_nz_mms_id:
            params["from_nz_mms_id"] = from_nz_mms_id
        if from_cz_mms_id:
            params["to_cz_mms_id"] = from_cz_mms_id
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
        override_warning: bool = True,
        override_lock: bool = True,
        stale_version_check: bool = False,
        cataloguer_level: str | None = None,
        check_match: bool = False,
    ) -> str:
        params: dict[str, str | bool] = {
            "validate": validate,
            "override_warning": override_warning,
            "check_match": check_match,
        }
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
        override: bool = True,
        cataloguer_level: str | None = None,
    ) -> None:
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
