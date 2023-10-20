from typing import Any, Dict, Optional, Union

import re

from box import Box
from httpx import AsyncClient

from almapy.client import Client
from almapy.exceptions import APIClientError, RequestFailedError
from almapy.users import CannotRenewError
from almapy.utils import Request


class InvalidCodeError(APIClientError):
    def __init__(self, msg: str) -> None:
        super().__init__("401873", msg)
        self.message = msg

    def __str__(self):
        return self.message


class SubClientBibs(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/bibs"
        self.loans = SubClientBibLoans(session, self.con_params, rate_limit)
        self.requests = SubClientBibRequests(session, self.con_params, rate_limit)

    async def get_item(self, item_barcode: str) -> Union[Box, str]:
        response = await self.__get_req__("/almaws/v1/items", params={"item_barcode": item_barcode})
        return response

    async def update_item(
        self, mms_id: str, holding_id: str, item_pid: str, item: Dict[str, Any], xml: bool = False
    ) -> Union[Box, str]:
        url = f"/almaws/v1/bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}"
        try:
            if not xml:
                assert isinstance(item, Box)
                response = await self.__put_req__(url, item)
                return response
            else:
                assert isinstance(item, str)
                response = await self.__put_req__(url, item, xml=True)
            return response
        except RequestFailedError as e:
            m = re.match(r"Request failed: Invalid (?P<type>\w+) code: (?P<code>.+)", e.message)
            if m:
                raise InvalidCodeError(f"Invalid {m.group('type')} '{m.group('code')}'") from e
            else:
                raise

    async def get_items(
        self,
        mms_id: str,
        holding_id: str,
        expand: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        current_library: Optional[str] = None,
        current_location: Optional[str] = None,
        q: Optional[str] = None,
        order_by: Optional[str] = None,
        direction: Optional[str] = "desc",
        create_date_from: Optional[str] = None,
        create_date_to: Optional[str] = None,
        modify_date_from: Optional[str] = None,
        receive_date_from: Optional[str] = None,
        receive_date_to: Optional[str] = None,
        expected_receive_date_from: Optional[str] = None,
        expected_receive_date_to: Optional[str] = None,
        view: Optional[str] = "brief",
    ) -> Union[Box, str]:
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
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/" f"{holding_id}/items",
            params=params,
        )

        return response

    async def get_portfolios(self, mms_id: str, limit: int = 10, offset: int = 0) -> Union[Box, str]:
        params = {"limit": limit, "offset": offset}
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/portfolios",
            params=params,
        )
        return response

    async def get_holding(self, mms_id: str, holding_id: str) -> str:
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}",
            xml=True,
        )
        return response

    async def update_holding(self, mms_id: str, holding_id: str, record: str) -> str:
        response = await self.__put_req__(f"/almaws/v1/bibs/{mms_id}/holdings/{holding_id}", data=record, xml=True)
        return response

    async def scan_in(
        self,
        mms_id: str,
        holding_id: str,
        item_pid: str,
        *,
        library: Optional[str] = None,
        department: Optional[str] = None,
        circ_desk: Optional[str] = None,
        work_order_type: Optional[str] = None,
        status: Optional[str] = None,
        external_id: bool = False,
        request_id: Optional[str] = None,
        auto_print_slip: bool = False,
        place_on_hold_shelf: bool = False,
        confirm: bool = False,
        register_in_house_use: bool = False,
        done: bool = False,
        xml: bool = False,
    ) -> Union[Box, str]:
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
        response = await self.__post_req__(
            f"/almaws/v1/bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}", params=params, xml=xml
        )
        return response


class SubClientBibLoans(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/bibs"

    async def get_loans(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "due_date",
        direction: str = "asc",
        loan_status: str = "Active",
    ) -> Box:
        if loan_status not in ["Active", "Complete"]:
            raise ValueError("loan_status must be 'Active' or 'Complete'")
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}/items/{item_id}/loans", params=params
        )
        return response

    async def create_loan(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        circ_desk: str,
        library: str,
        request_id: Optional[str] = None,
    ) -> Box:
        loan = Box({"circ_desk": {"value": circ_desk}, "library": {"value": library}})
        if request_id:
            loan.request_id = {"value": request_id}
        response = await self.__post_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}/items/{item_id}/loans",
            data=loan,
            params={"user_id": user_id},
        )
        return response

    async def get_loan(self, mms_id: str, holding_id: str, item_id: str, loan_id: str) -> Box:
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/" f"{holding_id}/items/{item_id}/loans/{loan_id}"
        )
        return response

    async def renew_loan(self, mms_id: str, holding_id: str, item_id: str, loan_id: str) -> Box:
        try:
            response = await self.__post_req__(
                f"{self.con_params['api_endpoint']}/{mms_id}/holdings/" f"{holding_id}/items/{item_id}/loans/{loan_id}",
                params={"op": "renew"},
            )
            return response
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            else:
                raise

    async def change_loan_due_date(
        self, mms_id: str, holding_id: str, item_id: str, loan_id: str, due_date: str
    ) -> Box:
        loan = Box({"due_date": due_date})
        response = await self.__put_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/" f"{holding_id}/items/{item_id}/loans/{loan_id}",
            data=loan,
        )
        return response

    async def get_bib_loans(
        self,
        mms_id: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "due_date",
        direction: str = "asc",
        loan_status: str = "Active",
    ) -> Box:
        if loan_status not in ["Active", "Complete"]:
            raise ValueError("loan_status must be 'Active' or 'Complete'")
        params = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "direction": direction,
            "loan_status": loan_status,
        }
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{mms_id}/loans", params=params)
        return response

    async def get_bib_loan(self, mms_id: str, loan_id: str) -> Box:
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{mms_id}/loans/{loan_id}")
        return response


class SubClientBibRequests(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/bibs"

    async def get_requests(
        self, mms_id: str, holding_id: str, item_id: str, request_type: str = "all_types", status: str = "active"
    ):
        if request_type not in ["all_types", "HOLD", "DIGITIZATION", "BOOKING"]:
            raise ValueError("request_type must be 'all_types', 'HOLD', 'DIGITIZATION' or 'BOOKING'")
        params = {"request_type": request_type, "status": status}

        return await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}/items/{item_id}/requests", params=params
        )

    async def cancel_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        request_id: str,
        reason: str,
        notify_user: bool,
        note: Optional[str] = None,
    ):
        params = {"reason": reason, "note": note, "notify_user": notify_user}
        await self.__delete_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}/items/{item_id}/requests/{request_id}",
            params=params,
        )

    async def create_request(
        self,
        mms_id: str,
        holding_id: str,
        item_id: str,
        user_id: str,
        request: Request,
        user_id_type: str = "all_unique",
        allow_same_request: bool = False,
    ):
        params = {"user_id": user_id, "user_id_type": user_id_type, "allow_same_request": allow_same_request}
        return await self.__post_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}/items/{item_id}/requests",
            params=params,
            data=request,
        )
