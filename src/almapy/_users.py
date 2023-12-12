from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gracy import Gracy, GracyNamespace

from almapy._endpoints import AlmaEndpoint
from almapy.exceptions import (
    APIClientError,
    CannotRenewError,
    UserMissingFieldError,
    UserNotFoundError,
)

if TYPE_CHECKING:
    from almapy._utils import RESP_TYPE, Request


class AlmaClientUserLoansNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for user loan functionality, exposed at AlmaClient.user.loans."""

    async def get_loans(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = "due_date",
        direction: Literal["asc", "desc"] = "asc",
        expand: Literal["renewable"] | None = None,
        loan_status: Literal["Active", "Complete"] = "Active",
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.USER_LOANS,
            {"USER_ID": user_id},
            params={
                "limit": limit,
                "offset": offset,
                "order_by": order_by,
                "direction": direction,
                "expand": expand,
                "loan_status": loan_status,
            },
        )
        return resp

    async def create_loan(
        self,
        user_id: str,
        item_barcode: str,
        circ_desk: str,
        library: str,
        request_id: str | None = None,
    ) -> RESP_TYPE:
        body = {"circ_desk": {"value": circ_desk}, "library": {"value": library}}
        if request_id:
            body["request_id"] = {"value": request_id}
        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.USER_LOANS,
            {"USER_ID": user_id},
            params={"item_barcode": item_barcode},
            json=body,
        )
        return resp

    async def get_loan(self, user_id: str, loan_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.USER_LOAN, {"USER_ID": user_id, "LOAN_ID": loan_id}
        )
        return resp

    async def renew_loan(self, user_id: str, loan_id: str) -> RESP_TYPE:
        try:
            resp: RESP_TYPE = await self.post(
                AlmaEndpoint.USER_LOAN,
                {"USER_ID": user_id, "LOAN_ID": loan_id},
                params={"op": "renew"},
            )
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            raise
        return resp

    async def change_loan_due_date(
        self, user_id: str, loan_id: str, due_date: str, *, notify_user: bool = False
    ) -> RESP_TYPE:
        body = {"due_date": due_date}
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.USER_LOAN,
            {"USER_ID": user_id, "LOAN_ID": loan_id},
            params={"notify_user": notify_user},
            json=body,
        )
        return resp


class AlmaClientUserFinesNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for user fines functionality, exposed at AlmaClient.user.fines."""

    async def get_fines(
        self,
        user_id: str,
        user_id_type: str = "all_unique",
        status: Literal["ACTIVE", "INDISPUTE", "EXPORTED", "CLOSED"] = "ACTIVE",
    ) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.USER_FEES,
            {"USER_ID": user_id},
            {"user_id_type": user_id_type, "status": status},
        )
        return resp


class AlmaClientUserRequestsNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for user requests, exposed at AlmaClient.user.requests."""

    async def get_request(self, user_id: str, request_id: str) -> RESP_TYPE:
        resp: RESP_TYPE = await self.get(
            AlmaEndpoint.USER_REQUEST, {"USER_ID": user_id, "REQUEST_ID": request_id}
        )
        return resp

    async def create_request(
        self,
        user_id: str,
        request: Request,
        user_id_type: str = "all_unique",
        *,
        allow_same_request: bool = False,
        mms_id: str,
        item_id: str,
    ) -> RESP_TYPE:
        if (mms_id and item_id) or (not mms_id and not item_id):
            msg = "must provide exactly one of mms_id or item_id"
            raise ValueError(msg)
        params = {"user_id_type": user_id_type, "allow_same_request": allow_same_request}
        if mms_id:
            params["mms_id"] = mms_id
        if item_id:
            params["item_id"] = item_id

        resp: RESP_TYPE = await self.post(
            AlmaEndpoint.USER_REQUESTS, {"USER_ID": user_id}, params=params, json=request
        )
        return resp

    async def update_request(self, user_id: str, request_id: str, request: Request) -> RESP_TYPE:
        resp: RESP_TYPE = await self.put(
            AlmaEndpoint.USER_REQUEST, {"USER_ID": user_id, "REQUEST_ID": request_id}, json=request
        )
        return resp


class AlmaClientUserNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for user functionality, exposing a number of sub-namespace via attrs.

    - loans
    - fines
    - requests
    """

    def __init__(self, parent: Gracy[AlmaEndpoint], **kwargs: Any):
        super().__init__(parent, **kwargs)
        self.loans = AlmaClientUserLoansNS(parent)
        self.fines = AlmaClientUserFinesNS(parent)
        self.requests = AlmaClientUserRequestsNS(parent)

    async def get_users(
        self,
        limit: int = 10,
        offset: int = 0,
        *,
        q: str | None = None,
        order_by: Literal["last_name", "first_name", "primary_id"] | None = None,
        expand: bool = False,
    ) -> RESP_TYPE:
        params = {"limit": limit, "offset": offset, expand: expand}
        if q:
            params["q"] = q
        if order_by:
            params["order_by"] = order_by
        resp: RESP_TYPE = await self.get(AlmaEndpoint.USERS, params=params)
        return resp

    async def get_user(self, user_id: str) -> RESP_TYPE:
        """Get user information by user ID.

        Args:
            user_id (str): The ID of the user.

        Returns:
            Dict[str, Any]: The user dict

        Raises:
            UserNotFoundError: If the user identifier is not found.
            APIClientError: If another error occurred while making the API request.
        """
        try:
            resp: RESP_TYPE = await self.get(AlmaEndpoint.USER, {"USER_ID": user_id})
        except APIClientError as e:
            if e.code == "401861":
                raise UserNotFoundError(e.error, user_id) from e
            raise
        return resp

    async def update_user(self, user_id: str, user: dict[str, Any]) -> RESP_TYPE:
        """Update a user.

        Args:
            user_id (str): The ID of the user to be updated.
            user (Dict[str, Any]): The updated user object.

        Returns:
            Dict[str, Any]: The user dict

        Raises:
            UserMissingFieldError: In case of missing mandatory fields.
            APIClientError: If any other API client error occurs.
        """
        try:
            resp: RESP_TYPE = await self.put(AlmaEndpoint.USER, {"USER_ID": user_id}, json=user)
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user_id) from e
            raise
        return resp

    async def create_user(self, user: dict[str, Any]) -> RESP_TYPE:
        """Create a new user.

        Args:
            user (Dict[str, Any]): The user object to be create.

        Returns:
            Dict[str, Any]: The user dict

        Raises:
            UserMissingFieldError: In case of missing mandatory fields.
            APIClientError: If any other API client error occurs.
        """
        try:
            resp: RESP_TYPE = await self.post(AlmaEndpoint.USERS, json=user)
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user["primary_id"]) from e
            raise
        return resp
