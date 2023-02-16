from typing import Any, Dict, Optional

from httpx import AsyncClient

from almapy.client import Client


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

    async def get_item(self, item_barcode: str):
        response = await self.__get_req__("/almaws/v1/items", params={"item_barcode": item_barcode})
        return response

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
    ):
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

    async def get_portfolios(self, mms_id: str, limit: int = 10, offset: int = 0):
        params = {"limit": limit, "offset": offset}
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/portfolios",
            params=params,
        )
        return response

    async def get_holding(self, mms_id: str, holding_id: str):
        response = await self.__get_req__(
            f"{self.con_params['api_endpoint']}/{mms_id}/holdings/{holding_id}",
            xml=True,
        )
        return response

    async def update_holding(self, mms_id: str, holding_id: str, record):
        response = await self.__put_req__(f"/almaws/v1/bibs/{mms_id}/holdings/{holding_id}", data=record, xml=True)
        return response
