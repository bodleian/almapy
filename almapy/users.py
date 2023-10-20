from typing import Any, Dict, Literal, Optional, Union, overload

from box import Box
from httpx import AsyncClient

from almapy.client import Client
from almapy.utils import APIClientError, Request


class UserMissingFieldError(APIClientError):
    def __init__(self, msg: str, user_id: str) -> None:
        super().__init__("401664", msg)
        self.user_id = user_id
        self.message = msg

    def __str__(self):
        return self.message


class CannotRenewError(APIClientError):
    def __init__(self, msg: str, loan_id: str) -> None:
        super().__init__("401822", msg)
        self.loan_id = loan_id
        self.message = msg

    def __str__(self):
        return self.message


class UserNotFoundError(APIClientError):
    def __init__(self, msg: str, user_id: str) -> None:
        super().__init__("401861", msg)
        self.user_id = user_id
        self.message = msg

    def __str__(self):
        return self.message


class SubClientUserLoans(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/users"

    async def get_loans(
        self, user_id: str, limit: int = 100, offset: int = 0, order_by: str = "due_date", direction: str = "asc"
    ) -> Box:
        params = {"limit": limit, "offset": offset, "order_by": order_by, "direction": direction}
        try:
            response = await self.__get_req__(
                f"{self.con_params['api_endpoint']}/{user_id}/loans",
                params=params,
            )
            return response
        except APIClientError as e:
            if e.code == "401861":
                raise UserNotFoundError(e.error, user_id) from e
            else:
                raise

    async def create_loan(
        self, user_id: str, item_barcode: str, circ_desk: str, library: str, request_id: Optional[str] = None
    ) -> Box:
        loan = Box({"circ_desk": {"value": circ_desk}, "library": {"value": library}})
        if request_id:
            loan.request_id = {"value": request_id}
        response = await self.__post_req__(
            f"{self.con_params['api_endpoint']}/{user_id}/loans",
            data=loan,
            params={"item_barcode": item_barcode},
        )
        return response

    async def get_loan(self, user_id: str, loan_id: str) -> Box:
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}")
        return response

    async def renew_loan(self, user_id: str, loan_id: str) -> Box:
        try:
            response = await self.__post_req__(
                f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}", params={"op": "renew"}
            )
            return response
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            else:
                raise

    async def change_loan_due_date(self, user_id: str, loan_id: str, due_date: str, notify_user: bool = False) -> Box:
        loan = Box({"due_date": due_date})
        response = await self.__put_req__(
            f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}",
            data=loan,
            params={"notify_user": notify_user},
        )
        return response


class SubClientUserRequests(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/users"

    async def get_request(self, user_id: str, request_id: str, xml: bool = False) -> Union[Box, str]:
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}/requests/{request_id}", xml=xml)
        return response

    async def create_request(
        self,
        user_id: str,
        request: Request,
        user_id_type: str = "all_unique",
        allow_same_request: bool = False,
        *,
        mms_id: str,
        item_id: str,
    ):
        if (mms_id and item_id) or (not mms_id and not item_id):
            raise ValueError("must provide exactly one of mms_id or item_id")
        params = {"mms_id": mms_id, "user_id_type": user_id_type, "allow_same_request": allow_same_request}
        return await self.__post_req__(
            f"{self.con_params['api_endpoint']}/{user_id}/requests",
            params=params,
            data=request,
        )


class SubClientUsers(Client):
    def __init__(self, session: AsyncClient, con_params: Dict[str, Any], rate_limit: int = 20) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/users"
        self.loans = SubClientUserLoans(session, self.con_params, rate_limit)
        self.requests = SubClientUserRequests(session, self.con_params, rate_limit)

    async def get_user(self, user_id: str, xml: bool = False) -> Union[Box, str]:
        try:
            response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}", xml=xml)
            return response
        except APIClientError as e:
            if e.code == "401861":
                raise UserNotFoundError(e.error, user_id) from e
            else:
                raise

    @overload
    async def update_user(self, user_id: str, user: str, xml: Literal[True]) -> str:
        ...

    @overload
    async def update_user(self, user_id: str, user: Box, xml: Literal[False]) -> Box:
        ...

    @overload
    async def update_user(self, user_id: str, user: Box) -> Box:
        ...

    async def update_user(self, user_id: str, user: Union[str, Box], xml: bool = False) -> Union[Box, str]:
        url = f"{self.con_params['api_endpoint']}/{user_id}"
        try:
            if not xml:
                assert isinstance(user, Box)
                response = await self.__put_req__(url, user)
                return response
            else:
                assert isinstance(user, str)
                response = await self.__put_req__(url, user, xml=True)
            return response
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user_id) from e
            else:
                raise

    async def create_user(self, user: Union[str, Box], xml: bool = False) -> Union[Box, str]:
        url = f"{self.con_params['api_endpoint']}"
        try:
            if not xml:
                assert isinstance(user, Box)
                response = await self.__post_req__(url, user)
                return response
            else:
                assert isinstance(user, str)
                response = await self.__post_req__(url, user, xml=True)
            return response
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user.primary_identifier) from e
            else:
                raise
