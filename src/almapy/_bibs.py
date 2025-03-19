from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal

from gracy import Gracy, GracyNamespace, graceful

from almapy._endpoints import AlmaEndpoint
from almapy.exceptions import APIClientError, CannotRenewError, InvalidCodeError, RequestFailedError

if TYPE_CHECKING:
    from almapy._utils import RESP_TYPE, Request


class AlmaClientBibLoansNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for bib requests, exposed at AlmaClient.bibs.requests."""

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
    ) -> RESP_TYPE:
        """Retrieves loans for a specific item.

        Args:
            mms_id (str): The item's parent bib record MMS ID.
            holding_id (str): The item's parent holding record ID.
            item_id (str): The item PID.
            limit (int, optional): The maximum number of loans to return. Defaults to 100.
            offset (int, optional): The number of loans to skip. Defaults to 0.
            order_by (str, optional): The field by which to sort the returned loans.
                Options are "loan_date", "due_date", "barcode", "title", "author" and "return_date".
                Defaults to "due_date".
            direction (str, optional): The direction in which to sort the returned loans.
                Options are "asc" and "desc".
                Defaults to "asc".
            loan_status (str, optional): The status of the loans to return.
                Options are "Active" and "Complete".
                Defaults to "Active".

        Returns:
            Dict[str, Any]: A response dict with the requested loan information.

        Raises:
            APIClientError: If there is an error with the input.
            APIServerError: If there is an error with the server.

        """
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEM_LOANS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            params=params,
        )
        return resp

    async def create_loan(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        circ_desk: str,
        library: str,
        request_id: str | None = None,
    ) -> RESP_TYPE:
        """Creates a loan for a specific copy of an item.

        Args:
            mms_id (str): The item's parent bib record MMS ID.
            holding_id (str): The item's parent holding record ID.
            item_id (str): The item PID.
            user_id (str): The user identifier.
            circ_desk (str): The circulation desk from which to loan the item.
            library (str): The library at which to loan the item.
            request_id (str, optional): The request identifier associated with the loan, if any.

        Returns:
            Dict[str, Any]: A response dict with the requested loan information.

        Raises:
            APIClientError: If there is an error with the input.
            APIServerError: If there is an error with the server.

        """
        loan = {"circ_desk": {"value": circ_desk}, "library": {"value": library}}
        if request_id:
            loan["request_id"] = {"value": request_id}
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.ITEM_LOANS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            json=loan,
            params={"user_id": user_id},
        )
        return resp

    async def get_loan(self, mms_id: str, holding_id: str, item_id: str, loan_id: str) -> RESP_TYPE:
        """Get the details of a specific loan on a specific copy of an item.

        Args:
            mms_id (str): The item's parent bib record MMS ID.
            holding_id (str): The item's parent holding record ID.
            item_id (str): The item PID.
            loan_id (str): The loan ID.

        Returns:
            Dict[str, Any]: A response dict with the requested loan information.

        Raises:
            APIClientError: If there is an error with the input.
            APIServerError: If there is an error with the server.

        """
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEM_LOAN,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id, "LOAN_ID": loan_id},
        )
        return resp

    async def renew_loan(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str
    ) -> RESP_TYPE:
        """Renew a loan on a specific copy of an item.

        Args:
            mms_id (str): The item's parent bib record MMS ID.
            holding_id (str): The item's parent holding record ID.
            item_id (str): The item PID.
            loan_id (str): The loan ID.

        Returns:
            Dict[str, Any]: The updated loan information.

        Raises:
            CannotRenewError: If the item cannot be renewed for any reason.
            APIClientError: If there is an error with the input.
            APIServerError: If there is an error with the server.

        """
        try:
            resp: RESP_TYPE = await self.post(
                AlmaEndpoint.ITEM_LOAN,
                {
                    "MMS_ID": mms_id,
                    "HOLDING_ID": holding_id,
                    "ITEM_PID": item_id,
                    "LOAN_ID": loan_id,
                },
                params={"op": "renew"},
            )
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            raise
        return resp

    async def change_loan_due_date(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, due_date: str
    ) -> RESP_TYPE:
        """Changes the due date of a loan on a specific copy of an item.

        Args:
            mms_id (str): The item's parent bib record MMS ID.
            holding_id (str): The item's parent holding record ID.
            item_id (str): The item PID.
            loan_id (str): The loan ID.
            due_date (str): Due date in the format YYYY-MM-DD.

        Returns:
            Dict[str, Any]: The updated loan information.

        Raises:
            CannotRenewError: If the item cannot be renewed for any reason.
            APIClientError: If there is an error with the input.
            APIServerError: If there is an error with the server.

        """
        loan = {"due_date": due_date}
        resp: RESP_TYPE = await self.put(
            AlmaEndpoint.ITEM_LOAN,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id, "LOAN_ID": loan_id},
            json=loan,
        )
        return resp

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
    ) -> RESP_TYPE:
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        resp: RESP_TYPE = await self.get(AlmaEndpoint.BIB_LOANS, {"MMS_ID": mms_id}, params=params)
        return resp

    async def get_bib_loan(self, mms_id: str, loan_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.BIB_LOAN, {"MMS_ID": mms_id, "LOAN_ID": loan_id}
        )
        return resp


class AlmaClientBibRequestsNS(GracyNamespace[AlmaEndpoint]):
    async def get_requests(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = "all_types",
        status: Literal["active", "history"] = "active",
    ) -> RESP_TYPE:
        params = {"request_type": request_type, "status": status}
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEM_REQUESTS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            params=params,
        )
        return resp

    get_requests_for_item = get_requests

    async def get_requests_for_bib(
        self,
        mms_id: str,
        request_type: Literal["all_types", "HOLD", "DIGITIZATION", "BOOKING"] = "all_types",
        status: Literal["active", "history"] = "active",
    ) -> RESP_TYPE:
        params = {"request_type": request_type, "status": status}
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.BIB_REQUESTS,
            {"MMS_ID": mms_id},
            params=params,
        )
        return resp

    async def get_request(
        self, mms_id: str, holding_id: str, item_id: str, request_id: str
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEM_REQUEST,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
                "ITEM_PID": item_id,
                "REQUEST_ID": request_id,
            },
        )
        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda _: True, "default": lambda _: False})
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
    ) -> bool:
        params = {"reason": reason, "notify_user": notify_user}
        if note:
            params["note"] = note
        resp: bool = await self.delete(
            AlmaEndpoint.ITEM_REQUEST,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
                "ITEM_PID": item_id,
                "REQUEST_ID": request_id,
            },
            params=params,
        )
        return resp

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
    ) -> RESP_TYPE:
        params = {
            "user_id": user_id,
            "user_id_type": user_id_type,
            "allow_same_request": allow_same_request,
        }
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.ITEM_REQUESTS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_id},
            params=params,
            json=request,
        )
        return resp


class AlmaClientBibNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for user functionality, exposing a number of sub-namespace via attrs.

    - loans
    - requests
    """

    def __init__(self, parent: Gracy[AlmaEndpoint], **kwargs: Any):
        super().__init__(parent, **kwargs)
        self.loans = AlmaClientBibLoansNS(parent)
        self.requests = AlmaClientBibRequestsNS(parent)

    async def get_item(self, item_barcode: str) -> RESP_TYPE:
        """Get item information by barcode.

        Args:
            item_barcode (str): The item barcode.

        Returns:
            Dict[str, Any]: The item dict

        Raises:
            APIClientError: If an error occurred while making the API request.
        """
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.BARCODE, params={"item_barcode": item_barcode}
        )
        return resp

    async def get_item_by_pid(self, mms_id: str, holding_id: str, item_pid: str) -> RESP_TYPE:
        """Get item information by barcode.

        Args:
            mms_id (str): The MMS ID.
            holding_id (str): The Holding ID.
            item_pid (str): The Item PID.

        Returns:
            Dict[str, Any]: The item dict

        Raises:
            APIClientError: If an error occurred while making the API request.
        """
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEM, {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid}
        )
        return resp

    async def create_item(
        self,
        mms_id: str,
        holding_id: str,
        item: dict[str, Any],
        *,
        generate_description: bool = False,
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.ITEMS,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            params={"generate_description": generate_description},
            json=item,
        )
        return resp

    async def update_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        item: dict[str, Any],
    ) -> RESP_TYPE:
        """Get item information by barcode.

        Args:
            mms_id (str): The MMS ID.
            holding_id (str): The Holding ID.
            item_pid (str): The Item PID.
            item (Dict[str, Any]): The updated item data.

        Returns:
            Dict[str, Any]: The item dict

        Raises:
            InvalidCodeError: If a field contained an invalid code (e.g. Library).
            APIClientError: If another error occurred while making the API request.
        """
        try:
            resp: RESP_TYPE = await self.put(
                AlmaEndpoint.ITEM,
                {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
                json=item,
            )
        except RequestFailedError as e:
            m = re.match(r"Request failed: Invalid (?P<type>\w+) code: (?P<code>.+)", e.message)
            if m:
                msg = f"Invalid {m.group('type')} '{m.group('code')}'"
                raise InvalidCodeError(msg) from e
            raise
        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda _: True, "default": lambda _: False})
    async def withdraw_item(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        override: bool = False,
        handle_holding: Literal["retain", "delete", "suppress"] = "retain",
        handle_bib: Literal["retain", "delete", "suppress"] = "retain",
    ) -> bool:
        resp: bool = await self.delete(
            AlmaEndpoint.ITEM,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
            params={"bib": handle_bib, "holdings": handle_holding, "override": override},
        )
        return resp

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
    ) -> RESP_TYPE:
        params = {
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
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.ITEMS, {"MMS_ID": mms_id, "HOLDING_ID": holding_id}, params=params
        )
        return resp

    async def get_portfolios(self, mms_id: str, limit: int = 10, offset: int = 0) -> RESP_TYPE:
        params = {"limit": limit, "offset": offset}
        resp: RESP_TYPE = await self.get(AlmaEndpoint.PORTFOLIOS, {"MMS_ID": mms_id}, params=params)
        return resp

    @graceful(
        parser={
            "default": lambda r: r.text,
        },
    )
    async def get_holding(self, mms_id: str, holding_id: str) -> str:
        resp: str = await self.get[str](
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml"},
        )
        return resp

    @graceful(
        parser={
            "default": lambda r: r.text,
        },
    )
    async def update_holding(self, mms_id: str, holding_id: str, record: str) -> str:
        resp: str = await self.put[str](
            AlmaEndpoint.HOLDING,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id},
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
            content=record,
        )
        return resp

    @graceful(
        parser={
            "default": lambda r: r.text,
        },
    )
    async def create_holding(self, mms_id: str, record: str) -> str:
        resp: str = await self.post[str](
            AlmaEndpoint.HOLDINGS,
            {"MMS_ID": mms_id},
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
            content=record,
        )
        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda _: True, "default": lambda _: False})
    async def delete_holding(
        self,
        mms_id: str,
        holding_id: str,
        *,
        handle_bib: Literal["retain", "delete", "suppress"] = "retain",
    ):
        resp: bool = await self.delete(
            AlmaEndpoint.HOLDING,
            {
                "MMS_ID": mms_id,
                "HOLDING_ID": holding_id,
            },
            params={"bib": handle_bib},
        )
        return resp

    async def get_holdings(self, mms_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(AlmaEndpoint.HOLDINGS, {"MMS_ID": mms_id})
        return resp

    @graceful(parser={"default": lambda r: r.text})
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

        resp: str = await self.post[str](
            AlmaEndpoint.BIBS,
            {},
            content=record,
            params=params,
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
        )
        return resp

    @graceful(
        parser={
            "default": lambda r: r.text,
        },
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
        params = {"view": view}
        if expand_param_string:
            params["expand"] = expand_param_string

        resp: str = await self.get[str](
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            params=params,
            headers={"Accept": "application/xml"},
        )
        return resp

    @graceful(parser={"default": lambda r: r.text})
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

        resp: str = await self.put[str](
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            content=record,
            params=params,
            headers={"Accept": "application/xml", "Content-Type": "application/xml"},
        )
        return resp

    @graceful(parser={HTTPStatus.NO_CONTENT: lambda _: True, "default": lambda _: False})
    async def delete_bib(
        self,
        mms_id: str,
        *,
        override: bool = True,
        cataloguer_level: str | None = None,
    ) -> bool:
        params: dict[str, str | bool] = {"override": override}
        if cataloguer_level:
            params["cataloguer_level"] = cataloguer_level

        resp: bool = await self.delete(
            AlmaEndpoint.BIB,
            {"MMS_ID": mms_id},
            params=params,
        )
        return resp

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
    ) -> RESP_TYPE:
        params = {
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
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.ITEM,
            {"MMS_ID": mms_id, "HOLDING_ID": holding_id, "ITEM_PID": item_pid},
            params=params,
        )
        return resp
