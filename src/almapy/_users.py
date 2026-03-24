import base64
from typing import TYPE_CHECKING, Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Request, _ModelT
from almapy.exceptions import (
    APIClientError,
    CannotRenewError,
    UserMissingFieldError,
)

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


class AlmaClientUserLoansNS(BaseNamespace):
    """Namespace for user loan functionality, exposed at AlmaClient.user.loans."""

    @overload
    async def get_loans(
        self,
        user_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        expand: Literal["renewable"] | None = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_loans(
        self,
        user_id: str,
        limit: int = ...,
        offset: int = ...,
        order_by: Literal[
            "loan_date", "due_date", "barcode", "title", "author", "return_date"
        ] = ...,
        direction: Literal["asc", "desc"] = ...,
        expand: Literal["renewable"] | None = ...,
        loan_status: Literal["Active", "Complete"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

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
        *,
        model: Any = None,
    ) -> Any:
        return await self._get(
            AlmaEndpoint.USER_LOANS,
            {"USER_ID": user_id},
            model=model,
            params={
                "limit": limit,
                "offset": offset,
                "order_by": order_by,
                "direction": direction,
                "expand": expand,
                "loan_status": loan_status,
            },
        )

    @overload
    async def create_loan(
        self,
        user_id: str,
        item_barcode: str,
        circ_desk: str,
        library: str,
        request_id: str | None = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_loan(
        self,
        user_id: str,
        item_barcode: str,
        circ_desk: str,
        library: str,
        request_id: str | None = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_loan(
        self,
        user_id: str,
        item_barcode: str,
        circ_desk: str,
        library: str,
        request_id: str | None = None,
        *,
        model: Any = None,
    ) -> Any:
        body = {"circ_desk": {"value": circ_desk}, "library": {"value": library}}
        if request_id:
            body["request_id"] = {"value": request_id}
        return await self._post(
            AlmaEndpoint.USER_LOANS,
            {"USER_ID": user_id},
            model=model,
            params={"item_barcode": item_barcode},
            json=body,
        )

    @overload
    async def get_loan(self, user_id: str, loan_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_loan(self, user_id: str, loan_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_loan(self, user_id: str, loan_id: str, *, model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.USER_LOAN, {"USER_ID": user_id, "LOAN_ID": loan_id}, model=model
        )

    @overload
    async def renew_loan(self, user_id: str, loan_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def renew_loan(self, user_id: str, loan_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def renew_loan(self, user_id: str, loan_id: str, *, model: Any = None) -> Any:
        try:
            resp: Any = await self._post(
                AlmaEndpoint.USER_LOAN,
                {"USER_ID": user_id, "LOAN_ID": loan_id},
                params={"op": "renew"},
                model=model,
            )
        except APIClientError as e:
            if e.code == "401822":
                raise CannotRenewError(e.error, loan_id) from e
            raise
        return resp

    @overload
    async def change_loan_due_date(
        self,
        user_id: str,
        loan_id: str,
        due_date: str,
        *,
        notify_user: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def change_loan_due_date(
        self,
        user_id: str,
        loan_id: str,
        due_date: str,
        *,
        notify_user: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def change_loan_due_date(
        self,
        user_id: str,
        loan_id: str,
        due_date: str,
        *,
        notify_user: bool = False,
        model: Any = None,
    ) -> Any:
        body = {"due_date": due_date}
        return await self._put(
            AlmaEndpoint.USER_LOAN,
            {"USER_ID": user_id, "LOAN_ID": loan_id},
            model=model,
            params={"notify_user": notify_user},
            json=body,
        )


class AlmaClientUserFinesNS(BaseNamespace):
    """Namespace for user fines functionality, exposed at AlmaClient.user.fines."""

    @overload
    async def get_fines(
        self,
        user_id: str,
        user_id_type: str = ...,
        status: Literal["ACTIVE", "INDISPUTE", "EXPORTED", "CLOSED"] = ...,
        *,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_fines(
        self,
        user_id: str,
        user_id_type: str = ...,
        status: Literal["ACTIVE", "INDISPUTE", "EXPORTED", "CLOSED"] = ...,
        *,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_fines(
        self,
        user_id: str,
        user_id_type: str = "all_unique",
        status: Literal["ACTIVE", "INDISPUTE", "EXPORTED", "CLOSED"] = "ACTIVE",
        *,
        model: Any = None,
    ) -> Any:
        return await self._get(
            AlmaEndpoint.USER_FEES,
            {"USER_ID": user_id},
            model=model,
            params={"user_id_type": user_id_type, "status": status},
        )

    get_fees = get_fines

    @overload
    async def create_fee(
        self, user_id: str, fine: dict[str, Any], *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def create_fee(
        self, user_id: str, fine: dict[str, Any], *, model: None = ...
    ) -> RESP_TYPE: ...

    async def create_fee(self, user_id: str, fine: dict[str, Any], *, model: Any = None) -> Any:
        return await self._post(
            AlmaEndpoint.USER_FEES, {"USER_ID": user_id}, model=model, json=fine
        )

    @overload
    async def pay_fees(
        self,
        user_id: str,
        *,
        user_id_type: str = ...,
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"],
        comment: str | None = ...,
        external_transaction_id: str | None = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def pay_fees(
        self,
        user_id: str,
        *,
        user_id_type: str = ...,
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"],
        comment: str | None = ...,
        external_transaction_id: str | None = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def pay_fees(
        self,
        user_id: str,
        *,
        user_id_type: str = "all_unique",
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"],
        comment: str | None = None,
        external_transaction_id: str | None = None,
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {
            "op": "pay",
            "user_id_type": user_id_type,
            "amount": amount,
            "method": method,
        }
        if comment:
            params["comment"] = comment
        if external_transaction_id:
            params["external_transaction_id"] = external_transaction_id
        return await self._post(
            AlmaEndpoint.USER_FEES_ALL, {"USER_ID": user_id}, model=model, params=params
        )

    @overload
    async def get_fee(
        self, user_id: str, fee_id: str, *, user_id_type: str = ..., model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_fee(
        self, user_id: str, fee_id: str, *, user_id_type: str = ..., model: None = ...
    ) -> RESP_TYPE: ...

    async def get_fee(
        self, user_id: str, fee_id: str, *, user_id_type: str = "all_unique", model: Any = None
    ) -> Any:
        return await self._get(
            AlmaEndpoint.USER_FEE,
            {"USER_ID": user_id, "FEE_ID": fee_id},
            model=model,
            params={"user_id_type": user_id_type},
        )

    @overload
    async def update_fee(
        self,
        user_id: str,
        fee_id: str,
        *,
        op: Literal["pay", "waive", "dispute", "restore"],
        user_id_type: str = ...,
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"] | None = ...,
        reason: str | None = ...,
        comment: str | None = ...,
        external_transaction_id: str | None = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def update_fee(
        self,
        user_id: str,
        fee_id: str,
        *,
        op: Literal["pay", "waive", "dispute", "restore"],
        user_id_type: str = ...,
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"] | None = ...,
        reason: str | None = ...,
        comment: str | None = ...,
        external_transaction_id: str | None = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def update_fee(
        self,
        user_id: str,
        fee_id: str,
        *,
        op: Literal["pay", "waive", "dispute", "restore"],
        user_id_type: str = "all_unique",
        amount: float,
        method: Literal["CREDIT_CARD", "ONLINE", "CASH"] | None = None,
        reason: str | None = None,
        comment: str | None = None,
        external_transaction_id: str | None = None,
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {
            "op": op,
            "user_id_type": user_id_type,
            "amount": amount,
            "method": method,
        }
        if reason:
            params["reason"] = reason
        if comment:
            params["comment"] = comment
        if external_transaction_id:
            params["external_transaction_id"] = external_transaction_id
        return await self._post(
            AlmaEndpoint.USER_FEE,
            {"USER_ID": user_id, "FEE_ID": fee_id},
            model=model,
            params=params,
            json={},
        )


class AlmaClientUserRequestsNS(BaseNamespace):
    """Namespace for user requests, exposed at AlmaClient.user.requests."""

    @overload
    async def get_request(
        self, user_id: str, request_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_request(
        self, user_id: str, request_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_request(self, user_id: str, request_id: str, *, model: Any = None) -> Any:
        return await self._get(
            AlmaEndpoint.USER_REQUEST,
            {"USER_ID": user_id, "REQUEST_ID": request_id},
            model=model,
        )

    @overload
    async def get_requests(
        self,
        user_id: str,
        *,
        request_type: Literal["HOLD", "DIGITIZATION", "BOOKING"] | None = ...,
        user_id_type: str = ...,
        limit: int = ...,
        offset: int = ...,
        status: Literal["active", "history"] = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_requests(
        self,
        user_id: str,
        *,
        request_type: Literal["HOLD", "DIGITIZATION", "BOOKING"] | None = ...,
        user_id_type: str = ...,
        limit: int = ...,
        offset: int = ...,
        status: Literal["active", "history"] = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_requests(
        self,
        user_id: str,
        *,
        request_type: Literal["HOLD", "DIGITIZATION", "BOOKING"] | None = None,
        user_id_type: str = "all_unique",
        limit: int = 10,
        offset: int = 0,
        status: Literal["active", "history"] = "active",
        model: Any = None,
    ) -> Any:
        params: dict[str, Any] = {
            "user_id_type": user_id_type,
            "offset": offset,
            "limit": limit,
            "status": status,
        }
        if request_type:
            params["request_type"] = request_type
        return await self._get(
            AlmaEndpoint.USER_REQUESTS, {"USER_ID": user_id}, model=model, params=params
        )

    @overload
    async def create_request(
        self,
        user_id: str,
        request: Request,
        user_id_type: str = ...,
        *,
        allow_same_request: bool = ...,
        mms_id: str = ...,
        item_id: str = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_request(
        self,
        user_id: str,
        request: Request,
        user_id_type: str = ...,
        *,
        allow_same_request: bool = ...,
        mms_id: str = ...,
        item_id: str = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_request(
        self,
        user_id: str,
        request: Request,
        user_id_type: str = "all_unique",
        *,
        allow_same_request: bool = False,
        mms_id: str = "",
        item_id: str = "",
        model: Any = None,
    ) -> Any:
        if bool(mms_id) == bool(item_id):
            msg = "must provide exactly one of mms_id or item_id"
            raise ValueError(msg)

        params: dict[str, Any] = {
            "user_id_type": user_id_type,
            "allow_same_request": allow_same_request,
        } | ({"mms_id": mms_id} if mms_id else {"item_id": item_id})

        return await self._post(
            AlmaEndpoint.USER_REQUESTS,
            {"USER_ID": user_id},
            model=model,
            params=params,
            json=request,
        )

    @overload
    async def update_request(
        self, user_id: str, request_id: str, request: Request, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_request(
        self, user_id: str, request_id: str, request: Request, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_request(
        self, user_id: str, request_id: str, request: Request, *, model: Any = None
    ) -> Any:
        return await self._put(
            AlmaEndpoint.USER_REQUEST,
            {"USER_ID": user_id, "REQUEST_ID": request_id},
            model=model,
            json=request,
        )

    async def cancel_request(
        self,
        user_id: str,
        request_id: str,
        reason: str,
        *,
        notify_user: bool,
        note: str | None = None,
    ) -> bool:
        params: dict[str, Any] = {"reason": reason, "notify_user": notify_user}
        if note:
            params["note"] = note
        await self._delete(
            AlmaEndpoint.USER_REQUEST,
            {"USER_ID": user_id, "REQUEST_ID": request_id},
            parser="none",
            params=params,
        )
        return True


class AlmaClientUserNS(BaseNamespace):
    """Namespace for user functionality, exposing a number of sub-namespaces via attrs.

    - loans
    - fees
    - requests
    """

    def __init__(self, client: "_AlmaExecutable") -> None:
        super().__init__(client)
        self.loans = AlmaClientUserLoansNS(client)
        self.fines = AlmaClientUserFinesNS(client)
        self.fees = self.fines
        self.requests = AlmaClientUserRequestsNS(client)

    @overload
    async def get_users(
        self,
        limit: int = ...,
        offset: int = ...,
        *,
        q: str | None = ...,
        order_by: Literal["last_name", "first_name", "primary_id"] | None = ...,
        expand: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def get_users(
        self,
        limit: int = ...,
        offset: int = ...,
        *,
        q: str | None = ...,
        order_by: Literal["last_name", "first_name", "primary_id"] | None = ...,
        expand: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def get_users(
        self,
        limit: int = 10,
        offset: int = 0,
        *,
        q: str | None = None,
        order_by: Literal["last_name", "first_name", "primary_id"] | None = None,
        expand: bool = False,
        model: Any = None,
    ) -> Any:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        if order_by:
            params["order_by"] = order_by
        if expand:
            params["expand"] = "full"
        return await self._get(AlmaEndpoint.USERS, model=model, params=params)

    @overload
    async def get_user(self, user_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def get_user(self, user_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def get_user(self, user_id: str, *, model: Any = None) -> Any:
        """Get user information by user ID.

        Args:
            user_id (str): The ID of the user.

        Returns:
            Dict[str, Any]: The user dict

        Raises:
            UserNotFoundError: If the user identifier is not found.
            APIClientError: If another error occurred while making the API request.
        """
        return await self._get(AlmaEndpoint.USER, {"USER_ID": user_id}, model=model)

    @overload
    async def update_user(
        self, user_id: str, user: dict[str, Any], *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def update_user(
        self, user_id: str, user: dict[str, Any], *, model: None = ...
    ) -> RESP_TYPE: ...

    async def update_user(self, user_id: str, user: dict[str, Any], *, model: Any = None) -> Any:
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
            resp: Any = await self._put(
                AlmaEndpoint.USER, {"USER_ID": user_id}, model=model, json=user
            )
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user_id) from e
            raise
        return resp

    @overload
    async def create_user(self, user: dict[str, Any], *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def create_user(self, user: dict[str, Any], *, model: None = ...) -> RESP_TYPE: ...

    async def create_user(self, user: dict[str, Any], *, model: Any = None) -> Any:
        """Create a new user.

        Args:
            user (Dict[str, Any]): The user object to be created.

        Returns:
            Dict[str, Any]: The user dict

        Raises:
            UserMissingFieldError: In case of missing mandatory fields.
            APIClientError: If any other API client error occurs.
        """
        try:
            resp: Any = await self._post(AlmaEndpoint.USERS, model=model, json=user)
        except APIClientError as e:
            if e.code == "401664":
                raise UserMissingFieldError(e.error, user["primary_id"]) from e
            raise
        return resp

    @overload
    async def create_user_attachment(
        self,
        user_id: str,
        file_name: str,
        content: str,
        *,
        note: str = ...,
        description: str = ...,
        url: str = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def create_user_attachment(
        self,
        user_id: str,
        file_name: str,
        content: str,
        *,
        note: str = ...,
        description: str = ...,
        url: str = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def create_user_attachment(
        self,
        user_id: str,
        file_name: str,
        content: str,
        *,
        note: str = "",
        description: str = "",
        url: str = "",
        model: Any = None,
    ) -> Any:
        encoded_content = base64.b64encode(bytes(content, "utf-8")).decode("utf-8")
        attachment = {
            "file_name": file_name,
            "content": encoded_content,
            "description": description,
            "note": note,
            "url": url,
        }
        return await self._post(
            AlmaEndpoint.USER_ATTACHMENTS, {"USER_ID": user_id}, model=model, json=attachment
        )
