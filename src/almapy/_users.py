"""User and patron namespaces.

Reached as ``client.users``, which carries three sub-namespaces alongside its own
user-record methods:

| Attribute | Covers |
|---|---|
| ``client.users.loans`` | Loans held by a user — listing, creating, renewing |
| ``client.users.fines`` (alias ``client.users.fees``) | Fines and fees, and paying them |
| ``client.users.requests`` | Holds, digitisation and booking requests |
"""

import base64
from typing import TYPE_CHECKING, Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, Body, Request, _dump_body, _ModelT
from almapy.exceptions import (
    APIClientError,
    CannotRenewError,
    UserMissingFieldError,
)

if TYPE_CHECKING:
    from almapy._base import _AlmaExecutable


class AlmaClientUserLoansNS(BaseNamespace):
    """Namespace for user loan functionality, exposed at ``client.users.loans``.

    Loans reached through a user. The same loans are also addressable through their
    bibliographic record via ``client.bibs.loans``, which is the route to take when
    you know the item but not the borrower.
    """

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
        """List a user's loans.

        Args:
            user_id: The user identifier.
            limit: Maximum number of loans to return in this page.
            offset: Index of the first loan to return, for paging.
            order_by: Field to sort by.
            direction: Sort direction.
            expand: Pass ``"renewable"`` to have Alma calculate and include each
                loan's renewability. This costs Alma extra work, so it is off by
                default.
            loan_status: ``"Active"`` for loans still out, ``"Complete"`` for
                returned ones.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of loans, with ``total_record_count`` giving the full result size.

        Raises:
            UserNotFoundError: If no user matches the identifier.

        Examples:
            ```python
            loans = await client.users.loans.get_loans(
                "12345678", expand="renewable", order_by="due_date"
            )
            for loan in loans.item_loan:
                print(loan.title, loan.due_date, loan.renewable)
            ```
        """
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
        """Loan an item to a user.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could create a duplicate loan. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier of the borrower.
            item_barcode: Barcode of the item to loan.
            circ_desk: Code of the circulation desk the loan is made at, as returned
                by ``client.config.libraries.get_circ_desks()``.
            library: Code of the library owning that circulation desk.
            request_id: Identifier of a request being fulfilled by this loan, when
                the loan satisfies an existing hold.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created loan record, including its ``loan_id`` and ``due_date``.

        Raises:
            BarcodeNotFoundError: If no item has that barcode.
            IllegalBarcodeError: If the barcode is malformed.
            UserNotFoundError: If no user matches the identifier.
            LoanLimitError: If the user is already at their simultaneous-loan limit.
            LoanBlockedError: If a block on the user prevents the loan.
            ParallelLoanError: If the user already has another copy of this title out.
            ItemAlreadyLoanedToUserError: If this item is already on loan to them.
            ExpiredCardError: If the user's card has expired.
            CannotBeLoanedError: If the item cannot be loaned from this desk.
            UserIsNotAPatronError: If the user has no active patron role.

        Examples:
            ```python
            loan = await client.users.loans.create_loan(
                "12345678", "39001234567890", circ_desk="DEFAULT", library="MAIN"
            )
            print(loan.loan_id, loan.due_date)
            ```
        """
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
        """Retrieve a single loan held by a user.

        Args:
            user_id: The user identifier.
            loan_id: The loan identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The loan record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            LoanNotFoundError: If the user has no loan with that ID.

        Examples:
            ```python
            loan = await client.users.loans.get_loan("12345678", "987654321")
            ```
        """
        return await self._get(
            AlmaEndpoint.USER_LOAN, {"USER_ID": user_id, "LOAN_ID": loan_id}, model=model
        )

    @overload
    async def renew_loan(self, user_id: str, loan_id: str, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def renew_loan(self, user_id: str, loan_id: str, *, model: None = ...) -> RESP_TYPE: ...

    async def renew_loan(self, user_id: str, loan_id: str, *, model: Any = None) -> Any:
        """Renew a loan.

        Args:
            user_id: The user identifier.
            loan_id: The loan identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The renewed loan record, carrying its new ``due_date``.

        Raises:
            CannotRenewError: If Alma refused the renewal (code ``401822``) — because
                the item is requested by someone else, the renewal limit is reached,
                or a block applies. The exception carries the ``loan_id`` and Alma's
                own reason.
            UserNotFoundError: If no user matches the identifier.
            LoanNotFoundError: If the user has no loan with that ID.

        Examples:
            ```python
            from almapy.exceptions import CannotRenewError

            try:
                loan = await client.users.loans.renew_loan("12345678", "987654321")
                print("renewed to", loan.due_date)
            except CannotRenewError as e:
                print("refused:", e.error)
            ```
        """
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
        """Change a loan's due date.

        Args:
            user_id: The user identifier.
            loan_id: The loan identifier.
            due_date: The new due date, in ISO 8601 form with a ``Z`` suffix, e.g.
                ``"2026-09-30Z"``.
            notify_user: Whether Alma should send the user a notification about the
                change.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated loan record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            LoanNotFoundError: If the user has no loan with that ID.
            APIClientError: If the date is malformed or in the past.

        Examples:
            ```python
            loan = await client.users.loans.change_loan_due_date(
                "12345678", "987654321", "2026-09-30Z", notify_user=True
            )
            ```
        """
        body = {"due_date": due_date}
        return await self._put(
            AlmaEndpoint.USER_LOAN,
            {"USER_ID": user_id, "LOAN_ID": loan_id},
            model=model,
            params={"notify_user": notify_user},
            json=body,
        )


class AlmaClientUserFinesNS(BaseNamespace):
    """Namespace for user fines functionality, exposed at ``client.users.fines``.

    Also available as ``client.users.fees`` — Alma's own API calls these "fees"
    throughout, so both spellings are provided and refer to the same object.

    Two ways to settle a balance:
    [`pay_fees`][almapy._users.AlmaClientUserFinesNS.pay_fees] pays against the
    user's whole account at once, while
    [`update_fee`][almapy._users.AlmaClientUserFinesNS.update_fee] acts on one
    individual fee and can also waive, dispute or restore it.
    """

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
        """List a user's fines and fees.

        Also callable as ``client.users.fines.get_fees(...)``.

        Args:
            user_id: The user identifier.
            user_id_type: Which kind of identifier ``user_id`` is. Defaults to
                ``"all_unique"``, matching against any of the user's unique IDs.
            status: ``"ACTIVE"`` for outstanding fees, ``"CLOSED"`` for settled ones,
                ``"INDISPUTE"`` for disputed, ``"EXPORTED"`` for those sent to an
                external bursar system.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The user's fees, with ``total_sum`` giving the balance across them.

        Raises:
            UserNotFoundError: If no user matches the identifier.

        Examples:
            ```python
            fines = await client.users.fines.get_fines("12345678")
            print("owes", fines.total_sum)
            for fee in fines.fee:
                print(fee.id, fee.type.desc, fee.balance)
            ```
        """
        return await self._get(
            AlmaEndpoint.USER_FEES,
            {"USER_ID": user_id},
            model=model,
            params={"user_id_type": user_id_type, "status": status},
        )

    get_fees = get_fines
    """Alias for [`get_fines`][almapy._users.AlmaClientUserFinesNS.get_fines]."""

    @overload
    async def create_fee(self, user_id: str, fine: Body, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def create_fee(self, user_id: str, fine: Body, *, model: None = ...) -> RESP_TYPE: ...

    async def create_fee(self, user_id: str, fine: Body, *, model: Any = None) -> Any:
        """Charge a fee to a user.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could charge the user twice. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier.
            fine: The fee record to create. Requires at least a ``type`` from the
                ``FineFeeTypes`` code table and an ``original_amount``. Accepts a
                mapping or any object implementing ``dump``/``model_dump``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created fee record, including its assigned ``id``.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the fee type is not valid or the amount is missing.

        Examples:
            ```python
            fee = await client.users.fines.create_fee(
                "12345678",
                {
                    "type": {"value": "LOSTITEMREPLACEMENTFEE"},
                    "original_amount": 25.00,
                    "comment": "Replacement charge",
                },
            )
            ```
        """
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
        """Pay against a user's whole fee balance.

        Alma applies the payment across the user's active fees rather than to any one
        of them. To act on a single fee — or to waive rather than pay — use
        [`update_fee`][almapy._users.AlmaClientUserFinesNS.update_fee].

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could take the payment twice. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier.
            user_id_type: Which kind of identifier ``user_id`` is.
            amount: The amount to pay, in the institution's currency.
            method: How the payment was taken.
            comment: Free-text note recorded against the transaction.
            external_transaction_id: Reference from the payment provider, for
                reconciling against an external system.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The user's remaining fees after the payment is applied.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the amount exceeds the outstanding balance or the
                method is not enabled for this institution.

        Examples:
            ```python
            remaining = await client.users.fines.pay_fees(
                "12345678",
                amount=12.50,
                method="CREDIT_CARD",
                external_transaction_id="txn_9f2c",
            )
            ```
        """
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
        """Retrieve a single fee.

        Args:
            user_id: The user identifier.
            fee_id: The fee identifier.
            user_id_type: Which kind of identifier ``user_id`` is.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The fee record, including its ``original_amount``, ``balance`` and any
            transactions against it.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the user has no fee with that ID.

        Examples:
            ```python
            fee = await client.users.fines.get_fee("12345678", "987654321")
            print(fee.balance, fee.status.value)
            ```
        """
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
        """Pay, waive, dispute or restore a single fee.

        The counterpart to [`pay_fees`][almapy._users.AlmaClientUserFinesNS.pay_fees],
        which works across the user's whole balance instead.

        Being a POST, this call is **not replayed** if the response is lost in
        transit. See [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier.
            fee_id: The fee identifier.
            op: What to do — ``"pay"`` settles it, ``"waive"`` cancels the charge,
                ``"dispute"`` marks it as contested, ``"restore"`` reverses a
                previous waiver or dispute.
            user_id_type: Which kind of identifier ``user_id`` is.
            amount: The amount to act on. May be less than the balance for a partial
                payment or waiver.
            method: How the payment was taken. Required for ``op="pay"``, ignored
                otherwise.
            reason: Justification code, required for ``op="waive"``. Values come from
                the ``PaymentAndWaiveReasons`` code table.
            comment: Free-text note recorded against the transaction.
            external_transaction_id: Reference from the payment provider.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated fee record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the fee does not exist, the amount exceeds its
                balance, or a required argument for the chosen ``op`` is missing.

        Examples:
            Waive a fee in full:

            ```python
            fee = await client.users.fines.get_fee("12345678", "987654321")
            await client.users.fines.update_fee(
                "12345678",
                "987654321",
                op="waive",
                amount=float(fee.balance),
                reason="LIBRARYERROR",
                comment="Item was returned on time",
            )
            ```
        """
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
    """Namespace for user requests, exposed at ``client.users.requests``.

    Requests are holds, digitisation requests and bookings placed on behalf of a
    user. The same requests can also be reached from the bibliographic side via
    ``client.bibs.requests``, which is where to look when starting from a record
    rather than a borrower.
    """

    @overload
    async def get_request(
        self, user_id: str, request_id: str, *, model: type[_ModelT]
    ) -> _ModelT: ...

    @overload
    async def get_request(
        self, user_id: str, request_id: str, *, model: None = ...
    ) -> RESP_TYPE: ...

    async def get_request(self, user_id: str, request_id: str, *, model: Any = None) -> Any:
        """Retrieve a single request placed by a user.

        Args:
            user_id: The user identifier.
            request_id: The request identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The request record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the user has no request with that ID.

        Examples:
            ```python
            req = await client.users.requests.get_request("12345678", "987654321")
            print(req.request_status, req.pickup_location)
            ```
        """
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
        """List the requests placed by a user.

        Args:
            user_id: The user identifier.
            request_type: Restrict to one kind of request. All kinds are returned
                when omitted.
            user_id_type: Which kind of identifier ``user_id`` is.
            limit: Maximum number of requests to return in this page. Note the
                default here is 10, not 100.
            offset: Index of the first request to return, for paging.
            status: ``"active"`` for outstanding requests, ``"history"`` for
                completed and cancelled ones.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of requests, with ``total_record_count`` giving the full result
            size.

        Raises:
            UserNotFoundError: If no user matches the identifier.

        Examples:
            ```python
            reqs = await client.users.requests.get_requests(
                "12345678", request_type="HOLD", limit=100
            )
            for req in reqs.user_request:
                print(req.request_id, req.title, req.request_status)
            ```
        """
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
        """Place a request on behalf of a user.

        A request is placed against **either** a bibliographic record or a specific
        item, never both: pass exactly one of ``mms_id`` and ``item_id``. A title
        level request (``mms_id``) lets Alma pick any suitable copy; an item level
        request (``item_id``) pins it to one.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could place a duplicate request. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier.
            request: The request to create. Requires at least ``request_type`` and,
                for holds, a ``pickup_location_type`` and ``pickup_location_library``.
            user_id_type: Which kind of identifier ``user_id`` is.
            allow_same_request: Whether to permit a second request when the user
                already has one on this title.
            mms_id: MMS ID for a title level request.
            item_id: Item PID for an item level request.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created request record, including its ``request_id``.

        Raises:
            ValueError: If both or neither of ``mms_id`` and ``item_id`` are given.
                Raised locally, before any request is made.
            RequestFailedError: If Alma rejected the request (code ``401873``).
            NoItemsCanFulfillRequestError: If no item can satisfy it (code ``401129``).
            ParallelRequestError: If the user already has a request on another copy
                and ``allow_same_request`` is False.
            UserNotFoundError: If no user matches the identifier.
            MMSIdNotFoundError: If the MMS ID does not exist.

        Examples:
            ```python
            req = await client.users.requests.create_request(
                "12345678",
                {
                    "request_type": "HOLD",
                    "pickup_location_type": "LIBRARY",
                    "pickup_location_library": "MAIN",
                },
                mms_id="99123456789012345",
            )
            ```
        """
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
        """Update a request.

        Alma replaces the whole request, so fetch it with
        [`get_request`][almapy._users.AlmaClientUserRequestsNS.get_request] and modify
        that rather than sending a partial body. Not every field is editable — the
        pickup location and expiry date generally are; the request type is not.

        Args:
            user_id: The user identifier.
            request_id: The request identifier.
            request: The full, modified request record.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated request record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the request does not exist, or a field that cannot be
                changed was modified.

        Examples:
            ```python
            req = await client.users.requests.get_request("12345678", "987654321")
            req.pickup_location_library = "SCIENCE"
            await client.users.requests.update_request("12345678", "987654321", req)
            ```
        """
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
    ) -> None:
        """Cancel a request placed by a user.

        Args:
            user_id: The user identifier.
            request_id: The request identifier.
            reason: Cancellation reason. Must be a code from the
                ``RequestCancellationReasons`` code table — fetch the valid values
                with ``client.config.code_tables.get_code_table()``.
            notify_user: Whether Alma should notify the user of the cancellation.
            note: Free-text note included in the notification.

        Returns:
            ``None``. Alma returns an empty body on success.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the request does not exist, is already fulfilled, or
                the reason code is not valid.

        Examples:
            ```python
            await client.users.requests.cancel_request(
                "12345678",
                "987654321",
                reason="CannotBeFulfilled",
                notify_user=True,
                note="Item is now missing",
            )
            ```
        """
        params: dict[str, Any] = {"reason": reason, "notify_user": notify_user}
        if note:
            params["note"] = note
        await self._delete(
            AlmaEndpoint.USER_REQUEST,
            {"USER_ID": user_id, "REQUEST_ID": request_id},
            parser="none",
            params=params,
        )


class AlmaClientUserNS(BaseNamespace):
    """Namespace for user functionality, exposed at ``client.users``.

    Carries the user-record methods themselves, plus three sub-namespaces:

    | Attribute | Class |
    |---|---|
    | ``client.users.loans`` | [`AlmaClientUserLoansNS`][almapy._users.AlmaClientUserLoansNS] |
    | ``client.users.fines`` / ``.fees`` | [`AlmaClientUserFinesNS`][almapy._users.AlmaClientUserFinesNS] |
    | ``client.users.requests`` | [`AlmaClientUserRequestsNS`][almapy._users.AlmaClientUserRequestsNS] |
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
        """Search for users.

        Args:
            limit: Maximum number of users to return in this page. Note the default
                here is 10, not 100.
            offset: Index of the first user to return, for paging.
            q: Search query, in Alma's ``field~value`` form, e.g. ``"last_name~Smith"``
                or ``"ALL~Smith"`` to search every indexed field. Every user is
                returned when omitted.
            order_by: Field to sort the results by.
            expand: When True, requests Alma's ``full`` view, which adds each user's
                fees and loans to the response. This costs Alma noticeably more work
                per user, so leave it off for plain searches.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            A page of users, with ``total_record_count`` giving the full result size.

        Raises:
            APIClientError: If the query is malformed or names an unindexed field.

        Examples:
            ```python
            page = await client.users.get_users(
                q="last_name~Smith", limit=100, order_by="last_name"
            )
            for user in page.user:
                print(user.primary_id, user.last_name)
            ```
        """
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
        """Retrieve a single user record.

        Args:
            user_id: The user identifier.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The user record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If another error occurred while making the API request.

        Examples:
            ```python
            user = await client.users.get_user("12345678")
            print(user.first_name, user.last_name, user.user_group.desc)
            ```
        """
        return await self._get(AlmaEndpoint.USER, {"USER_ID": user_id}, model=model)

    @overload
    async def update_user(self, user_id: str, user: Body, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def update_user(self, user_id: str, user: Body, *, model: None = ...) -> RESP_TYPE: ...

    async def update_user(self, user_id: str, user: Body, *, model: Any = None) -> Any:
        """Update a user record.

        Alma replaces the whole user, so fetch it with
        [`get_user`][almapy._users.AlmaClientUserNS.get_user] and modify that — a
        partial body drops the fields it omits, including roles and addresses.

        Args:
            user_id: The identifier of the user to update.
            user: The full, modified user record. Accepts a mapping or any object
                implementing ``dump``/``model_dump``, so a Pydantic model can be
                passed directly.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The updated user record.

        Raises:
            UserMissingFieldError: If a mandatory field is missing (Alma code
                ``401664``). The exception carries the user ID.
            InvalidFieldError: If a field — often a role — is not valid.
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If any other API client error occurs.

        Examples:
            ```python
            user = await client.users.get_user("12345678")
            user.contact_info.email[0].email_address = "new@example.ac.uk"
            await client.users.update_user("12345678", user)
            ```
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
    async def create_user(self, user: Body, *, model: type[_ModelT]) -> _ModelT: ...

    @overload
    async def create_user(self, user: Body, *, model: None = ...) -> RESP_TYPE: ...

    async def create_user(self, user: Body, *, model: Any = None) -> Any:
        """Create a new user.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could create a duplicate user. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user: The user record to create. Alma requires at least a
                ``primary_id``, ``last_name``, ``user_group``, ``account_type`` and
                ``status``. Accepts a mapping or any object implementing
                ``dump``/``model_dump``.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created user record.

        Raises:
            UserMissingFieldError: If a mandatory field is missing (Alma code
                ``401664``). The exception carries the ``primary_id`` from the body.
            InvalidFieldError: If a field — often a role — is not valid.
            APIClientError: If any other API client error occurs.

        Examples:
            ```python
            user = await client.users.create_user(
                {
                    "primary_id": "new.user@example.ac.uk",
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "user_group": {"value": "STAFF"},
                    "account_type": {"value": "INTERNAL"},
                    "status": {"value": "ACTIVE"},
                }
            )
            ```
        """
        try:
            resp: Any = await self._post(AlmaEndpoint.USERS, model=model, json=user)
        except APIClientError as e:
            if e.code == "401664":
                body = _dump_body(user)
                raise UserMissingFieldError(e.error, body.get("primary_id", "")) from e
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
        """Attach a file to a user's record.

        ``content`` is base64-encoded for you before it is sent — pass the plain
        text, not an already-encoded string. Note that it is typed as ``str`` and
        encoded as UTF-8, so this method handles text attachments only; binary files
        are not supported.

        Being a POST, this call is **not replayed** if the response is lost in
        transit — a retry could attach the file twice. See
        [Rate limiting](../guide/rate-limiting.md).

        Args:
            user_id: The user identifier.
            file_name: Name to store the attachment under, including its extension.
            content: The file's text content, unencoded.
            note: Free-text note recorded against the attachment.
            description: Human-readable description shown in Alma.
            url: External URL for the attachment, as an alternative to inline content.
            model: Optional Pydantic model class to validate the response into.

        Returns:
            The newly created attachment record.

        Raises:
            UserNotFoundError: If no user matches the identifier.
            APIClientError: If the attachment is rejected — for example when it
                exceeds Alma's size limit.

        Examples:
            ```python
            attachment = await client.users.create_user_attachment(
                "12345678",
                "proof_of_address.txt",
                "Utility bill received 2026-07-01",
                description="Address verification",
            )
            ```
        """
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
